from beautifultable import BeautifulTable
from termcolor import cprint
import pandas as pd
import os
import random


class Link:
    # The names of the attributes in this object
    attr_names = [
        "Name",
        "Node_1",
        "Node_2",
        "Counter",
        "Bandwidth",
        "Loss Rate",
        "Propagation",
        "Power_Consumed",
        "Max_Packet_Queue"
    ]

    def __init__(self, name, bandwidth, loss_rate, source, target, propagation, energy_consumption, counter,
                 max_packet_queue):
        """ The definition of the virtual Link

        Args:
            name (str): name of the edge node
            bandwidth (int): The bandwidth (MB/s)
            loss_rate (float): The loss rate
            source (str): Is the source node
            target (str): Is the target node
            propagation (int): Is the propagation time between the edge nodes (ms)
            energy_consumption (float): Is the energy consumed by the link (Watt/hour) (https://riunet.upv.es/bitstream/handle/10251/47643/Router_Power_Consumption_Analysis%20_Towards_Green_Communications%20-%20Final.pdf;jsessionid=5307B300AA345E7EC00625DC07598538?sequence=2) the value is using the link in full bandwidth
            counter (int): The counter of the links between the same nodes source and target
            max_packet_queue (int): The max number of packets in the Link's Queue
        """
        self.name = name
        self.bandwidth = bandwidth
        self.loss_rate = loss_rate
        self.source = source
        self.target = target
        self.propagation = propagation
        self.energy_consumption = energy_consumption
        self.counter = counter
        self.max_packet_queue = max_packet_queue

        # The number os packets in the Link Queue
        self.packet_queue_count = 0

    def add_packet_in_queue(self):
        """
        Plus one to the packet queue size
        """
        if self.packet_queue_count < self.max_packet_queue or self.max_packet_queue == -1:
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

    def get_latency(self, packet_size):
        return (packet_size / self.bandwidth) + self.propagation

    def get_energy_consumed(self, packet_size):
        """Return the energy that will be used to send the packet

        Args:
            packet_size (int): Packet size in bits

        Returns:
            [float]: The total in watts used to send that packet
        """
        power_per_second = self.energy_consumption / 36000

        return power_per_second * (packet_size / self.bandwidth);

    def show(self):
        cprint("Link [{}] Details".format(self.name), "blue", attrs=['bold'])
        table = BeautifulTable()
        table.rows.append([self.name])
        # table.rows.append([self.latency])
        table.rows.append([self.source])
        table.rows.append([self.target])
        table.rows.append([self.counter])
        table.rows.append(["{} Mbps".format(self.bandwidth)])
        table.rows.append(["{}%".format(self.loss_rate)])
        table.rows.append(["{} ms".format(self.propagation)])
        table.rows.append(["{} Watts/Hour".format(self.energy_consumption)])
        table.rows.append(["{} ".format(self.max_packet_queue)])
        table.rows.header = self.attr_names
        print(table)
        print("\n")

    @staticmethod
    def save_csv(links, file_path="."):
        """
        Save the Link entities into a CSV file

        Args:
            file_path (str, optional): The path where the file will be stored. Defaults to ".".
        """

        link_rows = []

        for link in links:
            aux = links[link]
            link_rows.insert(0, [
                aux.name,
                aux.source,
                aux.target,
                aux.counter,
                aux.bandwidth,
                aux.loss_rate,
                aux.propagation,
                aux.energy_consumption,
                aux.max_packet_queue
            ])

        df = pd.DataFrame(link_rows, columns=Link.attr_names)

        # create the dir if it not exist
        if not os.path.exists(file_path):
            os.makedirs(file_path)

        file_name = "{}/links.csv".format(file_path)

        df.to_csv(file_name, sep=';', index=False)

    @staticmethod
    def get_links_between_nodes(links, source_node, target_node):
        """Return a list with the links between two nodes

        Args:
            links (Dict): Dic with all the possible links
            source_node (str): Name of the source node
            target_node (str): Name of the target node
        """

        links_between_nodes = []

        aux_s = source_node[2:]
        aux_t = target_node[2:]

        # Get the loopback link
        if aux_s == aux_t:
            loopback_link = "l_{}_loopback".format(aux_s)
            links_between_nodes.append(links[loopback_link])
        else:
            count = 0
            link_name = "l_{}_{}_{}".format(aux_s, aux_t, count)
            aux_keys = links.keys()
            while link_name in aux_keys:
                links_between_nodes.append(links[link_name])
                count = count + 1
                link_name = "l_{}_{}_{}".format(aux_s, aux_t, count)

        # This is the approach we used but it was very slow
        # links_between_nodes2 = []
        # for link in list(links.values()):
        #     if link.source == source_node and link.target == target_node:
        #         links_between_nodes2.append(link)
        #
        # print("************")
        # Link.list(links_between_nodes)
        # Link.list(links_between_nodes2)
        # print("--------------")

        return links_between_nodes

    @staticmethod
    def get_random_link_between_nodes(links, source_node, target_node):
        """Return the name of a random link between two nodes

    Args:
        links (Dict): Dic with all the possible links
        source_node (str): Name of the source node
        target_node (str): Name of the target node
    """
        links_between_nodes = Link.get_links_between_nodes(links, source_node, target_node)

        link_name = ''
        if len(links_between_nodes) > 0:
            link_selected = random.choice(links_between_nodes)
            link_name = link_selected.name
        return link_name

    @staticmethod
    def list(links):
        print("Links (total: {})".format(len(links)))
        table = BeautifulTable(150)
        table.columns.header = Link.attr_names

        for link in links:

            if isinstance(link, str):
                aux = links[link]
            else:
                aux = link

            table.rows.append([
                aux.name,
                aux.source,
                aux.target,
                aux.counter,
                aux.bandwidth,
                aux.loss_rate,
                aux.propagation,
                aux.energy_consumption,
                aux.max_packet_queue
            ])

        print(table)
        print("\n")

    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)
