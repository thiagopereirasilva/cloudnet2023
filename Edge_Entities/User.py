from beautifultable import BeautifulTable
from termcolor import colored, cprint
import pandas as pd
import os


class User:
    # The names of the attributes in this object
    attr_names = [
        "Name",
        "Node",
        "Initial_Node",
        "Latency",
        "Bandwidth",
        "Loss_Rate",
        "SFCs_Requested",
        "SFC_Ingress_Egress",
        "Priority"
    ]

    def __init__(self, name, sfcs, latency, bandwidth, loss_rate, node, priority):
        """
        The User swill request the creation of the SFCs

        Args:
            name (str): user name
            sfcs (array): The SFCs that the users will request
            latency (int): The latency between the user and the edge node that it is connected
            bandwidth (int): The bandwidth between the user and the edge node that it is connected
            loss_rate (float): The loss rate of the link
            node (Node): The edge node that the user is connected
            priority (int): The priority of the user, define the priority order from SFCs be responded
        """
        self.name = name
        self.sfcs = sfcs
        self.latency = latency
        self.bandwidth = bandwidth
        self.loss_rate = loss_rate
        self.node = node
        self.initial_node = node
        self.priority = priority

        # This is a set of the value for the ingress, egress and packet_size for a requested SFC by the user
        # {'s_3': {'ingress_node': 'n_3', 'egress_node': 'n_0', 'packet_size': 30},
        #  's_1': {'ingress_node': 'n_2', egress_node': 'n_2', 'packet_size': 50},
        #  's_0': {'ingress_node': 'n_3', 'egress_node': 'n_0', 'packet_size': 20}}
        # in the example the s_3 has a packet_size of 30
        self.sfc_ingress_egress = {}

    def moved(self):
        """
        Return True if the First Node and the Actual Node are the same, and False otherwise
        """
        if self.node.name == self.initial_node.name:
            return False

        return True

    def add_ingress_egress(self, sfc, ingress_node, egress_node, packet_size):
        data = {
            'ingress_node': ingress_node,
            'egress_node': egress_node,
            'packet_size': packet_size
        }

        self.sfc_ingress_egress[sfc] = data

    def show(self):
        cprint("User [{}] Details".format(self.name), "blue", attrs=['bold'])
        table = BeautifulTable()
        table.rows.append([self.name])
        table.rows.append([self.node.name])
        table.rows.append([self.initial_node.name])
        table.rows.append(["{} ms".format(self.latency)])
        table.rows.append(["{} Mb".format(self.bandwidth)])
        table.rows.append(["{}%".format(self.loss_rate)])
        table.rows.append([self.sfcs])
        table.rows.append([self.sfc_ingress_egress])
        table.rows.append([self.priority])
        table.rows.header = self.attr_names
        print(table)
        print("\n")

    @staticmethod
    def save_csv(users, file_path="."):
        """
        Save the User entities into a CSV file

        Args:
            users (list): List of users that will be saved
            file_path (str, optional): The path where the file will be stored. Defaults to ".".
        """

        user_rows = []

        for user in users:
            aux = users[user]
            user_rows.insert(0,[
                aux.name,
                aux.node.name,
                aux.initial_node.name,
                aux.latency,
                aux.bandwidth,
                aux.loss_rate,
                aux.sfcs,
                aux.sfc_ingress_egress,
                aux.priority
            ])

        df = pd.DataFrame(user_rows, columns=User.attr_names)

        # create the dir if it not exist
        if not os.path.exists(file_path):
            os.makedirs(file_path)

        file_name = "{}/users.csv".format(file_path)
        df.to_csv(file_name, sep=';', index=False)

    @staticmethod
    def list(users):
        print("Users (total: {})".format(len(users)))
        table = BeautifulTable(150)
        table.columns.header = User.attr_names

        for user in users:
            aux = users[user]
            table.rows.append([
                aux.name,
                aux.node.name,
                aux.initial_node.name,
                aux.latency,
                aux.bandwidth,
                aux.loss_rate,
                aux.sfcs,
                aux.sfc_ingress_egress,
                aux.priority
            ])
        print(table)
        print("\n")

    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)
