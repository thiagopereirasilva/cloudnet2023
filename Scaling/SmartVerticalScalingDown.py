import Edge_Environment
from Simulation_Data import Simulation_Data
from Scaling.Scaling import Scaling
from Simulation_Entities.VNF_Instance import VNF_Instance
from dataclasses import dataclass
import pprint
import json


@dataclass
class RIT:
    vnf: None
    load_metric: float
    process_contribution: float
    resource_allocated: float
    rit: float = 0.0

class SmartVerticalScalingDown(Scaling):

    def __init__(self,
                 env,
                 edge_environment,
                 sd,
                 resource_decrement,
                 monitor_interval,
                 monitor_window_size,
                 cpu_node_available_importance,
                 mem_node_available_importance,
                 prioritize_nodes_with_more_resource_available,
                 cpu_vnf_load_importance,
                 mem_vnf_load_importance,
                 load_vnf_instance_limit,
                 load_metric_importance,
                 process_contribution_importance,
                 resource_available_importance,
                 waiting_time_between_scaling_ups
                 ):
        """
         The definition of the Scaling Down algorithm that will scaling down the VNF instances

        Args:
            edge_environment (Edge_Environment): The edge environment
            env (Environment): The simpy simulation environment
            sd (Simulation_Data): The object that log the changes in the simulation
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
            load_metric_importance (float): Is the importance of the VNF Instance Load Metric in the RIT
            process_contribution_importance (float): Is the importance of the Contribution Metric in the RIT
            resource_available_importance (float): Is the importance of the Resource Available Metric in the RIT
            waiting_time_between_scaling_ups (int): Time that the monitor must wait after a scaling up before monitoring the SFC Instance again
        """

        self.env = env
        self.edge_environment = edge_environment

        self.resource_decrement = float(resource_decrement)

        self.sd = sd
        self.monitor_interval = int(monitor_interval)
        self.monitor_window_size = int(monitor_window_size)

        self.cpu_node_available_importance = float(cpu_node_available_importance)
        self.mem_node_available_importance = float(mem_node_available_importance)

        self.cpu_vnf_load_importance = float(cpu_vnf_load_importance)
        self.mem_vnf_load_importance = float(mem_vnf_load_importance)

        self.prioritize_nodes_with_more_resource_available = prioritize_nodes_with_more_resource_available

        self.load_vnf_instance_limit = float(load_vnf_instance_limit)

        self.load_metric_importance = float(load_metric_importance)
        self.process_contribution_importance = float(process_contribution_importance)
        self.resource_available_importance = float(resource_available_importance)

        # Validation
        if self.monitor_window_size < self.monitor_interval:
            print("Scaling Config Error: The monitor_window_size MUST be greater than the monitor_interval.")
            quit()

        self.active_packets = {} # number os packets in execution

        self.sfc_instance_last_scaling = {}  # store the simulation time where the scaling up occurs

        self.waiting_time_between_scaling_ups = int(waiting_time_between_scaling_ups)

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
                self.sd.add_monitor_event(
                    event=self.sd.EVENT_MONITOR_ACTIVATION,
                    time=self.env.now,
                    sfc_instance=sfc_instance,
                    window_size=self.monitor_window_size,
                    monitor_interval=self.monitor_interval
                )
                # if there is the dict sfc_instance_last_scaling there is a key for the sfc instance thus
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

        sfc_instance (SFC_Instance): The SFC Instance that will be scaled down
        num_packet_sla_violated (int): The number of packets that violated the SLA in the monitored time window
        num_active_packet (int): The number of packets that was not processed, dropped or got time expired
        """
        # TODO - Implementar isso aqui!!!
        sfc_instace_packet_metric = 0
        if num_packet_sla_violated == 0:
            self.planner(sfc_instance, sfc_instace_packet_metric)
        return True

    def planner(self, sfc_instance, metric):
        """
        The planner phase of the MAPE-K

        sfc_instance (SFC_Instance): The SFC Instance monitored
        metric (float): How much the SFC Instance is violating the SLA
        """
        vnf_instances = self.edge_environment.get_vnf_instance_of_sfc_instance(sfc_instance)
        dict_vnf_instance = {}
        for aux in vnf_instances:
            dict_vnf_instance[aux.name] = aux

        rits = []
        # w1=w2=w3=1
        for aux in vnf_instances:
            a = self.calc_vnf_load_metric(aux)
            b = self.process_contribution_metric(aux)
            c = 1 - self.calc_resource_available_metric(aux.node)
            rit = a*self.load_metric_importance + b*self.process_contribution_importance + c*self.resource_available_importance
            rits.append(RIT(aux, a, b, c, rit))
            
        # Sorted list of RIT metrics
        rits.sort(key=lambda x: x.rit, reverse=True)
        # print("****************Printing RIT****************")
        # pprint.pprint(rits)

        # Get the first element from list rits
        if len(rits) == 0:
            return
        vnf_instance = rits[0].vnf

        # define how much resource will be increase
        new_cpu = vnf_instance.cpu - (vnf_instance.cpu * self.resource_decrement)
        new_mem = vnf_instance.mem - (vnf_instance.mem * self.resource_decrement)

        # Set the minimum CPU and memory required to run the VNF Instance
        # print("VNF INSTANCE")
        # print(vnf_instance)
        

        if new_cpu < vnf_instance.cpu_min_required:
            new_cpu = vnf_instance.cpu_min_required
        if new_mem < vnf_instance.mem_min_required:
            new_mem = vnf_instance.mem_min_required

        # Prevent to unecessary scaling down
        if new_cpu == vnf_instance.cpu:
            self.sd.add_scaling_event(
                event=self.sd.EVENT_NO_SCALING_CPU,
                time=self.env.now,
                vnf_instance=vnf_instance,
                old=vnf_instance.cpu,
                new=vnf_instance.cpu
            )
            self.sd.add_scaling_event(
                event=self.sd.EVENT_NO_SCALING_MEM,
                time=self.env.now,
                vnf_instance=vnf_instance,
                old=vnf_instance.mem,
                new=vnf_instance.mem
            )
            total_old_cpu_sfc, total_old_mem_sfc = self.get_sfc_instance_resources(sfc_instance)
            self.sd.add_sfc_instance_resources_event(
                event=self.sd.EVENT_NO_SCALING_CPU,
                time=self.env.now,
                sfc_instance=sfc_instance,
                old_cpu=total_old_cpu_sfc,
                new_cpu=total_old_cpu_sfc,
                old_mem=total_old_mem_sfc,
                new_mem=total_old_mem_sfc
            )
            self.sd.add_sfc_instance_resources_event(
                event=self.sd.EVENT_NO_SCALING_MEM,
                time=self.env.now,
                sfc_instance=sfc_instance,
                old_cpu=total_old_cpu_sfc,
                new_cpu=total_old_cpu_sfc,
                old_mem=total_old_mem_sfc,
                new_mem=total_old_mem_sfc
            )
            return True

        self.executer(vnf_instance, sfc_instance ,new_cpu, new_mem)

        return True

    def executer(self, vnf_instance, sfc_instance, new_cpu, new_mem):
        old_cpu = vnf_instance.cpu
        old_mem = vnf_instance.mem
        total_old_cpu_sfc, total_old_mem_sfc = self.get_sfc_instance_resources(sfc_instance)
        if self.scaling_down_cpu(vnf_instance, new_cpu):

            self.sfc_instance_last_scaling[sfc_instance.name] = self.env.now

            self.sd.add_scaling_event(
                event=self.sd.EVENT_SCALING_DOWN_CPU,
                time=self.env.now,
                vnf_instance=vnf_instance,
                old=old_cpu,
                new=new_cpu
            )
            # Get the CPU and Memory allocated per SFC after the scaling
            total_new_cpu_sfc, total_new_mem_sfc = self.get_sfc_instance_resources(sfc_instance)
            self.sd.add_sfc_instance_resources_event(
                event=self.sd.EVENT_SFC_INSTANCE_CPU_DECREASE,
                time=self.env.now,
                sfc_instance=sfc_instance,
                old_cpu=total_old_cpu_sfc,
                new_cpu=total_new_cpu_sfc,
                old_mem=total_old_mem_sfc,
                new_mem=total_new_mem_sfc
            )            
        else:
            self.sd.add_scaling_event(
                event=self.sd.EVENT_SCALING_DOWN_CPU_FAIL,
                time=self.env.now,
                vnf_instance=vnf_instance,
                old=old_cpu,
                new=new_cpu
            )
            self.sd.add_scaling_event(
                event=self.sd.EVENT_NO_SCALING_CPU,
                time=self.env.now,
                vnf_instance=vnf_instance,
                old=vnf_instance.cpu,
                new=vnf_instance.cpu
            )

        if self.scaling_down_mem(vnf_instance, new_mem):
            # Get the CPU and Memory allocated per SFC after the scaling
            total_new_cpu_sfc, total_new_mem_sfc = self.get_sfc_instance_resources(sfc_instance)
            self.sd.add_scaling_event(
                event=self.sd.EVENT_SCALING_DOWN_MEM,
                time=self.env.now,
                vnf_instance=vnf_instance,
                old=old_mem,
                new=new_mem
            )
            self.sd.add_sfc_instance_resources_event(
                event=self.sd.EVENT_SFC_INSTANCE_MEM_DECREASE,
                time=self.env.now,
                sfc_instance=sfc_instance,
                old_cpu=total_old_cpu_sfc,
                new_cpu=total_new_cpu_sfc,
                old_mem=total_old_mem_sfc,
                new_mem=total_new_mem_sfc
            )
            # total_old_cpu_sfc, total_old_mem_sfc = self.get_sfc_instance_resources(sfc_instance)
            self.sd.add_sfc_instance_resources_event(
                event=self.sd.EVENT_NO_SCALING_CPU,
                time=self.env.now,
                sfc_instance=sfc_instance,
                old_cpu=total_old_cpu_sfc,
                new_cpu=total_old_cpu_sfc,
                old_mem=total_old_mem_sfc,
                new_mem=total_new_mem_sfc
            )

        else:
            self.sd.add_scaling_event(
                event=self.sd.EVENT_SCALING_DOWN_MEM_FAIL,
                time=self.env.now,
                vnf_instance=vnf_instance,
                old=old_mem,
                new=new_mem
            )
            self.sd.add_scaling_event(
                    event=self.sd.EVENT_NO_SCALING_MEM,
                    time=self.env.now,
                    vnf_instance=vnf_instance,
                    old=vnf_instance.mem,
                    new=vnf_instance.mem
            )
            total_old_cpu_sfc, total_old_mem_sfc = self.get_sfc_instance_resources(sfc_instance)
            self.sd.add_sfc_instance_resources_event(
                event=self.sd.EVENT_NO_SCALING_MEM,
                time=self.env.now,
                sfc_instance=sfc_instance,
                old_cpu=total_old_cpu_sfc,
                new_cpu=total_old_cpu_sfc,
                old_mem=total_old_mem_sfc,
                new_mem=total_old_mem_sfc
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

    def process_contribution_metric(self, vnf_instance):
        """
        Process contribution metric is the part B of metric RIT
        Retrieve Pck_CPU_Demand from vnf.csv
        """
        return vnf_instance.vnf.packet_cpu_demand

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

        return round((cpu_load*self.cpu_vnf_load_importance + mem_load*self.mem_vnf_load_importance)/2,2)

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
