import random
import operator

from Edge_Entities.Link import Link
from Simulation_Entities.VNF_Instance import VNF_Instance
from beautifultable import BeautifulTable
from collections import defaultdict

from Placement.SfcPriority import SfcPriority

from Placement.Placement import Placement


class SmartPlacement(Placement):

    def __init__(self, environment, sfc_instance_sharable):
        """This is the proposed dynamic heuristic placement, which is based on energy, computational resource and
        latency and takes into account the arrival of SFC Requests over time.

        Args:
            environment (Edge_Environment): The Edge environment with all the entities that will be used
            sfc_instance_sharable (bool): If the Placement will share or not the SFC_Instance
            G (NetworkX graph): The graph of edge nodes related to an SFC Request

        Returns:
            [set]: The vnf_instances plan that define where instance hosted in the node will execute the VNF os each SFC
        """
        Placement.__init__(self, environment)

        self.environment = environment
        self.vnf_instances = environment.vnf_instances
        self.sfc_instance_sharable = sfc_instance_sharable
        self.G = None
        self.sd = None
        self.time = None

    def execute(self, sfc_requests, sd, time, file_path=""):
        """ Executes the online-based placement (over time)

        Args:
            sfc_requests (list): SFC_Requests that must be placed
            sd (Simulation_Data): Simulation Data
            time (int): Simulation Time
            file_path (str): The path to the generated graph image
        """
        self.sd = sd
        self.time = time

        # For each request
        for aux_req in sfc_requests:

            # Only share the sfc_instance if the simulation allows
            if self.sfc_instance_sharable:

                # Verify if there is any SFC Instance that can handle the SFC Request
                sfc_instance_mapped = False
                for sfc_instance in self.environment.sfc_instances:

                    if aux_req.sfc.name == sfc_instance.sfc.name and sfc_instance.is_unlocked() and sfc_instance.ingress_node.name == aux_req.ingress_node.name and sfc_instance.egress_node.name == aux_req.egress_node.name:
                        sfc_instance.add_sfc_request(aux_req)
                        sfc_instance_mapped = True
                        aux_req.placed = True
                        aux_req.sfc_instance = sfc_instance
                        #aux_req.user_node_when_placed = aux_req.user.node
                        continue

                # If the SFC_Request already had an SFC_Instance that can handle it, thus, continue to the next SFC_Request
                if sfc_instance_mapped:
                    continue

            # create the SFC_Instance in the environment
            sfc_instance = self.environment.create_sfc_instance(
                sfc_request=aux_req,
                slice=1
            )

            # associate the SFC Request with the SFC Instance created
            aux_req.sfc_instance = sfc_instance

            # Get the graph of the VNF Placement plan, the weight of the edge was propagation
            self.G = self.create_graph(
                sfc_request=aux_req,
                link_metric_edge_weight="propagation",
                file_path=file_path,
            )

            all_vnf_placed = True
            vnf_instances_created = []
            vnf_instances_mapped  = []

            # For each VNF in the SFC
            for vnf_name in aux_req.sfc.vnfs:

                current_vnf = self.environment.vnfs[vnf_name]

                # Verify if there is an instance that can be used to handle this VNF
                current_vnf_instance = self.add_vnf_request_to_existing_vnf_instance(current_vnf, aux_req, sfc_instance)

                if not current_vnf_instance: #TODO: in this case the placement can fail due link outage. should we try to create a new instance?
                    # Try to place a new VNF instance
                    placement_result, current_vnf_instance = self.place_new_instance(current_vnf, aux_req, sfc_instance)
                    vnf_instances_created.append(current_vnf_instance)
                    if not placement_result:
                        all_vnf_placed = False
                        break
                    else:
                        vnf_instances_mapped.append(current_vnf_instance)
                else:
                    vnf_instances_mapped.append(current_vnf_instance)

            if all_vnf_placed:

                aux_req.placed = True
                #aux_req.user_node_when_placed = aux_req.user.node

                # Log creation event
                sd.add_sfc_instance_event(
                    event=sd.EVENT_SFC_INSTANCE_CREATED,
                    time=time,
                    sfc_instance=sfc_instance
                )

                # Registering VNF Instances creation events
                for current_vnf_instance in vnf_instances_created:
                    # log creation event
                    sd.add_vnf_instance_event(
                        event=sd.EVENT_INSTANCE_CREATED,
                        time=time,
                        vnf_instance=current_vnf_instance
                    )

                # Registering VNF Instances mapped events
                for current_vnf_instance in vnf_instances_mapped:
                    # log sfc instance mapped into vnf instance if the link was successfully created
                    self.sd.add_sfc_instance_vnf_mapping_event(
                        event=self.sd.EVENT_SFC_INSTANCE_VNF_MAPPED,
                        time=self.time,
                        sfc_instance=sfc_instance,
                        vnf_instance=current_vnf_instance
                    )

                # Create the image with the edges and nodes painted
                if file_path:
                    self.save_image_placed_plan(sfc_instance, file_path)

            else:
                aux_req.placed = False
                aux_req.sfc_instance = None

                self.environment.remove_sfc_instance(sfc_instance)

                # Remove the created instances for this SFC_request
                for vnf_instance in vnf_instances_created:
                    if vnf_instance:
                        self.vnf_instances.remove(vnf_instance)

        return self.vnf_instances

    # Phase 1 – exploiting already-placed VNF vnf_instances
    def add_vnf_request_to_existing_vnf_instance(self, current_vnf, sfc_request, sfc_instance):

        ################# Specific attributes for Phase 1        
        previous_vnf_instance = None
        available_vnf_instances_list_for_current_vnf = self.get_available_vnf_instances_for_current_vnf(
            self.vnf_instances, current_vnf)
        #################

        ################# Common attributes for Phases 1 and 2
        vnf_instance = None
        priorities_order = self.environment.sfcs[sfc_request.sfc.name].priorities_order
        user = sfc_request.user
        sfc = sfc_request.sfc
        sfc_flow_info = user.sfc_ingress_egress[sfc.name]
        previous_vnf_instance = None
        result = False

        if sfc.vnfs[0] == current_vnf.name:
            node_source = sfc_request.ingress_node.name
            packet_size = sfc_flow_info['packet_size']
        else:
            previous_vnf_instance = self.get_previous_vnf_instance(current_vnf, user, sfc_request)
            node_source = previous_vnf_instance.node.name
            packet_size = self.environment.vnfs[previous_vnf_instance.vnf.name].packet_network_demand
        ################

        if priorities_order[0] == SfcPriority.latency:

            available_instances_with_shortest_latency = \
                self.get_available_instances_with_shortest_latency(available_vnf_instances_list_for_current_vnf,
                                                                   node_source, packet_size)

            if len(available_instances_with_shortest_latency) == 1:
                vnf_instance = available_instances_with_shortest_latency[0]
                result = self.map_vnf_instance(vnf_instance, current_vnf, sfc_request, sfc_instance, node_source, previous_vnf_instance)

            elif len(available_instances_with_shortest_latency) > 1:
                # Multiple VNF vnf_instances with shortest latency were selected
                if priorities_order[1] == SfcPriority.capacity:
                    # SFC Priority: latency > capacity > energy
                    hightest_capacity_instances_among_shortest_latency = \
                        self.get_available_instances_with_highest_capacity(available_instances_with_shortest_latency)
                    if len(hightest_capacity_instances_among_shortest_latency) == 1:
                        vnf_instance = hightest_capacity_instances_among_shortest_latency[0]
                        result = self.map_vnf_instance(vnf_instance, current_vnf, sfc_request, sfc_instance, node_source, previous_vnf_instance)

                    elif len(hightest_capacity_instances_among_shortest_latency) > 1:
                        # Multiple VNF vnf_instances with the hightest capacity were selected
                        hightest_energy_instances_among_hightest_capacity = \
                            self.get_available_instances_with_min_consumed_energy \
                                (hightest_capacity_instances_among_shortest_latency,
                                 previous_vnf_instance, packet_size, node_source)
                        if len(hightest_energy_instances_among_hightest_capacity) >= 1:
                            vnf_instance = random.choice(hightest_energy_instances_among_hightest_capacity)
                            result = self.map_vnf_instance(vnf_instance, current_vnf, sfc_request, sfc_instance, node_source, previous_vnf_instance)
                else:
                    # SFC Priority: latency > energy > capacity
                    hightest_energy_instances_among_shortest_latency = \
                        self.get_available_instances_with_min_consumed_energy(available_instances_with_shortest_latency,
                                                                              previous_vnf_instance, packet_size,
                                                                              node_source)
                    if len(hightest_energy_instances_among_shortest_latency) == 1:
                        vnf_instance = hightest_energy_instances_among_shortest_latency[0]
                        result = self.map_vnf_instance(vnf_instance, current_vnf, sfc_request, sfc_instance, node_source, previous_vnf_instance)

                    elif len(hightest_energy_instances_among_shortest_latency) > 1:
                        # Multiple VNF vnf_instances with the hightest energy were selected
                        hightest_capacity_instances_among_hightest_energy = \
                            self.get_available_instances_with_highest_capacity \
                                (hightest_energy_instances_among_shortest_latency)
                        if len(hightest_capacity_instances_among_hightest_energy) >= 1:
                            vnf_instance = random.choice(hightest_capacity_instances_among_hightest_energy)
                            result = self.map_vnf_instance(vnf_instance, current_vnf, sfc_request, sfc_instance, node_source, previous_vnf_instance)

        elif priorities_order[0] == SfcPriority.capacity:

            available_instances_with_hightest_capacity = \
                self.get_available_instances_with_highest_capacity(available_vnf_instances_list_for_current_vnf)
            if len(available_instances_with_hightest_capacity) == 1:
                vnf_instance = available_instances_with_hightest_capacity[0]
                result = self.map_vnf_instance(vnf_instance, current_vnf, sfc_request, sfc_instance, node_source, previous_vnf_instance)

            elif len(available_instances_with_hightest_capacity) > 1:
                # Multiple VNF vnf_instances with hightest capacity were selected
                if priorities_order[1] == SfcPriority.latency:
                    # SFC Priority: capacity > latency > energy
                    shortest_latency_instances_among_hightest_capacity = \
                        self.get_available_instances_with_shortest_latency(available_instances_with_hightest_capacity,
                                                                           node_source, packet_size)
                    if len(shortest_latency_instances_among_hightest_capacity) == 1:
                        vnf_instance = shortest_latency_instances_among_hightest_capacity[0]
                        result = self.map_vnf_instance(vnf_instance, current_vnf, sfc_request, sfc_instance, node_source, previous_vnf_instance)

                    elif len(shortest_latency_instances_among_hightest_capacity) > 1:
                        # Multiple VNF vnf_instances with the shortest latency were selected
                        hightest_energy_instances_among_shortest_latency = \
                            self.get_available_instances_with_min_consumed_energy \
                                (shortest_latency_instances_among_hightest_capacity,
                                 previous_vnf_instance, packet_size, node_source)
                        if len(shortest_latency_instances_among_hightest_capacity) >= 1:
                            vnf_instance = random.choice(shortest_latency_instances_among_hightest_capacity)
                            result = self.map_vnf_instance(vnf_instance, current_vnf, sfc_request, sfc_instance, node_source, previous_vnf_instance)

                else:
                    # SFC Priority: capacity > energy > latency
                    hightest_energy_instances_among_hightest_capacity = \
                        self.get_available_instances_with_min_consumed_energy(
                            available_instances_with_hightest_capacity,
                            previous_vnf_instance, packet_size, node_source)
                    if len(hightest_energy_instances_among_hightest_capacity) == 1:
                        vnf_instance = hightest_energy_instances_among_hightest_capacity[0]
                        result = self.map_vnf_instance(vnf_instance, current_vnf, sfc_request, sfc_instance, node_source, previous_vnf_instance)

                    elif len(hightest_energy_instances_among_hightest_capacity) > 1:
                        # Multiple VNF vnf_instances with the hightest energy were selected
                        shortest_latency_instances_among_hightest_energy = \
                            self.get_available_instances_with_shortest_latency \
                                (hightest_energy_instances_among_hightest_capacity, node_source, packet_size)
                        if len(shortest_latency_instances_among_hightest_energy) >= 1:
                            vnf_instance = random.choice(shortest_latency_instances_among_hightest_energy)
                            result = self.map_vnf_instance(vnf_instance, current_vnf, sfc_request, sfc_instance, node_source, previous_vnf_instance)

        elif priorities_order[0] == SfcPriority.energy:

            available_instances_with_hightest_energy = self. \
                get_available_instances_with_min_consumed_energy(available_vnf_instances_list_for_current_vnf,
                                                                 previous_vnf_instance,
                                                                 packet_size, node_source)
            if len(available_instances_with_hightest_energy) == 1:
                vnf_instance = available_instances_with_hightest_energy[0]
                result = self.map_vnf_instance(vnf_instance, current_vnf, sfc_request, sfc_instance, node_source, previous_vnf_instance)

            elif len(available_instances_with_hightest_energy) > 1:
                # Multiple VNF vnf_instances with hightest energy were selected
                if priorities_order[1] == SfcPriority.latency:
                    # SFC Priority: energy > latency > capacity
                    shortest_latency_instances_among_hightest_energy = \
                        self.get_available_instances_with_shortest_latency(available_instances_with_hightest_energy,
                                                                           node_source, packet_size)
                    if len(shortest_latency_instances_among_hightest_energy) == 1:
                        vnf_instance = shortest_latency_instances_among_hightest_energy[0]
                        result = self.map_vnf_instance(vnf_instance, current_vnf, sfc_request, sfc_instance, node_source, previous_vnf_instance)

                    elif len(shortest_latency_instances_among_hightest_energy) > 1:
                        # Multiple VNF vnf_instances with the shortest latency were selected
                        hightest_capacity_instances_among_shortest_latency = \
                            self.get_available_instances_with_highest_capacity \
                                (shortest_latency_instances_among_hightest_energy)
                        if len(hightest_capacity_instances_among_shortest_latency) >= 1:
                            vnf_instance = random.choice(hightest_capacity_instances_among_shortest_latency)
                            result = self.map_vnf_instance(vnf_instance, current_vnf, sfc_request, sfc_instance, node_source, previous_vnf_instance)

                else:
                    # SFC Priority: energy > capacity > latency
                    hightest_capacity_instances_among_hightest_energy = \
                        self.get_available_instances_with_highest_capacity(available_instances_with_hightest_energy)
                    if len(hightest_capacity_instances_among_hightest_energy) == 1:
                        vnf_instance = hightest_capacity_instances_among_hightest_energy[0]
                        result = self.map_vnf_instance(vnf_instance, current_vnf, sfc_request, sfc_instance, node_source, previous_vnf_instance)

                    elif len(hightest_capacity_instances_among_hightest_energy) > 1:
                        # Multiple VNF vnf_instances with the hightest capacity were selected
                        shortest_latency_instances_among_hightest_capacity = \
                            self.get_available_instances_with_shortest_latency \
                                (hightest_capacity_instances_among_hightest_energy,
                                 node_source, packet_size)
                        if len(shortest_latency_instances_among_hightest_capacity) >= 1:
                            vnf_instance = random.choice(shortest_latency_instances_among_hightest_capacity)
                            result = self.map_vnf_instance(vnf_instance, current_vnf, sfc_request, sfc_instance, node_source, previous_vnf_instance)

        return result

    # Phase 2 – new VNF vnf_instances must to be created to attend the current request
    def place_new_instance(self, current_vnf, sfc_request, sfc_instance):

        ################# Specific attributes for Phase 2
        candidate_nodes = self.environment.get_nodes_vnf(current_vnf.name)
        nodes_candidate = []
        for candidate in candidate_nodes:
            available_resource = self.environment.get_node_available_resource(self.vnf_instances, candidate.name)
            if available_resource['cpu'] >= current_vnf.cpu and available_resource['mem'] >= current_vnf.mem:
                nodes_candidate.append(candidate)
        #################

        # There are not nodes available for the requested VNF
        if len(nodes_candidate) == 0:
            return None, None

        ################# Common attributes for Phases 1 and 2
        vnf_instance = None
        priorities_order = self.environment.sfcs[sfc_request.sfc.name].priorities_order
        user = sfc_request.user
        sfc = sfc_request.sfc
        sfc_flow_info = user.sfc_ingress_egress[sfc.name]
        previous_vnf_instance = None

        if sfc.vnfs[0] == current_vnf.name:
            node_source = sfc_request.ingress_node.name
            packet_size = sfc_flow_info['packet_size']
        else:
            previous_vnf_instance = self.get_previous_vnf_instance(current_vnf, user, sfc_request)
            node_source = previous_vnf_instance.node.name
            packet_size = self.environment.vnfs[previous_vnf_instance.vnf.name].packet_network_demand
        ################

        if priorities_order[0] == SfcPriority.latency:
            nodes_with_shortest_latency = \
                self.get_nodes_with_shortest_latency(nodes_candidate, node_source, packet_size)

            if len(nodes_with_shortest_latency) == 1:
                node_selected = nodes_with_shortest_latency[0]
                placement_result, vnf_instance = self.create_new_vnf_instance(current_vnf, sfc_request, sfc_instance, node_selected, node_source, previous_vnf_instance)

            elif len(nodes_with_shortest_latency) > 1:
                # Multiple nodes with shortest latency were selected
                if priorities_order[1] == SfcPriority.capacity:
                    # SFC Priority: latency > capacity > energy
                    hightest_capacity_nodes_among_shortest_latency = \
                        self.get_nodes_with_highest_capacity(nodes_with_shortest_latency)
                    if len(hightest_capacity_nodes_among_shortest_latency) == 1:
                        node_selected = hightest_capacity_nodes_among_shortest_latency[0]
                        placement_result, vnf_instance = self.create_new_vnf_instance(current_vnf, sfc_request, sfc_instance, node_selected, node_source, previous_vnf_instance)

                    elif len(hightest_capacity_nodes_among_shortest_latency) > 1:
                        # Multiple nodes with the hightest capacity were selected
                        hightest_energy_nodes_among_hightest_capacity = \
                            self.get_nodes_with_min_consumed_energy \
                                (hightest_capacity_nodes_among_shortest_latency,
                                 node_source, packet_size, current_vnf)
                        if len(hightest_energy_nodes_among_hightest_capacity) >= 1:
                            node_selected = random.choice(hightest_energy_nodes_among_hightest_capacity)
                            placement_result, vnf_instance = self.create_new_vnf_instance(current_vnf, sfc_request, sfc_instance, node_selected, node_source, previous_vnf_instance)

                else:
                    # SFC Priority: latency > energy > capacity
                    hightest_energy_nodes_among_shortest_latency = \
                        self.get_nodes_with_min_consumed_energy(nodes_with_shortest_latency,
                                                                node_source, packet_size, current_vnf)
                    if len(hightest_energy_nodes_among_shortest_latency) == 1:
                        node_selected = hightest_energy_nodes_among_shortest_latency[0]
                        placement_result, vnf_instance = self.create_new_vnf_instance(current_vnf, sfc_request, sfc_instance, node_selected, node_source, previous_vnf_instance)
                    elif len(hightest_energy_nodes_among_shortest_latency) > 1:
                        # Multiple nodes with the hightest energy were selected
                        hightest_capacity_nodes_among_hightest_energy = \
                            self.get_nodes_with_highest_capacity \
                                (hightest_energy_nodes_among_shortest_latency)
                        if len(hightest_capacity_nodes_among_hightest_energy) >= 1:
                            node_selected = random.choice(hightest_capacity_nodes_among_hightest_energy)
                            placement_result, vnf_instance = self.create_new_vnf_instance(current_vnf, sfc_request, sfc_instance, node_selected, node_source, previous_vnf_instance)
                        else:
                            print("1")
                    else:
                        print("2")
            else:
                print("3")

        elif priorities_order[0] == SfcPriority.capacity:
            nodes_with_hightest_capacity = \
                self.get_nodes_with_highest_capacity(nodes_candidate)

            if len(nodes_with_hightest_capacity) == 0:
                return None, None

            if len(nodes_with_hightest_capacity) == 1:
                node_selected = nodes_with_hightest_capacity[0]
                placement_result, vnf_instance = self.create_new_vnf_instance(current_vnf, sfc_request, sfc_instance, node_selected, node_source, previous_vnf_instance)

            elif len(nodes_with_hightest_capacity) > 1:
                # Multiple nodes with hightest capacity were selected
                if priorities_order[1] == SfcPriority.latency:
                    # SFC Priority: capacity > latency > energy
                    shortest_latency_nodes_among_hightest_capacity = \
                        self.get_nodes_with_shortest_latency(nodes_with_hightest_capacity, node_source, packet_size)
                    if len(shortest_latency_nodes_among_hightest_capacity) == 1:
                        node_selected = shortest_latency_nodes_among_hightest_capacity[0]
                        placement_result, vnf_instance = self.create_new_vnf_instance(current_vnf, sfc_request, sfc_instance, node_selected, node_source, previous_vnf_instance)

                    elif len(shortest_latency_nodes_among_hightest_capacity) > 1:
                        # Multiple nodes with the shortest latency were selected
                        hightest_energy_nodes_among_shortest_latency = \
                            self.get_nodes_with_min_consumed_energy \
                                (shortest_latency_nodes_among_hightest_capacity,
                                 node_source, packet_size, current_vnf)
                        if len(shortest_latency_nodes_among_hightest_capacity) >= 1:
                            node_selected = random.choice(shortest_latency_nodes_among_hightest_capacity)
                            placement_result, vnf_instance = self.create_new_vnf_instance(current_vnf, sfc_request, sfc_instance, node_selected, node_source, previous_vnf_instance)

                else:
                    # SFC Priority: capacity > energy > latency
                    hightest_energy_nodes_among_hightest_capacity = \
                        self.get_nodes_with_min_consumed_energy(nodes_with_hightest_capacity,
                                                                node_source, packet_size, current_vnf)
                    if len(hightest_energy_nodes_among_hightest_capacity) == 1:
                        node_selected = hightest_energy_nodes_among_hightest_capacity[0]
                        placement_result, vnf_instance = self.create_new_vnf_instance(current_vnf, sfc_request, sfc_instance, node_selected, node_source, previous_vnf_instance)

                    elif len(hightest_energy_nodes_among_hightest_capacity) > 1:
                        # Multiple nodes with the hightest energy were selected
                        shortest_latency_nodes_among_hightest_energy = \
                            self.get_nodes_with_shortest_latency \
                                (hightest_energy_nodes_among_hightest_capacity, node_source, packet_size)
                        if len(shortest_latency_nodes_among_hightest_energy) >= 1:
                            node_selected = random.choice(shortest_latency_nodes_among_hightest_energy)
                            placement_result, vnf_instance = self.create_new_vnf_instance(current_vnf, sfc_request, sfc_instance, node_selected, node_source, previous_vnf_instance)

        elif priorities_order[0] == SfcPriority.energy:
            nodes_with_hightest_energy = self. \
                get_nodes_with_min_consumed_energy(nodes_candidate, node_source, packet_size, current_vnf)
            if len(nodes_with_hightest_energy) == 1:
                node_selected = nodes_with_hightest_energy[0]
                placement_result, vnf_instance = self.create_new_vnf_instance(current_vnf, sfc_request, sfc_instance, node_selected, node_source, previous_vnf_instance)

            elif len(nodes_with_hightest_energy) > 1:
                # Multiple nodes with hightest energy were selected
                if priorities_order[1] == SfcPriority.latency:
                    # SFC Priority: energy > latency > capacity
                    shortest_latency_nodes_among_hightest_energy = \
                        self.get_nodes_with_shortest_latency(nodes_with_hightest_energy, node_source, packet_size)
                    if len(shortest_latency_nodes_among_hightest_energy) == 1:
                        node_selected = shortest_latency_nodes_among_hightest_energy[0]
                        placement_result, vnf_instance = self.create_new_vnf_instance(current_vnf, sfc_request, sfc_instance, node_selected, node_source, previous_vnf_instance)

                    elif len(shortest_latency_nodes_among_hightest_energy) > 1:
                        # Multiple nodes with the shortest latency were selected
                        hightest_capacity_nodes_among_shortest_latency = \
                            self.get_nodes_with_highest_capacity \
                                (shortest_latency_nodes_among_hightest_energy)
                        if len(hightest_capacity_nodes_among_shortest_latency) >= 1:
                            node_selected = random.choice(hightest_capacity_nodes_among_shortest_latency)
                            placement_result, vnf_instance = self.create_new_vnf_instance(current_vnf, sfc_request, sfc_instance, node_selected, node_source, previous_vnf_instance)

                else:
                    # SFC Priority: energy > capacity > latency
                    hightest_capacity_nodes_among_hightest_energy = \
                        self.get_nodes_with_highest_capacity(nodes_with_hightest_energy)
                    if len(hightest_capacity_nodes_among_hightest_energy) == 1:
                        node_selected = hightest_capacity_nodes_among_hightest_energy[0]
                        placement_result, vnf_instance = self.create_new_vnf_instance(current_vnf, sfc_request, sfc_instance, node_selected, node_source, previous_vnf_instance)

                    elif len(hightest_capacity_nodes_among_hightest_energy) > 1:
                        # Multiple nodes with the hightest capacity were selected
                        shortest_latency_nodes_among_hightest_capacity = \
                            self.get_nodes_with_shortest_latency \
                                (hightest_capacity_nodes_among_hightest_energy, node_source, packet_size)
                        if len(shortest_latency_nodes_among_hightest_capacity) >= 1:
                            node_selected = random.choice(shortest_latency_nodes_among_hightest_capacity)
                            placement_result, vnf_instance = self.create_new_vnf_instance(current_vnf, sfc_request, sfc_instance, node_selected, node_source, previous_vnf_instance)

        # print(current_vnf, sfc_request, sfc_instance)
        # sfc_request.show()
        return placement_result, vnf_instance

    def create_vnf_links(self, current_vnf, sfc_request, node_selected, node_source, previous_vnf_instance):

        if sfc_request.sfc.vnfs[0] == current_vnf.name:  # if is the first vnf, add a link from ingress node
            # # Get links from the ingress node to the node that has the first vnf
            node_name = "ingress_{}".format(sfc_request.ingress_node.name)
            vnf_name = "ingress"
        else:  # for others vnfs consider the previous node
            node_name = "{}_{}".format(node_source, previous_vnf_instance.vnf.name)
            vnf_name = previous_vnf_instance.vnf.name

        node_selected_name = node_selected.name
        edges = self.G.out_edges(node_name, data=True)
        local_links = self.get_links_between_nodes_from_edges(edges, node_name, node_selected_name)

        link = ""
        for aux_link in local_links:
            bw_available = self.environment.calc_bw_available_link(aux_link)
            if bw_available <= 0 and self.compute_link_bw_limit:
                continue
            else:
                link = aux_link
                break

        if link == "": #TODO: verify if we can return at this point or if we still need to set vnf link
            return False

        sfc_request.sfc_instance.set_vnf_link(
            vnf_name=vnf_name,
            link_name=link
        )

        if sfc_request.sfc.vnfs[-1] == current_vnf.name:  # if is the last vnf, add the last link to the egress node

            vnf_name = current_vnf.name
            node_name = "{}_{}".format(node_selected.name, current_vnf.name)
            node_selected_name = sfc_request.egress_node.name

            edges = self.G.out_edges(node_name, data=True)
            local_links = self.get_links_between_nodes_from_edges(edges, node_name, node_selected_name)

            link = ""
            for aux_link in local_links:
                bw_available = self.environment.calc_bw_available_link(aux_link)
                if bw_available <= 0 and self.compute_link_bw_limit:
                    continue
                else:
                    link = aux_link
                    break

            if link == "":
                return False

            sfc_request.sfc_instance.set_vnf_link(
                vnf_name=vnf_name,
                link_name=link
            )

        return True

    def map_vnf_instance(self, vnf_instance, current_vnf, sfc_request, sfc_instance, node_source, previous_vnf_instance):
        vnf_instance.add_sfc_instance(sfc_instance.name)

        result = self.create_vnf_links(current_vnf, sfc_request, vnf_instance.node, node_source, previous_vnf_instance)

        # if result:
        #     # log sfc instance mapped into vnf instance if the link was successfully created
        #     self.sd.add_sfc_instance_vnf_mapping_event(
        #         event=self.sd.EVENT_SFC_INSTANCE_VNF_MAPPED,
        #         time=self.time,
        #         sfc_instance=sfc_request.sfc_instance,
        #         vnf_instance=vnf_instance
        #     )
        if not result:
            vnf_instance = None

        return vnf_instance

    def get_previous_vnf_instance(self, current_vnf, user, sfc_request):
        for i in range(len(sfc_request.sfc.vnfs)):
            if sfc_request.sfc.vnfs[i] == current_vnf.name:
                previous_vnf = sfc_request.sfc.vnfs[i - 1]
                break

        for aux_vnf_instance in self.vnf_instances:
            if aux_vnf_instance.vnf.name == previous_vnf and sfc_request.sfc_instance.name in aux_vnf_instance.sfc_instances:
                return aux_vnf_instance

    def sort_sfc_name_list_by_latency(self, list_sfc_names):
        sorted_sfc_name_list_by_latency = []
        name_latency_dic_by_latency = {}
        for sfc_name in list_sfc_names:
            current_sfc = self.environment.sfcs[sfc_name]
            name_latency_dic_by_latency[sfc_name] = current_sfc.max_latency
        sorted_tuples = sorted(name_latency_dic_by_latency.items(), key=operator.itemgetter(1))
        sorted_name_latency_dic_by_latency = {k: v for k, v in sorted_tuples}

        for sfc_name in sorted_name_latency_dic_by_latency:
            sorted_sfc_name_list_by_latency.append(sfc_name)

        return sorted_sfc_name_list_by_latency

    def get_available_vnf_instances_for_current_vnf(self, vnf_instances, current_vnf):

        available_vnf_instances_for_current_vnf = []
        for instance in vnf_instances:
            if instance.vnf.name == current_vnf.name \
                    and len(instance.sfc_instances) < self.environment.vnfs[current_vnf.name].max_share \
                    and instance.accept_sfc_instances:
                available_vnf_instances_for_current_vnf.append(instance)

        return available_vnf_instances_for_current_vnf

    def get_available_instances_with_shortest_latency(self, instances_list, node_source, packet_size):

        min_latency = -1
        available_instances_with_shortest_latency = []
        for instance in instances_list:
            # for link in self.environment.links:
            #   link_object = self.environment.links[link]
            links = Link.get_links_between_nodes(self.environment.links, node_source, instance.node.name)
            for link_object in links:
                # if link_object.source == node_source and link_object.target == instance.node.name:
                if link_object.target == instance.node.name:
                    aux_latency = link_object.get_latency(packet_size)
                    if min_latency == -1 or aux_latency < min_latency:
                        min_latency = aux_latency
                        available_instances_with_shortest_latency.clear()
                        available_instances_with_shortest_latency.append(instance)
                    if aux_latency == min_latency:
                        available_instances_with_shortest_latency.append(instance)

        return available_instances_with_shortest_latency

    def get_available_instances_with_highest_capacity(self, instances_list):

        hightest_capacity = 0
        available_instances_with_hightest_capacity = []
        for instance in instances_list:

            # current available capacity of the node in which the current instance is hosted.
            current_capacity = self.get_node_available_cpu_capacity(instances_list, instance.node) + \
                               self.get_node_available_mem_capacity(instances_list, instance.node)
            if current_capacity > hightest_capacity:
                hightest_capacity = current_capacity
                available_instances_with_hightest_capacity.clear()
                available_instances_with_hightest_capacity.append(instance)
            if current_capacity == hightest_capacity:
                available_instances_with_hightest_capacity.append(instance)

        return available_instances_with_hightest_capacity

    def get_available_instances_with_min_consumed_energy(self, instances_list, previous_instance,
                                                         packet_size, node_source):

        min_energy = -1
        available_instances_with_min_consumed_energy = []
        for instance in instances_list:

            # current available energy of the node in which the current instance is hosted plus
            # the available energy between the previous_node of the SFC and the current
            # instance node to be selected.
            current_energy = self.get_node_consumed_energy_from_instance \
                (instance, previous_instance, packet_size, node_source)
            if min_energy == -1 or current_energy < min_energy:
                min_energy = current_energy
                available_instances_with_min_consumed_energy.clear()
                available_instances_with_min_consumed_energy.append(instance)
            elif current_energy == min_energy:
                available_instances_with_min_consumed_energy.append(instance)

        return available_instances_with_min_consumed_energy

    def get_nodes_with_shortest_latency(self, nodes_candidate, node_source, packet_size):

        min_latency = -1
        nodes_with_shortest_latency = []
        for node_candidate in nodes_candidate:
            links = Link.get_links_between_nodes(self.environment.links, node_source, node_candidate.name)
            for link in links:
                aux_latency = link.get_latency(packet_size)
                if min_latency == -1 or aux_latency < min_latency:
                    min_latency = aux_latency
                    nodes_with_shortest_latency.clear()
                    nodes_with_shortest_latency.append(node_candidate)
                elif aux_latency == min_latency:
                    nodes_with_shortest_latency.append(node_candidate)

        return nodes_with_shortest_latency

    def get_nodes_with_highest_capacity(self, nodes_with_shortest_latency):

        hightest_capacity = 0
        nodes_with_hightest_capacity = []
        for node_candidate in nodes_with_shortest_latency:

            # current available capacity of the candidate node.
            current_capacity = self.get_node_available_cpu_capacity(self.vnf_instances, node_candidate) + \
                               self.get_node_available_mem_capacity(self.vnf_instances, node_candidate)

            if current_capacity > hightest_capacity:
                hightest_capacity = current_capacity
                nodes_with_hightest_capacity.clear()
                nodes_with_hightest_capacity.append(node_candidate)
            elif current_capacity == hightest_capacity:
                nodes_with_hightest_capacity.append(node_candidate)

        return nodes_with_hightest_capacity

    def get_nodes_with_min_consumed_energy(self, hightest_capacity_nodes_among_shortest_latency,
                                           node_source, packet_size, current_vnf):

        min_energy = -1
        nodes_with_min_energy = []
        for node_candidate in hightest_capacity_nodes_among_shortest_latency:

            # current consumed energy of the candidate node plus
            # the link consumed energy between the previous_node of the SFC and the current
            # candidate node.
            current_energy = self.get_node_consumed_energy_from_node \
                (node_candidate, node_source, packet_size, current_vnf)

            if min_energy == -1 or current_energy < min_energy:
                min_energy = current_energy
                nodes_with_min_energy.clear()
                nodes_with_min_energy.append(node_candidate)
            elif current_energy == min_energy:
                nodes_with_min_energy.append(node_candidate)

        return nodes_with_min_energy

    def create_new_vnf_instance(self, current_vnf, sfc_request, sfc_instance, node_selected, node_source, previous_vnf_instance):

        name = self.create_unique_instance_name(node_selected.name, current_vnf.name)
        vnf_instance = VNF_Instance(name, current_vnf, current_vnf.cpu, current_vnf.mem, node_selected)
        vnf_instance.add_sfc_instance(sfc_instance.name)
        self.vnf_instances.append(vnf_instance)
        link_creation_result = self.create_vnf_links(current_vnf, sfc_request, node_selected, node_source, previous_vnf_instance)

        # if link_creation_result:
        #     # log sfc instance mapped into vnf instance
        #     self.sd.add_sfc_instance_vnf_mapping_event(
        #         event=self.sd.EVENT_SFC_INSTANCE_VNF_MAPPED,
        #         time=self.time,
        #         sfc_instance=sfc_instance,
        #         vnf_instance=vnf_instance
        #     )

        return link_creation_result, vnf_instance

    def get_node_consumed_energy_from_instance(self, instance, previous_vnf_instance, packet_size, node_source):

        energy_consumed_total = 0
        if previous_vnf_instance is None:
            previous_node = self.environment.nodes[node_source]
        else:
            previous_node = previous_vnf_instance.node

        node = instance.node
        links = Link.get_links_between_nodes(self.environment.links, previous_node.name, node.name)

        if previous_node.name != node.name:
            l = links[0]
            # l = self.environment.links[(previous_node.name, node.name)]
            energy_consumed_link = l.get_energy_consumed(packet_size)

            energy_consumed_processing = node.energy_idle + (
                    self.get_cpu_allocated(node, instance.vnf) * (node.energy_max - node.energy_idle))

            energy_consumed_total = energy_consumed_link + energy_consumed_processing

        return energy_consumed_total

    def get_node_consumed_energy_from_node(self, node_candidate, node_source, packet_size, current_vnf):

        energy_consumed_total = 0

        links = Link.get_links_between_nodes(self.environment.links, node_source, node_candidate.name)

        if node_source != node_candidate.name:
            l = links[0]
            energy_consumed_link = l.get_energy_consumed(packet_size)

            energy_consumed_processing = node_candidate.energy_idle + (
                    self.get_cpu_allocated(node_candidate, current_vnf) *
                    (node_candidate.energy_max - node_candidate.energy_idle))

            energy_consumed_total = energy_consumed_link + energy_consumed_processing

        return energy_consumed_total

    def get_cpu_allocated(self, node, vnf):

        resources = self.environment.get_node_available_resource(self.vnf_instances, node.name)

        return float("{:.2f}".format((node.cpu - resources['cpu']) / node.cpu))

    def get_node_available_cpu_capacity(self, instances_list, node):

        resources = self.environment.get_node_available_resource(instances_list, node.name)

        return resources['cpu']

    def get_node_available_mem_capacity(self, instances_list, node):

        resources = self.environment.get_node_available_resource(instances_list, node.name)

        return resources['mem']

    def show(self):
        print("Placement Plan")
        table = BeautifulTable()
        table.columns.header = ["Instance", "CPU", "Memory", "Node", "SFCs"]
        for aux in self.vnf_instances:
            table.rows.append([aux.name, aux.cpu, aux.mem, aux.node.name, aux.sfcs])

        print(table)
