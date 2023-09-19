import random
import pandas as pd
import os
import csv
import json

from beautifultable import BeautifulTable
from termcolor import cprint

from Edge_Entities.VNF import VNF
from Edge_Entities.SFC import SFC
from Edge_Entities.Node import Node
from Edge_Entities.Link import Link
from Edge_Entities.User import User
from Edge_Entities.Data_Source import Data_Source

from Simulation_Entities.SFC_Request import SFC_Request
from Simulation_Entities.SFC_Instance import SFC_Instance
from Placement.SfcPriority import SfcPriority


class Edge_Environment:

    def __init__(self, name, specs, random_seed, total_time, time_window, max_replacement_retries, replacement_backoff_slot_size):
        """
        Create the Edge Environment based on the configured parameters

        Args:
            name (str): the name of the VNF
            specs (Dict): The dict with the configurations that will generate the environment
            random_seed (int): The seed used to generate the entities
            total_time (int): The total simulation time
            time_window (int): The time window
            max_replacement_retries (int)
            replacement_backoff_slot_size (int)
        """

        self.name = name
        self.vnf_num = specs["entities_number"]["vnfs"]
        self.node_num = specs["entities_number"]["nodes"]
        self.sfc_num = specs["entities_number"]["sfcs"]
        self.data_source_num = specs["entities_number"]["data_sources"]
        self.user_num = specs["entities_number"]["users"]
        self.random_seed = random_seed
        self.total_time = total_time
        self.time_window = time_window

        # Creation of random entities
        self.sfc_similarity = {}

        self.vnfs = self.vnf_random_creation(self.vnf_num, specs['vnf'])
        self.nodes = self.node_random_creation(self.node_num, specs['node'])
        self.sfcs = self.sfc_random_creation(self.sfc_num, specs['sfc'])
        self.links = self.link_random_creation(self.node_num, specs['link'])
        self.users = self.user_random_creation(self.user_num, specs['user'], specs['data_source'])
        self.data_sources = self.data_source_random_creation(self.data_source_num, specs['data_source'])
        self.sfc_requests = self.sfc_request_random_creation(specs['user'], specs['sfc_requests'])

        self.sfc_requests_waiting_replacement = {}
        self.replacement_schedule = {}
        self.max_replacement_retries = max_replacement_retries
        self.replacement_backoff_slot_size = replacement_backoff_slot_size

        self.vnf_instances = []
        self.sfc_instances = []

        # The number total os sfc_instances that were created
        self.sfc_instances_counter = 0

    def calc_bw_available_link(self, link_name):
        """
        Calculate how much of the total link bandwidth is available in the link

        It is calculated based on the total ot the active SFC_Instances that mapped to the link

        Args:
            link_name (str): The name of the link that will be tested

        Returns:
            total_bw_available (float): The total of the bandwidth available
        """
        link = self.links[link_name]
        total_bw_available = link.bandwidth

        for sfc_instance in self.sfc_instances:
            if sfc_instance.active:
                for vnf_name, link_name2 in sfc_instance.links.items():
                    if link_name == link_name2:
                        if vnf_name in self.vnfs:
                            vnf = self.vnfs[vnf_name]
                            total_bw_available -= vnf.min_bandwidth

        return total_bw_available

    def calc_total_energy_consumption(self):
        """
        Calc the total of SFC Requests active
        """
        total_energy_node = {}
        total_energy = 0
        for aux_node in self.nodes:
            node = self.nodes[aux_node]
            resources = self.get_node_available_resource(self.vnf_instances, node.name)
            total_energy_node[node.name] = node.energy_idle + (node.energy_max - node.energy_idle) * float("{:.2f}".format((node.cpu - resources['cpu']) / node.cpu))

        for aux in total_energy_node:
            total_energy += total_energy_node[aux]

        return total_energy

    def get_num_sfc_requests_active(self):
        """
        Calc the total of SFC Requests active
        """
        total = 0

        for aux in self.sfc_requests:
            sfc_request = self.sfc_requests[aux]
            if sfc_request.active and sfc_request.placed:
                total += 1

        return total

    def add_sfc_request_to_replacement(self, sfc_request, time_now):
        print("Adding",sfc_request.name,"to replacement wait. Time:",time_now)
        self.sfc_requests_waiting_replacement[sfc_request.name] = (0, time_now)
        if time_now in self.replacement_schedule:
            self.replacement_schedule[time_now].append(sfc_request)
        else:
            self.replacement_schedule[time_now] = [sfc_request]

    def is_waiting_placement(self, sfc_request_name):
        return sfc_request_name in self.sfc_requests_waiting_replacement

    def pop_sfc_requests_waiting_for_placement(self, time_now):
        if time_now in self.replacement_schedule:
            requests = self.replacement_schedule.pop(time_now)
            for req in requests:
                self.update_replacement_retry_time(req, time_now)
            return requests
        return []

    def update_replacement_retry_time(self, sfc_request, time_now):
        (retries, next_try) = self.sfc_requests_waiting_replacement[sfc_request.name]
        retries += 1
        if retries < self.max_replacement_retries:
            next_try = (pow(2,retries) - 1) * self.replacement_backoff_slot_size + time_now
            print("Setting next try of request",sfc_request.name,"to:",next_try)
            if next_try in self.replacement_schedule:
                self.replacement_schedule[next_try].append(sfc_request)
            else:
                self.replacement_schedule[next_try] = [sfc_request]
        self.sfc_requests_waiting_replacement[sfc_request.name] = (retries, next_try)

    def remove_sfc_request_from_replacement_wait(self, sfc_request):
        print("Removing",sfc_request.name,"from replacement wait.")
        (retries, next_try) = self.sfc_requests_waiting_replacement.pop(sfc_request.name)
        print(sfc_request.name,"next try was",next_try)
        if next_try in self.replacement_schedule:
            self.replacement_schedule[next_try].remove(sfc_request)
            print("Schedule length:",len(self.replacement_schedule[next_try]))
            if len(self.replacement_schedule[next_try]) == 0:
                del self.replacement_schedule[next_try]

    def calc_resources_usage(self):
        """
        Sum the amount of CPU and memory consumed by the VNF_Instances
        """
        cpu = 0
        mem = 0
        vnf_instances_count = 0
        sfc_instances_count = 0
        for vnf_instance in self.vnf_instances:
            if vnf_instance.active:
                vnf_instances_count += 1
                cpu = cpu + vnf_instance.cpu
                mem = mem + vnf_instance.mem

        for sfc_instance in self.sfc_instances:
            if sfc_instance.active:
                sfc_instances_count += 1

        return {
            'cpu_allocated': cpu,
            'mem_allocated': mem,
            'vnf_instances_count': vnf_instances_count,
            'sfc_instances_count': sfc_instances_count
        }

    def sfc_similarity_matrix(self):
        """Print a matrix with the similarity between the SFCs
        """
        table = BeautifulTable(180)

        column_name = [" "]
        for sfc in self.sfcs:
            aux_sfc = self.sfcs[sfc]
            column_name.append(aux_sfc.name)

        table.columns.header = column_name

        for sfc in self.sfcs:
            row_data = []
            aux_sfc = self.sfcs[sfc]
            row_data.append(aux_sfc.name)
            for sfc_2 in self.sfcs:
                aux_sfc_2 = self.sfcs[sfc_2]
                val = 1
                if aux_sfc_2.name != aux_sfc.name:
                    val = self.sfc_similarity[aux_sfc.name][aux_sfc_2.name]

                row_data.append(val)

            table.rows.append(row_data)

        print(table)

    def get_vnf_instance_of_sfc_instance(self, sfc_instance):
        """Return a list with the vnf_instances of a sfc_instance

        Args:
            sfc_instance (SFC Instance): The SFC Instance
        """
        aux = []
        for vnf_instance in self.vnf_instances:
            if sfc_instance.name in vnf_instance.sfc_instances:
                aux.append(vnf_instance)

        return aux

    def get_active_sfc_instance_by_sfc_request(self, sfc_request):
        """Finds the active SFC_Instance that handle the SFC_Request

        Args:
            sfc_request (SFC_Request): The SFC_Request

        Returns:
            SFC_Instance: The SFC_Instance, or False
        """
        for sfc_instance in self.sfc_instances:
            if sfc_instance.active and sfc_request.name in sfc_instance.get_sfc_requests_names():
                return sfc_instance
        return False

