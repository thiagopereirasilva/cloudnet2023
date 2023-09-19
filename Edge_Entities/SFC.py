from beautifultable import BeautifulTable
from termcolor import colored, cprint
import pandas as pd
import os


class SFC:

    PRIORITIZE_LATENCY  = 1
    PRIORITIZE_CAPACITY = 2
    PRIORITIZE_ENERGY   = 3

    # The names of the attributes in this object
    attr_names = [
        "Name",
        "Max_Latency",
        "Priority",
        "Timeout",
        "VNFs"
    ]

    def __init__(self, name, vnfs, max_latency, priorities_order, timeout):
        """
        It is the chain of VNFs

        Args:
            name (str): the name of the VNF
            vnfs (list): The VNFs that composed the SFC
            max_latency (int): Max tolerable time to the data travels from the producer to the consumer of the SFC
            priorities_order (int): 1, 2 and 3 values represent latency, capacity and energy priorities respectively.
            timeout (int): The life time of the SFC
        """
        self.name = name
        self.max_latency = max_latency
        self.priorities_order = priorities_order
        self.timeout = timeout
        self.vnfs = vnfs

    def show(self):
        cprint("SFC [{}] Details".format(self.name), "blue", attrs=['bold'])
        table = BeautifulTable()
        table.rows.append([self.name])
        table.rows.append(["{} ms".format(self.max_latency)])
        table.rows.append([self.priorities_order])
        table.rows.append(["{} ms".format(self.timeout)])
        table.rows.append([self.vnfs])
        table.rows.header = SFC.attr_names
        print(table)
        print("\n")

    @staticmethod
    def save_csv(sfcs, file_path="."):
        """
        Save the SFC entities into a CSV file

        Args:
            sfcs (list): The list of SFCs that will be saved in the CSV
            file_path (str, optional): The path where the file will be stored. Defaults to ".".
        """
        sfc_rows = []

        for sfc in sfcs:
            aux = sfcs[sfc]
            sfc_rows.insert(0,[
                aux.name,
                aux.max_latency,
                aux.priorities_order,
                aux.timeout,
                aux.vnfs
            ])

        df = pd.DataFrame(sfc_rows, columns=SFC.attr_names)

        # create the dir if it not exist
        if not os.path.exists(file_path):
            os.makedirs(file_path)

        file_name = "{}/sfcs.csv".format(file_path)

        df.to_csv(file_name, sep=';', index=False)

    @staticmethod
    def list(sfcs):
        print("SFC Types (total: {})".format(len(sfcs)))
        table = BeautifulTable(150)
        table.columns.header = SFC.attr_names
        for sfc in sfcs:
            aux = sfcs[sfc]
            table.rows.append([
                aux.name,
                aux.max_latency,
                aux.priorities_order,
                aux.timeout,
                aux.vnfs
            ])
        print(table)
        print("\n")
