from textwrap import indent
from Simulation_Entities.VNF_Instance import VNF_Instance
from Simulation_Entities.SFC_Instance import SFC_Instance
from Simulation_Entities.Packet import Packet

import numpy as np
from numpy.lib.function_base import place
import pandas as pd
import os
import csv

# Object to store the data logs from the simulation
class Simulation_Data():

    # User Mobility
    EVENT_USER_MOVED = "USER_MOVED"

    # Time Window Events
    EVENT_TIME_WINDOW_STARTED         = "TIME_WINDOW_STARTED"
    EVENT_TIME_WINDOW_PROCESSED       = "TIME_WINDOW_PROCESSED"

    # Placement Events
    EVENT_PLACEMENT_STARTED        = "PLACEMENT_STARTED"
    EVENT_PLACEMENT_PROCESSED      = "PLACEMENT_PROCESSED"

    # Packets Events
    EVENT_PACKET_CREATED                     = "PACKET_CREATED"
    EVENT_PACKET_SIMULATION_TIME_EXPIRED     = "PACKET_SIMULATION_TIME_EXPIRED"
    EVENT_PACKET_PROCESSED                   = "PACKET_PROCESSED"
    EVENT_PACKET_ORPHAN                      = "PACKET_ORPHAN"
    EVENT_PACKET_SLA_VIOLATED                = "EVENT_PACKET_SLA_VIOLATED"
    EVENT_PACKET_DROPPED_VNF_INSTANCE_QUEUE  = "PACKET_DROPPED_VNF_INSTANCE_QUEUE"

    # SFC Requests  Events
    EVENT_SFC_REQUEST_PLACED       = "SFC_REQUEST_PLACED"
    EVENT_SFC_REQUEST_NOT_PLACED   = "SFC_REQUEST_NOT_PLACED"
    EVENT_SFC_REQUEST_PACKET_GENERATION_STARTED = "SFC_REQUEST_PACKET_GENERATION_STARTED"
    EVENT_SFC_REQUEST_PACKET_GENERATION_STOPPED = "SFC_REQUEST_PACKET_GENERATION_STOPPED"
    EVENT_SFC_REQUEST_REPLACED = "SFC_REQUEST_REPLACED"
    EVENT_SFC_REQUEST_REPLACEMENT_FAILED = "SFC_REQUEST_REPLACEMENT_FAILED"

    # Migration Events
    EVENT_SFC_REQUEST_ABOVE_MIGRATION_THRESHOLD = "SFC_REQUEST_ABOVE_MIGRATION_THRESHOLD"
    EVENT_SFC_REQUEST_BELOW_MIGRATION_THRESHOLD = "SFC_REQUEST_BELOW_MIGRATION_THRESHOLD"

    # SFC_Instance Events
    EVENT_SFC_INSTANCE_CREATED         = "SFC_INSTANCE_CREATED"
    EVENT_SFC_INSTANCE_DESTROYED       = "SFC_INSTANCE_DESTROYED"
    EVENT_SFC_INSTANCE_LOCKED          = "SFC_INSTANCE_LOCKED"
    EVENT_SFC_INSTANCE_UNLOCKED        = "SFC_INSTANCE_UNLOCKED"

    EVENT_SFC_INSTANCE_VNF_MAPPED      = "EVENT_SFC_INSTANCE_VNF_MAPPED"
    EVENT_SFC_INSTANCE_VNF_UNMAPPED    = "EVENT_SFC_INSTANCE_VNF_UNMAPPED"

    # VNF_Instances Packets Process Events
    VNF_INSTANCE_PACKET_ARRIVED            = "VNF_INSTANCE_PACKET_ARRIVED"
    VNF_INSTANCE_PACKET_PROCESS_STARTED    = "VNF_INSTANCE_PACKET_PROCESS_STARTED"
    VNF_INSTANCE_PACKET_PROCESSED          = "VNF_INSTANCE_PACKET_PROCESSED"
    VNF_INSTANCE_REMOTE_DATA_RECEIVED      = "VNF_INSTANCE_REMOTE_DATA_RECEIVED"
    VNF_INSTANCE_PACKET_DROPPED            = "VNF_INSTANCE_PACKET_DROPPED"

    # Contants for the Link Events
    EVENT_LINK_ARRIVED                = "LINK_PACKET_ARRIVED"
    EVENT_LINK_STARTED                = "LINK_PACKET_STARTED"
    EVENT_LINK_PROCESSED              = "LINK_PACKET_SENT"
    EVENT_LINK_PACKET_DROPPED_QUEUE   = "LINK_QUEUE_PACKET_DROPPED"

    # VNF_Instance Events
    EVENT_INSTANCE_CREATED            = "INSTANCE_CREATED"
    EVENT_INSTANCE_DESTROYED          = "INSTANCE_DESTROYED"
    EVENT_INSTANCE_STARTUP            = "INSTANCE_STARTUP"
    EVENT_INSTANCE_SHUTDOWN           = "INSTANCE_SHUTDOWN"

    EVENT_INSTANCE_CPU_AVAILABILITY_INCREASE = "CPU_INCREASE_AVAILABILITY"
    EVENT_INSTANCE_CPU_AVAILABILITY_DECREASE = "CPU_DECREASE_AVAILABILITY"

    EVENT_INSTANCE_MEM_AVAILABILITY_INCREASE = "MEM_INCREASE_AVAILABILITY"
    EVENT_INSTANCE_MEM_AVAILABILITY_DECREASE = "MEM_DECREASE_AVAILABILITY"

    EVENT_INSTANCE_RESOURCE_USAGE_INCREASE = "INSTANCE_RESOURCE_USAGE_INCREASE"
    EVENT_INSTANCE_RESOURCE_USAGE_DECREASE = "INSTANCE_RESOURCE_USAGE_DECREASE"
    EVENT_INSTANCE_RESOURCE_DISK_ACCESS    = "INSTANCE_RESOURCE_DISK_ACCESS"

    EVENT_RESOURCE_CPU_USAGE = "CPU_USAGE"

    # EVENT_INSTANCE_CPU_INCREASE_USAGE = "CPU_INCREASE_USAGE"
    # EVENT_INSTANCE_CPU_DECREASE_USAGE = "CPU_DECREASE_USAGE"
    # EVENT_INSTANCE_MEM_CHANGED        = "MEM_CHANGED"    
    # EVENT_INSTANCE_MEM_INCREASE_USAGE = "MEM_INCREASE_USAGE"
    # EVENT_INSTANCE_MEM_DECREASE_USAGE = "MEM_DECREASE_USAGE"

    #Scaling
    EVENT_SCALING_UP         = "SCALING_UP"
    EVENT_SCALING_DOWN       = "SCALING_DOWN"

    EVENT_SCALING_UP_CPU         = "SCALING_UP_CPU"
    EVENT_SCALING_UP_CPU_FAIL    = "SCALING_UP_CPU_FAIL" # when the node does not have resource
    EVENT_SCALING_DOWN_CPU       = "SCALING_DOWN_CPU"
    EVENT_SCALING_DOWN_CPU_FAIL  = "SCALING_DOWN_CPU_FAIL"
    EVENT_NO_SCALING_CPU         = "EVENT_NO_SCALING_CPU"

    EVENT_SCALING_UP_MEM         = "SCALING_UP_MEM"
    EVENT_SCALING_UP_MEM_FAIL    = "SCALING_UP_MEM_FAIL" # when the node does not have resource
    EVENT_SCALING_DOWN_MEM       = "SCALING_DOWN_MEM"
    EVENT_SCALING_DOWN_MEM_FAIL  = "SCALING_DOWN_MEM_FAIL"
    EVENT_NO_SCALING_MEM         = "EVENT_NO_SCALING_MEM"

    EVENT_SCALING_MONITORING     = "SCALING_MONITORING"

    # SFC resources events
    EVENT_SFC_INSTANCE_CPU_INCREASE = "EVENT_SFC_INSTANCE_CPU_INCREASE"
    EVENT_SFC_INSTANCE_CPU_DECREASE = "EVENT_SFC_INSTANCE_CPU_DECREASE"
    EVENT_SFC_INSTANCE_MEM_INCREASE = "EVENT_SFC_INSTANCE_MEM_INCREASE"
    EVENT_SFC_INSTANCE_MEM_DECREASE = "EVENT_SFC_INSTANCE_MEM_DECREASE"

    # Monitor events
    EVENT_MONITOR_WINDOW_SIZE_INCREASE = "EVENT_MONITOR_WINDOW_SIZE_INCREASE"
    EVENT_MONITOR_WINDOW_SIZE_DECREASE = "EVENT_MONITOR_WINDOW_SIZE_DECREASE"
    EVENT_MONITOR_INTERVAL_INCREASE    = "EVENT_MONITOR_INTERVAL_INCREASE"
    EVENT_MONITOR_INTERVAL_DECREASE    = "EVENT_MONITOR_INTERVAL_DECREASE"
    EVENT_MONITOR_ACTIVATION           = "EVENT_MONITOR_ACTIVATION"

    # RL Agent events
    EVENT_RLAGENT_INCREASE_RESOURCE_DECREMENT = "EVENT_RLAGENT_INCREASE_RESOURCE_DECREMENT"
    EVENT_RLAGENT_MAINTAIN_RESOURCE_DECREMENT = "EVENT_RLAGENT_MAINTAIN_RESOURCE_DECREMENT"
    EVENT_RLAGENT_DECREASE_RESOURCE_DECREMENT = "EVENT_RLAGENT_DECREASE_RESOURCE_DECREMENT"

    EVENT_RLAGENT_INCREASE_THRESHOLD_UP = "EVENT_RLAGENT_INCREASE_THRESHOLD_UP"
    EVENT_RLAGENT_MAINTAIN_THRESHOLD_UP = "EVENT_RLAGENT_MAINTAIN_THRESHOLD_UP"
    EVENT_RLAGENT_DECREASE_THRESHOLD_UP = "EVENT_RLAGENT_DECREASE_THRESHOLD_UP"

    EVENT_RLAGENT_INCREASE_THRESHOLD_DOWN = "EVENT_RLAGENT_INCREASE_THRESHOLD_DOWN"
    EVENT_RLAGENT_MAINTAIN_THRESHOLD_DOWN = "EVENT_RLAGENT_MAINTAIN_THRESHOLD_DOWN"
    EVENT_RLAGENT_DECREASE_THRESHOLD_DOWN = "EVENT_RLAGENT_DECREASE_THRESHOLD_DOWN"
    
    # Collumns name for the events
    resource_usage_columns         = ["Event", "Time", "Value"]
    time_window_columns            = ["Event", "Time", "Window Init", "Window_End", "SFC_Requests_Placed", "SFC_Requests_Not_Placed", "CPU_Allocated", "Mem_Allocated", "VNF_Instances_Count", "SFC_Instances_Count", "Total_Alg_Time", "Count_SFC_Requests", "SFC_Requests","Total_Energy_Consumption"]
    packets_columns                = ["Event", "Time", "Packet_ID", "SFC_Request", "SFC_Instance", "User", "SFC", "Data_Source"]
    vnf_instance_packets_columns   = ["Event", "Time", "Packet_ID", "VNF_Instance", "SFC_Request", "SFC_Instance", "User", "SFC", "Data_Source", "Size", "Elapsed_Time"]
    vnf_instance_resources_columns = ["Event", "Time", "VNF_Instance", "CPU", "CPU_Usage", "Mem", "Mem_Usage", "User", "SFC_Request", "SFC_Instance", "Packet_ID"]
    placement_columns              = ["Event", "Time"]
    vnf_instance_columns           = ["Event", "Time", "VNF_Instance", "Node", "VNF", "VNF_CPU", "VNF_Mem"]
    sfc_instance_columns           = ["Event", "Time", "SFC_Instance"]
    sfc_requests_columns           = ["Event", "Time", "SFC_Request", "SFC_Instance", "Placement_Order"]
    links_columns                = ["Event", "Time", "Packet_ID", "Link", "SFC_Request", "SFC_Instance", "User", "SFC", "Data_Source", "VNF_Instance", "Packet_Size"]

    sfc_instance_vnf_mapping_columns = ["Event", "Time", "SFC_Instance", "VNF_Instance"]

    scaling_columns = ["Event", "Time", "VNF_Instance", "Old", "New"]

    user_mobility_columns = ["Event", "Time", "User", "Origin_Node", "Destiny_Node"]

    migration_columns     = ["Event", "Time", "SFC_Request", "User"]

    sfc_instance_resources_columns =  ["Event", "Time", "SFC_Instance", "old_CPU", "new_CPU", "old_Mem", "new_Mem"]

    monitor_columns = ["Event", "Time", "SFC_Instance", "Window_Size", "Monitor_Interval"]
    
    rlagent_columns = ["Event", "Time", "VNF_Instance", "Agent", "Value", "Reward"]

    # sfcs = pd.DataFrame(columns=sfcs_columns)
    # scaling =  pd.DataFrame(columns=scaling_columns)
    # resources             = pd.DataFrame(columns=resources_columns)
    scaling_buffer = []
    vnf_instance_resources_buffer = []
    vnf_instance_packets_buffer = []
    vnf_instance_buffer = []
    sfc_instance_buffer = []
    links_buffer = []
    sfc_request_buffer = []
    placement_buffer = []
    time_window_buffer = []
    packets_buffer = []
    sfc_instance_vnf_mapping_buffer = []
    user_mobility_buffer = []
    migration_buffer = []
    sfc_instance_resources_buffer = []
    resource_usage_buffer = []
    monitor_buffer = []
    rlagent_buffer = []

    vnf_instance_resources      = pd.DataFrame(columns=vnf_instance_resources_columns)
    vnf_instance_packets        = pd.DataFrame(columns=vnf_instance_packets_columns)
    vnf_instance                = pd.DataFrame(columns=vnf_instance_columns)
    sfc_instance                = pd.DataFrame(columns=sfc_instance_columns)
    links                       = pd.DataFrame(columns=links_columns)    
    sfc_request                 = pd.DataFrame(columns=sfc_requests_columns)    
    placement                   = pd.DataFrame(columns=placement_columns)
    time_window                 = pd.DataFrame(columns=time_window_columns)
    packets                     = pd.DataFrame(columns=packets_columns)
    sfc_instance_vnf_mapping    = pd.DataFrame(columns=sfc_instance_vnf_mapping_columns)
    user_mobility               = pd.DataFrame(columns=user_mobility_columns)
    migration                   = pd.DataFrame(columns=migration_columns)
    scaling                     = pd.DataFrame(columns=scaling_columns)
    sfc_instance_resources      = pd.DataFrame(columns=sfc_instance_resources_columns)
    resource_usage              = pd.DataFrame(columns=resource_usage_columns)
    monitor                     = pd.DataFrame(columns=monitor_columns)
    rlagent                     = pd.DataFrame(columns=rlagent_columns)

    def add_user_mobility_event(self, event, time, user_name, origin_node_name, destiny_node_name):
        """Add a new SFC Instance event, created or destroyed

        Args:
            event (str): The event type
            time (int): Time simulation
            user (User): The User
            origin_node_name (Node): actual node
            destiny_node_name (Node): new node
        """
        self.user_mobility_buffer.insert(0,[
            event,
            "{:.2f}".format(time),
            user_name,
            origin_node_name,
            destiny_node_name
        ])

    def get_user_mobility_events(self):
        self.user_mobility = self.flush_events(self.user_mobility, self.user_mobility_buffer)
        return self.user_mobility

    def get_num_packets_ingress_sfc_instance(self, sfc_instance, start, end):
        """Return the number of packets that ingress in a SFC_Instance

        Args:
            sfc_instance (SFC_Instance): The SFC_Instance
            start (int): The start time
            end (int): The duration time
        """        
        columns_name_sfc_instance = "SFC Instance"
        df = self.packets
        df = df.loc[(df[columns_name_sfc_instance] == sfc_instance.name) & (df['Event'] == self.EVENT_PACKET_CREATED) & (pd.to_numeric(df['Time']) >= start) & (pd.to_numeric(df['Time']) <= end)]

        return df.shape[0]

    def check_service_delay_above_threshold(self, df_packets, df_vnf_packets, number_of_packets, migration_threshold, sfc_req):
        df_vnf_packets.Time = pd.to_numeric(df_vnf_packets["Time"])
        df_vnf_packets = df_vnf_packets.sort_values(by='Time', ascending=False)
        df_vnf_packets = df_vnf_packets.head(number_of_packets)
        
        packets_to_consider = df_vnf_packets["Packet_ID"].unique()
        df_packets = df_packets.loc[(df_packets["Packet_ID"].isin(packets_to_consider))]

        aux = pd.merge(df_packets, df_vnf_packets, how = 'inner', on=["User", "Packet_ID", "SFC_Request", "SFC_Instance", "SFC", "Data_Source"])
        aux['Latency'] = pd.to_numeric(aux['Time_y']) - pd.to_numeric(aux['Time_x'])
        #print(aux)
        #if sfc_req == "r_1":
            #if(str(aux["Latency"].mean()) != "nan"):
        #    print(sfc_req, "mean: "+str(aux["Latency"].mean()), "threshold:", migration_threshold)
        if aux["Latency"].mean() > migration_threshold:
            return True
        return False   

    def get_services_above_migration_threshold(self, sfc_instance, number_of_packets, migration_threshold):
        """Get the SFC Requests whose last N packets has a latency average above migration threshold

        Args:
            sfc_instance (SFC_Instance): The SFC_Instance
            number_of_packets (int): The number of most recent packets processed by a VNF to be considered.
            migration_threshold (float): The migration threshold to be compared with average latency
        """   
        above_threshold_services = []
        df_packets = self.packets
        df_vnf_packets = self.get_vnf_instance_packets_events()
        df_vnf_packets["Time"] = pd.to_numeric(df_vnf_packets["Time"])
        df_packets = df_packets.loc[(df_packets["SFC_Instance"] == sfc_instance.name) & (df_packets['Event'] == self.EVENT_PACKET_CREATED)]
            
        df_vnf_packets = df_vnf_packets.loc[(df_vnf_packets['Event'] == self.VNF_INSTANCE_PACKET_PROCESSED)]

        idx = df_vnf_packets.groupby(['Packet_ID'])['Time'].transform(max) == df_vnf_packets['Time']
        df_vnf_packets = df_vnf_packets[idx]
        for sfc_req in sfc_instance.get_sfc_requests_names():
            if sfc_req not in above_threshold_services and self.check_service_delay_above_threshold(df_packets.loc[(df_packets["SFC_Request"] == sfc_req)], df_vnf_packets.loc[(df_vnf_packets["SFC_Request"] == sfc_req)].copy(), number_of_packets, migration_threshold, sfc_req):
                above_threshold_services.append(sfc_req)
        return above_threshold_services

        #for vnf_instance in vnf_instances:      
        #    df_vnf_inst_packets = df_vnf_packets.loc[(df_vnf_packets["VNF_Instance"] == vnf_instance.name) & (df_vnf_packets['Event'] == self.VNF_INSTANCE_PACKET_PROCESSED)]
        #    for sfc_req in sfc_instance.sfc_requests:
        #        if sfc_req not in above_threshold_services and self.check_service_delay_above_threshold(df_packets.loc[(df_packets["SFC_Request"] == sfc_req)], df_vnf_inst_packets.loc[(df_vnf_inst_packets["SFC_Request"] == sfc_req)].copy(), number_of_packets, migration_threshold):
        #            above_threshold_services.append(sfc_req)
        #return above_threshold_services

    def get_num_packets_violated_sla(self, sfc_instance, start, end):
        """Return a dataframe with the packet that violated the sla in the interval

        Args:
            sfc_instance (SFC_Instance): The SFC_Instance
            start (int): The start time
            end (int): The duration time
        """
        columns_name_sfc_instance = "SFC_Instance"

        df = self.get_packets_events()

        df_packet_violated = df.loc[(df[columns_name_sfc_instance] == sfc_instance.name) & (df['Event'] == self.EVENT_PACKET_SLA_VIOLATED) & (pd.to_numeric(df['Time']) >= start) & (pd.to_numeric(df['Time']) <= end)]

        return df_packet_violated
        # df_processed = df.loc[(df[columns_name_sfc_instance] == sfc_instance.name) & (df['Event'] == self.EVENT_PACKET_PROCESSED) & (pd.to_numeric(df['Time']) >= start) & (pd.to_numeric(df['Time']) <= end)]
        # aux = pd.merge(df_created, df_processed, how = 'inner', on=["Packet_ID", "SFC_Request"])
        # aux['Latency'] = pd.to_numeric(aux['Time_y']) - pd.to_numeric(aux['Time_x'])
        # aux2 = aux.loc[aux["Latency"] > max_latency]
        # return aux2.shape[0]

    def add_time_window_event(self, event, time, window_init, window_end, sfc_requests, sfc_requests_placed=0,
                              sfc_requests_not_placed=0, total_cpu_allocated=0, total_mem_allocated=0,
                              vnf_instances_count=0, sfc_instances_count=0, total_alg_time = 0,
                              total_energy_consumption = 0):
        """Add a new Time Window event to the log system

        Args:
            event (str): The event type
            time (int): Time simulation
            window_init (int): The time window init
            window_end (int): The time window end
            sfc_requests (list): A list with the sfc_requests processed in that time_window
            sfc_requests_placed (int): The number of sfc_requested placed in that time window
            sfc_requests_not_placed (int): The number of sfc_requested not placed in that time window
            total_cpu_allocated (int): The amount of cpu used
            total_mem_allocated (int): The amount of mem used
            vnf_instances_count (int): The total of VNF Instances active
            sfc_instances_count (int): The total of SFC Instances active
            total_alg_time (float): The total REAL time for creating the placement plan
        """
        aux_list = []
        for sfc_request in sfc_requests:
            aux_list.append(sfc_request.name)

        self.time_window_buffer.insert(0,[
            event, 
            "{:.2f}".format(time),
            window_init,
            window_end,
            sfc_requests_placed,
            sfc_requests_not_placed,
            total_cpu_allocated,
            total_mem_allocated,
            vnf_instances_count,
            sfc_instances_count,
            total_alg_time,
            len(aux_list),
            aux_list,
            total_energy_consumption
        ])

    def get_time_window_events(self):
        self.time_window = self.flush_events(self.time_window, self.time_window_buffer)
        return self.time_window

    def add_packet_event(self, event, time, packet_id, sfc_request):
        """Add packets events

        Args:
            event (str): The event type
            time (int): The simulation time
            packet_id (int): The Packet ID            
            sfc_request (SFC_Request): The SFC_Request
        """

        ## SFC_INSTANCE_MISSED THE SFC INSTANCE MAPPED FOR THE SFC REQUEST WAS DROPPED
        sfc_instance_name = ""
        if sfc_request.sfc_instance:
            sfc_instance_name = sfc_request.sfc_instance.name

        self.packets_buffer.insert(0,[
            event, 
            "{:.2f}".format(time),
            packet_id,
            sfc_request.name,
            sfc_instance_name,
            sfc_request.user.name,
            sfc_request.sfc.name,
            sfc_request.data_source.name,
        ])

    def get_packets_events(self):
        self.packets = self.flush_events(self.packets, self.packets_buffer)
        return self.packets

    def get_packets_events_from_sfc_instance(self, sfc_instance_name, start_time, end_time):
        """
        Return all the packet event from an SFC Instance

        sfc_instance_name (str): The name of the SFC Instance
        start_time: Return events with time higher than start_time
        end_time: Return events with time below the end_time
        """
        self.packets = self.flush_events(self.packets, self.packets_buffer)
        self.packets["Time"] = pd.to_numeric(self.packets["Time"])
        # print(start_time, end_time)
        return self.packets[(self.packets["SFC_Instance"] == sfc_instance_name) & (self.packets["Time"] >= start_time)
                            & (self.packets["Time"] < end_time)]

    def get_packets_events_from_vnf_instance(self, vnf_instance_name, sfc_instance_name, start_time, end_time):
        """
        Return all the packet event from an SFC Instance

        sfc_instance_name (str): The name of the SFC Instance
        start_time: Return events with time higher than start_time
        end_time: Return events with time below the end_time
        """
        self.vnf_instance_packets = self.get_vnf_instance_packets_events()

        self.vnf_instance_packets["Time"] = pd.to_numeric(self.vnf_instance_packets["Time"])

        return self.vnf_instance_packets[
            (self.vnf_instance_packets["VNF_Instance"] == vnf_instance_name) &
            (self.vnf_instance_packets["SFC_Instance"] == sfc_instance_name) &
            (self.vnf_instance_packets["Time"] >= start_time) & (self.vnf_instance_packets["Time"] < end_time)
        ]

    def add_placement_event(self, event, time):
        """Add a new VNF event to the log system

        Args:
            event (str): The event type
            time (int): Time simulation
        """
        self.placement_buffer.insert(0,[
            event, 
            "{:.2f}".format(time)
        ])

    def get_placement_events(self):
        self.placement = self.flush_events(self.placement, self.placement_buffer)
        return self.placement

    def add_migration_event(self, event, time, sfc_request):
        """Add a new migration event to the log system

        Args:
            event (str): The event type
            time (int): Time simulation
            sfc_request (SFC_Request): The SFC Request
        """

        self.migration_buffer.insert(0,[
            event, 
            "{:.2f}".format(time),
            sfc_request.name,
            sfc_request.user.name,
        ])

    def get_migration_events(self):
        self.migration = self.flush_events(self.migration, self.migration_buffer)
        return self.migration

    def add_sfc_request_event(self, event, time, sfc_request, sfc_request_placement_order = -1):
        """Add a new SFC_Request event to the log system

        Args:
            event (str): The event type
            time (int): Time simulation
            sfc_request (SFC_Request): The SFC Request
            sfc_request_placement_order (int): The order of the placement execution of this SFC Request
        """
        try:
            sfc_instance_name = sfc_request.sfc_instance.name
        except:
            sfc_instance_name = ""

        self.sfc_request_buffer.insert(0,[
            event, 
            "{:.2f}".format(time),
            sfc_request.name,
            sfc_instance_name,
            sfc_request_placement_order
        ])

    def get_sfc_request_events(self):
        self.sfc_request = self.flush_events(self.sfc_request, self.sfc_request_buffer)
        return self.sfc_request

    def add_vnf_instance_event(self, event, time, vnf_instance):
        """Add a new VNF Instance event, created or destroyed

        Args:
            event (str): The event type
            time (int): Time simulation
            vnf_instance (VNF_Instance): The VNF_Instance
        """
        self.vnf_instance_buffer.insert(0,[
            event, 
            "{:.2f}".format(time),
            vnf_instance.name,
            vnf_instance.node.name,
            vnf_instance.vnf.name,
            vnf_instance.vnf.cpu,
            vnf_instance.vnf.mem
        ])
    
    def get_vnf_instance_events(self):
        self.vnf_instance = self.flush_events(self.vnf_instance, self.vnf_instance_buffer)
        return self.vnf_instance

    def add_sfc_instance_event(self, event, time, sfc_instance):
        """Add a new SFC Instance event, created or destroyed

        Args:
            event (str): The event type
            time (int): Time simulation
            sfc_instance (SFC_Instance): The SFC_Instance
        """
        self.sfc_instance_buffer.insert(0,[
            event, 
            "{:.2f}".format(time),
            sfc_instance.name
        ])

    def get_sfc_instance_events(self):
        self.sfc_instance = self.flush_events(self.sfc_instance, self.sfc_instance_buffer)
        return self.sfc_instance

    def add_sfc_instance_vnf_mapping_event(self, event, time, sfc_instance, vnf_instance):
        """Add a new SFC Instance event, created or destroyed

        Args:
            event (str): The event type
            time (int): Time simulation
            sfc_instance (SFC_Instance): The SFC_Instance
            vnf_instance (SFC_Instance): The VNF_Instance
        """
        self.sfc_instance_vnf_mapping_buffer.insert(0,[
            event,
            "{:.2f}".format(time),
            sfc_instance.name,
            vnf_instance.name,
        ])

    def get_sfc_instance_vnf_mapping_events(self):
        self.sfc_instance_vnf_mapping = self.flush_events(self.sfc_instance_vnf_mapping, self.sfc_instance_vnf_mapping_buffer)
        return self.sfc_instance_vnf_mapping

    def add_vnf_instance_packets_event(self, event, time, packet_id, vnf_instance, sfc_request, sfc_instance, packet_size = 0, wait_time=-1):
        """Add packets events in the VNF_Instance

        Args:
            event (str): The event type
            time (int): The simulation time
            packet_id (int): Packet Id
            vnf_instance (VNF_Instance): The VNF_Instance where the event accour
            sfc_request (SFC_Request): The SFC_Request
            sfc_instance (SFC_Instance): The SFC_Instance
            packet_size (int): Total em IPTs consumed by the packet
            wait_time (int): Time in which the packet waited in VNF queue OR waited to be processed by the VNF
        """
        self.vnf_instance_packets_buffer.insert(0,[event, 
            "{:.2f}".format(time),
            packet_id,
            vnf_instance.name,
            sfc_request.name,
            sfc_instance.name,
            sfc_request.user.name,
            sfc_request.sfc.name,
            sfc_request.data_source.name,
            packet_size,
            wait_time])

    def get_vnf_instance_packets_events(self):
        self.vnf_instance_packets = self.flush_events(self.vnf_instance_packets, self.vnf_instance_packets_buffer)
        return self.vnf_instance_packets

    def flush_events(self, df, df_buffer):
        if len(df_buffer) > 0:
            df = pd.concat([pd.DataFrame(df_buffer,columns=df.columns),df],ignore_index=True)
            df_buffer.clear()
        return df

    def add_link_event(self, event, time, packet_id, link, sfc_request, sfc_instance, vnf_instance_name, packet_size):
        """Add link events

        Args:
            event (str): The event type
            time (int): The simulation time
            packet_id (int): Packet Id
            link (str): Link Name
            sfc_request (SFC_Request): The SFC_Request
            sfc_instance (SFC_Instance): The SFC_Instance
            vnf_instance_name (str): The vnf_instance name
        """
        self.links_buffer.insert(0,[
            event, 
            "{:.2f}".format(time),
            packet_id,
            link.name,
            sfc_request.name,
            sfc_instance.name,
            sfc_request.user.name,
            sfc_request.sfc.name,
            sfc_request.data_source.name,
            vnf_instance_name,
            packet_size
            #link.total_traffic

        ])

    def get_link_events(self):
        self.links = self.flush_events(self.links, self.links_buffer)
        return self.links

    def add_vnf_instance_resources_event(self, event, time, vnf_instance, cpu_usage, mem_usage, sfc_request, packet_id):
        """Add a new Instance  event to the log system 

        Args:
            instance (VNF_Instance): The instance that changed
            event (str): Event name
            time (int): Simulation time
            vnf_instance (VNF_Instance): The VNF_Instance.
            cpu_usage (int): The new cpu usage
            mem_usage (int): The new mem usage
            sfc_request (SFC_Request): The SFC Request
            packet_id (int): The packet id
        """
        self.vnf_instance_resources_buffer.insert(0,[
            event,
            "{:.2f}".format(time),
            vnf_instance.name,            
            vnf_instance.cpu, 
            "{:.2f}".format(cpu_usage),
            vnf_instance.mem, 
            "{:.2f}".format(mem_usage),
            sfc_request.user.name,
            sfc_request.name,
            sfc_request.sfc_instance.name,
            packet_id
        ])
    
    def get_vnf_instance_resources_events(self):
        self.vnf_instance_resources = self.flush_events(self.vnf_instance_resources, self.vnf_instance_resources_buffer)
        return self.vnf_instance_resources

    def get_vnf_instance_resources_events_window(self, vnf_instance_name, start_time, end_time):
        """
        Return all the packet event from an SFC Instance

        vnf_instance_name (str): The name of the VNF Instance
        start_time: Return events with time higher than start_time
        end_time: Return events with time below the end_time
        """
        events = self.get_vnf_instance_resources_events()
        events["Time"] = pd.to_numeric(events["Time"])
        return events[(events["VNF_Instance"] == vnf_instance_name) & (events["Time"] >= start_time)
                            & (events["Time"] <= end_time)]

        # self.packets = self.flush_events(self.packets, self.packets_buffer)
        # self.packets["Time"] = pd.to_numeric(self.packets["Time"])
        # return self.packets[(self.packets["SFC_Instance"] == sfc_instance_name) & (self.packets["Time"] >= start_time)
        #                     & (self.packets["Time"] <= end_time)]

    def add_scaling_event(self, event, time, vnf_instance, old, new):
        """Add a new CPU / Mem Scaling event to the log system

        Args:
            event (str): Event name
            time (int): Simulation time
            vnf_instance (VNF_Instance): The instance that changed
            old (float): Previous CPU / Mem allocated
            new (float): New CPU / Mem allocated
        """

        self.scaling_buffer.insert(0,[
            event,
            "{:.2f}".format(time),
            vnf_instance.name,
            "{:.2f}".format(old),
            "{:.2f}".format(new)
        ])

    def add_monitor_event(self, event, time, sfc_instance, window_size, monitor_interval):
        """
        Add a new Monitor event to the log system 

        Args:
            event (str): Event name
            time (int): Simulation time
            window_size (int): The new size of the monitor window
            monitor_interval (int): The new monitor interval
            sfc_instance (SFC_Instance): The SFC_Instance
        """
        self.monitor_buffer.insert(0, [
            event,
            "{:.2f}".format(time),
            sfc_instance.name,
            "{:.2f}".format(window_size),
            "{:.2f}".format(monitor_interval)
        ])

    def add_RLAgent_event(self, event, time, vnf_instance, agent, value, new_reward):
        """
        Add a new RL Agent event to the log system 

        Args:
            event (str): Event name
            time (int): Simulation time
            vnf_instance (VNF_Instance): The VNF_Instance
            new_threshold_up (float): The new threshold up
            new_threshold_down (float): The new threshold down
            new_reward_up (float): The new reward up
            new_reward_down (float): The new reward down
        """
        # rlagent_columns = ["Event", "Time", "VNF_Instance", "Agent", "Value", "Reward"]
        self.rlagent_buffer.insert(0, [
            event,
            "{:.2f}".format(time),
            vnf_instance.name,
            agent,
            "{:.2f}".format(value),
            # "{:.2f}".format(new_threshold_down),
            "{}".format(new_reward)
            # "{}".format(new_reward_down)
        ])

    def get_scaling_events(self):
        self.scaling = self.flush_events(self.scaling, self.scaling_buffer)
        return self.scaling

    def add_sfc_instance_resources_event(self, event, time, sfc_instance, old_cpu, new_cpu, old_mem, new_mem):
        self.sfc_instance_resources_buffer.insert(0, [
            event,
            "{:.2f}".format(time),
            sfc_instance.name,
            "{:.2f}".format(old_cpu),
            "{:.2f}".format(new_cpu),
            "{:.2f}".format(old_mem),
            "{:.2f}".format(new_mem)
        ])

    def get_sfc_instance_resources_events(self):
        self.sfc_instance_resources = self.flush_events(self.sfc_instance_resources, self.sfc_instance_resources_buffer)
        return self.sfc_instance_resources

    def add_resource_usage_event(self, event, time, value):
        self.resource_usage_buffer.insert(0, [
            event,
            "{:.2f}".format(time),
            "{:.2f}".format(value)
        ])
    
    def get_resource_usage_events(self):
        self.resource_usage = self.flush_events(self.resource_usage, self.resource_usage_buffer)
        return self.resource_usage

    def get_monitor_events(self):
        self.monitor = self.flush_events(self.monitor, self.monitor_buffer)
        return self.monitor

    def get_rlagent_events(self):
        self.rlagent = self.flush_events(self.rlagent, self.rlagent_buffer)
        return self.rlagent

    def save_events_csv(self, edge_environment, sm, file_path="."):
        """Save the evenst into a CSV file

        Args:
        file_path (str, optional): The path where the file will be stored. Defaults to ".".
        """
        # create the dir if it not exist
        if not os.path.exists(file_path):
            os.makedirs(file_path)

        # self.resources.to_csv(file_name_resources, sep=';', index=False, quoting=csv.QUOTE_NONE)
        # file_name_resources         = "{}/resources.csv".format(file_path)

        file_name_links               = "{}/links.csv".format(file_path)
        file_name_placement           = "{}/placement.csv".format(file_path)
        file_time_window              = "{}/time_window.csv".format(file_path)
        file_packets                  = "{}/packets.csv".format(file_path)
        file_vnf_instance_packets     = "{}/vnf_instance_packets.csv".format(file_path)
        file_vnf_instance_resources   = "{}/vnf_instance_resources.csv".format(file_path)
        file_vnf_instance             = "{}/vnf_instance.csv".format(file_path)
        file_sfc_instance             = "{}/sfc_instance.csv".format(file_path)
        file_sfc_request              = "{}/sfc_request.csv".format(file_path)
        file_sfc_instance_vnf_mapping = "{}/sfc_instance_vnf_mapping.csv".format(file_path)
        file_user_mobility            = "{}/user_mobility.csv".format(file_path)
        file_migration                = "{}/migration.csv".format(file_path)
        file_scaling                  = "{}/vnf_instance_scaling.csv".format(file_path)
        file_sfc_instance_resources   = "{}/sfc_instance_resources.csv".format(file_path)
        file_resource_usage           = "{}/resource_usage.csv".format(file_path)
        file_monitor                  = "{}/monitor.csv".format(file_path)
        file_rlagent                  = "{}/rl_agent.csv".format(file_path)

        self.vnf_instance_resources      = self.get_vnf_instance_resources_events()
        self.vnf_instance_packets        = self.get_vnf_instance_packets_events()
        self.vnf_instance                = self.get_vnf_instance_events()
        self.sfc_instance                = self.get_sfc_instance_events()
        self.links                       = self.get_link_events()
        self.sfc_request                 = self.get_sfc_request_events()   
        self.placement                   = self.get_placement_events()
        self.time_window                 = self.get_time_window_events()
        self.packets                     = self.get_packets_events()
        self.sfc_instance_vnf_mapping    = self.get_sfc_instance_vnf_mapping_events()
        self.user_mobility               = self.get_user_mobility_events()
        self.migration                   = self.get_migration_events()
        self.scaling                     = self.get_scaling_events()
        self.sfc_instance_resources      = self.get_sfc_instance_resources_events()
        self.resource_usage              = self.get_resource_usage_events()
        self.monitor                     = self.get_monitor_events()
        self.rlagent                     = self.get_rlagent_events()

        self.links.to_csv(file_name_links, sep=';', index=False, quoting=csv.QUOTE_NONE)
        self.placement.to_csv(file_name_placement, sep=';', index=False, quoting=csv.QUOTE_NONE)        
        self.time_window.to_csv(file_time_window, sep=';', index=False, quoting=csv.QUOTE_NONE)
        self.packets.to_csv(file_packets, sep=';', index=False, quoting=csv.QUOTE_NONE)
        self.vnf_instance_packets.to_csv(file_vnf_instance_packets, sep=';', index=False, quoting=csv.QUOTE_NONE)
        self.vnf_instance_resources.to_csv(file_vnf_instance_resources, sep=';', index=False, quoting=csv.QUOTE_NONE)
        self.vnf_instance.to_csv(file_vnf_instance, sep=';', index=False, quoting=csv.QUOTE_NONE)
        self.sfc_instance.to_csv(file_sfc_instance, sep=';', index=False, quoting=csv.QUOTE_NONE)
        self.sfc_request.to_csv(file_sfc_request, sep=';', index=False, quoting=csv.QUOTE_NONE)
        self.sfc_instance_vnf_mapping.to_csv(file_sfc_instance_vnf_mapping, sep=';', index=False, quoting=csv.QUOTE_NONE)
        self.user_mobility.to_csv(file_user_mobility, sep=';', index=False, quoting=csv.QUOTE_NONE)
        self.migration.to_csv(file_migration, sep=';', index=False, quoting=csv.QUOTE_NONE)
        self.scaling.to_csv(file_scaling, sep=';', index=False, quoting=csv.QUOTE_NONE)
        self.sfc_instance_resources.to_csv(file_sfc_instance_resources, sep=';', index=False, quoting=csv.QUOTE_NONE)
        self.resource_usage.to_csv(file_resource_usage, sep=';', index=False, quoting=csv.QUOTE_NONE)
        self.monitor.to_csv(file_monitor, sep=';', index=False, quoting=csv.QUOTE_NONE)
        self.rlagent.to_csv(file_rlagent, sep=';', index=False, quoting=csv.QUOTE_NONE)

        VNF_Instance.save_csv(edge_environment.vnf_instances, file_path)
        SFC_Instance.save_csv(edge_environment.sfc_instances, edge_environment.vnf_instances, file_path)
        Packet.save_csv(sm.packets, file_path)
