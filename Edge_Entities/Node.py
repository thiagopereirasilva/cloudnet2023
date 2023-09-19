from beautifultable import BeautifulTable
from termcolor import colored, cprint
import pandas as pd
import os


class Node:

    # The names of the attributes in this object
    attr_names = [
        "Name",
        "Group",
        "Type",
        "CPU",
        "Mem",
        "Energy_Max",
        "Energy_Idle",
        "Disk_Delay",
        "Location",
        "VNFs",
    ]

    RAN_NODE = 'RAN'
    CORE_NODE = 'CORE'
    DEFAULT_NODE = 'DEFAULT'

    def __init__(self, name, group, cpu, mem, vnfs, energy_max, energy_idle, disk_delay, node_type, location):
        """ The definition of the Edge Node that will execute the VNF instances

    Args:
        name (str): name of the edge node
        group (str): The group what the not is part of
        cpu (float): The amount of CPU available in the edge node (GHz)
        mem (int): The amount of memory available (MB)
        vnfs (list): The number of VNF Types that can be executed in the edge node
        energy_max (float): The energy consumed when the CPU is in the max usage
        energy_idle ([type]): The energy consumed when the edge node is in idle
        disk_delay [(float)]: The time to access the data in the disk
        node_type (str): The node type
        location (obj): Location object
    """
        self.name = name
        self.group = group
        self.cpu = cpu
        self.mem = mem
        self.vnfs = vnfs
        self.energy_max = energy_max
        self.energy_idle = energy_idle
        self.disk_delay = disk_delay
        self.node_type = node_type
        self.location = location

    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)

    @staticmethod
    def get_nodes_by_type(nodes, node_type):
        """
        Get the nodes by type
        nodes (nodes): List of nodes
        node_type (str): The node type
        """
        selected_nodes = []
        for node in nodes:
            aux_node = nodes[node]
            if aux_node.node_type == node_type:
                selected_nodes.append(aux_node)

        return selected_nodes

    def is_overloaded(self, instances):
        """ Verify if the sum of resources demanded by all the instances running in the
    node area greater than the resources available in the node.

    Args:
        instances (list): The list of instances
    """
        cpu_used = 0
        mem_used = 0

        for instance in instances:
            if self.name == instance.node.name:
                cpu_used = cpu_used + instance.cpu
                mem_used = mem_used + instance.mem

        if cpu_used > self.cpu or mem_used > self.mem:
            return {'cpu_used': cpu_used, 'mem_used': mem_used}

        return False

    def show(self):
        cprint("Node [{}] Details".format(self.name), "blue", attrs=['bold'])
        table = BeautifulTable()
        table.rows.append([self.name])
        table.rows.append([self.group])
        table.rows.append([self.node_type])
        table.rows.append(["{} IPT".format(self.cpu)])
        table.rows.append(["{} MB".format(self.mem)])
        table.rows.append(["{} W".format(self.energy_max)])
        table.rows.append(["{} W".format(self.energy_idle)])
        table.rows.append(["{} ms".format(self.disk_delay)])
        table.rows.append(["{}".format(self.location['key'])])
        table.rows.append([self.vnfs])
        table.rows.header = Node.attr_names
        print(table)
        print("\n")

    @staticmethod
    def save_csv(nodes, file_path="."):
        """Save the Node entities into a CSV file

      Args:
          file_path (str, optional): The path where the file will be stored. Defaults to ".".
      """

        node_rows = []

        df = pd.DataFrame(columns=Node.attr_names)
        for node in nodes:
            aux = nodes[node]
            node_rows.insert(0,[
                aux.name,
                aux.group,
                aux.node_type,
                aux.cpu,
                aux.mem,
                aux.energy_max,
                aux.energy_idle,
                aux.disk_delay,
                aux.location,
                aux.vnfs
            ])

        df = pd.DataFrame(node_rows, columns=Node.attr_names)

        # create the dir if it not exist
        if not os.path.exists(file_path):
            os.makedirs(file_path)

        file_name = "{}/nodes.csv".format(file_path)

        df.to_csv(file_name, sep=';', index=False)

    @staticmethod
    def list(nodes):
        print("Nodes (total: {})".format(len(nodes)))
        table = BeautifulTable(150)
        table.columns.header = Node.attr_names

        for node in nodes:

            if isinstance(node, str):
                aux = nodes[node]
            else:
                aux = node

            table.rows.append([
                aux.name,
                aux.group,
                aux.node_type,
                aux.cpu,
                aux.mem,
                aux.energy_max,
                aux.energy_idle,
                aux.disk_delay,
                aux.location['key'],
                aux.vnfs])
        print(table)
        print("\n")