#
#    def get_sfc_requests_of_sfc_instance(self, sfc_instance):
#        """Finds the SFC_Requests that are associated to an SFC_Instance
#
#        Args:
#            sfc_instance (SFC_Instance): The SFC_Instance
#
#        Returns:
#            list of SFC_Requests
#        """

#        return [self.sfc_requests[sfc_request] for sfc_request in sfc_instance.sfc_requests]

    def create_sfc_instance(self, sfc_request, slice):
        """Create a new instance of SFC_Instance

        Args:
            sfc_request (SFC_Request): The SFC_Re
            slice (Slice): The Slice where the SFC_Instance is executed
        """

        # create the SFC_Instance

        sfc_instance = SFC_Instance(
            name='si_{}'.format(self.sfc_instances_counter),
            sfc=sfc_request.sfc,
            timeout=sfc_request.sfc.timeout,
            slice=slice,
            ingress_node=sfc_request.ingress_node,
            egress_node=sfc_request.egress_node
        )

        # Add the SFC_Request to the SFC_Instance
        sfc_instance.add_sfc_request(sfc_request)

        # Add the SFC_Instance to the edge environment
        self.sfc_instances.append(sfc_instance)

        # add one to the SFC_Instance counter
        self.sfc_instances_counter += 1

        return sfc_instance

    def remove_sfc_instance(self, sfc_instance):
        """Remove a SFC_Instance

        Args:
            sfc_instance (SFC_instance): The SFC_Instance
        """
        # Remove the SFC_Instance to the edge environment        
        self.sfc_instances.remove(sfc_instance)

        # Remove all map between the VNF_Instance and the SFC_Instance that was not used
        for vnf_instance in self.vnf_instances:
            if sfc_instance.name in vnf_instance.sfc_instances:
                vnf_instance.sfc_instances.remove(sfc_instance.name)

        # remove one to the SFC_Instance counter
        self.sfc_instances_counter -= 1

    def add_sfc_instance(self, sfc_instance):
        """Add the instance to the environment object

        Args:
            sfc_instance (SFC_Instance): The new SFC_Instance
        """
        self.sfc_instances.append(sfc_instance)

    def set_instances(self, vnf_instances):
        self.vnf_instances = vnf_instances

    def add_instance(self, vnf_instance):
        """Add an instance to the VNF Instances dict

        Args:
            vnf_instance (VNF_Instance]): The VNF Instance object
        """
        self.vnf_instances.append(vnf_instance)

    def get_vnf_instance_available(self, vnf_instances, node_name, vnf_name):
        """Return the VNF_Instances of a particular node that can attend a new SFC

        Args:
            vnf_instances (list): List of possible instances
            node_name (str): The name of the node
            vnf_name (str): The name of the VNF
        """
        aux_instances = []
        for instance in vnf_instances:
            if instance.node.name == node_name and instance.vnf.name == vnf_name and instance.accept_sfc_instances:
                # only if the number of attended SFC was lower them the max_share of the VNF
                if len(instance.sfcs) < self.vnfs[vnf_name].max_share:
                    aux_instances.append(instance)

        return aux_instances

    def get_node_available_resource(self, vnf_instances, node_name):
        """Return the available resources of a node given the VNF_Instances that already run on such node

        Args:
            vnf_instances (list): List of possible instances
            node_name (str): The name of the node
        """

        node = self.nodes[node_name]

        resource = {
            'cpu': node.cpu,
            'mem': node.mem
        }

        for vnf_instance in vnf_instances:
            if vnf_instance.active and node_name == vnf_instance.node.name:
                resource['cpu'] = resource['cpu'] - vnf_instance.cpu
                resource['mem'] = resource['mem'] - vnf_instance.mem

        return resource

    def get_node_vnf_instances(self, vnf_instances, node_name):
        """Return the instances that are running in a node

    Args:
        vnf_instances (list): The instances list
        node_name (str): The name of the node
    """
        vnf_instances_found = []

        for vnf_instance in vnf_instances:
            if node_name == vnf_instance.node.name:
                vnf_instances_found.append(vnf_instance)

        return vnf_instances_found

    def get_nodes_vnf(self, vnf_name):
        """Get a list of edge nodes that can be run a VNF

        Args:
            vnf_name (str): The VNF name
        """
        candidate_nodes = []
        for node in self.nodes:
            aux = self.nodes[node]
            if vnf_name in aux.vnfs:
                candidate_nodes.append(aux)

        return candidate_nodes

    def user_random_creation(self, user_num, user_specs, data_source_specs):
        """Create new users

        Args:
            user_num (int): The number of users
            user_specs (array): The possible values of each User attribute
            data_source_specs (array): The possible data sources associated with each SFC request

        Returns:
            [array]: The users created
        """
        random.seed(self.random_seed)
        ran_nodes = Node.get_nodes_by_type(self.nodes, Node.RAN_NODE)
        core_nodes = Node.get_nodes_by_type(self.nodes, Node.CORE_NODE)

        user_node = random.choice(ran_nodes)

        # Users creation
        users = {}
        for i in range(user_num):
            name = 'u_{}'.format(i)
            aux_user = User(
                name=name,
                sfcs=random.sample(list(self.sfcs), k=random.choice(user_specs['sfc_request_num'])),
                latency=random.choice(user_specs['latency']),
                bandwidth=random.choice(user_specs['bandwidth']),
                loss_rate=random.choice(user_specs['loss_rate']),
                node=user_node,
                priority=random.choice(user_specs['priority'])
            )

            # For each SFC generate the ingress and egress node
            for sfc in aux_user.sfcs:
                # ingress_node = self.nodes[random.choice(list(self.nodes))].name
                #
                # # the egress not will have 50% of chance to be the node where
                # # the user is attached
                # if random.random() < .5:
                #     egress_node = self.nodes[random.choice(list(self.nodes))].name
                # else:
                #     egress_node = aux_user.node.name

                ingress_node = user_node
                egress_node = random.choice(core_nodes)

                packet_size = random.choice(data_source_specs['packet_size'])
                aux_user.add_ingress_egress(sfc, ingress_node.name, egress_node.name, packet_size)

            users[name] = aux_user

        return users

    def sfc_random_creation(self, sfc_num, specs):
        """Create the SFCs randomly

        Args:
            sfc_num (int): The number of SFC that will be created
            specs (array): The possible values of each SFC attribute

        Returns:
            [set]: Set of SFCs
        """
        random.seed(self.random_seed)

        # SFCs creation
        sfcs = {}
        for i in range(sfc_num):

            priorities_order = ""

            # If priorities_order is not set use rondaom
            if 'priorities_order' in specs.keys():
                aux_order = random.choice(specs['priorities_order'])

                # The most import factor if Latency
                if aux_order == 1:
                    priorities_order = [SfcPriority.latency, SfcPriority.capacity, SfcPriority.energy]

                # The most import factor if CPU Capacity
                if aux_order == 2:
                    priorities_order = [SfcPriority.capacity, SfcPriority.latency, SfcPriority.energy]

                # The most import factor if Energy consumption
                if aux_order == 3:
                    priorities_order = [SfcPriority.energy, SfcPriority.latency, SfcPriority.capacity]
            else:
                priorities_order = random.sample([SfcPriority.latency, SfcPriority.capacity, SfcPriority.energy], k=3)

            name = 's_{}'.format(i)
            sfcs[name] = SFC(
                name=name,
                vnfs=random.sample(list(self.vnfs), k=random.choice(specs['vnf_num'])),
                max_latency=random.choice(specs['max_latency']),
                priorities_order=priorities_order,
                timeout=random.choice(specs['timeout'])
            )

        self.calc_sfc_similarity(sfcs)

        return sfcs

    def calc_sfc_similarity(self, sfcs):
        """Create a table with the similarity between the SFC
        """
        for sfc_1 in sfcs:
            self.sfc_similarity[sfc_1] = {}
            aux_sfc_1 = sfcs[sfc_1]
            for sfc_2 in sfcs:
                aux_sfc_2 = sfcs[sfc_2]
                if sfc_1 != sfc_2:
                    num_equals_vnf = len(list(set(aux_sfc_1.vnfs).intersection(aux_sfc_2.vnfs)))
                    self.sfc_similarity[sfc_1][sfc_2] = num_equals_vnf / min(len(aux_sfc_1.vnfs), len(aux_sfc_2.vnfs))

    def vnf_random_creation(self, vnf_num, specs):
        """Create the VNFs randomly

    Args:
        vnf_num (int): The number of VNF that will be created
        specs (array): The possible values of each VNF attribute

    Returns:
        [set]: Set of VNF
    """
        random.seed(self.random_seed)

        # VNFs creation
        vnfs = {}
        for i in range(vnf_num):
            name = 'v_{}'.format(i)

            val_resource_intensive = "CPU"
            if 'resource_intensive' in specs:
                val_resource_intensive = random.choice(specs['resource_intensive'])

            vnfs[name] = VNF(
                name,
                random.choice(specs['cpu']),
                random.choice(specs['mem']),
                random.choice(specs['max_share']),
                random.choice(specs['min_bandwidth']),
                random.choice(specs['packet_mem_demand']),
                random.choice(specs['remote_data_access_cost']),
                random.choice(specs['remote_data_access_prob']),
                random.choice(specs['packet_cpu_demand']),
                random.choice(specs['packet_network_demand']),
                random.choice(specs['startup_ipt']),
                random.choice(specs['shutdown_ipt']),
                random.choice(specs['timeout']),
                random.choice(specs['max_packet_queue']),
                val_resource_intensive
            )

        return vnfs

    def data_source_random_creation(self, data_source_num, specs):
        """ Create the Data Sources entities randomly

        Args:
            data_source_num (int): The number of Data Sources that will be created
            specs (array): The possible values of each Source attribute

        Returns:
            [set]: Set of Data Sources
        """
        random.seed(self.random_seed)

        # Source creation
        data_sources = {}
        for i in range(data_source_num):
            name = 'src_{}'.format(i)
            data_sources[name] = Data_Source(
                name=name,
                packet_size=random.choice(specs['packet_size']),
                packet_interval=random.choice(specs['packet_interval']),
                packets_burst_size=random.choice(specs['packets_burst_size']),
                packets_burst_interval=random.choice(specs['packets_burst_interval'])
            )

        return data_sources

    def sfc_request_random_creation(self, user_specs, sfc_requests_specs):
        """
            Will generate a list with the SFC requests creation based on the SFC that each user will demand.
        """
        sfc_requests = {}

        # The max arrival of an SFC request will be the total time simulation - the time windows, thus none SFC Request will be
        # generated out of the window time

        try:
            max_arrival_time = sfc_requests_specs['max_arrival_time']
        except KeyError as ke:
            max_arrival_time = self.total_time - self.time_window

        # count the total of SFC Requests that will be processed
        total_sfc_requested = 0
        for user in self.users:
            aux_user = self.users[user]
            total_sfc_requested = total_sfc_requested + len(aux_user.sfcs)

        arrival_time = []

        if sfc_requests_specs['arrival'] == SFC_Request.ARRIVAL_POISSON:
            arrival_time = SFC_Request.generate_poisson_arrival(self.random_seed, total_sfc_requested, max_arrival_time)

        if sfc_requests_specs['arrival'] == SFC_Request.ARRIVAL_LINEAR:
            num_windows = int(max_arrival_time / self.time_window)
            arrival_time = SFC_Request.generate_linear_arrival(num_windows, self.time_window, sfc_requests_specs['increase_requests_per_window'])

            if len(arrival_time) != len(self.users):
                print("The number of user must be {}.".format(len(arrival_time)))
                exit(0)

        # debug
        try:
            if os.environ["NSS_DEBUG"] == "1":
                print("Arrival SFC Requests Generated")
                counts = {}
                for n in arrival_time:
                    counts[n] = counts.get(n, 0) + 1
                print(counts)
                print(arrival_time)

        except KeyError as ke:
            pass

        if len(arrival_time) == 0:
            cprint("The arrival rate of the SFC Requests was incorrect. Go to simulation file and make the correction.", "red", attrs=['bold'])
            quit()

        count = -1

        # For each user get the requested SFCs
        for user in self.users:
            aux_user = self.users[user]

            # For each SFC for a user generate the request object    
            for sfc in aux_user.sfcs:
                count = count + 1
                aux_sfc = self.sfcs[sfc]

                src = random.choice(list(self.data_sources))
                aux_src = self.data_sources[src]

                priority = random.randint(0, aux_user.priority)

                name = "r_{}".format(count)
                sfc_requests[name] = SFC_Request(
                    name=name,
                    user=aux_user,
                    sfc=aux_sfc,
                    data_source=aux_src,
                    priority=priority,
                    arrival_time=arrival_time[count],
                    ingress_node = self.nodes[aux_user.sfc_ingress_egress[sfc]['ingress_node']],
                    egress_node = self.nodes[aux_user.sfc_ingress_egress[sfc]['egress_node']],
                    duration=random.choice(sfc_requests_specs['duration'])
                )

        # Return the SFC_Requests
        return sfc_requests

    def node_random_creation(self, node_num, specs_node):
        """Create the Nodes randomly

        Args:
            node_num (int): The number of Nodes that will be created
            specs_node [(str)]: The possible values of each Node attribute

        Returns:
            [type]: [description]
        """
        random.seed(self.random_seed)
        location_probability = {}
        locations = {}
        for location in specs_node['location']:
            location_probability[location['key']] = round(location['node_prob'],2)
            locations[location['key']] = location

        dic2 = dict(sorted(location_probability.items(), key=lambda item: item[1]))
        accumulated_probability = 0
        for loc in dic2.items():
            accumulated_probability += loc[1]
            dic2[loc[0]] = accumulated_probability

        # Nodes creation
        nodes = {}
        for i in range(node_num):
            name = 'n_{}'.format(i)
            energy_max = random.choice(specs_node['energy_max'])

            # is there are none values in energy_idle, use the 0.7 of the energy max
            # otherwise random select the value in the list given
            if len(specs_node['energy_idle']) == 0:
                energy_idle = energy_max * 0.7
            else:
                # Found in among the possible energy_idle those lower than the energy_max randomly selected
                possible_energy_idle = []
                for aux_energy_idle in specs_node['energy_idle']:
                    if aux_energy_idle < energy_max:
                        possible_energy_idle.append(aux_energy_idle)

                energy_idle = energy_max * 0.7
                if len(possible_energy_idle) > 0:
                    energy_idle = random.choice(possible_energy_idle)

            ran_node_prob = specs_node['ran_node_prob']
            core_node_prob = specs_node['core_node_prob']
            type_prob = random.random()

            node_type = str(Node.DEFAULT_NODE)
            if type_prob <= ran_node_prob:
                node_type = str(Node.RAN_NODE)

            if ran_node_prob < type_prob <= (ran_node_prob + core_node_prob):
                node_type = str(Node.CORE_NODE)

            # at least one node must be RAN type
            if i == 0:
                node_type = str(Node.RAN_NODE)

            # at least one node must be CORE type
            if i == (node_num-1):
                node_type = str(Node.CORE_NODE)

            # Select the Location
            node_prob_loc = random.random()
            location_selected = ""
            for prob in dic2.items():
                if node_prob_loc <= prob[1]:
                    location_selected = prob[0]
                    break

            nodes[name] = Node(
                name,
                random.choice(specs_node['group']),
                random.choice(specs_node['cpu']),
                random.choice(specs_node['mem']),
                random.sample(list(self.vnfs), k=random.choice(specs_node['vnf_num'])),
                energy_max,
                energy_idle,
                random.choice(specs_node['disk_delay']),
                node_type,
                locations[location_selected]
            )

        # Each VNF must have at least one node where instances can be executed.
        # because of that, if there is a VNF that can be run in any node we are place
        # it in a random server
        for vnf in self.vnfs:
            candidate_nodes = []
            for node in nodes:
                if vnf in nodes[node].vnfs:
                    candidate_nodes.append(node)

            # If there are no node then select one randomly
            # Because of it, sometimes, one node can be assigned to run more than the max vnf
            # defined in the configuration environment file
            if len(candidate_nodes) == 0:
                node_name = random.choice(list(nodes))
                node_selected = nodes[node_name]
                node_selected.vnfs.append(vnf)

        return nodes

    def link_random_creation(self, node_num, specs_link):
        """Create the links randomly

        Args:
            node_num (int): Number of edge nodes 
            specs_link (array): The possible values of each Link attribute

        Returns:
            [type]: [description]
        """
        # Create the virtual link between all the nodes
        random.seed(self.random_seed)

        # If the max_packet_queue was not defined it will the queue in the link will be considered unlimited
        if not 'max_packet_queue' in specs_link:
            specs_link['max_packet_queue'] = [-1]

        links = {}

        # Create the loopback link (link from the host for the same host)
        for i in range(node_num):
            node_1 = 'n_{}'.format(i)

            # create the link from A -> A
            name_loopback = "l_{}_loopback".format(i, node_1)
            link_loopback = Link(
                name=name_loopback,
                bandwidth=random.choice(specs_link['loopback_bandwidth']),
                loss_rate=0,
                source=node_1,
                target=node_1,
                counter=1,
                propagation=0,
                energy_consumption=0,
                max_packet_queue=-1
            )

            links[name_loopback] = link_loopback

        # Create links for all the nodes
        for i in range(node_num):
            node_1 = 'n_{}'.format(i)
            for j in range(node_num):
                if (i < j):
                    # if random.random() <= 0.2:
                    #     break

                    node_2 = 'n_{}'.format(j)
                    num_links_between_nodes = random.choice(specs_link['num_links_between_nodes'])

                    for k in range(num_links_between_nodes):
                        # create the link from A -> B
                        name1 = "l_{}_{}_{}".format(i, j, k)
                        link1 = Link(
                            name=name1,
                            bandwidth=random.choice(specs_link['bandwidth']),
                            loss_rate=random.choice(specs_link['loss_rate']),
                            source=node_1,
                            target=node_2,
                            counter=k,
                            propagation=random.choice(specs_link['propagation']),
                            energy_consumption=random.choice(specs_link['energy_consumption']),
                            max_packet_queue=random.choice(specs_link['max_packet_queue'])
                        )

                        # create the link from B -> A
                        name2 = "l_{}_{}_{}".format(j, i, k)
                        link2 = Link(
                            name=name2,
                            bandwidth=link1.bandwidth,
                            loss_rate=link1.loss_rate,
                            source=node_2,
                            target=node_1,
                            counter=k,
                            propagation=link1.propagation,
                            energy_consumption=link1.energy_consumption,
                            max_packet_queue=random.choice(specs_link['max_packet_queue'])
                        )

                        # In this simulation the link has the same attributes, but it is possible to change and
                        # make a more realist link where the packet from A->B travels from one path and the packet
                        # from B->A travels from another path.

                        # the key is a set of (source, target)
                        links[name1] = link1
                        links[name2] = link2

        return links

    def save_sfcs_notplaced(self, sfcs, file_path="."):
        """Save the SFCs not placed into a CSV file

        Args:
            file_path (str, optional): The path where the file will be stored. Defaults to ".".
            sfcs (dict): The SFCs that cold not be placed by the algorithm
        """

        sfcs_notplaced_column = ["User", "SFC"]
        sfcs_notplaced = pd.DataFrame(columns=sfcs_notplaced_column)

        # create the dir if it not exist
        if not os.path.exists(file_path):
            os.makedirs(file_path)

        for sfc in sfcs:
            sfcs_notplaced = pd.concat([pd.DataFrame([[
                sfc[0],
                sfc[1],
            ]], columns=sfcs_notplaced_column), sfcs_notplaced], ignore_index=True)

        file_name = "{}/sfcs_notplaced.csv".format(file_path)

        # Generate the CVS files white the logs
        sfcs_notplaced.to_csv(file_name, sep=';', index=False, quoting=csv.QUOTE_NONE)

    def save_entities_csv(self, file_path=".", log_link_entity=True):
        Node.save_csv(self.nodes, file_path)
        VNF.save_csv(self.vnfs, file_path)
        SFC.save_csv(self.sfcs, file_path)
        User.save_csv(self.users, file_path)
        Data_Source.save_csv(self.data_sources, file_path)
        SFC_Request.save_csv(self.sfc_requests, file_path)

        if log_link_entity:
            Link.save_csv(self.links, file_path)

    def get_links(self, node_source_name, node_target_name):
        """
        Return the links between two nodes

        Args:
            node_source_name (str): The source node name
            node_target_name (str): The target node name
        """
        links = []
        for aux in self.links:
            link = self.links[aux]
            if link.source == node_source_name and link.target == node_target_name:
                links.append(link)

        return links

    def save_entities_json(self, file_name):

        # create the dir if it not exist
        file_path = os.path.dirname(file_name)
        if not os.path.exists(file_path):
            os.makedirs(file_path)

        # generate a object to save for the users
        users = []
        for user in self.users:
            aux_user = self.users[user]
            users.append({
                'name': aux_user.name,
                'sfcs': aux_user.sfcs,
                'latency': aux_user.latency,
                'bandwidth': aux_user.bandwidth,
                'loss_rate': aux_user.loss_rate,
                'node': aux_user.node.name,
                'sfc_ingress_egress': aux_user.sfc_ingress_egress,
                'priority': aux_user.priority
            })

        # generate a object to save for the sfcs
        sfcs = []
        for sfc in self.sfcs:
            aux_sfc = self.sfcs[sfc]
            enum_prio = []
            for e in aux_sfc.priorities_order:
                enum_prio.append(e.name)

            aux = {
                'name': aux_sfc.name,
                'vnfs': aux_sfc.vnfs,
                'max_latency': aux_sfc.max_latency,
                'priorities_order': enum_prio,
                'timeout': aux_sfc.timeout
            }

            sfcs.append(aux)

            # generate a object to save for the users
        vnfs = []
        for vnf in self.vnfs:
            aux_vnf = self.vnfs[vnf]
            vnfs.append({
                'name': aux_vnf.name,
                'cpu': aux_vnf.cpu,
                'mem': aux_vnf.mem,
                'max_share': aux_vnf.max_share,
                'min_bandwidth': aux_vnf.min_bandwidth,
                'packet_mem_demand': aux_vnf.packet_mem_demand,
                'remote_data_access_cost': aux_vnf.remote_data_access_cost,
                'remote_data_access_prob': aux_vnf.remote_data_access_prob,
                'packet_cpu_demand': aux_vnf.packet_cpu_demand,
                'packet_network_demand': aux_vnf.packet_network_demand,
                'startup_ipt': aux_vnf.startup_ipt,
                'shutdown_ipt': aux_vnf.shutdown_ipt,
                'timeout': aux_vnf.timeout,
                'max_packet_queue': aux_vnf.max_packet_queue,
                'resource_intensive': aux_vnf.resource_intensive
            })

        # generate a object to save for the nodes
        nodes = []
        for node in self.nodes:
            aux_node = self.nodes[node]
            nodes.append({
                'name': aux_node.name,
                'group': aux_node.group,
                'node_type': aux_node.node_type,
                'cpu': aux_node.cpu,
                'mem': aux_node.mem,
                'vnfs': aux_node.vnfs,
                'energy_max': aux_node.energy_max,
                'energy_idle': aux_node.energy_idle,
                'disk_delay': aux_node.disk_delay,
                'location': aux_node.location
            })

        # generate a object to save for the links
        links = []
        for link in self.links:
            aux_link = self.links[link]
            links.append({
                'name': aux_link.name,
                'bandwidth': aux_link.bandwidth,
                'loss_rate': aux_link.loss_rate,
                'counter': aux_link.counter,
                'source': aux_link.source,
                'target': aux_link.target,
                'propagation': aux_link.propagation,
                'energy_consumption': aux_link.energy_consumption,
            })

        data_sources = []
        for src in self.data_sources:
            aux_src = self.data_sources[src]
            data_sources.append({
                'name': aux_src.name,
                'packet_size': aux_src.packet_size,
                'packet_interval': aux_src.packet_interval,
                'packets_burst_interval': aux_src.packets_burst_interval,
                'packets_burst_size': aux_src.packets_burst_size,
            })

        sfc_requests = []
        for sfc_req in self.sfc_requests:
            aux_sfc_req = self.sfc_requests[sfc_req]
            sfc_requests.append({
                'name': aux_sfc_req.name,
                'user': aux_sfc_req.user.name,
                'sfc': aux_sfc_req.sfc.name,
                'data_source': aux_sfc_req.data_source.name,
                'priority': aux_sfc_req.priority,
                'arrival_time': aux_sfc_req.arrival_time,
                'ingress_node': aux_sfc_req.ingress_node.name,
                'egress_node': aux_sfc_req.egress_node.name,
                'duration': aux_sfc_req.duration
            })

        data = {
            'users': users,
            'sfcs': sfcs,
            'vnfs': vnfs,
            'nodes': nodes,
            'links': links,
            'data_sources': data_sources,
            'sfc_requests': sfc_requests
        }

        file = open(file_name, 'w')
        file.write(json.dumps(data, indent=2))
        file.close()

    def load_entities_json(self, file_name):
        file = open(file_name, "r")
        data = eval(file.read())
        file.close()

        # load the nodes
        self.nodes = []
        nodes = {}
        for node in data['nodes']:
            nodes[node['name']] = Node(
                name=node['name'],
                group=node['group'],
                node_type=node['node_type'],
                cpu=node['cpu'],
                mem=node['mem'],
                vnfs=node['vnfs'],
                energy_max=node['energy_max'],
                energy_idle=node['energy_idle'],
                disk_delay=node['disk_delay'],
                location=node['location']
            )

        self.nodes = nodes

        # load the links
        self.links = []
        links = {}
        for link in data['links']:
            aux_link = Link(
                name=link['name'],
                counter=link['counter'],
                bandwidth=link['bandwidth'],
                loss_rate=link['loss_rate'],
                source=link['source'],
                target=link['target'],
                propagation=link['propagation'],
                energy_consumption=link['energy_consumption']
            )

            # the key is a set of (source, target)
            links[(link['source'], link['target'])] = aux_link
            links[(link['target'], link['source'])] = aux_link

        self.links = links

        # load the users
        self.users = []
        users = {}
        for user in data['users']:
            users[user['name']] = User(
                name=user['name'],
                sfcs=user['sfcs'],
                latency=user['latency'],
                bandwidth=user['bandwidth'],
                loss_rate=user['loss_rate'],
                node=self.nodes[user['node']],
                priority=user['priority']
            )

            for sfc in user['sfc_ingress_egress']:
                aux = user['sfc_ingress_egress'][sfc]
                users[user['name']].add_ingress_egress(sfc, aux['ingress_node'], aux['egress_node'], aux['packet_size'])

        self.users = users

        # load the VNFs
        self.vnfs = []
        vnfs = {}
        for vnf in data['vnfs']:
            vnfs[vnf['name']] = VNF(
                name=vnf['name'],
                cpu=vnf['cpu'],
                mem=vnf['mem'],
                max_share=vnf['max_share'],
                min_bandwidth=vnf['min_bandwidth'],
                packet_mem_demand=vnf['packet_mem_demand'],
                remote_data_access_cost=vnf['remote_data_access_cost'],
                remote_data_access_prob=vnf['remote_data_access_prob'],
                packet_cpu_demand=vnf['packet_cpu_demand'],
                packet_network_demand=vnf['packet_network_demand'],
                startup_ipt=vnf['startup_ipt'],
                shutdown_ipt=vnf['shutdown_ipt'],
                timeout=vnf['timeout'],
                max_packet_queue=vnf['max_packet_queue'],
                resource_intensive=vnf['resource_intensive']
            )

        self.vnfs = vnfs

        # load the VNFs
        self.sfcs = []
        sfcs = {}
        for sfc in data['sfcs']:

            prio_order = []

            for aux in sfc['priorities_order']:
                prio_order.append(eval("SfcPriority.{}".format(aux)))

            sfcs[sfc['name']] = SFC(
                name=sfc['name'],
                vnfs=sfc['vnfs'],
                max_latency=sfc['max_latency'],
                priorities_order=prio_order,
                timeout=sfc['timeout']
            )

        self.sfcs = sfcs

        # Load the Data Sources
        self.data_sources = []
        data_sources = {}
        for src in data['data_sources']:
            data_sources[src['name']] = Data_Source(
                name=src['name'],
                packet_size=src['packet_size'],
                packet_interval=src['packet_interval'],
                packets_burst_interval=src['packets_burst_interval'],
                packets_burst_size=src['packets_burst_size']
            )

        self.data_sources = data_sources

        # Load the SFC_Requests
        self.sfc_requests = []
        sfc_requests = {}
        for sfc_req in data['sfc_requests']:
            sfc_requests[sfc_req['name']] = SFC_Request(
                name=sfc_req['name'],
                user=self.users[sfc_req['user']],
                sfc=self.sfcs[sfc_req['sfc']],
                data_source=self.data_sources[sfc_req['data_source']],
                priority=sfc_req['priority'],
                arrival_time=sfc_req['arrival_time'],
                ingress_node=self.nodes[sfc_req['ingress_node']],
                egress_node=self.nodes[sfc_req['egress_node']],
                duration=sfc_req['duration']
            )

        self.sfc_requests = sfc_requests