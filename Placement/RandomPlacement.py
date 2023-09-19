import os
import sys
import random

from beautifultable import BeautifulTable

from Placement.Placement import Placement
from Simulation_Entities.VNF_Instance import VNF_Instance
from Edge_Environment import  Edge_Environment

class RandomPlacement(Placement):

    def __init__(self, environment, sfc_instance_sharable):
        """This is the naive placement where if there is already an instance deployed AND the number of attended
        SFC is lower then the max_share attribute than this VNF_Instance will attend the SFC

        Args:
            environment (Edge_Environment): The Edge environment with all the entities that will be used
            sfc_instance_sharable (bool): If the Placement will share or not the SFC_Instance

        Returns:
            [set]: The instances plan that define where instance hosted in the node will execute the VNF os each SFC
        """
        Placement.__init__(self, environment)
        self.environment = environment
        self.vnf_instances = environment.vnf_instances
        self.sfc_instance_sharable = sfc_instance_sharable

    # def set_instances(self, vnf_instances):
    #   """Define the instances that already are in execution in the infrastructure

    #   Args:
    #       vnf_instances (list): List with the VNF Instances
    #   """
    #   self.instances = vnf_instances
    @staticmethod
    def get_random_edge(edges):
        aux = []
        for edge in edges:
            source_node = edge[0]
            target_node = edge[1]
            link_data = edge[2]
            aux.append({
                'virtual_source_node': source_node,
                'virtual_target_node': target_node,
                'link_data': link_data
            })

        return random.choice(aux)

    def execute(self, sfc_requests, sd, time, file_path=""):
        """ Execute the placement for the Greedy heuristic. The node selected will be the
         node with more cpu available, the link selected will be the one with the small latency

    Args:
        sfc_requests (list): SFC_Requests that must be placed
        sd (Simulation_Data): Simulation Data
        time (int): Simulation Time
        file_path (str): The path where the file will be saved
    """

        # For each request make the
        for aux_req in sfc_requests:

            vnf_instances_created_for_request = []
            vnf_instances_mapped_for_request = []

            ingress_node_name = "ingress_{}".format(aux_req.ingress_node.name)
            egress_node_name = "egress_{}".format(aux_req.egress_node.name)

            # create the SFC_Instance in the environment
            sfc_instance = self.environment.create_sfc_instance(
                sfc_request=aux_req,
                slice=1
            )

            # Get the graph of the VNF Placement plan, the weight of the edge was propagation
            G = self.create_graph(
                sfc_request=aux_req,
                link_metric_edge_weight="propagation",
                file_path=file_path,
            )

            # All the edges from the ingress node
            node_name = ingress_node_name
            edges = G.out_edges(node_name, data=True)
            i = 0

            all_vnf_placed = True
            list_link_selected = []

            # When hit the egress node the out_edges will be null then the while ends
            while edges:

                # Search for the node with more cpu available
                checked_node = []
                for edge in edges:
                    node_name = edge[2]['target_node']

                    # For optimization only, not to test the same node more than one time
                    # because we have multiples links between two consecutive nodes
                    if node_name in checked_node:
                        continue

                    checked_node.append(node_name)

                selected_node_name = random.choice(checked_node)

                node_selected = self.environment.nodes[selected_node_name]

                if i < len(aux_req.sfc.vnfs):
                    aux_node_name = "{}_{}".format(selected_node_name, aux_req.sfc.vnfs[i])
                else:
                    aux_node_name = egress_node_name

                link_selected = ""
                ant_link_weight = sys.maxsize
                for edge in edges:
                    aux_link = edge[2]
                    if edge[1] == aux_node_name and (link_selected == "" or ant_link_weight > aux_link['weight']):
                        link_selected = aux_link['link_name']
                        ant_link_weight = aux_link['weight']

                list_link_selected.append((link_selected))

                if 0 <= i < len(aux_req.sfc.vnfs):
                    create_instance = True
                    vnf = aux_req.sfc.vnfs[i]
                    aux_vnf = self.environment.vnfs[vnf]

                    # # verify is there is a instance that can used to handle this SFC VNF
                    for instance in self.vnf_instances:
                        if instance.node.name == node_selected.name:
                            if instance.vnf.name == vnf:
                                if len(instance.sfc_instances) < aux_vnf.max_share:
                                    if instance.accept_sfc_instances:
                                        if instance.active:
                                            instance.add_sfc_instance(sfc_instance.name)
                                            vnf_instances_mapped_for_request.append(instance)
                                            create_instance = False
                                            continue

                    if create_instance:

                        # If there are no resources in the edge node selected than the request will fail
                        available_resource = self.environment.get_node_available_resource(self.vnf_instances, node_selected.name)

                        if available_resource['cpu'] < aux_vnf.cpu or available_resource['mem'] < aux_vnf.mem:
                            all_vnf_placed = False

                            # Debug
                            try:
                                if os.environ["NSS_DEBUG"] == "3":
                                    print("Resource outrage")
                                    print("---")
                                    aux_vnf.show()
                                    aux_req.show()
                                    node_selected.show()
                            except KeyError as ke:
                                pass

                        else:
                            # if there is resources
                            name = self.create_unique_instance_name(node_selected.name, vnf)
                            instance = VNF_Instance(name, aux_vnf, aux_vnf.cpu, aux_vnf.mem, node_selected)
                            # instance.add_sfc(aux_req.user.name, aux_req.sfc.name ,vnf)
                            instance.add_sfc_instance(sfc_instance.name)
                            self.vnf_instances.append(instance)
                            vnf_instances_created_for_request.append(instance)

                    # Debug
                    try:
                        if os.environ["NSS_DEBUG"] == "2":
                            print("------")
                            print(edges)
                            print("====")
                    except KeyError as ke:
                        pass

                edges = G.out_edges(aux_node_name, data=True)
                i = i + 1

            # Only add the event if all the instances of the map was created
            if all_vnf_placed:
                # set the link
                i = -1
                for link_name in list_link_selected:
                    if i == -1:
                        name = "ingress"
                    else:
                        name = aux_req.sfc.vnfs[i]

                    sfc_instance.set_vnf_link(
                        vnf_name=name,
                        link_name=link_name
                    )
                    i = i+1

                aux_req.placed = True
                aux_req.sfc_instance = sfc_instance
                #aux_req.user_node_when_placed = aux_req.user.node

                # Create the log that all the VNF Instances were created or mapped
                for vnf_instance in vnf_instances_created_for_request:
                    # log sfc instance mapped into vnf instance
                    sd.add_sfc_instance_vnf_mapping_event(
                        event=sd.EVENT_SFC_INSTANCE_VNF_MAPPED,
                        time=time,
                        sfc_instance=sfc_instance,
                        vnf_instance=vnf_instance
                    )

                    # log creation event
                    sd.add_vnf_instance_event(
                        event=sd.EVENT_INSTANCE_CREATED,
                        time=time,
                        vnf_instance=vnf_instance
                    )

                # log that the SFC Instance used some VNF Instance
                for vnf_instance in vnf_instances_mapped_for_request:
                    # log sfc instance mapped into vnf instance
                    sd.add_sfc_instance_vnf_mapping_event(
                        event=sd.EVENT_SFC_INSTANCE_VNF_MAPPED,
                        time=time,
                        sfc_instance=sfc_instance,
                        vnf_instance=vnf_instance
                    )

                # Log creation event
                sd.add_sfc_instance_event(
                    event=sd.EVENT_SFC_INSTANCE_CREATED,
                    time=time,
                    sfc_instance=sfc_instance
                )

                # Create the image with the edges and nodes painted
                if file_path:
                    self.save_image_placed_plan(sfc_instance, file_path)

            else:
                aux_req.placed = False

                # Remove the SFC_Instances for this SFC_request, it also remove the VNF Mapping with the
                # removed sfc_instance
                self.environment.remove_sfc_instance(sfc_instance)

                # Remove the created instances for this SFC_request
                for vnf_instance in vnf_instances_created_for_request:
                    self.vnf_instances.remove(vnf_instance)

        return self.vnf_instances

    def show(self):
        print("Greedy Placement Plan")
        table = BeautifulTable()
        table.columns.header = ["VNF Instance", "CPU", "Memory", "Node", "SFCs"]
        for aux in self.vnf_instances:
            table.rows.append([aux.name, aux.cpu, aux.mem, aux.node.name, aux.sfcs])

        print(table)