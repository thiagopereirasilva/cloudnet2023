from concurrent.futures import thread
import Edge_Environment
from Simulation_Data import Simulation_Data
from Scaling.Scaling import Scaling
from Simulation_Entities.VNF_Instance import VNF_Instance
import json

class TCPInspiredVerticalScalingUp(Scaling):

    def __init__(self, env, edge_environment, sd, resource_increment, monitor_interval, monitor_window_size, cpu_node_available_importance, mem_node_available_importance, prioritize_nodes_with_more_resource_available, cpu_vnf_load_importance, mem_vnf_load_importance, load_vnf_instance_limit, acceptable_sla_violation_rate, waiting_time_between_scaling_ups, threshold):
        """
         The TCP-Inspired scaling up algorithm doubles the amount of resources of a given VNF instance until it reaches
         a certain threshol (e.g. 50% of the available resources on the node). After that, the scaling up follows a
         progressive strategy, increasing the resources by 10%.

        Args:
            edge_environment (Edge_Environment): The edge environment
            env (Environment): The simpy simulation environment
            sd (Simulation_Data): The object that log the changes in the simulation
            resource_increment (float): The percentage of CPU and Memory increment
            monitor_interval (int): The interval between the monitors of the VNF Instances
            monitor_window_size (int): The size of the window packet monitor, if 2000 and the monitor interval is 500
            in the simulation time 5000 the packet events monitored will be between 3000 and 5000
            cpu_node_available_importance (float): value between 0-1 that define the importance of the CPU resource for the metric
            mem_node_available_importance (float): value between 0-1 that define the importance of the Mem resource for the metric
            prioritize_nodes_with_more_resource_available (int): 1 if the vnf instances running in the node with more
            resources available will be scaled firstly 0 otherwise

            cpu_vnf_load_importance (float): The importance of the cpu load in the vnf instance
            mem_vnf_load_importance (float): The importance of the mem load in the vnf instance

            load_vnf_instance_limit (float): The mim load metric required to trigger the scaling up
            acceptable_sla_violation_rate (float): Is the acceptable SLA violation rate of an SFC instance
            waiting_time_between_scaling_ups (int): Time that the monitor must wait after a scaling up before monitoring the SFC Instance again

            threshold (float): The threshold for scaling up
        """

        self.env = env
        self.edge_environment = edge_environment

        self.resource_increment = float(resource_increment)

        self.sd = sd
        self.monitor_interval = int(monitor_interval)
        self.monitor_window_size = int(monitor_window_size)

        self.cpu_node_available_importance = float(cpu_node_available_importance)
        self.mem_node_available_importance = float(mem_node_available_importance)

        self.cpu_vnf_load_importance = float(cpu_vnf_load_importance)
        self.mem_vnf_load_importance = float(mem_vnf_load_importance)

        self.prioritize_nodes_with_more_resource_available = prioritize_nodes_with_more_resource_available

        self.load_vnf_instance_limit = float(load_vnf_instance_limit)

        self.acceptable_sla_violation_rate = json.loads(acceptable_sla_violation_rate.replace("'","\""))

        self.waiting_time_between_scaling_ups = int(waiting_time_between_scaling_ups)

        self.sfc_instance_last_scaling = {} # store the simulation time where the scaling up occurs
        self.threshold = threshold

        # Validation
        if self.monitor_window_size < self.monitor_interval:
            print("Scaling Config Error: The monitor_window_size MUST be greater than the monitor_interval.")
            quit()

        self.active_packets = {} # number os packets in execution

    def get_monitor_window(self):
        end_time = self.env.now  # the window end
        start_time = end_time - self.monitor_window_size  # the start window monitor
        star_new_events_time = end_time - self.monitor_interval  # the start of the window for new events

        if star_new_events_time < 0:
            star_new_events_time = 0

        if start_time < 0:
            start_time = 0

        return {
            "end_time": end_time,
            "start_time": start_time,
            "star_new_events_time": star_new_events_time
        }

    def monitor(self):
        while True:
            # Avoid monitoring at time zero
            if self.env.now == 0:
                yield self.env.timeout(self.monitor_interval)
                continue

            aux = self.get_monitor_window()
            end_time = aux["end_time"]
            start_time = aux["start_time"]
            star_new_events_time = aux["star_new_events_time"]

            # For each SFC_Instance in the environment execute the monitoring
            for sfc_instance in self.edge_environment.sfc_instances:
                # if there in the dict sfc_instance_last_scaling there is a key for the sfc instance thus
                # wait the time configure until perfome the monitor again
                if sfc_instance.name in self.sfc_instance_last_scaling:
                    del self.sfc_instance_last_scaling[sfc_instance.name]
                    yield self.env.timeout(self.waiting_time_between_scaling_ups)

                if sfc_instance.active:
                    # Creat the item in the dictionary
                    if sfc_instance.name not in self.active_packets:
                        self.active_packets[sfc_instance.name] = 0

                    # get all the events in the window monitored
                    window_monitor_events = self.sd.get_packets_events_from_sfc_instance(sfc_instance.name, start_time, end_time)

                    # get all the new events in the window monitored
                    new_packet_events = self.sd.get_packets_events_from_sfc_instance(sfc_instance.name, star_new_events_time, end_time)

                    # number of packet violated during the time window
                    packet_sla_violated_in_window = window_monitor_events[window_monitor_events['Event'] == self.sd.EVENT_PACKET_SLA_VIOLATED].shape[0]

                    self.active_packets[sfc_instance.name] += new_packet_events[new_packet_events['Event'] == self.sd.EVENT_PACKET_CREATED].shape[0]
                    self.active_packets[sfc_instance.name] -= new_packet_events[new_packet_events['Event'] == self.sd.EVENT_PACKET_PROCESSED].shape[0]
                    self.active_packets[sfc_instance.name] -= new_packet_events[new_packet_events['Event'] == self.sd.EVENT_PACKET_ORPHAN].shape[0]
                    self.active_packets[sfc_instance.name] -= new_packet_events[new_packet_events['Event'] == self.sd.EVENT_LINK_PACKET_DROPPED_QUEUE].shape[0]
                    self.active_packets[sfc_instance.name] -= new_packet_events[new_packet_events['Event'] == self.sd.EVENT_PACKET_DROPPED_VNF_INSTANCE_QUEUE].shape[0]
                    self.active_packets[sfc_instance.name] -= new_packet_events[new_packet_events['Event'] == self.sd.EVENT_PACKET_SIMULATION_TIME_EXPIRED].shape[0]

                    # packets created in the new events montired
                    # print("-----------")
                    # print(window_monitor_events)
                    # print("Packets SLA Violated = {} ".format(packet_sla_violated_in_window))
                    # print("===============")
                    # print(new_packet_events)
                    # print("Packets Active = {} ".format(self.active_packets[sfc_instance.name]))
                    # print("-----------")

                    self.analyzer(sfc_instance, packet_sla_violated_in_window, self.active_packets[sfc_instance.name])

                else:
                    # Remove the counter
                    if sfc_instance.name in self.active_packets:
                        del self.active_packets[sfc_instance.name]

            # Wait a period to monitoring the SFC
            yield self.env.timeout(self.monitor_interval)

    def analyzer(self, sfc_instance, num_packet_sla_violated, num_active_packet):
        """"
        Analyzer

        Calc the metric based on the values collected by the monitor in the knowledge

        sfc_instance (SFC_Instance): The SFC Instance that will be scaled up
        num_packet_sla_violated (int): The number of packets that violated the SLA in the monitored time window
        num_active_packet (int): The number of packets that was not processed, dropped or got time expired

        """
        sfc_instace_packet_metric = 0
        if self.active_packets[sfc_instance.name] > 0:
            sfc_instace_packet_metric = (num_packet_sla_violated / num_active_packet)

        sla_violation_rate = float(self.acceptable_sla_violation_rate['default'])

        if sfc_instance.sfc.name in self.acceptable_sla_violation_rate:
            sla_violation_rate = float(self.acceptable_sla_violation_rate[sfc_instance.sfc.name])

        if sfc_instace_packet_metric >= sla_violation_rate:
            self.planner(sfc_instance, sfc_instace_packet_metric)
            return True

        return False

    def planner(self, sfc_instance, metric):
        """
        The planner phase of the MPKE
        sfc_instance (SFC_Instance): The SFC Instance monitored
        metric (float): How much the SFC Instance is violating the SLA
        """
        vnf_instances = self.edge_environment.get_vnf_instance_of_sfc_instance(sfc_instance)
        dict_vnf_instance = {}
        for aux in vnf_instances:
            dict_vnf_instance[aux.name] = aux

        nodes = {}
        for vnf_instance  in vnf_instances:
            node = vnf_instance.node
            if node.name not in nodes:
                # calc the metric and add into dict
                nodes[node.name] = self.calc_resource_available_metric(node)

        rev = True
        if self.prioritize_nodes_with_more_resource_available == "0":
            rev = False

        sorted_nodes = dict(sorted(nodes.items(), key=lambda x: x[1], reverse=rev))

        for node in sorted_nodes.items():
            node_name = node[0]
            available_resource = self.edge_environment.get_node_available_resource(self.edge_environment.vnf_instances, node_name)

            vnf_instance_in_node = {}
            for vnf_instance in vnf_instances:
                if vnf_instance.node.name == node_name:
                    # calc the load metric for the VNFs in the node
                    vnf_instance_in_node[vnf_instance.name] = self.calc_vnf_load_metric(vnf_instance)

            # Sort the vnf instances by the load metric (first the VNF Instance with higher load metric)
            sorted_vnf_instances = dict(sorted(vnf_instance_in_node.items(), key=lambda x: x[1], reverse=True))

            for vnf_instance_name  in sorted_vnf_instances:
                vnf_instance_load_metric = vnf_instance_in_node[vnf_instance_name]
                if vnf_instance_load_metric > self.load_vnf_instance_limit:
                    vnf_instance = dict_vnf_instance[vnf_instance_name]

                    # define how much resource will be increase
                    # print("Total CPU of node {} = {}".format(node_name, vnf_instance.node.cpu))
                    if vnf_instance.cpu > (vnf_instance.node.cpu * float(self.threshold)):
                        extra_cpu = vnf_instance.cpu * self.resource_increment
                        extra_mem = vnf_instance.mem * self.resource_increment

                    # Exponential growth - Doubles the amount of resources if the resources allocated to VNF
                    # is below the threshold (e.g., 50% of nodes' resources)
                    else:
                        extra_cpu = vnf_instance.cpu
                        extra_mem = vnf_instance.mem

                    # Ensures that all the resource currently available on the node will be allocated to the VNF.
                    if extra_cpu > available_resource['cpu']:
                        extra_cpu = available_resource['cpu']
                    if extra_mem > available_resource['mem']:
                        extra_mem = available_resource['mem']

                    self.executer(vnf_instance, sfc_instance, extra_cpu, extra_mem)                        

        return True

    def executer(self, vnf_instance, sfc_instance, extra_cpu, extra_mem):
        old_cpu = vnf_instance.cpu
        new_cpu = vnf_instance.cpu + extra_cpu

        old_mem = vnf_instance.mem
        new_mem = vnf_instance.mem + extra_mem
        total_old_cpu, total_old_mem = self.get_sfc_instance_resources(sfc_instance)
        # print("old_CPU={}\t old_MEM={} in SFC {}".format(total_old_cpu, total_old_mem, sfc_instance.name))
        # print("VNF {} - old values CPU={} Mem={}".format(vnf_instance.name, old_cpu, old_mem))
        # print("VNF {} - new values CPU={} Mem={}\n".format(vnf_instance.name, new_cpu, new_mem))
        if self.scaling_up_cpu(vnf_instance, new_cpu):

            self.sfc_instance_last_scaling[sfc_instance.name] = self.env.now

            self.sd.add_scaling_event(
                event=self.sd.EVENT_SCALING_UP_CPU,
                time=self.env.now,
                vnf_instance=vnf_instance,
                old=old_cpu,
                new=new_cpu
            )

            self.sd.add_sfc_instance_resources_event(
                event=self.sd.EVENT_SFC_INSTANCE_CPU_INCREASE,
                time=self.env.now,
                sfc_instance=sfc_instance,
                old_cpu=total_old_cpu,
                new_cpu=total_old_cpu+extra_cpu,
                old_mem=total_old_mem,
                new_mem=total_old_mem+extra_mem
            )

        else:
            self.sd.add_scaling_event(
                event=self.sd.EVENT_SCALING_UP_CPU_FAIL,
                time=self.env.now,
                vnf_instance=vnf_instance,
                old=old_cpu,
                new=new_cpu
            )

        if self.scaling_up_mem(vnf_instance, new_mem):

            self.sfc_instance_last_scaling[sfc_instance.name] = self.env.now

            self.sd.add_scaling_event(
                event=self.sd.EVENT_SCALING_UP_MEM,
                time=self.env.now,
                vnf_instance=vnf_instance,
                old=old_mem,
                new=new_mem
            )
            self.sd.add_sfc_instance_resources_event(
                event=self.sd.EVENT_SFC_INSTANCE_MEM_INCREASE,
                time=self.env.now,
                sfc_instance=sfc_instance,
                old_cpu=total_old_cpu,
                new_cpu=total_old_cpu+extra_cpu,
                old_mem=total_old_mem,
                new_mem=total_old_mem+extra_mem
            )            
        else:
            self.sd.add_scaling_event(
                event=self.sd.EVENT_SCALING_UP_MEM_FAIL,
                time=self.env.now,
                vnf_instance=vnf_instance,
                old=old_mem,
                new=new_mem
            )



        return False

    def get_sfc_instance_resources(self, sfc_instance):
        """
        Calc the total resources allocated to the SFC Instance.

        The SFC resources are the sum of the resources of each VNF instance that compose the SFC Instance
        """
        vnf_instances = self.edge_environment.get_vnf_instance_of_sfc_instance(sfc_instance)
        total_cpu = total_mem = 0
        for vnf_instance in vnf_instances:
            total_cpu += vnf_instance.cpu
            total_mem += vnf_instance.mem
        return total_cpu, total_mem

    def calc_vnf_load_metric(self, vnf_instance):
        """
        Calc the load metric for the VNF Instance

        Get all the load event during the time window and calc the avg for cpu and memory
        """
        aux = self.get_monitor_window()
        end_time = aux["end_time"]
        start_time = aux["start_time"]

        events = self.sd.get_vnf_instance_resources_events_window(vnf_instance.name, start_time, end_time)

        cpu_load = 0
        mem_load = 0
        for aux in events.iterrows():
            resource = aux[1]

            if resource.Event == 'INSTANCE_RESOURCE_USAGE_INCREASE':
                cpu_load += float(resource.CPU_Usage)
                mem_load += float(resource.Mem_Usage)

            if resource.Event == 'INSTANCE_RESOURCE_USAGE_DECREASE':
                cpu_load -= float(resource.CPU_Usage)
                mem_load -= float(resource.Mem_Usage)

        metric = round(
            (cpu_load*self.cpu_vnf_load_importance + mem_load*self.mem_vnf_load_importance) /
            (self.cpu_vnf_load_importance + self.mem_vnf_load_importance), 2)

        return metric

    def calc_resource_available_metric(self, node):
        """
        Calc the amount of resource available in the node. The metric value will be between 0 - 1
        0 = there is no resource left / 1 = all the resources are available

        The node with the greater value is the node with more available resource, if we sort asc thus
        we will try to execute the Scaling Up in the node with less resource available

        if we sort desc thus we will try to Scaling Up the VNF Instances in the node with more available resource, this
        approach will increase the ratio of SFC Requests placed because of the number of nodes with resources
        available.

        node (Node): the Node that execute at least one VNF Instance used by the SFC Instance monitored
        """
        available_resource = self.edge_environment.get_node_available_resource(self.edge_environment.vnf_instances, node.name)

        # If there is none CPU available, return 0
        if available_resource['cpu'] <= 0:
            return 0

        # If there is none Mem available, return 0
        if available_resource['mem'] <= 0:
            return 0

        cpu_perc_available = (available_resource['cpu'] / node.cpu) * self.cpu_node_available_importance
        mem_perc_available = (available_resource['mem'] / node.mem) * self.mem_node_available_importance

        metric = round((cpu_perc_available + mem_perc_available) / (self.cpu_node_available_importance+self.mem_node_available_importance), 2)

        return metric

    def run(self):
        return self.monitor()
