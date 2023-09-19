from beautifultable import BeautifulTable
from termcolor import colored, cprint
import pandas as pd
import os


class VNF:
    # The names of the attributes in this object
    attr_names = [
        "Name",
        "Min_CPU",
        "Min_Mem",
        "Max_Share",
        "Min_Bandwidth",
        "Pck_Mem_Demand",
        "Data_Acc_Cost",  # Remote Data Access Cost
        "Data_Acc_Prob",  # Remote Data Access Probability,
        "Pck_CPU_Demand",
        "Pck_Network_Demand",
        "Startup_CPU_Demand",
        "Shutdown_CPU_Demand",
        "Timeout",
        "Max_Packets_Queue",
        "Resource_Intensive"
    ]

    def __init__(self, name, cpu, mem, max_share, min_bandwidth, packet_mem_demand, remote_data_access_cost,
                 remote_data_access_prob, packet_cpu_demand, packet_network_demand, startup_ipt, shutdown_ipt, timeout,
                 max_packet_queue, resource_intensive = ""):
        """ VNF is a unit that will process some data flow

    Args:
        name (str): the name of the VNF
        cpu (float): Minimum amount of cpu required to run the VNF (IPT)
        mem (int): Minimum amount of memory required to run the VNF (MB)
        max_share (int): number of SFCs that can use the VNF
        min_bandwidth (int): min output bandwith
        packet_mem_demand (int): Memory consumed per packet size
        remote_data_access_cost (int): Is the time to collect a data in another entity (data lake, other node, etc), in milliseconds
        remote_data_access_prob (float): Is the change of a packet requires the data for another entity [0-1] This prob is per packet çomputed in the VNF
        packet_cpu_demand (int): mean size of CPU Instructions that will be used to process the packet (use to process the VNF) measured in IP
        packet_network_demand (int): mean size of Link bandwidth that will be uses to process the packet (used to process the link) measured in bits
        startup_ipt (int): number of CPU instructions consumed to startup the VNF Instance
        shutdown_ipt (int): number of CPU instructions consumed to shutdown the VNF Instance
        timeout (int): The amount of time that a VNF will be running without a SFC Instance
        max_packet_queue (int): Define the max number of packets in the Queue
        resource_intensive (String): Define the resource most valuable for the VNF, this attr will be used to calculate the load metric
    """
        self.name = name
        self.cpu = cpu
        self.mem = mem
        self.max_share = max_share
        self.min_bandwidth = min_bandwidth
        self.packet_mem_demand = packet_mem_demand
        self.remote_data_access_cost = remote_data_access_cost
        self.remote_data_access_prob = remote_data_access_prob
        self.packet_cpu_demand = packet_cpu_demand
        self.packet_network_demand = packet_network_demand
        self.startup_ipt = startup_ipt
        self.shutdown_ipt = shutdown_ipt
        self.timeout = timeout
        self.max_packet_queue = max_packet_queue
        self.resource_intensive = resource_intensive

    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)

    def show(self):
        cprint("VNF [{}] Details".format(self.name), "blue", attrs=['bold'])
        table = BeautifulTable()
        table.rows.append([self.name])
        table.rows.append(["{} IPT".format(self.cpu)])
        table.rows.append(["{} MB".format(self.mem)])
        table.rows.append([self.max_share])
        table.rows.append(["{} Mb".format(self.min_bandwidth)])
        table.rows.append(["{} MB".format(self.packet_mem_demand)])
        table.rows.append(["{} ms".format(self.remote_data_access_cost)])
        table.rows.append(["{} %".format(self.remote_data_access_prob)])
        table.rows.append(["{} IP".format(self.packet_cpu_demand)])
        table.rows.append(["{} bits".format(self.packet_network_demand)])
        table.rows.append(["{} IPS".format(self.startup_ipt)])
        table.rows.append(["{} IPS".format(self.shutdown_ipt)])
        table.rows.append(["{} ms".format(self.timeout)])
        table.rows.append(["{}".format(self.max_packet_queue)])
        table.rows.append(["{}".format(self.resource_intensive)])
        table.rows.header = VNF.attr_names

        print(table)
        print("\n")

    @staticmethod
    def save_csv(vnfs, file_path="."):
        """Save the VNF entities into a CSV file

    Args:
        file_path (str, optional): The path where the file will be stored. Defaults to ".".
    """

        vnf_rows = []

        for aux in vnfs:
            aux = vnfs[aux]
            vnf_rows.insert(0,[
                aux.name,
                aux.cpu,
                aux.mem,
                aux.max_share,
                aux.min_bandwidth,
                aux.packet_mem_demand,
                aux.remote_data_access_cost,
                aux.remote_data_access_prob,
                aux.packet_cpu_demand,
                aux.packet_network_demand,
                aux.startup_ipt,
                aux.shutdown_ipt,
                aux.timeout,
                aux.max_packet_queue,
                aux.resource_intensive
            ])

        df = pd.DataFrame(vnf_rows, columns=VNF.attr_names)

        # create the dir if it not exist
        if not os.path.exists(file_path):
            os.makedirs(file_path)

        file_name = "{}/vnfs.csv".format(file_path)

        df.to_csv(file_name, sep=';', index=False)

    @staticmethod
    def list(vnfs):
        print("VNF Types (total: {})".format(len(vnfs)))

        table = BeautifulTable(150)

        table.columns.header = VNF.attr_names

        for vnf in vnfs:
            aux = vnfs[vnf]
            table.rows.append([
                aux.name,
                aux.cpu,
                aux.mem,
                aux.max_share,
                aux.min_bandwidth,
                aux.packet_mem_demand,
                aux.remote_data_access_cost,
                aux.remote_data_access_prob,
                aux.packet_cpu_demand,
                aux.packet_network_demand,
                aux.startup_ipt,
                aux.shutdown_ipt,
                aux.timeout,
                aux.max_packet_queue,
                aux.resource_intensive
            ])
        print(table)
        print("\n")
