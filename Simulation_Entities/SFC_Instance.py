from beautifultable import BeautifulTable
from termcolor import colored, cprint
import pandas as pd
import os


class SFC_Instance:

    # The names of the attributes in the SFC_Instances
    attr_names = [
        "Name",
        "SFC",
        "Timeout",
        "Net_Slice",
        "Accept_New_Requests",
        "Active",
        "SFC_Req",
        "Ingress",
        "Egress",
        "Links"
    ]

    def __init__(self, name, sfc, timeout, slice, ingress_node, egress_node):
        """
        Is the object that will track all the SFC Requests to the VNF Instance and the links
        used to transfer the packet between the VNF Instances

        Args:
            name (str): The name of the request
            sfc (SFC): The SFC type of the instance
            timeout (int): The time that the SFC Instance will be alive without any new packet arrive
            slice (str): The slice where the SFC Instance will be executed
            ingress_node (Node): The ingress node
            egress_node (Node): The egress node
        """
        self.name = name
        self.sfc = sfc
        self.timeout = timeout
        self.slice = slice
        self.accept_requests = True
        self.active = True
        self.ingress_node = ingress_node
        self.egress_node = egress_node
        self.sfc_requests = []

        # set with vnf name as key, it indicate the link that will be used to the next hope of the packet
        self.links = {}

    def get_link(self, vnf_name):
        """Return the link name that will be used by the SFC_Instance to send the data processed by VNF

        Args:
            vnf_name (str): The name of the VNF, or ingress if was the first VNF

        Returns:
            str: link name
        """
        return self.links[vnf_name]

    def set_vnf_link(self, vnf_name, link_name):
        """
        Define the link for the next VNF Instance

        Args:
            vnf_name (str): The name of the VNF
            link_name (str): The name of the link
        """
        self.links[vnf_name] = link_name

    def is_unlocked(self):
        return self.accept_requests

    def add_sfc_request(self, sfc_request):
        """
        Attach a new SFC_Request to the SFC_Instance

        Args:
            sfc_request (SFC_Request): The SFC_Request that will be attached to the SFC_Instance
        """
        self.sfc_requests.append(sfc_request)
        self.timeout = self.sfc.timeout

    def lock(self):
        """
        Not allow new SFC_Requests to be attached with the SFC_Instance
        """
        self.accept_requests = False

    def unlock(self):
        """
        Allows that new SFC_Requests to be attached with the SFC_Instance
        """
        self.accept_requests = True

    def get_sfc_requests_names(self):
        """
        Create a list with the SFC Requests that the SFC_Instance is hosting

        Returns:
            list: list of sfc name
        """
        aux_req = []
        for aux in self.sfc_requests:
            aux_req.append(aux.name)

        return aux_req

    def show(self):
        cprint("SFC Instance [{}] Details".format(self.name), "blue", attrs=['bold'])
        table = BeautifulTable()
        table.rows.append([self.name])
        table.rows.append([self.sfc.name])
        table.rows.append([self.timeout])
        table.rows.append([self.slice])
        table.rows.append([self.accept_requests])
        table.rows.append([self.active])
        table.rows.append([self.get_sfc_requests_names()])
        table.rows.append([self.ingress_node.name])
        table.rows.append([self.egress_node.name])
        table.rows.append([self.links])
        table.rows.header = SFC_Instance.attr_names
        print(table)
        print("\n")

    @staticmethod
    def save_csv(sfc_instances, vnf_instances, file_path="."):
        """
        Save the SFC instances into a CSV file

        Args:
            file_path (str, optional): The path where the file will be stored. Defaults to ".".
        """
        new_columns = SFC_Instance.attr_names.copy()
        new_columns.append("VNF_Instances")

        sfc_instance_rows = []

        for aux in sfc_instances:

            aux_vnf_instances = []
            for vnf_instance in vnf_instances:
                if aux.name in vnf_instance.sfc_instances:
                    aux_vnf_instances.append(vnf_instance.name)

            sfc_instance_rows.insert(0, [
                aux.name,
                aux.sfc.name,
                aux.timeout,
                aux.slice,
                aux.accept_requests,
                aux.active,
                aux.get_sfc_requests_names(),
                aux.ingress_node.name,
                aux.egress_node.name,
                aux.links,
                aux_vnf_instances
            ])

        df = pd.DataFrame(sfc_instance_rows, columns=new_columns)

        # create the dir if it not exist
        if not os.path.exists(file_path):
            os.makedirs(file_path)

        file_name = "{}/sfc_instance_entities.csv".format(file_path)

        df.to_csv(file_name, sep=';', index=False)

    @staticmethod
    def list(sfc_instances):
        print("SFC Instances (total: {})".format(len(sfc_instances)))
        table = BeautifulTable(180)
        table.columns.header = SFC_Instance.attr_names

        for sfc_instance in sfc_instances:
            if isinstance(sfc_instance, str):
                aux = sfc_instances[sfc_instance]
            else:
                aux = sfc_instance

            str_req = "\n".join(aux.get_sfc_requests_names())
            str_links = ""
            for k, v in aux.links.items():
                str_links = "{}\n{} = '{}'".format(str_links, k, v)

            table.rows.append([
                aux.name,
                aux.sfc.name,
                aux.timeout,
                aux.slice,
                aux.accept_requests,
                aux.active,
                str_req,
                aux.ingress_node.name,
                aux.egress_node.name,
                str_links
            ])

        print(table)
        print("\n")

    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)

    def __eq__(self, other):
        return self.name == other.name
