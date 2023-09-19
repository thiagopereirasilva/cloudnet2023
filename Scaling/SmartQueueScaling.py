from Scaling.RLAgent import RLAgent, ActionType
from Scaling.RLAgentProcessor import RLAgentProcessor, AgentInstances
import Edge_Environment
from Simulation_Data import Simulation_Data
from Scaling.Scaling import Scaling
import json
import pandas as pd
import numpy as np

class SmartQueueScaling(Scaling):
    def __init__(self, env, edge_environment, sd, resource_increment, resource_decrement, monitor_interval,
                 monitor_window_size, acceptable_sla_violation_rate, waiting_time_between_scalings_ups,
                 scaling_up_threshold, scaling_down_threshold, node_cpu_threshold, resource_increase_type,
                 monitor_control_strategy_type, monitor_vnf_cpu_load_threshold, monitor_max_window_size,
                 resource_decrement_delta, scaling_threshold_delta):
        """
         The definition of the Scaling algorithm that will scaling up/down the VNF instances

        Args:
            edge_environment (Edge_Environment): The edge environment
            env (Environment): The simpy simulation environment
            sd (Simulation_Data): The object that log the changes in the simulation
            monitor_interval (int): The interval between the monitors of the VNF Instances
            monitor_window_size (int): The size of the window packet monitor, if 2000 and the monitor interval is 500 in the simulation time 5000 the packet events monitored will be between 3000 and 5000
            waiting_time_between_scalings_ups (int): Time that the monitor must wait after a scaling up before monitoring the SFC Instance again
            acceptable_sla_violation_rate (float): Is the acceptable SLA violation rate of an SFC instance
            monitor_control_strategy_type (str): Specify the strategy used to control the monitor interval and monitor window size
            monitor_vnf_cpu_load_threshold (float): Sets the maximum tolerated load of VNF instances. If any VNF instance exceeds this limit, then the window size and monitoring interval are reduced
            monitor_max_window_size (int): Specifies the maximum possible size for the monitoring interval and window size
            resource_decrement_delta (float): Specifies the amount of change in the resource decrement in scaling down operation
        """

        self.env = env
        self.edge_environment = edge_environment

        self.sd = sd

        self.monitor_interval = int(monitor_interval)
        self.monitor_window_size = int(monitor_window_size)
        self.monitor_max_window_size = int(monitor_max_window_size)
        self.monitor_MSS = 10
        self.monitor_ssthresh = 9999999
        self.monitor_vnf_cpu_load_threshold = float(monitor_vnf_cpu_load_threshold)
        self.monitor_elapsed_time = 0
        self.monitor_interval_max = -1
        self.monitor_control_strategy_type = monitor_control_strategy_type        

        self.resource_increase_type = resource_increase_type

        self.resource_increment = float(resource_increment)
        self.resource_decrement = float(resource_decrement)

        self.acceptable_sla_violation_rate = json.loads(acceptable_sla_violation_rate.replace("'", "\""))
        self.node_cpu_threshold = float(node_cpu_threshold)

        self.waiting_time_between_scalings = int(waiting_time_between_scalings_ups)
        self.sfc_instance_last_scaling = {} # store the simulation time where the scaling up occurs

        self.rl_agent_processor = RLAgentProcessor()
        
        # self.scaling_threshold_delta = 0.05
        self.scaling_threshold_delta = float(scaling_threshold_delta)
        self.scaling_up_threshold = float(scaling_up_threshold)
        self.scaling_down_threshold = float(scaling_down_threshold)
        self.resource_decrement_delta = float(resource_decrement_delta)

        self.vnf_instance_up_threshold = {}
        self.vnf_instance_down_threshold = {}
        self.vnf_instance_agents_up = {}
        self.vnf_instance_agents_down = {}

        self.vnf_instance_resource_decrement = {}
        self.vnf_instance_agents_resource_down = {}

        # Controls de increasing rate of resources
        # With suscessive scaling ups we change the rate of resource growth,
        # decreasing the rate with each scaling up. This strategy avoids overprovisioning.
        self.resource_increase_decay = 0.9
        self.resource_increment_decayed = self.resource_increment
        self.sucessive_scaling_ups = False        

        # Validation
        if self.monitor_window_size < self.monitor_interval:
            print("Scaling Config Error: The monitor_window_size MUST be greater than the monitor_interval.")
            quit()

        self.active_packets = {} # number os packets in execution

    def get_vnf_allowed_service_time(self, vnf_instance, sfc_instance, sfc_instance_links_latency):
        """
        Calc the allowed service time of a VNF Instance in the SFC Instance

        vnf_instance (VNF_Instance): The VNF Instance
        sfc_instance (SFC_Instance): The SFC Instance
        """

        vnf_instances = self.edge_environment.get_vnf_instance_of_sfc_instance(sfc_instance)

        max_latency = sfc_instance.sfc.max_latency - sfc_instance_links_latency

        total_packet_delay_sfc_instance = 0
        for instance in vnf_instances:
            total_packet_delay_sfc_instance += instance.cpu

        allowed_service_time = (vnf_instance.cpu / total_packet_delay_sfc_instance) * max_latency

        return allowed_service_time

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

    def get_all_packets_events_from_vnf_instance(self, vnf_instance, start_time, end_time):
        vnf_instance_packet_events = pd.DataFrame()

        for sfc_instance in self.edge_environment.sfc_instances:
            vnf_instances = self.edge_environment.get_vnf_instance_of_sfc_instance(sfc_instance)
            vnf_instance_names = [vnf_instance.name for vnf_instance in vnf_instances]

            if vnf_instance.name in vnf_instance_names:
                events = self.sd.get_packets_events_from_vnf_instance(vnf_instance.name, sfc_instance.name, start_time, end_time)
                vnf_instance_packet_events = vnf_instance_packet_events.append(events)

        return vnf_instance_packet_events

    def get_sfc_instance_latency(self, sfc_instance, data_volume):
        vnf_instances = self.edge_environment.get_vnf_instance_of_sfc_instance(sfc_instance)
        latency = 0.

        for i in range(len(vnf_instances) - 1):
            src_node_name = vnf_instances[i].node.name
            dst_node_name = vnf_instances[i+1].node.name
            link = self.edge_environment.get_links(src_node_name, dst_node_name)[0]
            latency += link.get_latency(data_volume)

        return latency

    def initialize_sfc_instance_info(self, vnf_instances):
        sfc_instance_arrival = {}

        for vnf_instance in vnf_instances:
            sfc_instance_arrival[vnf_instance.name] = {'n_packets': 0, 'data_volume': 0}

        return sfc_instance_arrival

    def get_vnf_service_rate(self, vnf_instance_cpu, departure_volume):
        if departure_volume == 0:
            return 0

        vnf_service_time = (departure_volume / float(vnf_instance_cpu)) * 10**3
        vnf_service_rate = 1 / vnf_service_time

        return vnf_service_rate

    def get_vnf_instance_scaling_probability(self, arrival_rate, service_rate, allowed_service_time):
        exponent = ((service_rate - arrival_rate) * allowed_service_time) * (-1.0)
        # print("arrival_rate: ", arrival_rate)
        # print("service_rate: ", service_rate)
        # print("allowed_service_time: ", allowed_service_time)
        # print("exponent: ", exponent)
        # print("probability: ", np.format_float_positional(np.exp(exponent), trim="-"))
        # print()
        return np.exp(exponent)

    def get_linear_resource_increase(self, vnf_instance):
        # If this is a suscessive scaling up operation
        if self.sucessive_scaling_ups:
            extra_cpu = vnf_instance.cpu * self.resource_increment_decayed
            extra_mem = vnf_instance.mem * self.resource_increment_decayed
        else:
            extra_cpu = vnf_instance.cpu * self.resource_increment
            extra_mem = vnf_instance.mem * self.resource_increment
        return extra_cpu, extra_mem

    def get_tcp_inspired_resource_increase(self, vnf_instance, available_resource):
        if vnf_instance.cpu > (vnf_instance.node.cpu * self.node_cpu_threshold):
            extra_cpu = vnf_instance.cpu * self.resource_increment
            extra_mem = vnf_instance.mem * self.resource_increment
            # print("Stop exponential increase")

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

        return extra_cpu, extra_mem

    def set_monitor_interval_TCP_Reno(self, sfc_instance, start_time, end_time):
        """"
        Defines the new monitor interval and monitor window size considering the TCP Reno strategy.
        Therefore, using a dynamic monitor interval strategy, both the size of the monitor window
        and actuation intervals of the monitor component (monitor interval) will be dynamic.
        How this strategy works.
        First, during the Slow-Start phase, both monitor interval and monitor window is duplicated
        until there is a SLA violation or the load of VNF instances increase to a predefined threshold (variable EVENT_MONITOR_INTERVAL_INCREASE).
        The Congestion Avoidance phase linearly increases the size of the interval using a factor defined
        by monitor_MSS variable.
        When there is a SLA violation or the load of VNF instances increase to a predefined threshold,
        the monitor interval and monitor window is set to half of the current monitor interval and monitor window, respectively.

        sfc_instance (SFC_Instance): The SFC Instance monitored
        start_time (int): The initial time of the current monitor interval
        end_time (int): The final time of the current monitor interval
        """
        self.monitor_MSS = int(sfc_instance.sfc.max_latency*0.2)
        # get all the events in the window monitored
        window_monitor_events = self.sd.get_packets_events_from_sfc_instance(sfc_instance.name, start_time, end_time)

        # number of packet violated during the time window
        packet_sla_violated_in_window = window_monitor_events[window_monitor_events['Event'] == self.sd.EVENT_PACKET_SLA_VIOLATED].shape[0]

        # get all VNF instances from SFC
        vnf_instances = self.edge_environment.get_vnf_instance_of_sfc_instance(sfc_instance)
        HIGH_VNF_LOAD_FLAG = False
        for vnf_instance in vnf_instances:
            if vnf_instance.cpu_load > self.monitor_vnf_cpu_load_threshold:
                HIGH_VNF_LOAD_FLAG = True
                break
        
        # There are no SLA violations and the VNF load is below the monitor_vnf_cpu_threshold
        if (packet_sla_violated_in_window <= 0 & HIGH_VNF_LOAD_FLAG == False):

            # Slow-start phase (duplicates monitor interval and monitor window until the ssthresh)
            if (self.monitor_interval < self.monitor_ssthresh):
                self.monitor_interval = int(self.monitor_interval * 2)
                self.monitor_window_size = int(self.monitor_window_size * 2)

            # Linear increase after reached the ssthresh
            else:               
                self.monitor_interval = self.monitor_interval + self.monitor_MSS
                self.monitor_window_size = self.monitor_window_size + self.monitor_MSS

            # Ensure that monitor interval and monitor_will not be larger than the maximum tolerated size
            self.monitor_interval = min(self.monitor_interval, self.monitor_max_window_size)
            self.monitor_window_size = min(self.monitor_window_size, self.monitor_max_window_size)

            self.sd.add_monitor_event(
                event=self.sd.EVENT_MONITOR_INTERVAL_INCREASE,
                time=self.env.now,
                sfc_instance=sfc_instance,
                window_size=self.monitor_window_size,
                monitor_interval=self.monitor_interval
            )

        # decrease the monitor interval, monitor window and ssthresh
        else:
            self.monitor_ssthresh = max(int(self.monitor_interval / 2), self.monitor_MSS)

            self.monitor_interval = self.monitor_ssthresh + 3 * self.monitor_MSS
            self.monitor_window_size = self.monitor_ssthresh + 3 * self.monitor_MSS

            self.sd.add_monitor_event(
                event=self.sd.EVENT_MONITOR_INTERVAL_DECREASE,
                time=self.env.now,
                sfc_instance=sfc_instance,
                window_size=self.monitor_window_size,
                monitor_interval=self.monitor_interval
            )

    def set_monitor_interval_TCP_CUBIC(self, sfc_instance, start_time, end_time):
        """"
        This is the implementantion of CUBIC strategy to adjust the size of
        monitor window and monitor interval. The TCP CUBIC Congestion Control
        is defined in RFC 8312 (https://datatracker.ietf.org/doc/html/rfc8312).        
        CUBIC uses the following window increase function:
            W_cubic(t) = C*(t-K)^3 + W_max (Eq. 1)
        where C is a constant fixed to determine the aggressiveness of window
        increase in high BDP networks, t is the elapsed time from the
        beginning of the current congestion avoidance, and K is the time
        period that the above function takes to increase the current window
        size to W_max if there are no further congestion events and is
        calculated using the following equation:
            K = cubic_root(W_max*(1-beta_cubic)/C) (Eq. 2)
        where beta_cubic is the CUBIC multiplication decrease factor, that
        is, when a congestion event is detected, CUBIC reduces its cwnd to
        W_cubic(0)=W_max*beta_cubic.


        sfc_instance (SFC_Instance): The SFC Instance monitored
        start_time (int): The initial time of the current monitor interval
        end_time (int): The final time of the current monitor interval
        """
        # Set the MSS to 20% of the SLA. E.g., SLA=30 ms, than MSS=6
        self.monitor_MSS = int(sfc_instance.sfc.max_latency*0.2)
        # TCP CUBIC constants
        CONSTANT_beta = 0.7
        CONSTANT_C = 0.4

        # get all the events in the window monitored
        window_monitor_events = self.sd.get_packets_events_from_sfc_instance(sfc_instance.name, start_time, end_time)

        # number of packet violated during the time window
        packet_sla_violated_in_window = window_monitor_events[window_monitor_events['Event'] == self.sd.EVENT_PACKET_SLA_VIOLATED].shape[0]

        # get all VNF instances from SFC
        vnf_instances = self.edge_environment.get_vnf_instance_of_sfc_instance(sfc_instance)
        HIGH_VNF_LOAD_FLAG = False
        for vnf_instance in vnf_instances:
            if vnf_instance.cpu_load > self.monitor_vnf_cpu_load_threshold:
                HIGH_VNF_LOAD_FLAG = True
                break

        # Firt time running this method
        if self.monitor_elapsed_time == -1:
            self.monitor_elapsed_time = 1
        else:
            # Convert monitor_interval to seconds
            self.monitor_elapsed_time = self.monitor_elapsed_time + (self.monitor_interval / 1000.0)

        # There are no SLA violations and the VNF load is below the monitor_vnf_cpu_threshold
        if (packet_sla_violated_in_window <= 0 & HIGH_VNF_LOAD_FLAG == False):
            
            self.monitor_interval_max = self.monitor_interval

            # Slow-start phase (duplicates monitor_interval and monitor_window_size until ssthresh)
            if (self.monitor_interval < self.monitor_ssthresh):

                self.monitor_interval = int(self.monitor_interval * 2)
                self.monitor_window_size = int(self.monitor_window_size * 2)

            # CUBIC Window Increase Function after reached the ssthresh
            else:                
                # K = cubic_root(W_max*(1-beta_cubic)/C) (Eq. 2)
                K = int(((self.monitor_interval_max*(1-CONSTANT_beta))/CONSTANT_C)**(1./3.))

                # W_cubic(t) = C*(t-K)^3 + W_max (Eq. 1)
                self.monitor_interval = int(CONSTANT_C*(self.monitor_elapsed_time - K)**3 + self.monitor_interval_max)
                self.monitor_window_size = int(CONSTANT_C*(self.monitor_elapsed_time - K)**3 + self.monitor_interval_max)
            
            # Ensure that monitor interval and monitor_will not be larger than the maximum tolerated size
            self.monitor_interval = min(self.monitor_interval, self.monitor_max_window_size)
            self.monitor_window_size = min(self.monitor_window_size, self.monitor_max_window_size)
            self.monitor_interval_max = self.monitor_interval

            self.sd.add_monitor_event(
                event=self.sd.EVENT_MONITOR_INTERVAL_INCREASE,
                time=self.env.now,
                sfc_instance=sfc_instance,
                window_size=self.monitor_window_size,
                monitor_interval=self.monitor_interval
            )
        
        # decrease the monitor interval, monitor window, and ssthresh
        else:
            self.monitor_elapsed_time = 1
            self.monitor_interval_max = self.monitor_interval

            self.monitor_ssthresh = int(self.monitor_interval * CONSTANT_beta)
            self.monitor_ssthresh = max(self.monitor_ssthresh, self.monitor_MSS)
            
            self.monitor_interval = int (self.monitor_interval * CONSTANT_beta)
            self.monitor_window_size = int(self.monitor_window_size * CONSTANT_beta)

            self.sd.add_monitor_event(
                event=self.sd.EVENT_MONITOR_INTERVAL_DECREASE,
                time=self.env.now,
                sfc_instance=sfc_instance,
                window_size=self.monitor_window_size,
                monitor_interval=self.monitor_interval
            )

    def stop(self):
        for sfc_instance in self.edge_environment.sfc_instances:
            vnf_instances = self.edge_environment.get_vnf_instance_of_sfc_instance(sfc_instance)

            for vnf_instance in vnf_instances:
                '''
                    LEMBRAR DE ATUALIZAR O CAMINHO
                '''
                # self.vnf_instance_agents_resource_down[vnf_instance.name].save_agent("")

    def initialize_agents(self, vnf_instance):
        if vnf_instance.name in self.vnf_instance_agents_resource_down:
            return

        weight_list = [0.75, 0.25]
        exploration_min = 0.02
        exploration_max = 1.0
        exploration_decay = 0.99
        discount_factor = 0.9

        self.vnf_instance_agents_up[vnf_instance.name] = RLAgent(vnf_instance.name + "-up", [1],
                                                                         exploration_min, exploration_max,
                                                                         exploration_decay, discount_factor)

        self.vnf_instance_agents_down[vnf_instance.name] = RLAgent(vnf_instance.name + "-down", [1],
                                                                           exploration_min, exploration_max,
                                                                           exploration_decay, discount_factor)

        self.vnf_instance_agents_resource_down[vnf_instance.name] = RLAgent(vnf_instance.name, weight_list,
                                                                         exploration_min, exploration_max,
                                                                         exploration_decay, discount_factor)
        '''
            LEMBRAR DE ATUALIZAR O CAMINHO
        '''
        self.vnf_instance_agents_up[vnf_instance.name].load_agent("")
        self.vnf_instance_agents_down[vnf_instance.name].load_agent("")

        self.vnf_instance_up_threshold[vnf_instance.name] = self.scaling_up_threshold
        self.vnf_instance_down_threshold[vnf_instance.name] = self.scaling_down_threshold

        self.vnf_instance_agents_resource_down[vnf_instance.name].load_agent("")
        self.vnf_instance_resource_decrement[vnf_instance.name] = self.resource_decrement

    def get_rl_state(self, vnf_instance, packets_violated, active_packets):
        node_available_resource = self.edge_environment.get_node_available_resource(
            self.edge_environment.vnf_instances, vnf_instance.node.name)

        cpu_occupation = min(1.0, vnf_instance.cpu_load)
        host_cpu_availability = node_available_resource['cpu'] / float(vnf_instance.node.cpu)

        try:
            sla_violations = packets_violated / float(active_packets)
        except ZeroDivisionError:
            sla_violations = 0.0
        
        # if (1-sla_violations < 0):
        #     print(packets_violated, active_packets)    

        state = (cpu_occupation, host_cpu_availability, 1 - sla_violations)

        return state

    def get_rl_agents_actions_for(self, vnf_instance, packets_violated, active_packets):
        agent_resource_dec = self.vnf_instance_agents_resource_down[vnf_instance.name]
        agent_up = self.vnf_instance_agents_up[vnf_instance.name]
        agent_down = self.vnf_instance_agents_down[vnf_instance.name]

        state = self.get_rl_state(vnf_instance, packets_violated, active_packets)

        self.rl_agent_processor.set_instance(agent_resource_dec, AgentInstances.RESOURCE_DECREMENT)
        action_param_dict = self.rl_agent_processor.act(state, self.vnf_instance_resource_decrement[vnf_instance.name],
                                                        self.resource_decrement_delta)
        action_resource = action_param_dict['action']
        self.vnf_instance_resource_decrement[vnf_instance.name] = action_param_dict['updated_parameter']

        self.rl_agent_processor.set_instance(agent_up, AgentInstances.THRESHOLD_UP)
        action_param_dict = self.rl_agent_processor.act(state, self.vnf_instance_up_threshold[vnf_instance.name],
                                                        self.scaling_threshold_delta)
        action_up = action_param_dict['action']
        self.vnf_instance_up_threshold[vnf_instance.name] = action_param_dict['updated_parameter']

        self.rl_agent_processor.set_instance(agent_down, AgentInstances.THRESHOLD_DOWN)
        action_param_dict = self.rl_agent_processor.act(state, self.vnf_instance_down_threshold[vnf_instance.name],
                                                        self.scaling_threshold_delta)
        action_down = action_param_dict['action']
        self.vnf_instance_down_threshold[vnf_instance.name] = action_param_dict['updated_parameter']
    
        performed_actions = {'resource': action_resource, 'up': action_up, 'down': action_down}

        return performed_actions

    def update_rl_agents_for(self, vnf_instance, actions, state, next_state):
        # return
        agent_resource = self.vnf_instance_agents_resource_down[vnf_instance.name]
        self.rl_agent_processor.set_instance(agent_resource, AgentInstances.RESOURCE_DECREMENT)
        self.rl_agent_processor.update(actions['resource'], state, next_state)

        agent_up = self.vnf_instance_agents_up[vnf_instance.name]
        self.rl_agent_processor.set_instance(agent_up, AgentInstances.THRESHOLD_UP)
        self.rl_agent_processor.update(actions['up'], state, next_state)

        agent_down = self.vnf_instance_agents_down[vnf_instance.name]
        self.rl_agent_processor.set_instance(agent_down, AgentInstances.THRESHOLD_DOWN)
        self.rl_agent_processor.update(actions['down'], state, next_state)

        state_label = (RLAgent.get_cpu_occupation_state_label(state[0]),
                       RLAgent.get_host_cpu_availability_state_label(state[1]))
        
        event = ""

        if actions['resource'] == ActionType.ACTION_INCREASE:
            event = self.sd.EVENT_RLAGENT_INCREASE_RESOURCE_DECREMENT
        elif actions['resource'] == ActionType.ACTION_DECREASE:
            event = self.sd.EVENT_RLAGENT_DECREASE_RESOURCE_DECREMENT
        elif actions['resource'] == ActionType.ACTION_MAINTAIN:
            event = self.sd.EVENT_RLAGENT_MAINTAIN_RESOURCE_DECREMENT

        '''
            Atualizar o log do agente para ter somente um valor de alteração do threshold e da recompensa.
            A identificação de qual foi o agente e a ação está no evento.
        '''

        self.sd.add_RLAgent_event(
            event=event,
            time=self.env.now,
            vnf_instance=vnf_instance,
            agent="RESOURCE",
            value=self.vnf_instance_resource_decrement[vnf_instance.name],
            # new_threshold_down=self.vnf_instance_down_threshold[vnf_instance.name],
            new_reward=agent_resource.get_q_table_value(state_label, actions['resource']),
            # new_reward_down=agent_up.get_q_table_value(state_label, actions['down'])
        )

        state_label = (RLAgent.get_sla_violations_state_label(state[-1]))
                       

        if actions['up'] == ActionType.ACTION_INCREASE:
            event = self.sd.EVENT_RLAGENT_INCREASE_THRESHOLD_UP
        elif actions['up'] == ActionType.ACTION_DECREASE:
            event = self.sd.EVENT_RLAGENT_DECREASE_THRESHOLD_UP
        elif actions['up'] == ActionType.ACTION_MAINTAIN:
            event = self.sd.EVENT_RLAGENT_MAINTAIN_THRESHOLD_UP

        '''
            Atualizar o log do agente para ter somente um valor de alteração do threshold e da recompensa.
            A identificação de qual foi o agente e a ação está no evento.
        '''

        self.sd.add_RLAgent_event(
            event=event,
            time=self.env.now,
            vnf_instance=vnf_instance,
            agent="UP",
            value=self.vnf_instance_up_threshold[vnf_instance.name],
            # new_threshold_down=self.vnf_instance_down_threshold[vnf_instance.name],
            new_reward=agent_up.get_q_table_value(state_label, actions['up']),
            # new_reward_down=agent_up.get_q_table_value(state_label, actions['down'])
        )

        if actions['down'] == ActionType.ACTION_INCREASE:
            event = self.sd.EVENT_RLAGENT_INCREASE_THRESHOLD_DOWN
        elif actions['down'] == ActionType.ACTION_DECREASE:
            event = self.sd.EVENT_RLAGENT_DECREASE_THRESHOLD_DOWN
        elif actions['down'] == ActionType.ACTION_MAINTAIN:
            event = self.sd.EVENT_RLAGENT_MAINTAIN_THRESHOLD_DOWN

        self.sd.add_RLAgent_event(
            event=event,
            time=self.env.now,
            vnf_instance=vnf_instance,
            # new_threshold_up=self.vnf_instance_up_threshold[vnf_instance.name],
            agent="DOWN",
            value=self.vnf_instance_down_threshold[vnf_instance.name],
            # new_reward_up=agent_down.get_q_table_value(state_label, actions['up']),
            new_reward=agent_down.get_q_table_value(state_label, actions['down'])
        )

    def monitor(self):
        while True:
            # Avoid monitoring at time zero
            if self.env.now == 0:
                yield self.env.timeout(self.monitor_interval)
                continue

            monitor_window = self.get_monitor_window()
            end_time = monitor_window["end_time"]
            start_time = monitor_window["start_time"]
            start_new_events_time = monitor_window["star_new_events_time"]

            # For each SFC_Instance in the environment execute the monitoring
            for sfc_instance in self.edge_environment.sfc_instances:
                # if there is in the dict sfc_instance_last_scaling there is a key for the sfc instance thus
                # wait the time configure until perform the monitor again

                self.sd.add_monitor_event(
                    event=self.sd.EVENT_MONITOR_ACTIVATION,
                    time=self.env.now,
                    sfc_instance=sfc_instance,
                    window_size=self.monitor_window_size,
                    monitor_interval=self.monitor_interval
                )
                # Define new values for monitor_interval and monitor_window considering a
                #  TCP congestion control strategy or None
                if self.monitor_control_strategy_type == 'TCPCubic':
                    self.set_monitor_interval_TCP_CUBIC(sfc_instance, start_time, end_time)
                elif (self.monitor_control_strategy_type == 'TCPReno'):
                    self.set_monitor_interval_TCP_Reno(sfc_instance, start_time, end_time)

                if sfc_instance.name in self.sfc_instance_last_scaling:
                    del self.sfc_instance_last_scaling[sfc_instance.name]
                    yield self.env.timeout(self.waiting_time_between_scalings)

                if sfc_instance.active:
                    # Creat the item in the dictionary
                    if sfc_instance.name not in self.active_packets:
                        self.active_packets[sfc_instance.name] = 0

                    # get all the events in the window monitored
                    window_monitor_events = self.sd.get_packets_events_from_sfc_instance(sfc_instance.name,
                                                                                         start_time, end_time)

                    # get all the new events in the window monitored
                    new_packet_events = self.sd.get_packets_events_from_sfc_instance(sfc_instance.name,
                                                                                     start_new_events_time, end_time)

                    # number of packet violated during the time window
                    packet_sla_violated_in_window = new_packet_events[
                        new_packet_events['Event'] == self.sd.EVENT_PACKET_SLA_VIOLATED].shape[0]

                    actived_packets = self.active_packets[sfc_instance.name]
                    created_packets = new_packet_events[new_packet_events['Event'] == self.sd.EVENT_PACKET_CREATED].shape[0]
                    processed_packets = new_packet_events[new_packet_events['Event'] == self.sd.EVENT_PACKET_PROCESSED].shape[0]
                    
                    # if processed_packets > (actived_packets+created_packets):
                    #     print(actived_packets, created_packets, processed_packets)
                    # ATIVOS - CRIADOS - PROCESSADOS
                    # print(self.active_packets[sfc_instance.name], new_packet_events[new_packet_events['Event'] == self.sd.EVENT_PACKET_CREATED].shape[0],
                    #     new_packet_events[new_packet_events['Event'] == self.sd.EVENT_PACKET_PROCESSED].shape[0])


                    self.active_packets[sfc_instance.name] += \
                        new_packet_events[new_packet_events['Event'] == self.sd.EVENT_PACKET_CREATED].shape[0]

                    max_actived_packets_in_window = self.active_packets[sfc_instance.name]
                    # print("max_actived_packets_in_window = {}".format(max_actived_packets_in_window))

                    # if max_actived_packets_in_window < packet_sla_violated_in_window:
                    #     # print('menor')
                    #     print(len(new_packet_events[new_packet_events['Event'] == self.sd.EVENT_PACKET_SLA_VIOLATED]))

                    self.active_packets[sfc_instance.name] -= \
                        new_packet_events[new_packet_events['Event'] == self.sd.EVENT_PACKET_PROCESSED].shape[0]
                    

                    self.active_packets[sfc_instance.name] -= \
                        new_packet_events[new_packet_events['Event'] == self.sd.EVENT_PACKET_ORPHAN].shape[0]
                    self.active_packets[sfc_instance.name] -= \
                        new_packet_events[new_packet_events['Event'] == self.sd.EVENT_LINK_PACKET_DROPPED_QUEUE].shape[0]
                    self.active_packets[sfc_instance.name] -= \
                        new_packet_events[new_packet_events['Event'] == self.sd.EVENT_PACKET_DROPPED_VNF_INSTANCE_QUEUE].shape[0]
                    self.active_packets[sfc_instance.name] -= \
                        new_packet_events[new_packet_events['Event'] == self.sd.EVENT_PACKET_SIMULATION_TIME_EXPIRED].shape[0]

                    self.active_packets[sfc_instance.name] = max(0, self.active_packets[sfc_instance.name])
                    
                    vnf_instances = self.edge_environment.get_vnf_instance_of_sfc_instance(sfc_instance)

                    sfc_instance_arrival_info = self.initialize_sfc_instance_info(vnf_instances)
                    sfc_instance_departure_info = self.initialize_sfc_instance_info(vnf_instances)
                    rl_actions = -1

                    # Get all the VNF Instances mapped by the SFC Instance monitored
                    for vnf_instance in vnf_instances:
                        self.initialize_agents(vnf_instance)

                        vnf_instance_packet_events = self.get_all_packets_events_from_vnf_instance(vnf_instance, start_time, end_time)

                        # vnf instance arrival events
                        vnf_arrival_events = vnf_instance_packet_events[vnf_instance_packet_events['Event'] == self.sd.VNF_INSTANCE_PACKET_ARRIVED]

                        # vnf instance departure events
                        vnf_service_events = vnf_instance_packet_events[vnf_instance_packet_events['Event'] == self.sd.VNF_INSTANCE_PACKET_PROCESSED]

                        if not vnf_arrival_events.empty:
                            sfc_instance_arrival_info[vnf_instance.name]['n_packets'] = vnf_arrival_events.shape[0]
                            sfc_instance_arrival_info[vnf_instance.name]['data_volume'] = vnf_arrival_events['Size'].sum()

                        if not vnf_service_events.empty:
                            sfc_instance_departure_info[vnf_instance.name]['n_packets'] = vnf_service_events.shape[0]
                            sfc_instance_departure_info[vnf_instance.name]['data_volume'] = vnf_service_events['Size'].sum()

                        rl_actions = self.get_rl_agents_actions_for(vnf_instance, packet_sla_violated_in_window,
                                                                                  max_actived_packets_in_window)

                    self.analyzer(sfc_instance, sfc_instance_arrival_info, sfc_instance_departure_info,
                              packet_sla_violated_in_window, max_actived_packets_in_window,
                              rl_actions)

            # Wait a period to monitoring the SFC
            yield self.env.timeout(self.monitor_interval)

    def analyzer(self, sfc_instance, sfc_instance_arrival_info, sfc_instance_departure_info,
                 num_packet_sla_violated, num_active_packet, rl_actions):
        """"
        Analyzer
        sfc_instance (SFC_Instance): The SFC Instance monitored
        sfc_instance_arrival_info (dict): The arrival rates of each VNF Instance that composes the monitored
        SFC Instance
        """
        monitor_window = self.get_monitor_window()
        end_time = monitor_window["end_time"]
        start_time = monitor_window["start_time"]

        vnf_instances = self.edge_environment.get_vnf_instance_of_sfc_instance(sfc_instance)

        sfc_instance_queue_params = {}

        for vnf_instance in vnf_instances:
            vnf_arrival_rate = sfc_instance_arrival_info[vnf_instance.name]['n_packets'] / (end_time - start_time)
            vnf_departure_volume = sfc_instance_departure_info[vnf_instance.name]['data_volume'] / \
                                   (end_time - start_time)

            vnf_service_rate = self.get_vnf_service_rate(vnf_instance.cpu, vnf_departure_volume)

            sfc_instance_links_latency = self.get_sfc_instance_latency(sfc_instance,
                                                            sfc_instance_arrival_info[vnf_instance.name]['data_volume'])
            vnf_packet_allowed_service_time = self.get_vnf_allowed_service_time(vnf_instance, sfc_instance,
                                                                         sfc_instance_links_latency)
            vnf_allowed_service_time = vnf_packet_allowed_service_time * \
                                       sfc_instance_arrival_info[vnf_instance.name]['n_packets']

            sfc_instance_queue_params[vnf_instance.name] = {'arrival_rate': vnf_arrival_rate,
                                                            'allowed_service_time': vnf_allowed_service_time,
                                                            'service_rate': vnf_service_rate}

        sfc_instance_packet_metric = 0
        if num_active_packet > 0:
            sfc_instance_packet_metric = (num_packet_sla_violated / float(num_active_packet))
            # print(sfc_instance_packet_metric)

        self.planner(sfc_instance, num_packet_sla_violated, num_active_packet, sfc_instance_queue_params,
                     sfc_instance_departure_info, sfc_instance_packet_metric, rl_actions)
        return True

    def planner(self, sfc_instance, num_packet_sla_violated, num_active_packet, sfc_instance_queue_params,
                sfc_instance_departure_info, sfc_instance_packet_metric, rl_actions):
        """
        The planner phase of the MAPE-K
        sfc_instance (SFC_Instance): The SFC Instance monitored
        sfc_instance_queue_params (dict): The M/M/1 model parameters of each VNF Instance that composes the
        SFC Instance
        """

        vnf_instances = self.edge_environment.get_vnf_instance_of_sfc_instance(sfc_instance)

        sla_violation_rate = float(self.acceptable_sla_violation_rate['default'])

        if sfc_instance.sfc.name in self.acceptable_sla_violation_rate:
            sla_violation_rate = float(self.acceptable_sla_violation_rate[sfc_instance.sfc.name])

        for vnf_instance in vnf_instances:
            current_state = self.get_rl_state(vnf_instance, num_packet_sla_violated, num_active_packet)

            vnf_arrival_rate = sfc_instance_queue_params[vnf_instance.name]['arrival_rate']
            vnf_service_rate = sfc_instance_queue_params[vnf_instance.name]['service_rate']
            vnf_allowed_service_time = sfc_instance_queue_params[vnf_instance.name]['allowed_service_time']

            vnf_scaling_prob = self.get_vnf_instance_scaling_probability(vnf_arrival_rate, vnf_service_rate,
                                                                         vnf_allowed_service_time)

            node_available_resource = self.edge_environment.get_node_available_resource(
                self.edge_environment.vnf_instances, vnf_instance.node.name)
            # print(vnf_arrival_rate)
            if vnf_arrival_rate > 0 and (sfc_instance_packet_metric >= sla_violation_rate or
                    vnf_scaling_prob > self.vnf_instance_up_threshold[vnf_instance.name]):

                if sfc_instance_packet_metric < sla_violation_rate:
                    extra_cpu, extra_mem = self.get_linear_resource_increase(vnf_instance)

                    if extra_cpu < node_available_resource['cpu'] and extra_mem < node_available_resource['mem']:
                        self.executer_scaling_up(vnf_instance, sfc_instance, extra_cpu, extra_mem)

                # elif self.resource_increase_type == "TCPInspiredIncrease":
                else:
                    extra_cpu, extra_mem = self.get_tcp_inspired_resource_increase(vnf_instance, node_available_resource)

                    if extra_cpu > 0.0 and extra_mem > 0.0:
                        self.executer_scaling_up(vnf_instance, sfc_instance, extra_cpu, extra_mem)
                # else:
                    # print("The resource increase type '" + self.resource_increase_type + "' is not known.")
                    # quit()

            elif vnf_arrival_rate == 0 or vnf_scaling_prob < self.vnf_instance_down_threshold[vnf_instance.name]:
                # define how much resource will be increase
                new_cpu = vnf_instance.cpu - (vnf_instance.cpu * self.vnf_instance_resource_decrement[vnf_instance.name])
                new_mem = vnf_instance.mem - (vnf_instance.mem * self.vnf_instance_resource_decrement[vnf_instance.name])

                # Set the minimum CPU and memory required to run the VNF Instance
                if new_cpu < vnf_instance.cpu_min_required:
                    new_cpu = vnf_instance.cpu_min_required
                if new_mem < vnf_instance.mem_min_required:
                    new_mem = vnf_instance.mem_min_required

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

                monitor_window = self.get_monitor_window()
                end_time = monitor_window["end_time"]
                start_time = monitor_window["start_time"]

                departure_volume = sfc_instance_departure_info[vnf_instance.name]['data_volume'] / \
                                   (end_time - start_time)
                new_vnf_service_rate = self.get_vnf_service_rate(new_cpu, departure_volume)

                try:
                    vnf_utilization_factor = vnf_arrival_rate / float(new_vnf_service_rate)
                except ZeroDivisionError:
                    vnf_utilization_factor = np.finfo(float).max

                if vnf_utilization_factor >= 1.0 and vnf_arrival_rate > 0.0:
                    return True

                self.executer_scaling_down(vnf_instance, sfc_instance, new_cpu, new_mem)

            next_state = self.get_rl_state(vnf_instance, num_packet_sla_violated, num_active_packet)
            self.update_rl_agents_for(vnf_instance, rl_actions, current_state, next_state)

        return True

    def executer_scaling_up(self, vnf_instance, sfc_instance, extra_cpu, extra_mem):
        old_cpu = vnf_instance.cpu
        old_mem = vnf_instance.mem
        new_cpu = vnf_instance.cpu + extra_cpu
        new_mem = vnf_instance.mem + extra_mem
        total_old_cpu_sfc, total_old_mem_sfc = self.get_sfc_instance_resources(sfc_instance)
        # print("Scaling Up\nold_CPU={}\t old_MEM={} in VNF {}".format(vnf_instance.cpu, vnf_instance.mem, vnf_instance.name))
        # print("new_CPU={}\t new_MEM={} in VNF {}\n".format(new_cpu, new_mem, vnf_instance.name))
        if self.scaling_up_cpu(vnf_instance, new_cpu):

            self.sfc_instance_last_scaling[sfc_instance.name] = self.env.now
            total_new_cpu_sfc, total_new_mem_sfc = self.get_sfc_instance_resources(sfc_instance)

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
                old_cpu=total_old_cpu_sfc,
                new_cpu=total_new_cpu_sfc,
                old_mem=total_old_mem_sfc,
                new_mem=total_new_mem_sfc
            )
            self.sucessive_scaling_ups = True
            self.resource_increment_decayed *= self.resource_increase_decay

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
            total_new_cpu_sfc, total_new_mem_sfc = self.get_sfc_instance_resources(sfc_instance)

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
                old_cpu=total_old_cpu_sfc,
                new_cpu=total_new_cpu_sfc,
                old_mem=total_old_mem_sfc,
                new_mem=total_new_mem_sfc
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

    def executer_scaling_down(self, vnf_instance, sfc_instance, new_cpu, new_mem):
        old_cpu = vnf_instance.cpu
        old_mem = vnf_instance.mem
        total_old_cpu_sfc, total_old_mem_sfc = self.get_sfc_instance_resources(sfc_instance)

        # print("Scaling Down\nold_CPU={}\t old_MEM={} in VNF {}".format(vnf_instance.cpu, vnf_instance.mem,
        #                                                                vnf_instance.name))
        # print("new_CPU={}\t new_MEM={} in VNF {}\n".format(new_cpu, new_mem, vnf_instance.name))

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
            self.sucessive_scaling_ups = False
            self.resource_increment_decayed = self.resource_increment
        else:
            self.sd.add_scaling_event(
                event=self.sd.EVENT_SCALING_DOWN_CPU_FAIL,
                time=self.env.now,
                vnf_instance=vnf_instance,
                old=old_cpu,
                new=new_cpu
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

        else:
            self.sd.add_scaling_event(
                event=self.sd.EVENT_SCALING_DOWN_MEM_FAIL,
                time=self.env.now,
                vnf_instance=vnf_instance,
                old=old_mem,
                new=new_mem
            )

        return False

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
