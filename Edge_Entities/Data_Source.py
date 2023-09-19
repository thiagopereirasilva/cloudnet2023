from os import stat
from beautifultable import BeautifulTable
from termcolor import colored, cprint
import pandas as pd
import os
import numpy as np


class Data_Source:
    # The names of the attributes in this object
    attr_names = [
        "Name",
        "Packet_Size",
        "Packet_Interval",
        "Burst_Interval",
        "Burst_Num_Packets",
    ]

    def __init__(self, name, packet_size, packet_interval, packets_burst_interval, packets_burst_size):
        """
        The data source will define how the packets will be generated to be executed in the SFC.
        For each user associated with a SFC there will be a Data Source Generated the packets

        Args:
            name (str): the name of the VNF
            packet_size (int): the size of the packet data generated
            packet_interval (int): The mean time for the packet creation (ms)
            packets_burst_interval (int): The mean time between two packets bursts
            packets_burst_size (int): The mean size of packets from each SFC burst
        """
        self.name = name
        self.packet_size = packet_size
        self.packet_interval = packet_interval
        self.packets_burst_interval = packets_burst_interval
        self.packets_burst_size = packets_burst_size

    def get_packet_size(self):
        return np.random.poisson(self.packet_size)

    def get_packet_interval(self):
        return np.random.poisson(self.packet_interval)

    def get_packets_burst_interval(self):
        return np.random.poisson(self.packets_burst_interval)

    def get_packets_burst_size(self):
        return np.random.poisson(self.packets_burst_size)

    def show(self):
        cprint("Data Source [{}] Details".format(self.name), "blue", attrs=['bold'])
        table = BeautifulTable()
        table.rows.append([self.name])
        table.rows.append(["{} IP".format(self.packet_size)])
        table.rows.append(["{} ms".format(self.packet_interval)])
        table.rows.append(["{} ms".format(self.packets_burst_interval)])
        table.rows.append(["{} ms".format(self.packets_burst_size)])
        table.rows.header = Data_Source.attr_names
        print(table)
        print("\n")

    @staticmethod
    def save_csv(data_sources, file_path="."):
        """
        Save the Data Sources into a CSV file

        Args:
            data_sources (list): List of data sources that will be saved
            file_path (str, optional): The path where the file will be stored. Defaults to ".".
        """

        data_source_rows = []

        for src in data_sources:
            aux = data_sources[src]
            data_source_rows.insert(0,[
                aux.name,
                aux.packet_size,
                aux.packet_interval,
                aux.packets_burst_interval,
                aux.packets_burst_size
            ])

        df = pd.DataFrame(data_source_rows, columns=Data_Source.attr_names)

        # create the dir if it not exist
        if not os.path.exists(file_path):
            os.makedirs(file_path)

        file_name = "{}/data_source.csv".format(file_path)

        df.to_csv(file_name, sep=';', index=False)

    @staticmethod
    def list(data_sources):
        print("Data Sources (total: {})".format(len(data_sources)))
        table = BeautifulTable()

        table.columns.header = Data_Source.attr_names

        for src in data_sources:
            aux = data_sources[src]
            table.rows.append([
                aux.name,
                aux.packet_size,
                aux.packet_interval,
                aux.packets_burst_interval,
                aux.packets_burst_size])

        print(table)
        print("\n")

    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)
