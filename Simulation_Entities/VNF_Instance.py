from beautifultable import BeautifulTable
from termcolor import colored, cprint
import pandas as pd
import os
import csv


class VNF_Instance:
    # The names of the attributes in this object
    attr_names = [
        "Name",
        "VNF",
        "CPU",
        "Mem",
        "CPU_Load",
        "Mem_Load",
        "Node",
        "SFC_Inst_Attached",
        "Startup",
        "Shutdown",
        "Timeout",
        "Active",
        "Acpt_SFC_Inst"
    ]

    def __init__(self, name, vnf, cpu, mem, node):
        """
        VNF Instance is the entity that defines the place where the packet will be processed.

        A VNF Instance can be executed indise a Virtual Machine, Container or even as a function in a Server Less Environtmnet

        Args:
            name (str): The name of the VNF Instance
            vnf (VNF): The VNF Type
            cpu (float): The amount of CPU associated with the instance (this value can be changed during the execution time)
            mem (int): The amount of memory associated with this instance (this value can be changed during the execution time)
            node (Node): The node where the instance is executed
        """

        self.name = name
        self.vnf = vnf
        self.cpu = cpu
        self.mem = mem
        self.node = node
        self.cpu_min_required = cpu
        self.mem_min_required = mem

        # The SFCs instance that the VNF_Instance responds
        self.sfc_instances = []

        # The amount of CPU used by the instance to process the packets
        self.cpu_load = 0

        # The amount of Memory used by the instance to process the packets
        self.mem_load = 0

        # Time remain for the VNF Instance be ready for processing packets
        self.startup_remain_time = int((vnf.startup_ipt / node.cpu) * 1000)

        # Time remain for the VNF Instance release the resources used
        self.shutdown_remain_time = int((vnf.shutdown_ipt / node.cpu) * 1000)

        # The time remain for the vnf instance be alive
        self.timeout = vnf.timeout

        # Define if the VNF Instance is active or not
        self.active = True

        # Define if the VNF Instance can be mapped to any SFC Instance or not
        self.accept_sfc_instances = True

        # The number of packets that are in the VNF Instance Queue
        self.packet_queue_count = 0

    def add_packet_in_queue(self):
        """
        Count more one Packet in the VNF Instance Queue

        if max_packet_queue == -1 infinity queue
        """
        if self.packet_queue_count < self.vnf.max_packet_queue or self.vnf.max_packet_queue == -1:
            self.packet_queue_count += 1
            return True

        return False

    def dec_packet_in_queue(self):
        """
        Subtract one to the packet queue size
        """
        if self.packet_queue_count > 0:
            self.packet_queue_count -= 1
            return True

        return False

    def get_cpu_load(self):
        """
        Round the CPU load to 2 decimal
        """
        return round(self.cpu_load, 2)

    def get_mem_load(self):
        """
        Round the Mem load to 2 decimal
        """
        return round(self.mem_load, 2)

    def add_sfc_instance(self, sfc_instance_name):
        """
        Add a new SFC Instance to the VNF Instance. The VNF Instance must be active and accepting new SFC Instances

        Args:
            sfc_instance_name (str): The name of the SFC_Instance
        """
        if self.active and self.accept_sfc_instances:
            self.sfc_instances.append(sfc_instance_name)
            return True

        return False

    def remove_sfc_instance(self, sfc_instance_name):
        """
        Remove an SFC Instance for the VNF Instance

        Args:
            sfc_instance_name (str): The name of the SFC_Instance
        """
        if sfc_instance_name in self.sfc_instances:
            self.sfc_instances.remove(sfc_instance_name)
            return True

        return False

    def increase_cpu_load(self, cpu_load):
        self.cpu_load += cpu_load

    def decrease_cpu_load(self, cpu_load):
        self.cpu_load -= cpu_load
        if self.cpu_load < 0:
            self.cpu_load = 0

    def increase_mem_load(self, mem_load):
        self.mem_load += mem_load

    def decrease_mem_load(self, mem_load):
        self.mem_load -= mem_load
        if self.mem_load < 0:
            self.mem_load = 0

    def show(self):
        cprint("VNF Instance [{}] Details".format(self.name), "blue", attrs=['bold'])
        table = BeautifulTable()
        table.rows.append([self.name])
        table.rows.append([self.vnf.name])
        table.rows.append(["{:.2f} IPT".format(self.cpu)])
        table.rows.append(["{:.2f} Mb".format(self.mem)])
        table.rows.append(["{:.2f} %".format(self.cpu_load)])
        table.rows.append(["{:.2f} %".format(self.mem_load)])
        table.rows.append([self.node.name])
        table.rows.append([self.sfc_instances])
        table.rows.append([self.startup_remain_time])
        table.rows.append([self.shutdown_remain_time])
        table.rows.append([self.timeout])
        table.rows.append([self.active])
        table.rows.append([self.accept_sfc_instances])
        table.rows.append([self.packet_queue_count])

        columns = self.attr_names.copy()
        columns.append("Queue Size")

        table.rows.header = columns

        print(table)
        print("\n")

    @staticmethod
    def save_csv(vnf_instances, file_path="."):
        """
        Save the Instances entities into a CSV file

        Args:
            vnf_instances (list): List of VNF Instances that will be saved
            file_path (str, optional): The path where the file will be stored. Defaults to ".".
        """

        vnf_instances_rows = []

        for aux in vnf_instances:
            vnf_instances_rows.insert(0, [
                aux.name,
                aux.vnf.name,
                aux.cpu,
                aux.mem,
                "{:.2f}".format(aux.cpu_load),
                "{:.2f}".format(aux.mem_load),
                aux.node.name,
                aux.sfc_instances,
                aux.startup_remain_time,
                aux.shutdown_remain_time,
                aux.timeout,
                aux.active,
                aux.accept_sfc_instances
            ])

        df = pd.DataFrame(vnf_instances_rows, columns=VNF_Instance.attr_names)

        # create the dir if it is not created
        if not os.path.exists(file_path):
            os.makedirs(file_path)

        file_name = "{}/vnf_instances_entities.csv".format(file_path)

        df.to_csv(file_name, sep=';', index=False, quoting=csv.QUOTE_NONE)

    @staticmethod
    def list(vnf_instances):
        """
        Print a table with all the VNF Instances attributes

        Args:
            vnf_instances (list): List of VNF Instances that will be printed
        """
        print("VNF Instances (total: {})".format(len(vnf_instances)))
        table = BeautifulTable(150)
        table.columns.header = VNF_Instance.attr_names
        for aux in vnf_instances or []:
            table.rows.append([
                aux.name,
                aux.vnf.name,
                aux.cpu,
                aux.mem,
                aux.cpu_load,
                aux.mem_load,
                aux.node.name,
                aux.sfc_instances,
                aux.startup_remain_time if aux.startup_remain_time >= 0 else "Done",
                aux.shutdown_remain_time if aux.shutdown_remain_time >= 0 else "Done",
                aux.timeout if aux.timeout >= 0 else "Yes",
                aux.active,
                aux.accept_sfc_instances
            ])

        print(table)
        print("\n")

    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)
