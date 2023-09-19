from beautifultable import BeautifulTable
from termcolor import colored, cprint
import pandas as pd
import os
import numpy as np


class SFC_Request:

    ARRIVAL_POISSON="poisson"

    ARRIVAL_LINEAR="linear"

    # The names of the attributes in this object
    attr_names = [
        "Name",
        "User",
        "SFC",
        "Priority",
        "Arrival_Time",
        "Data_Source",
        "Ingress_Node",
        "Egress_Node",
        "Duration",
        "Placed",
        "Replacements",
        "Associated_SFC_Instance"
    ]

    def __init__(self, name, user, sfc, data_source, priority, arrival_time, ingress_node, egress_node, duration):
        """
        Define the SFC Request for the users. Each SFC requested by the user will generate a SFC_Request

        Args:
            name (str): The name of the request
            user (User): The user that requested the SFC
            sfc (SFC): The SFC requested
            data_source (Data_Source): The packet patter generator
            priority (int): The priority of the request, based on the User priority attribute
            arrival_time (int): The time when the request will be processed by the simulation
            ingress_node (Node): Where the data source is connected
            egress_node (Node): Where the last VNF Instance needs to deliver the processed data
            duration (int): The duration of the packets generation
        """
        self.name = name
        self.user = user
        self.sfc = sfc
        self.priority = priority
        self.arrival_time = arrival_time
        self.data_source = data_source
        self.ingress_node = ingress_node
        self.egress_node = egress_node
        self.duration = duration
        self.placed = False

        self.replacements = 0

        # The associated SFC Instance to the current SFC Request
        self.sfc_instance = None

        # It will be false when the packet generation stops
        self.active = True

    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)

    def show(self):
        cprint("SFC Request [{}] Details".format(self.name), "blue", attrs=['bold'])
        table = BeautifulTable()
        table.rows.append([self.name])
        table.rows.append([self.user.name])
        table.rows.append([self.sfc.name])
        table.rows.append([self.priority])
        table.rows.append(["{} ms".format(self.arrival_time)])
        table.rows.append([self.data_source.name])
        table.rows.append([self.ingress_node.name])
        table.rows.append([self.egress_node.name])
        table.rows.append([self.duration])
        table.rows.append([self.placed])
        table.rows.append([self.replacements])
        if self.placed:
            table.rows.append([self.sfc_instance.name])
        else:
            table.rows.append(["No instance"])

        aux_columns_name = SFC_Request.attr_names.copy()
        aux_columns_name.append("SFC's VNFs")
        table.rows.append([self.sfc.vnfs])

        table.rows.header = aux_columns_name

        print(table)
        print("\n")

    def has_user_moved(self):
        return self.user.node.name is not self.ingress_node.name

    @staticmethod
    def get_requests_in_time_window(sfc_requests, time_window_init, time_window_end):
        """
        Return the SFC_Requests in a time window

        Args:
            sfc_requests (dict): SFC_Request list
            time_window_init (int): The start of the time window
            time_window_end (int): The end o the time window
        """
        request_window = []
        for sfc_req in sfc_requests:
            aux_sfc_req = sfc_requests[sfc_req]
            if aux_sfc_req.arrival_time >= time_window_init and aux_sfc_req.arrival_time <= time_window_end:
                request_window.append(aux_sfc_req)

        return request_window

    @staticmethod
    def save_csv(sfc_requests, file_path="."):
        """
        Save the SFC entities into a CSV file

        Args:
            sfc_requests (list): The SFC_Requests that will be saved
            file_path (str, optional): The path where the file will be stored. Defaults to ".".
        """

        sfc_req_rows = []

        for sfc_req in sfc_requests:
            aux = sfc_requests[sfc_req]
            sfc_req_rows.insert(0,[
                aux.name,
                aux.user.name,
                aux.sfc.name,
                aux.priority,
                aux.arrival_time,
                aux.data_source.name,
                aux.ingress_node.name,
                aux.egress_node.name,
                aux.duration,
                aux.placed,
                aux.replacements,
                aux.sfc_instance.name if aux.placed else "No instance"
            ])

        df = pd.DataFrame(sfc_req_rows, columns=SFC_Request.attr_names)

        # create the dir if it not exist
        if not os.path.exists(file_path):
            os.makedirs(file_path)

        file_name = "{}/sfc_requests.csv".format(file_path)

        df.to_csv(file_name, sep=';', index=False)

    @staticmethod
    def list(sfc_requests):
        print("SFC Requests (total: {})".format(len(sfc_requests)))
        table = BeautifulTable(180)
        table.columns.header = SFC_Request.attr_names

        for sfc_req in sfc_requests:
            if isinstance(sfc_req, str):
                aux = sfc_requests[sfc_req]
            else:
                aux = sfc_req

            table.rows.append([
                aux.name,
                aux.user.name,
                aux.sfc.name,
                aux.priority,
                aux.arrival_time,
                aux.data_source.name,
                aux.ingress_node.name,
                aux.egress_node.name,
                aux.duration,
                aux.placed,
                aux.replacements,
                aux.sfc_instance.name if aux.placed else "No instance"
                #aux.user_node_when_placed.name if aux.placed else "None"
            ])
        print(table)
        print("\n")

    @staticmethod
    def order_sfc_requests_by_sfc_similarity(sfc_requests, sfc_similarity, ordering):
        """
        Return a list with sfc_requests ordered by the sfc_similarity

        Args:
            sfc_requests (list): List of the SFC_Requests
            sfc_similarity (dict): Dictionary with the similarity between all the SFCs
            ordering (bool): asc = The similar firstly, else the opposite
        """
        similarity = {}
        ordered_requests_list = []
        for sfc_req in sfc_requests:
            similarity[sfc_req.sfc.name] = 0

        for sfc_req_1 in sfc_requests:
            for sfc_req_2 in sfc_requests:
                if sfc_req_1.sfc.name != sfc_req_2.sfc.name:
                    if similarity[sfc_req_1.sfc.name] < sfc_similarity[sfc_req_1.sfc.name][sfc_req_2.sfc.name]:
                        similarity[sfc_req_1.sfc.name] = sfc_similarity[sfc_req_1.sfc.name][sfc_req_2.sfc.name]

        # order result
        for k, v in sorted(similarity.items(), key=lambda kv: kv[1], reverse=True):
            for sfc_req in sfc_requests:
                if sfc_req.sfc.name == k:
                    ordered_requests_list.append(sfc_req)

        # order result
        if ordering == "desc":
            return ordered_requests_list[::-1]

        return ordered_requests_list

    @staticmethod
    def generate_linear_arrival(num_windows, first_window_time, increase_requests_per_window):
        """
        Generate a linear arrival for the SFC Requests
        """
        val = 0
        instants = []
        count = 0
        for window in range(1, num_windows + 1):
            if count == 0:
                val = 0
            else:
                val = val + first_window_time

            count += 1

            for k in range(window * increase_requests_per_window):
                instants.append(val)

        return instants

    @staticmethod
    def generate_poisson_arrival(seed, sfc_requests_number, last_time_window):

        np.random.seed(int(seed))

        exp = np.random.exponential(size=sfc_requests_number)

        instants = [0]

        for i in list(range(1, len(exp))):
            instants.append(exp[i] + instants[i - 1])

        factor = 1

        if len(instants) > 1:
            factor = last_time_window / instants[-1]

        for i in range(sfc_requests_number):
            instants[i] = int(instants[i] * factor)
            if instants[i] >= last_time_window:
                instants[i] = last_time_window - 1

        return instants