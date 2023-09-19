from Simulation_Entities.SFC_Request import SFC_Request
from Simulation_Entities.VNF_Instance import VNF_Instance
from Simulation_Entities.SFC_Instance import SFC_Instance
from Simulation_Entities.Packet import Packet

from Edge_Entities.SFC import SFC
from Edge_Entities.Link import Link
from Edge_Entities.User import User
from Edge_Entities.Data_Source import Data_Source

import simpy
import random
import time
import os
import math
import numpy as np
import pandas as pd

# from Edge_Environment import Edge_Environment
# from Placement.Naive import Naive_Placement
from Simulation_Data import Simulation_Data

class Simulation:

    def __init__(self, edge_environment, placement, ctrl, env, sd, round, total_time_simulation, time_window,
                 resource_links, path_result_files, compute_loopback_time, order_sfc_request_by_similarity,
                 packet_generation, log_link_events, log_vnf_instance_events, user_mobility_file, execute_user_mobility,
                 time_limit_to_packet_generation):
        """Create the simulation object with the entities and parameters

    Args:
        edge_environment (Edge_Environment): The edge environment
        placement (Placement): The placement object
        ctrl (SDN_Controller): The controller
        env (SimPy): The simpy environment
        sd (Simulation_Data): The data storage from the simulation
        round (int): the round of the test
        total_time_simulation (int): Max total time simulation
        time_window (int): The time windows that the SFC_Request will be wait to be placed
        resource_links (link): List of resource links
        path_result_files (str): The path where the files must be saved
        compute_loopback_time (bool): Define if the time to process the data over the loopack is counted or note
        order_sfc_request_by_similarity (bool): Use or not the SFC Similatiry
        log_link_events (bool): Log or not the link events
        log_vnf_instance_events (bool): Log or not the vnf instance events events
        user_mobility_file (dict): A dict with the key as the time when some user moved from node A to node B, each key have one or multiples movements
        execute_user_mobility (bool): Define if the mobility pattern file will be processed or not
        time_limit_to_packet_generation (int): The max time for the packet generation
    """

        self.edge_environment = edge_environment
        self.placement = placement
        self.ctrl = ctrl
        self.env = env
        self.sd = sd
        self.round = round
        self.total_time_simulation = total_time_simulation
        self.time_window = time_window
        self.resource_links = resource_links
        self.path_result_files = path_result_files
        self.compute_loopback_time = compute_loopback_time
        self.resource_instances = {}
        self.order_sfc_request_by_similarity = order_sfc_request_by_similarity
        self.packet_generation = packet_generation
        self.log_link_events = log_link_events
        self.log_vnf_instance_events = log_vnf_instance_events

        self.time_limit_to_packet_generation = time_limit_to_packet_generation

        self.packets = {}

        # only process the user mobility if the simulation provide the attr to process the file
        if user_mobility_file and execute_user_mobility:
            self.user_mobility = self.process_user_mobility(user_mobility_file)
        else:
            self.user_mobility = {}

        # Load packets from file
        self.packets_flow = {}
        try:
            if "PATH_PACKET_FLOW_FILE" in os.environ and os.environ["PATH_PACKET_FLOW_FILE"]:
                self.load_packets_flow(os.environ["PATH_PACKET_FLOW_FILE"])
        except KeyError as ke:
            pass

    def load_packets_flow(self, file_name):
        """
        Load the packet flow from the file
        """
        try:
            data = pd.read_csv(file_name, sep=';', quotechar="'")
            data = data.fillna('')

            for i in data.iterrows():
                aux = i[1]
                k = (aux.user, aux.sfc)

                aux_data = {
                    "time": aux.time,
                    "packet_size": aux.packet_size
                }

                if k in self.packets_flow:
                    self.packets_flow[k].append(aux_data)
                else:
                    self.packets_flow[k] = [aux_data]

        except FileNotFoundError as e:
            print("Error during loading file", e)
            quit()

    def process_user_mobility(self, user_mobility_file):
        """
        Process the file with the user mobility pattern
        """
        user_mobility_data = pd.read_csv(user_mobility_file, sep=';', quotechar="'")
        max_transition_time = user_mobility_data['TransitionTime'].max()
        time_ratio = self.total_time_simulation / max_transition_time
        user_mobility_data['TransitionTime'] = user_mobility_data['TransitionTime'] * time_ratio
        user_mobility_data['TransitionTime'] = user_mobility_data['TransitionTime'].apply(np.ceil)

        user_mobility = {}
        for aux in user_mobility_data.iterrows():
            mobility = aux[1]
            if mobility['UID'] in self.edge_environment.users:
                time_event = int(mobility['TransitionTime'])
                if time_event in user_mobility:
                    user_mobility[time_event][mobility['UID']] = mobility['NID']
                else:
                    user_mobility[time_event] = {mobility['UID']: mobility['NID']}

        return user_mobility

    def run(self):
        """Run the simulation
    """
        # add the events that the simulation will perform
        self.env.process(self.simulation())

        # Run the simulation model
        self.env.run(until=self.total_time_simulation)

    def simulation(self):

        # A cumulative information about the SFC Requested placed or not
        sfc_request_placed = 0
        sfc_request_not_placed = 0
        sfc_request_placement_order = 0
        first_placement = True

        while True:

            # Compute the total of resources used by the VNF Instances and save it in a file
            try:
                if os.environ["NSS_LOG_TOTAL_RESOURCES"] == "1":
                    resource_usage = self.edge_environment.calc_resources_usage()
                    self.sd.add_resource_usage_event(
                        self.sd.EVENT_RESOURCE_CPU_USAGE,
                        self.env.now,
                        resource_usage['cpu_allocated'],
                    )
            except KeyError as ke:
                print(ke)
                pass

            # Wait for 1ms
            yield self.env.timeout(1)

            # Verify if some user change its position, if so, move from actual node to the new node
            self.change_users_location()

            # Increment the delay for all the packets that are not processed yet
            self.increase_packet_delay()

            # Reduce the timeout of the SFC_Instance
            self.decrease_sfc_instances_timeout()

            # Reduce the timeout for the VNF Instance without SFC Instances associated
            self.decrease_timeout_vnf_instance()

            # Reduce the startup for the new VNF Instances, packets only will be processed if the
            # "Startup Remain Time" for the VNF Instance being zero
            self.decrease_startup_vnf_instance_time()

            # Reduce the shutdown for the new VNF Instances
            # "Shutdown Remain Time" for the VNF Instance being zero mean that it already be removed
            self.decrease_shutdown_vnf_instance_time()

            self.handle_sfc_replacement()

            # Wait for the next time window
            run_placement = False
            time_window_init = 0
            time_window_end  = self.total_time_simulation
            sfc_requests = []

            # Execute the placement for ALL the SFC Request at the time 0
            if self.time_window == 0 and first_placement == True:
                # Update the arrival time for all the SFC Requests to 0
                for sfc_request in self.edge_environment.sfc_requests:
                    self.edge_environment.sfc_requests[sfc_request].arrival_time = 0

                sfc_requests = SFC_Request.get_requests_in_time_window(self.edge_environment.sfc_requests, 0, time_window_end)

                run_placement = True

            if self.time_window != 0 and self.env.now % self.time_window == 0:
                # Starts the time window process
                time_window_init = self.env.now - self.time_window
                time_window_end = self.env.now - 1

                # Get all the requests that must be executed in the time window
                sfc_requests = SFC_Request.get_requests_in_time_window(self.edge_environment.sfc_requests, time_window_init, time_window_end)
                run_placement = True

            if run_placement == True:
                # define that the placement where executed once
                first_placement = False

                if self.order_sfc_request_by_similarity != None:
                    sfc_requests = SFC_Request.order_sfc_requests_by_sfc_similarity(sfc_requests, self.edge_environment.sfc_similarity, self.order_sfc_request_by_similarity)

                # Debug
                try:
                    if os.environ["NSS_DEBUG"] == "1":
                        print("\nExecute Time Window => Init: {}ms End: {}ms".format(time_window_init, time_window_end))
                        SFC_Request.list(sfc_requests)
                except KeyError as ke:
                    pass

                self.sd.add_time_window_event(self.sd.EVENT_TIME_WINDOW_STARTED, self.env.now, time_window_init, time_window_end, sfc_requests)

                # Add event
                self.sd.add_placement_event(Simulation_Data.EVENT_PLACEMENT_STARTED, self.env.now)

                # Run the placement using the environment and the sfc_requested in the time window
                start = time.time()

                exp_path = ""
                try:
                    if os.environ["NSS_SAVE_IMAGE_PLACEMENT"] == "1":
                        exp_path = "{}/images/".format(self.path_result_files)
                except KeyError as ke:
                    pass

                try:
                    if os.environ["NSS_DEBUG"] == "2":
                        print("Path where the images will be saved.")
                        print("----")
                        print(exp_path)
                except KeyError as ke:
                    pass

                vnf_instances = self.placement.execute(
                    sfc_requests=sfc_requests,
                    sd=self.sd,
                    time=self.env.now,
                    file_path=exp_path
                )

                end = time.time()
                total_alg_time = float(end - start) * 1000

                # debug
                try:
                    if os.environ["NSS_DEBUG"] == "2":
                        print("Time {}".format(self.env.now))
                        SFC_Instance.list(self.edge_environment.sfc_instances)
                        VNF_Instance.list(vnf_instances)
                        SFC.list(self.edge_environment.sfcs)
                except KeyError as ke:
                    pass

                # Pass the time to execute the placement
                # yield self.env.timeout(total_time)

                # Create the shared resources for each VNF_instances for the simulation
                for instance in vnf_instances or []:
                    # Capacity is the max packets that the instance can handle in parallel, only for new instances
                    if instance.name not in self.resource_instances.keys():
                        self.resource_instances[instance.name] = simpy.Resource(self.env, capacity=instance.vnf.max_share)

                # finish the time placement process
                self.sd.add_placement_event(Simulation_Data.EVENT_PLACEMENT_PROCESSED, self.env.now)

                for sfc_req in sfc_requests:
                    sfc_request_placement_order = sfc_request_placement_order + 1

                    # Only for the placed SFC
                    if sfc_req.placed:
                        sfc_request_placed = sfc_request_placed + 1
                        self.sd.add_sfc_request_event(Simulation_Data.EVENT_SFC_REQUEST_PLACED, self.env.now, sfc_req, sfc_request_placement_order)

                        # only generate the packet flow if configured
                        if self.packet_generation:
                            # if os.environ["PATH_PACKET_FLOW_FILE"]:
                            if "PATH_PACKET_FLOW_FILE" in os.environ and os.environ["PATH_PACKET_FLOW_FILE"]:
                                # use the packets load from file
                                self.env.process(self.flow_generator_by_file(sfc_req))
                            else:
                                # generate the packets randomly
                                self.env.process(self.flow_generator(sfc_req, time_window_end))

                    else:
                        sfc_request_not_placed = sfc_request_not_placed + 1
                        # Add event that the SFC was not placed
                        self.sd.add_sfc_request_event(Simulation_Data.EVENT_SFC_REQUEST_NOT_PLACED, self.env.now,
                                                      sfc_req, sfc_request_placement_order)

                # finish the time window process
                resource = self.edge_environment.calc_resources_usage()

                total_energy_comsumption = self.edge_environment.calc_total_energy_consumption()

                self.sd.add_time_window_event(
                    self.sd.EVENT_TIME_WINDOW_PROCESSED,
                    self.env.now, time_window_init,
                    time_window_end,
                    sfc_requests,
                    sfc_request_placed,
                    sfc_request_not_placed,
                    resource['cpu_allocated'],
                    resource['mem_allocated'],
                    resource['vnf_instances_count'],
                    resource['sfc_instances_count'],
                    total_alg_time,
                    total_energy_comsumption
                )

    def flow_generator_by_file(self, sfc_request):
        """
        Get the packets defined in a file used as entry during the system startup.
        This file must have the parameters  .... @todo
        """
        # For each SFC starts the packet id with zero
        user_name = sfc_request.user.name
        sfc_name = sfc_request.sfc.name
        k = (user_name, sfc_name)

        # there is no packets to be processed
        if k not in self.packets_flow:
            return

        # Log the starting of the packet generation
        self.sd.add_sfc_request_event(Simulation_Data.EVENT_SFC_REQUEST_PACKET_GENERATION_STARTED, self.env.now, sfc_request)

        packets_flow_sfc_request = self.packets_flow[k]

        packet_id = 0

        start_time = self.env.now

        for packet_data in packets_flow_sfc_request:

            # stop the packet creation if the time was above the limit
            if self.env.now > self.time_limit_to_packet_generation:
                return

            packet_time = packet_data['time']
            packet_size = packet_data['packet_size']
            yield self.env.timeout(packet_time)
            packet_id += 1
            p = Packet (
                packet_id=packet_id,
                created_at=self.env.now,
                sfc_request=sfc_request,
                max_delay=sfc_request.sfc.max_latency,
                total_sfc_requests_active=self.edge_environment.get_num_sfc_requests_active(),
                size=packet_size
            )

            self.packets[(sfc_request.name, packet_id)] = p

            # Start processing the packet in the SFC
            self.env.process(self.process_sfc_request(packet_id, sfc_request))

        # Log the end of packet generation
        self.sd.add_sfc_request_event(Simulation_Data.EVENT_SFC_REQUEST_PACKET_GENERATION_STOPPED, self.env.now, sfc_request)

        # Define that this SFC Request will not send more packets
        sfc_request.active = False

        # Define the duration time based on the first and last packets processed in the SFC Request
        sfc_request.duration = self.env.now - start_time

        return True

    def flow_generator(self, sfc_request, time_window_end):
        """It will generate for each SFC requested

        Args:
            sfc_request (SFC_Request): The SFC requested
            time_window_end (int): The time where the packets of the sfc_request will start to be created
        Yields:
            [type]: [description]
        """

        src = sfc_request.data_source
        sfc_instance = self.edge_environment.get_active_sfc_instance_by_sfc_request(sfc_request)

        # Log the starting of the packet generation
        self.sd.add_sfc_request_event(Simulation_Data.EVENT_SFC_REQUEST_PACKET_GENERATION_STARTED, self.env.now, sfc_request)

        # The time_windows_end defines the moment when the placement was executed
        # thus the time limit for generating packet from the SFC Requests placed is
        # the duration of the SFC Rquest + the time when the time window were executed
        sfc_request_duration = sfc_request.duration + time_window_end

        # For each SFC starts the packet id with zero
        packet_id = 0
        while True:
            if sfc_request_duration >= self.env.now:

                # Wait for the time to start a new packet burst
                yield self.env.timeout(src.get_packets_burst_interval())

                # stop the packet creation if the time was above the limit
                if self.env.now > self.time_limit_to_packet_generation:
                    return

                for i in range(src.get_packets_burst_size()):
                    # If packet is generated we will restart the timeout
                    self.reset_sfc_timeout(sfc_instance)

                    # packet_id is used in all event of the simulation, it allow to know which packet generate each event
                    packet_id += 1

                    # Only create the packet IF the simulation remain time were greater than the max_delay for the SFC
                    if self.total_time_simulation > (self.env.now + sfc_request.sfc.max_latency):
                        # Create the entity Packet
                        packet_size = np.random.poisson(sfc_request.data_source.packet_size)
                        p = Packet (
                            packet_id=packet_id,
                            created_at=self.env.now,
                            sfc_request=sfc_request,
                            max_delay=sfc_request.sfc.max_latency,
                            total_sfc_requests_active=self.edge_environment.get_num_sfc_requests_active(),
                            size=packet_size
                        )

                        self.packets[(sfc_request.name, packet_id)] = p

                        # Time between multiples packets of the same SFC
                        yield self.env.timeout(src.get_packet_interval())

                        # Start processing the packet in the SFC
                        self.env.process(self.process_sfc_request(packet_id, sfc_request))
            else:
                # Log the end of packet generation
                self.sd.add_sfc_request_event(Simulation_Data.EVENT_SFC_REQUEST_PACKET_GENERATION_STOPPED, self.env.now, sfc_request)

                # Define that this SFC Request will not send more packets
                sfc_request.active = False
                return True

    def process_sfc_request(self, packet_id, sfc_request):
        """
        Process the packets generated for a SFC Request, the packet will travel across all the links
        and VNF Instances associated with the SFC Instance that is serving the SFC Request that generate the
        packet

        Args:
            packet_id (int): The Packet ID
            sfc_request (SFC_Request): The SFC_Request that is attended
        Yields:
            [type]: [description]
        """
        sfc_instance = self.edge_environment.get_active_sfc_instance_by_sfc_request(sfc_request)

        user = sfc_request.user
        sfc = sfc_request.sfc

        packet_init_time = self.env.now

        # Event log, the packet creation and start a new flow through the SFC's VNF's
        self.sd.add_packet_event(
            Simulation_Data.EVENT_PACKET_CREATED,
            packet_init_time,
            packet_id,
            sfc_request
        )

        # The SFC Instance where the SFC Request was mapped does not exist (timeout). This situation occur when
        # the total time for processing a packet inside a VNF Instance is greater than the SFC Instance Timeout

        if not sfc_instance:
            self.sd.add_packet_event(
                Simulation_Data.EVENT_PACKET_ORPHAN,
                self.env.now,
                packet_id,
                sfc_request
            )

            # Orphan packet must be deactivated
            self.packets[(sfc_request.name, packet_id)].orphan = True

            self.packets[(sfc_request.name, packet_id)].active = False

            # self.packets[(sfc_request.name, packet_id)].sla_violated = True
            self.mark_packet_as_sla_violated(sfc_request, packet_id)

            return False

        # Compute the mobility penalty
        if sfc_request.has_user_moved():
            packet = self.packets[(sfc_request.name, packet_id)]
            packet_size = sfc_request.data_source.packet_size

            links = self.edge_environment.get_links(
                sfc_request.user.node.name,
                sfc_request.ingress_node.name
            )

            # Select one of the links randomly
            link = random.choice(links)

            total_extra_delay = ((packet_size / link.bandwidth) * 1000) + link.propagation
            total_extra_delay = math.ceil(total_extra_delay) * 2
            yield self.env.timeout(total_extra_delay)

            # When the packet was generated, the penalty was applied
            packet.mobility_penalty = total_extra_delay

        packet_orphan = False # When the SFC Instance is removed and some packets remain in the VNF Instances
        packet_dropped = False # When the VNF Instance Queue is full

        for vnf_name, link_name in sfc_instance.links.items():

            # When k == ingress than only process the link time and not the VNF time

            if vnf_name != "ingress":
                # Execute the time for processing the VNF
                vnf_instance = self.ctrl.get_vnf_instance(sfc_request, vnf_name)
                #vnf_instance = vnfs_instances[vnf_name]

                # Debug
                if vnf_instance == False:
                    packet_orphan = True

                    self.packets[(sfc_request.name, packet_id)].active = False
                    self.packets[(sfc_request.name, packet_id)].orphan = True
                    # self.packets[(sfc_request.name, packet_id)].sla_violated = True
                    self.mark_packet_as_sla_violated(sfc_request, packet_id)

                    self.sd.add_packet_event(
                        Simulation_Data.EVENT_PACKET_ORPHAN,
                        self.env.now,
                        packet_id,
                        sfc_request
                    )

                    # debug
                    try:
                        if os.environ["NSS_DEBUG"] == "1":
                            print("VNF {} was not attached to an VNF Instance".format(vnf_name))
                            sfc_request.show()
                    except KeyError as ke:
                        pass
                else:
                    resource_vnf_instance = self.resource_instances[vnf_instance.name]
                    result = yield self.env.process(self.vnf_process(packet_id, resource_vnf_instance, vnf_instance, sfc_request))
                    if result == False:
                        packet_dropped = True
                        self.packets[(sfc_request.name, packet_id)].dropped = True
                        self.packets[(sfc_request.name, packet_id)].active = False
                        # self.packets[(sfc_request.name, packet_id)].sla_violated = True
                        self.mark_packet_as_sla_violated(sfc_request, packet_id)

            if packet_orphan or packet_dropped:
                break

            # Process the link
            resource_link = self.resource_links[link_name]
            link = self.edge_environment.links[link_name]

            packet = self.packets[(sfc_request.name, packet_id)]

            if vnf_name == "ingress":
                # packet_size = user.sfc_ingress_egress[sfc.name]['packet_size']
                # Value generated by the data source
                packet_size = packet.size
                vnf_instance_name = "data_source"
            else:
                #vnf_instance = vnfs_instances[vnf_name]
                vnf_instance = self.ctrl.get_vnf_instance(sfc_request, vnf_name)

                vnf_instance_name = ""
                packet_size = 0
                if vnf_instance:
                    vnf_instance_name = vnf_instance.name
                    # value calculated for each VNF where the packet is processed
                    packet_size = packet.size * vnf_instance.vnf.packet_network_demand
                else:
                    packet_orphan = True
                    # Orphan packet must be deactivated
                    self.packets[(sfc_request.name, packet_id)].orphan = True
                    self.packets[(sfc_request.name, packet_id)].active = False
                    # self.packets[(sfc_request.name, packet_id)].sla_violated = True
                    self.mark_packet_as_sla_violated(sfc_request, packet_id)

                    self.sd.add_packet_event(
                        Simulation_Data.EVENT_PACKET_ORPHAN,
                        self.env.now,
                        packet_id,
                        sfc_request
                    )

            if not packet_orphan:
                process_link = True
                if self.compute_loopback_time == 0 and link.source == link.target:
                    process_link = False

                if process_link:
                    link_process_result = yield self.env.process(
                        self.link_process(
                            packet_id,
                            packet_size,
                            resource_link,
                            link,
                            sfc_request,
                            vnf_instance_name
                        )
                    )

                    if not link_process_result:
                        return False

        # Event log, the packet processed is delivered to the last edge node before being consumed
        # by the application that wants the data.
        # self.sd.add_sfc_event(packet_id, user, sfc, Simulation_Data.EVENT_SFC_PACKET_PROCESSED,self.env.now)
        # sfc_instance = self.edge_environment.get_active_sfc_instance_by_sfc_request(sfc_request)

        # only create the event for packet processed if there are no packet orphan
        # and if it were not dropped by
        if not packet_orphan and not packet_dropped:
            delay = self.env.now - packet_init_time
            sla_violated = False
            if delay > sfc_instance.sfc.max_latency:
                sla_violated = True

            delay = "{:.2f}".format(delay)

            self.sd.add_packet_event(
                Simulation_Data.EVENT_PACKET_PROCESSED,
                self.env.now,
                packet_id,
                sfc_request
            )

            self.packets[(sfc_request.name, packet_id)].active = False
            self.packets[(sfc_request.name, packet_id)].processed = True

    def vnf_process(self, packet_id, resource_vnf_instance, vnf_instance, sfc_request):
        """ The process that occur inside the VNF

        Args:
            env (simpy): Simpy environment
            packet_id (int): The id that define the generated packet
            vnf_instance (VNF_Instance): Is the VNF instance object
            resource_vnf_instance (Simpy.Resource) The Simpy Resource used to map the VNF_Instance
            vnf (VNF): The VNF object
        Yields:
            [type]: The process time of the VNF
        """
        user = sfc_request.user
        sfc = sfc_request.sfc
        vnf = vnf_instance.vnf
        packet = self.packets[(sfc_request.name, packet_id)]
        packet_size = packet.size * vnf.packet_cpu_demand

        sfc_instance = self.edge_environment.get_active_sfc_instance_by_sfc_request(sfc_request)

        if self.log_vnf_instance_events:
            # log the time arrive at the VNF Instance
            self.sd.add_vnf_instance_packets_event(
                Simulation_Data.VNF_INSTANCE_PACKET_ARRIVED,
                self.env.now,
                packet_id,
                vnf_instance,
                sfc_request,
                sfc_instance,
                packet_size
            )

            packet_arrival_time = self.env.now

        if not vnf_instance.add_packet_in_queue():
            sfc_instance = self.edge_environment.get_active_sfc_instance_by_sfc_request(sfc_request)

            if self.log_vnf_instance_events:
                # Log the info at packet level
                self.packets[(sfc_request.name, packet_id)].active = False
                self.packets[(sfc_request.name, packet_id)].dropped = True
                # self.packets[(sfc_request.name, packet_id)].sla_violated = True
                self.mark_packet_as_sla_violated(sfc_request, packet_id)

                self.sd.add_packet_event(
                    Simulation_Data.EVENT_PACKET_DROPPED_VNF_INSTANCE_QUEUE,
                    self.env.now,
                    packet_id,
                    sfc_request
                )

                # Log the info at vnf instance level
                self.sd.add_vnf_instance_packets_event(
                    Simulation_Data.VNF_INSTANCE_PACKET_DROPPED,
                    self.env.now,
                    packet_id,
                    vnf_instance,
                    sfc_request,
                    sfc_instance,
                    packet_size
                )

            return False

        # Wait until the VNF Instance became available
        # startup_remain_time must be zero for entering in the process vnf mode
        if vnf_instance.startup_remain_time > 0:
            yield self.env.timeout(vnf_instance.startup_remain_time)

        # Wait for the resource instance
        with resource_vnf_instance.request() as request:
            yield request  # wait for the availability of the instance

            try:
                # Verify if the SFC Instance is active, if not, make tha packet orphan

                # If it is the first VNF thus the packet size is getting from the data_souce, ele, by the VNF Itself
                # if sfc.vnfs[0] == vnf.name:
                #     packet_size = sfc_request.data_source.packet_size
                
                packet_processing_start = self.env.now

                # log the time when the packet enter in the VNF Instance Queue
                if self.log_vnf_instance_events:
                    self.sd.add_vnf_instance_packets_event(
                        Simulation_Data.VNF_INSTANCE_PACKET_PROCESS_STARTED,
                        self.env.now,
                        packet_id,
                        vnf_instance,
                        sfc_request,
                        sfc_instance,
                        packet_size,
                        packet_processing_start - packet_arrival_time
                    )

                # how much time the packet will be use the CPU * 1000 to became milliseconds
                # the time for processing a packet is the time for the cpu usage + the time to access remote data
                # when it happen. This values came from the fields "remote_data_access_cost" and "remote_data_access_prob"
                # we also use a Poisson distribution to calculate this value
                remote_data_access_prob = np.random.poisson(vnf.remote_data_access_prob)

                # total_vnf_process_time = (packet_size / vnf_instance.cpu) * 1000
                # total_vnf_process_time = (packet.size / vnf_instance.cpu) * 1000 * (1 + vnf_instance.cpu_load * 0.1)
                total_vnf_process_time = (packet_size / vnf_instance.cpu) * 1000

                # increase the cpu usage because of the packet processing started
                packet_cpu_usage = packet_size / vnf_instance.cpu
                vnf_instance.increase_cpu_load(packet_cpu_usage)

                # increase the mem usage because of the packet processing started
                packet_mem_usage = (packet_size * vnf.packet_mem_demand) / vnf_instance.mem
                vnf_instance.increase_mem_load(packet_mem_usage)

                if self.log_vnf_instance_events:
                    self.sd.add_vnf_instance_resources_event(
                        Simulation_Data.EVENT_INSTANCE_RESOURCE_USAGE_INCREASE,
                        self.env.now,
                        vnf_instance,
                        packet_cpu_usage,
                        packet_mem_usage,
                        sfc_request,
                        packet_id
                    )

                if (random.random() < remote_data_access_prob):
                    total_vnf_process_time = total_vnf_process_time + vnf.remote_data_access_cost
                    # log the remote data access time
                    if self.log_vnf_instance_events:
                        self.sd.add_vnf_instance_packets_event(
                            Simulation_Data.VNF_INSTANCE_REMOTE_DATA_RECEIVED,
                            self.env.now,
                            packet_id,
                            vnf_instance,
                            sfc_request,
                            sfc_instance,
                            packet_size
                        )

                # if the memory usage is higher than 1 we will add the disk_delay time access in the total
                # process time of the packet
                if vnf_instance.mem_load > 1:
                    total_vnf_process_time = total_vnf_process_time + vnf_instance.node.disk_delay

                    # log the disk access by the instance
                    if self.log_vnf_instance_events:
                        self.sd.add_vnf_instance_resources_event(
                            Simulation_Data.EVENT_INSTANCE_RESOURCE_DISK_ACCESS,
                            self.env.now,
                            vnf_instance,
                            vnf_instance.cpu_load,
                            vnf_instance.mem_load,
                            sfc_request,
                            packet_id
                        )

                # if the laod if higher than 1 it means that the VNF Instance is overloaded
                if vnf_instance.cpu_load > 1:
                    total_vnf_process_time = total_vnf_process_time * vnf_instance.cpu_load

                # Decrement the VNF Instance Packet Queue Count in one packet
                vnf_instance.dec_packet_in_queue()
                yield self.env.timeout(int(total_vnf_process_time))

                # reduce the cpu usage because of the packet processing finalization
                vnf_instance.decrease_cpu_load(packet_cpu_usage)

                # reduce the mem usage because of the packet processing finalization
                vnf_instance.decrease_mem_load(packet_mem_usage)

                if self.log_vnf_instance_events:
                    self.sd.add_vnf_instance_resources_event(
                        Simulation_Data.EVENT_INSTANCE_RESOURCE_USAGE_DECREASE,
                        self.env.now,
                        vnf_instance,
                        packet_cpu_usage,
                        packet_mem_usage,
                        sfc_request,
                        packet_id
                    )

                    packet_processing_time = self.env.now - packet_processing_start

                    # log the time when the packet leave VNF Instance Queue
                    self.sd.add_vnf_instance_packets_event(
                        Simulation_Data.VNF_INSTANCE_PACKET_PROCESSED,
                        self.env.now,
                        packet_id,
                        vnf_instance,
                        sfc_request,
                        sfc_instance,
                        packet_size,
                        packet_processing_time
                    )

            except simpy.Interrupt:
                print("Something went very bad")

    def link_process(self, packet_id, packet_size, resource_link, link, sfc_request, vnf_instance_name):
        """Compute the total amount of time consumed to send the data from the node_source to node_target

        Args:
            packet_id (int): The packet id
            packet_size (int): The packet size
            resource_link (Resource): The simpy resource
            link (Link): The link entity
            sfc_request (SFC_request): The SFC Request
            vnf_instance_name (str): The VNF Instance name
        """

        sfc_instance = self.edge_environment.get_active_sfc_instance_by_sfc_request(sfc_request)
        # log the time when the packet arrive ate link Queue
        if self.log_link_events:
            self.sd.add_link_event(
                event=Simulation_Data.EVENT_LINK_ARRIVED,
                time=self.env.now,
                packet_id=packet_id,
                link=link,
                sfc_request=sfc_request,
                sfc_instance=sfc_instance,
                vnf_instance_name=vnf_instance_name,
                packet_size=packet_size
            )

        if not link.add_packet_in_queue():
            # Log that the packet was dropped in the link's queue
            if self.log_link_events:
                self.sd.add_link_event(
                    event=Simulation_Data.EVENT_LINK_PACKET_DROPPED_QUEUE,
                    time=self.env.now,
                    packet_id=packet_id,
                    link=link,
                    sfc_request=sfc_request,
                    sfc_instance=sfc_instance,
                    vnf_instance_name=vnf_instance_name,
                    packet_size=packet_size
                )

            # Orphan packet must be deactivated
            self.packets[(sfc_request.name, packet_id)].orphan = False
            self.packets[(sfc_request.name, packet_id)].active = False
            self.packets[(sfc_request.name, packet_id)].dropped = True
            # self.packets[(sfc_request.name, packet_id)].sla_violated = True
            self.mark_packet_as_sla_violated(sfc_request, packet_id)
            return False

        with resource_link.request() as request:
            yield request

            # log the time when the link start sending the packet
            if self.log_link_events:
                self.sd.add_link_event(
                    event=Simulation_Data.EVENT_LINK_STARTED,
                    time=self.env.now,
                    packet_id=packet_id,
                    link=link,
                    sfc_request=sfc_request,
                    sfc_instance=sfc_instance,
                    vnf_instance_name=vnf_instance_name,
                    packet_size=packet_size
                )

            # time for transfer the data from source node to target node
            # * 1000 convert from second to ms
            transfer_delay = (packet_size / link.bandwidth) * 1000

            total_delay = transfer_delay + link.propagation

            # print("{:.2f}, {:.2f}, Total Delay: {:.2f},".format(packet_size, link.bandwidth, total_delay))
            yield self.env.timeout(total_delay)

            link.dec_packet_in_queue()

            # log the time when the link start sending the packet
            if self.log_link_events:
                self.sd.add_link_event(
                    event=Simulation_Data.EVENT_LINK_PROCESSED,
                    time=self.env.now,
                    packet_id=packet_id,
                    link=link,
                    sfc_request=sfc_request,
                    sfc_instance=sfc_instance,
                    vnf_instance_name=vnf_instance_name,
                    packet_size=packet_size
                )

        return True

    def decrease_timeout_vnf_instance(self):
        """
        Decrease the timeout for the VNF Instances that is not attending any SFC Instance
        """
        for vnf_instance in self.edge_environment.vnf_instances:
            if vnf_instance.active:
                if len(vnf_instance.sfc_instances) > 0:
                    vnf_instance.timeout = vnf_instance.vnf.timeout
                    continue

                if vnf_instance.timeout > 0:
                    vnf_instance.timeout = vnf_instance.timeout - 1

                if vnf_instance.timeout == 0:
                    vnf_instance.timeout = -1
                    vnf_instance.accept_sfc_instances = False
                    self.sd.add_vnf_instance_event(
                        event=Simulation_Data.EVENT_INSTANCE_SHUTDOWN,
                        time=self.env.now,
                        vnf_instance=vnf_instance
                    )

    def decrease_shutdown_vnf_instance_time(self):
        """
            Decrease the shutdown_remain_time for all the VNF_Instances
        """
        for vnf_instance in self.edge_environment.vnf_instances:
            if vnf_instance.accept_sfc_instances == False and vnf_instance.shutdown_remain_time > 0:
                vnf_instance.shutdown_remain_time = vnf_instance.shutdown_remain_time - 1

            if vnf_instance.accept_sfc_instances == False and vnf_instance.shutdown_remain_time == 0:
                vnf_instance.shutdown_remain_time = -1
                vnf_instance.active = False
                # log complete startup event
                self.sd.add_vnf_instance_event(
                    event=Simulation_Data.EVENT_INSTANCE_DESTROYED,
                    time=self.env.now,
                    vnf_instance=vnf_instance
                )

    def decrease_startup_vnf_instance_time(self):
        """
            Decrease the startup_remain_time for all the VNF_Instances
            If the packet arrives to a VNF_Instance that the startup_remain_time is greater than 0
            the packet will wait until this value became zero to be processed
        """
        for vnf_instance in self.edge_environment.vnf_instances:
            if vnf_instance.startup_remain_time > 0:
                vnf_instance.startup_remain_time = vnf_instance.startup_remain_time - 1

            if vnf_instance.startup_remain_time == 0:
                vnf_instance.startup_remain_time = -1
                # log complete startup event
                self.sd.add_vnf_instance_event(
                    event=Simulation_Data.EVENT_INSTANCE_STARTUP,
                    time=self.env.now,
                    vnf_instance=vnf_instance
                )

    def decrease_sfc_instances_timeout(self):
        """
            Decrease the timeout of all the SFC_Instance in execution
        """
        for sfc_instance in self.edge_environment.sfc_instances:
            if sfc_instance.active:
                sfc_instance.timeout -= 1
                if sfc_instance.timeout <= 0:
                    self.destroy_sfc_instance(sfc_instance)

                    # log destruction event
                    self.sd.add_sfc_instance_event(
                        event=Simulation_Data.EVENT_SFC_INSTANCE_DESTROYED,
                        time=self.env.now,
                        sfc_instance=sfc_instance
                    )

    def destroy_sfc_instance(self, sfc_instance):
        """Destroy a SFC_Instance, The resources from VNF_Instances must be released

        Args:
            sfc_instance (SFC_Instance): The SFC_Instance that will be destroyed
        """
        # Remove the map between the VNF_Instance and the SFC_Instance
        for vnf_instance in self.edge_environment.vnf_instances:
            if sfc_instance.name in vnf_instance.sfc_instances:
                vnf_instance.sfc_instances.remove(sfc_instance.name)

                # log sfc instance mapped into vnf instance
                self.sd.add_sfc_instance_vnf_mapping_event(
                    event=Simulation_Data.EVENT_SFC_INSTANCE_VNF_UNMAPPED,
                    time=self.env.now,
                    sfc_instance=sfc_instance,
                    vnf_instance=vnf_instance
                )

        sfc_instance.active = False
        sfc_instance.accept_requests = False

    def reset_sfc_timeout(self, sfc_instance):
        sfc_instance.timeout = self.edge_environment.sfcs[sfc_instance.sfc.name].timeout

    def increase_packet_delay(self):
        """
        Increase the packet delay for all the packets that are not processed yet
        """
        for aux in self.packets:
            packet = self.packets[aux]
            if packet.active:
                packet.delay += 1
                if packet.sla_violated == False and packet.max_delay < packet.delay:
                    # packet.sla_violated = True
                    self.mark_packet_as_sla_violated(packet.sfc_request, packet.packet_id, (packet.delay - packet.max_delay) / packet.max_delay)

    def change_users_location(self):
        """
        Verify if in the simulation time now any user changed the node where it is associated,
        characterizing thus the "user mobility"
        """

        if self.env.now in self.user_mobility:

            mobility = self.user_mobility[self.env.now]

            for user_name in mobility:

                if user_name not in self.edge_environment.users:
                    print("Mobility ERROR: User {} not found".format(user_name))
                    quit()

                node_name = mobility[user_name]

                if node_name not in self.edge_environment.nodes:
                    print("Mobility ERROR: Node {} not found".format(node_name))
                    quit()

                # Only create a move event if the new node is different from the node where use user is
                # already associated
                if self.edge_environment.users[user_name].node.name != node_name:
                    # Log Event
                    #print("User", user_name, "moved from", self.edge_environment.users[user_name].node.name, "to", node_name)
                    self.sd.add_user_mobility_event(
                        self.sd.EVENT_USER_MOVED,
                        self.env.now,
                        user_name,
                        self.edge_environment.users[user_name].node.name,
                        node_name
                    )

                    # Change the node from the user
                    self.edge_environment.users[user_name].node = self.edge_environment.nodes[node_name]

    def handle_sfc_replacement(self):

        if(len(self.edge_environment.replacement_schedule) == 0):
            return

        requests_to_replace = self.edge_environment.pop_sfc_requests_waiting_for_placement(self.env.now)

        old_sfc_instances = {}
        old_ingress_nodes = {}

        if(len(requests_to_replace) > 0):
            print("Retrieving requests waiting for placement. Time:",self.env.now)
            for request in requests_to_replace:
                request.placed = 0
                old_ingress_nodes[request.name] = request.ingress_node
                request.ingress_node = request.user.node
                old_sfc_instances[request.name] = request.sfc_instance

            print("Replacement Called!")
            vnf_instances = self.placement.execute(
                sfc_requests=requests_to_replace,
                sd=self.sd,
                time=self.env.now,
                file_path=""
            )

            # Resource logic
            # Create the shared resources for each VNF_instances for the simulation
            for instance in vnf_instances or []:
                # Capacity is the max packets that the instance can handle in parallel, only for new instances
                if instance.name not in self.resource_instances.keys():
                    self.resource_instances[instance.name] = simpy.Resource(self.env, capacity=instance.vnf.max_share)

            for sfc_req in requests_to_replace:
                #sfc_instance = self.edge_environment.get_active_sfc_instance_by_sfc_request(sfc_req)
                #print("REQUEST",sfc_req.name,"MAPPED TO",sfc_instance.name)
                if sfc_req.placed:
                    print("Replacement successful!")
                    old_sfc_instance = old_sfc_instances[sfc_req.name]
                    if sfc_req.sfc_instance.name != old_sfc_instance.name:
                        #print("Destroying: ", old_sfc_instance.name, "Reason: Replacement")
                        self.destroy_sfc_instance(old_sfc_instance)
                        self.sd.add_sfc_instance_event(
                            event=Simulation_Data.EVENT_SFC_INSTANCE_DESTROYED,
                            time=self.env.now,
                            sfc_instance=old_sfc_instance
                        )
                    #self.edge_environment.sfc_instances.remove(old_sfc_instance)
                    #self.edge_environment.sfc_instances_counter -= 1
                    sfc_req.replacements += 1
                    self.edge_environment.remove_sfc_request_from_replacement_wait(sfc_req)
                    self.sd.add_sfc_request_event( 
                        Simulation_Data.EVENT_SFC_REQUEST_REPLACED,  
                        self.env.now, 
                        sfc_req)
                    #SFC_Instance.list(self.edge_environment.sfc_instances)
                    #sfc_instance = self.edge_environment.get_active_sfc_instance_by_sfc_request(sfc_req)
                    #print("REQUEST",sfc_req.name,"MAPPED TO",sfc_instance.name)
                else:
                    print("Replacement failed!")
                    sfc_req.placed = 1 # Change back placed variable to represent ongoing SLA-infringent request
                    sfc_req.ingress_node = old_ingress_nodes[sfc_req.name]
                    sfc_req.sfc_instance = old_sfc_instances[sfc_req.name]
                    self.sd.add_sfc_request_event(Simulation_Data.EVENT_SFC_REQUEST_REPLACEMENT_FAILED, 
                        self.env.now,                       
                        sfc_req)
                    

    def mark_packet_as_sla_violated(self, sfc_request, packet_id, violation_percentage=1.0):
        """
        Define the attr sla_violated in that packet to True and a violation percentage by default 100% (1.0)
        for orphan and dropped cases.
        """
        # Avoid double log to EVENT_PACKET_SLA_VIOLATED event
        if self.packets[(sfc_request.name, packet_id)].sla_violated == False:

            self.packets[(sfc_request.name, packet_id)].sla_violated = True
            self.packets[(sfc_request.name, packet_id)].sla_violation_percentage = round(violation_percentage, 2)

            # Event log, the packet sla violated
            if self.log_vnf_instance_events:
                self.sd.add_packet_event(
                    Simulation_Data.EVENT_PACKET_SLA_VIOLATED,
                    self.env.now,
                    packet_id,
                    sfc_request
                )

    def finish_simulation(self):
        """
        This method is executed after the Simpy finished the simulation.
        """

        # For all the packets that is not processed but active we will log an event for it disposal
        for aux in self.packets:
            packet = self.packets[aux]
            if packet.active:
                # Event log, the packet ACTIVE but not processed in the end of the simulation
                if self.log_vnf_instance_events:
                    self.sd.add_packet_event(
                        Simulation_Data.EVENT_PACKET_SIMULATION_TIME_EXPIRED,
                        self.env.now,
                        packet.packet_id,
                        packet.sfc_request
                    )
