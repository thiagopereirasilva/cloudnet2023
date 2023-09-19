from networkx.classes.function import nodes
from Simulation_Entities.VNF_Instance import VNF_Instance
from Edge_Entities.Link import Link
from collections import defaultdict
from Edge_Entities.Node import Node
from Edge_Entities.Link import Link
import networkx as nx
import matplotlib.pyplot as plt
import os


class Placement(object):

    def __init__(self, environment):
        self.environment = environment
        self.sfc_notplaced = {}
        self.instance_names = defaultdict(lambda: 0)
        self.pos = {}
        self.G = ""
        self.compute_link_bw_limit=0

        try:
            if os.environ["COMPUTE_LINK_BW_LIMIT"] == "1":
                self.compute_link_bw_limit = 1
        except KeyError as ke:
            pass

        super().__init__()

    def execute(self, sfc_requests, sd, time, file_path=""):
        pass

    def show(self):
        pass

    def create_unique_instance_name(self, node_name, vnf_name):
        """Create a name for a new instance

        Args:
            node_name (str): The name of the node
            vnf_name (str): The name of the VNF

        Returns:
            str: The name of the new instance
        """
        counter = self.instance_names[(node_name, vnf_name)] + 1
        instance_name = "{}_{}_{}".format(node_name, vnf_name, counter)
        self.instance_names[(node_name, vnf_name)] = counter
        return instance_name

    def add_sfc_not_placed(self, vnf_instances, user, sfc):
        """Define that an SFC cannot be placed.

        Remove the VNF_Instance for all the VNF of the SFC that already be placed

        Args:
            VNF_Instances (list): List of all VNF placed
            user (User): User object
            sfc (SFC): SFC object
        """
        for i in vnf_instances:
            vnf_name = i.vnf.name
            aux_k = (user.name, sfc.name, vnf_name)
            if aux_k in i.sfc_instances:
                i.sfcs.remove(aux_k)

        for i in vnf_instances:
            if len(i.sfc_instances) == 0:
                vnf_instances.remove(i)

        # verify if there is any instance without any 
        self.sfc_notplaced[(user.name, sfc.name)] = 1

        return vnf_instances

    def get_sfc_not_placed(self):
        return self.sfc_notplaced

    # This function will take a list of values we want to turn into nodes
    # Then it assigns a y-value for a specific value of X creating columns
    def create_pos(self, column, node_list, max_len):

        pos = {}

        y_val = int(max_len / 2) - len(node_list) + 1

        if y_val < 0:
            y_val = 0

        for key in node_list:
            pos[key] = (column, y_val)
            y_val = y_val + 1
        return pos

    def get_link_attr(self, link, attr):
        """Get the value of a particular attribute

        Args:
            link (Link): The link
            attr (str): The attribute

        Returns:
            int: The value of the attribute in the link
        """
        if attr == "bandwidth":
            return link.bandwidth

        if attr == "propagation":
            return link.propagation

        if attr == "energy_consumption":
            return link.energy_consumption

    def get_nodes_vnf(self, G, vnf_name):
        """Return the nodes of a graph that can process a VNF

        Args:
            G (Networkx): The Graph
            vnf_name (str): The VNF Name
        """
        aux_nodes = []
        nodes = G.nodes(data=True)
        for node in nodes:
            name = node[0]
            data = node[1]
            if 'vnf' in data.keys() and data['vnf'] == vnf_name:
                aux_nodes.append(node)

            # if node['vnf'] == vnf_name:
            #     aux_nodes.append(node)

        return aux_nodes

    def create_graph(self, sfc_request, link_metric_edge_weight="bandwidth", file_path=""):
        """Create a graph of the possible graph for the SFC Request

        Args:
            sfc_request (SFC_Request): The SFC Request to be placed
            link_metric_edge_weight (str): The name of the attribute that will be placed in the edge weight (bandwidth / propagation / energy_consumption)
            file_path (str): The path where the file with the graph image will be saved
        """
        G = nx.MultiDiGraph()
        vnfs = sfc_request.sfc.vnfs
        sfc_len = len(vnfs)
        nodes_vnf_level = {}
        nodes_vnf = []
        node_level = {}

        level = 0
        for i in range(sfc_len + 2):
            nodes_vnf_level[i] = []
            node_level[i] = []

        # Add the ingress node
        ingress_node_name = "ingress_{}".format(sfc_request.ingress_node.name)
        node_level[0].append(ingress_node_name)

        # Add the egress node
        egress_node_name = "egress_{}".format(sfc_request.egress_node.name)
        node_level[sfc_len + 1].append(egress_node_name)

        level = 1
        max_nodes = 0

        for vnf in vnfs:
            for aux in self.environment.get_nodes_vnf(vnf):
                node_name = "{}_{}".format(aux.name, vnf)
                node_level[level].append(node_name)

                # Link from the ingress with all the nodes of the first VNF
                if level == 1:
                    links = Link.get_links_between_nodes(self.environment.links, sfc_request.ingress_node.name,
                                                         aux.name, )
                    for link in links:
                        G.add_edge(ingress_node_name, node_name, link_name=link.name,
                                   weight=self.get_link_attr(link, link_metric_edge_weight), target_node=aux.name,
                                   aux_node_name=node_name)

                    # if sfc_request.ingress_node.name == aux.name:
                    #     # key_name = "{}_{}".format(ingress_node_name, node_name)
                    #     G.add_edge(ingress_node_name, node_name, link_name="", weight=0, target_node=aux.name, aux_node_name=node_name)

                # Link for the middle of the SFC
                if level < sfc_len:
                    next_vnf = vnfs[level]
                    for aux2 in self.environment.get_nodes_vnf(next_vnf):
                        next_node_name = "{}_{}".format(aux2.name, next_vnf)
                        links = Link.get_links_between_nodes(self.environment.links, aux.name, aux2.name)
                        for link in links:
                            G.add_edge(node_name, next_node_name, link_name=link.name,
                                       weight=self.get_link_attr(link, link_metric_edge_weight), target_node=aux2.name,
                                       aux_node_name=node_name)

                        # # This self is only for creating a key_name, the simulation will skip to get links between the same 
                        # # source and target node
                        # if aux.name == aux2.name:
                        #     # key_name = "self_{}_{}".format(aux.name, aux2.name)
                        #     G.add_edge(node_name, next_node_name, link_name="", weight=0, target_node=aux2.name, aux_node_name=node_name)

                # Link to the egress with all the nodes of the first VNF
                if level == sfc_len:
                    links = Link.get_links_between_nodes(self.environment.links, aux.name, sfc_request.egress_node.name)
                    for link in links:
                        G.add_edge(node_name, egress_node_name, link_name=link.name,
                                   weight=self.get_link_attr(link, link_metric_edge_weight),
                                   target_node=sfc_request.egress_node.name,
                                   node_name=sfc_request.egress_node.name, aux_node_name=node_name)

                    # if sfc_request.egress_node.name == aux.name:                        
                    #     G.add_edge(node_name, egress_node_name, link_name="", weight=0, node_name=sfc_request.egress_node.name, aux_node_name=node_name)

            if len(node_level[level]) > max_nodes:
                max_nodes = len(node_level[level])

            # Add all the nodes
            for n in node_level[level]:
                G.add_node(n, node=aux.name, vnf=vnf)

            # G.add_nodes_from(node_level[level])

            level += 1

        # Save the figure
        pos = {}
        for i in range(level + 1):
            p = self.create_pos(i, node_level[i], max_nodes)
            pos.update(p)

        if file_path:
            # create folder if not exist
            if not os.path.exists(file_path):
                os.makedirs(file_path)

            file_name = "{}{}.png".format(file_path, sfc_request.name)

            color_map = []

            for node in nx.nodes(G):

                if node == ingress_node_name:
                    color_map.append('orange')
                elif node == egress_node_name:
                    color_map.append('orange')
                else:
                    color_map.append('grey')

            fig = plt.figure(3, figsize=(10, 10))
            fig.clf()

            ax = fig.gca()
            for e in G.edges:
                ax.annotate("",
                            xy=pos[e[0]], xycoords='data',
                            xytext=pos[e[1]], textcoords='data',
                            arrowprops=dict(arrowstyle="<-", color="black",
                                            shrinkA=5, shrinkB=5,
                                            patchA=None, patchB=None,
                                            connectionstyle="arc3,rad=rrr".replace('rrr', str(0.3 * e[2])
                                                                                   ),
                                            )
                            )
            ax.margins(0.1)
            plt.axis("off")
            nx.draw_networkx_nodes(G, pos, node_color=color_map)
            nx.draw_networkx_labels(G, pos, font_color='red')

            # plt.show()
            fig.savefig(file_name)

        # Returns the Graph with all the nodes and links in the environment that potentially can be used in the
        # placement plan
        self.pos = pos
        self.G = G

        return G

    def save_image_placed_plan(self, sfc_instance, file_path):
        """Create a image using the graph and the links select by the placement algorithm

        Args:
            G (networkx): The networkx graph
            sfc_instance (SFC Instance): The sfc instance
            file_path (str): The path where the file will be saved
        """

        if not os.path.exists(file_path):
            os.makedirs(file_path)

        file_name = "{}/{}_plan.png".format(file_path, sfc_instance.name)

        vnf_instances = self.environment.get_vnf_instance_of_sfc_instance(sfc_instance)

        links = []
        for k, v in sfc_instance.links.items():
            links.append(v)

        node_names = ["ingress_{}".format(sfc_instance.ingress_node.name),
                      "egress_{}".format(sfc_instance.egress_node.name)]

        for vnf_instance in vnf_instances:
            node_names.append("{}_{}".format(vnf_instance.node.name, vnf_instance.vnf.name))

        color_map = []

        G = self.G
        pos = self.pos

        for node in nx.nodes(G):
            if node in node_names or node.find('ingress') == 0 or node.find('egress') == 0:
                color_map.append('grey')
            else:
                color_map.append('grey')

        fig = plt.figure(3, figsize=(10, 10))
        fig.clf()

        ax = fig.gca()
        ax.clear()

        for e in G.edges:
            # the the edge are in the links of the SFC_Instance use green, otherwise use black
            c = "grey"
            line_style = "--"
            line_width = 0.5

            edge_data = G.edges[e]

            # @todo This edge_blue variable can be used if more restrictions of edge nodes were discovered
            edge_blue = False

            if edge_data['link_name'] in links and e[0] in node_names and e[1] in node_names:
                edge_blue = True

            if edge_blue:
                c = "blue"
                line_style = "-"
                line_width = 2

            ax.annotate("",
                        xy=pos[e[0]], xycoords='data',
                        xytext=pos[e[1]], textcoords='data',
                        arrowprops=dict(arrowstyle="<-", color=c, linestyle=line_style, linewidth=line_width,
                                        shrinkA=5, shrinkB=5,
                                        patchA=None, patchB=None,
                                        connectionstyle="arc3,rad=rrr".replace('rrr', str(0.3 * e[2])
                                                                               ),
                                        )
                        )
        ax.margins(0.1)
        plt.axis("off")
        nx.draw_networkx_nodes(G, self.pos, node_color=color_map)
        nx.draw_networkx_labels(G, self.pos, font_color='blue')
        fig.savefig(file_name)

    @staticmethod
    def get_links_between_nodes_from_edges(edges, source_node_name, target_node_name):

        links = []
        for edge in edges:
            if edge[0] == source_node_name and edge[2]['target_node'] == target_node_name:
                links.append(edge[2]['link_name'])

        return links
