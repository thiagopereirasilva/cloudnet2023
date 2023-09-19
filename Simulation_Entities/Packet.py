from beautifultable import BeautifulTable
from termcolor import colored, cprint
import pandas as pd
import os
import csv


class Packet:
    # The names of the attributes in the Packet
    attr_names = [
        "Packet_ID",
        "Created_At",
        "Size",
        "SFC_Request",
        "Total_SFC_Requests_Active",
        "User",
        "Max_Delay",
        "Delay",
        "Mobility_Penalty",
        "SLA_Violated",
        "SLA_Violation_Percentage",
        "Active",
        "Dropped",
        "Orphan",
        "Processed"
    ]

    def __init__(self, packet_id, created_at, sfc_request, max_delay, total_sfc_requests_active, size):
        """ The Packet entity
        Args:
            packet_id (str): The Packet_ID
            created_at (int): The simulation time when it were created
            sfc_request (SFC_Request): The SFC Request that generate the packet
            max_delay (int): The SLA will be considered violated if the delay were higher than the max_delay
            total_sfc_requests_active (int): The total of SFC Requests active when the packet was created
            size (int): The packet size (used to calc the process time in the VNF and in the link
        """
        self.packet_id = packet_id
        self.created_at = created_at
        self.sfc_request = sfc_request
        self.max_delay = max_delay
        self.delay = 0
        self.mobility_penalty = 0
        self.sla_violated = False
        self.sla_violation_percentage = 0.0
        self.active = True
        self.dropped = False
        self.orphan = False
        self.processed = False
        self.total_sfc_requests_active = total_sfc_requests_active
        self.size = size

    def set_size(self, size):
        """
        Define the size of the packet, this value will be used to compute the total of cpu and bandwidth usage

        Args:
            size (int): The packet size in CP
        """
        self.size = size

    def show(self):
        cprint("Packet [{}] Details".format(self.packet_id), "blue", attrs=['bold'])
        table = BeautifulTable()
        table.rows.append([self.packet_id])
        table.rows.append([self.created_at])
        table.rows.append([self.size])
        table.rows.append([self.sfc_request.name])
        table.rows.append([self.total_sfc_requests_active])
        table.rows.append([self.sfc_request.user.name])
        table.rows.append([self.max_delay])
        table.rows.append([self.delay])
        table.rows.append([self.mobility_penalty])
        table.rows.append([self.sla_violated])
        table.rows.append([self.sla_violation_percentage])
        table.rows.append([self.active])
        table.rows.append([self.dropped])
        table.rows.append([self.orphan])
        table.rows.append([self.processed])
        table.rows.header = Packet.attr_names
        print(table)
        print("\n")

    @staticmethod
    def save_csv(packets, file_path="."):
        """Save the SFC instances into a CSV file

        Args:
            packets: The list os all the packets, the index is a tuple (sfc_request_name, packet_id)
            file_path (str, optional): The path where the file will be stored. Defaults to ".".
        """

        # create the dir if it not exist
        if not os.path.exists(file_path):
            os.makedirs(file_path)

        # Older approach using pandas to generate the CSV (it is slow)
        file_name2 = "{}/packets_entities.csv".format(file_path)
        new_columns = Packet.attr_names.copy()

        packets_rows = []
        
        for aux in packets:
            packet = packets[aux]
        
            packets_rows.insert(0,[
                packet.packet_id,
                packet.created_at,
                packet.size,
                packet.sfc_request.name,
                packet.total_sfc_requests_active,
                packet.sfc_request.user.name,
                packet.max_delay,
                packet.delay,
                packet.mobility_penalty,
                packet.sla_violated,
                packet.sla_violation_percentage,
                packet.active,
                packet.dropped,
                packet.orphan,
                packet.processed,
            ])
        
        df = pd.DataFrame(packets_rows, columns=new_columns)

        df.to_csv(file_name2, sep=';', index=False)

    @staticmethod
    def list(packets):
        print("Packets ({})".format(len(packets)))

        table = BeautifulTable(180)
        table.columns.header = Packet.attr_names

        for aux in packets:
            packet = packets[aux]
            table.rows.append([
                packet.packet_id,
                packet.created_at,
                packet.size,
                packet.sfc_request.name,
                packet.total_sfc_requests_active,
                packet.sfc_request.user.name,
                packet.max_delay,
                packet.delay,
                packet.mobility_penalty,
                packet.sla_violated,
                packet.sla_violation_percentage,
                packet.active,
                packet.dropped,
                packet.orphan,
                packet.processed
            ])

        print(table)
        print("\n")

    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)
