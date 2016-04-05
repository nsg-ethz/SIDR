#!/usr/bin/env python
#  Author:
#  Rudiger Birkner (ETH Zurich)

import networkx as nx
import itertools

from collections import namedtuple, defaultdict


class ASTopo(nx.Graph):
    def __init__(self, topology_file, topology_format, backedges_removed, tier1_threshold, ixp_dataset,
                 c2p_factor, ixp_mode, test=False):
        """
        AS-level topology object.
        :param topology_file: path of the toplogy file
        :param topology_format: format of the topology file (CAIDA = 0, UCLA = 1)
        :param backedges_removed: True if the backedges have already been removed from the topology
        :param tier1_threshold: all nodes with more than tier1_threshold connections and no providers are considered tier1 nodes
        :param ixp_dataset: mapping of ixp_id to its participants' asns
        :param c2p_factor: when adding ixp connections, we add c2p links between nodes whose number of connections differ by c2p_factor
        :param ixp_mode:
        :param test: optional - if True then the test method is started
        :return:
        """

        super(ASTopo, self).__init__()

        self.tier1_nodes = []
        self.no_provider_nodes = []

        if test:
            self.test()
        else:
            # build graph
            print "Build from Topology File"
            self.build_from_file(topology_file, topology_format)

            print "Identify all Nodes without Provider"
            self.no_provider_nodes = self.get_all_nodes_without_provider()

            print "Identify Tier 1 Nodes"
            self.tier1_nodes = self.identify_tier1_nodes(tier1_threshold)

            if not backedges_removed:
                print "Remove Backedges"
                self.remove_backedges()

            if ixp_dataset:
                print "Add IXP Dataset"
                self.add_ixp_links(ixp_dataset, c2p_factor, ixp_mode)

            print "Update list of nodes without Provider"
            self.no_provider_nodes = self.get_all_nodes_without_provider()

            print "Remove Backedges"
            self.remove_backedges()

            print "Count False P2P IXP Links"
            num_ixp_p2p_links, num_false_ixp_p2p_links = self.count_wrong_p2p_links(ixp_dataset)

            # print basic information
            print "Built AS-Level Topology"
            print "-> No. ASes: " + str(self.number_of_nodes())
            print "-> No. of Connections: " + str(self.number_of_edges())
            print "-> No. of Tier 1 ASes: " + str(len(self.tier1_nodes))
            print "-> Tier 1 ASes: " + str(self.tier1_nodes)
            print "-> No. of IXP P2P Links: " + str(num_ixp_p2p_links) + \
                  ", No. of False IXP P2P Links: " + str(num_false_ixp_p2p_links)

    def build_from_file(self, topology_file, topology_format):
        """
        build basic networkx topology from file
        :param topology_file: path of the topology file
        :param topology_format: format of the topology file (CAIDA = 0, UCLA = 1)
        """
        with open(topology_file) as infile:
            for line in infile:
                if line.startswith("#"):
                    continue
                else:
                    if topology_format == 0:
                        x = line.split("\n")[0].split("|")
                        as1 = int(x[0])
                        as2 = int(x[1])
                        relationship = int(x[2])
                    else:
                        x = line.split("\n")[0].split("\t")
                        if x[2] == "p2c":
                            as1 = int(x[0])
                            as2 = int(x[1])
                            relationship = -1
                        elif x[2] == "c2p":
                            as1 = int(x[1])
                            as2 = int(x[0])
                            relationship = -1
                        elif x[2] == "p2p":
                            as1 = int(x[1])
                            as2 = int(x[0])
                            relationship = 0
                        else:
                            continue

                    if not self.has_edge(as1, as2):
                        self.add_edge(as1, as2, relationship=relationship, as1=as1, as2=as2)

    def has_customers(self, asn):
        """
        checks if an AS has customers.
        :param asn: asn of the AS to be checked
        :return: True if the AS has customers, else False
        """
        for neighbor in nx.all_neighbors(self, asn):
            edge_data = self.get_edge_data(asn, neighbor)

            # node is a provider of neighbor
            if edge_data["relationship"] == -1 and edge_data["as1"] == asn:
                return True
        return False

    def has_providers(self, asn):
        """
        checks if an AS has providers.
        :param asn: asn of the AS to be checked
        :return: True if the AS has customers, else False
        """
        for neighbor in nx.all_neighbors(self, asn):
            edge_data = self.get_edge_data(asn, neighbor)

            # node is a customer of neighbor
            if edge_data["relationship"] == -1 and edge_data["as2"] == asn:
                return True
        return False

    def number_of_connections(self, asn):
        """
        Method that counts the number of links of an AS with respect to their type.
        :param asn: asn of the AS of which we are interested in the number of links
        :return: a tuple consisting of the number of customers, providers and peers
        """
        customer_count = 0
        provider_count = 0
        peer_count = 0

        for neighbor in nx.all_neighbors(self, asn):
            edge_data = self.get_edge_data(asn, neighbor)
            if edge_data["relationship"] == -1 and edge_data["as1"] == asn:
                customer_count += 1
            elif edge_data["relationship"] == -1 and edge_data["as2"] == asn:
                provider_count += 1
            elif edge_data["relationship"] == 0:
                peer_count += 1
        return customer_count, provider_count, peer_count

    def get_all_nodes_without_provider(self):
        """
        This method goes through the whole graph and finds all nodes without provider.
        :return: list of all nodes without provider (asns)
        """

        no_provider_nodes = []
        # create list of all nodes without provider and more than tier1_threshold customers
        for node in self.nodes():
            tier1 = True

            # check that node is not a customer of any node
            if not self.has_providers(node):
                no_provider_nodes.append(node)

        return no_provider_nodes

    def identify_tier1_nodes(self, tier1_threshold):
        """
        This method goes through the whole graph and builds a set of tier1 nodes. A node is considered to be tier1
        if it doesn't have any providers or if it has more than tier1_threshold links. Afterwards it makes sure that
        all tier1 nodes are connected to each other through p2p links.
        :return: list of all tier1 nodes (asns)
        """
        tier1_nodes = []

        # create list of all nodes without provider and more than tier1_threshold customers
        for node in self.no_provider_nodes:
            # check the number of customers
            if self.number_of_connections(node)[0] > tier1_threshold:
                tier1_nodes.append(node)

        # make sure that all tier1 nodes are connected through p2p
        pairs = itertools.combinations(tier1_nodes, 2)

        for node1, node2 in pairs:
            if node1 != node2:
                if self.has_edge(node1, node2):
                    if self[node1][node2]['relationship'] == 0:
                        continue
                    else:
                        self[node1][node2]['relationship'] = 0
                else:
                    self.add_edge(node1, node2, relationship=0, as1=node1, as2=node2)

        return tier1_nodes

    def remove_backedges(self):
        """
        Based on the identified tier1 nodes, this method removes all backedges by doing a DFS traversal of the
        topology starting at a tier1 node.
        """

        # Add virtual super node
        super_node = 1000000
        self.add_node(super_node)

        # connect super node to all nodes that don't have a provider through c2p
        for np_node in self.no_provider_nodes:
            self.add_edge(super_node, np_node, relationship=-1, as1=super_node, as2=np_node)

        qnode = namedtuple('Node', 'asn path')

        q = list()
        q.append(qnode(super_node, list()))

        visited = list()

        num_deleted_edges = 0
        j = 0
        while q:
            node = q.pop()

            # debug output
            if node.asn in self.no_provider_nodes:
                j += 1
                print str(j) + "/" + str(len(self.no_provider_nodes))

            # update list of visited nodes and copy it
            if node.path:
                path = list(node.path)
            else:
                path = list()

            path.append(node.asn)
            visited.append(node.asn)

            # first we mark backedges and after checking all neighbors, we remove them
            edges_to_remove = []

            for neighbor in nx.all_neighbors(self, node.asn):
                edge_data = self.get_edge_data(node.asn, neighbor)
                # node is a customer of neighbor - only follow provider to customer links
                if edge_data["relationship"] == -1 and edge_data["as1"] == node.asn:
                    # if we see a backedge, mark it and continue search
                    if neighbor in path:
                        edges_to_remove.append((node.asn, neighbor))
                    # if we haven't looked at this node yet, we add it to the list of nodes
                    elif neighbor not in visited:
                        q.append(qnode(neighbor, list(path)))

            # remove the marked edges
            for edge in edges_to_remove:
                num_deleted_edges += 1
                self.remove_edge(edge[0], edge[1])

        # Remove virtual node and all edges
        for np_node in self.no_provider_nodes:
            self.remove_edge(super_node, np_node)
        self.remove_node(super_node)

        print "Removed " + str(num_deleted_edges) + " backedges"

    def c2p_connection(self, u, v):
        """
        Checks if a pure c2p connection exists between nodes u and v
        :param u: asn
        :param v: asn
        :return: True if c2p connection exists, else False
        """
        qnode = namedtuple('Node', 'asn path_type')

        q = list()
        q.append(qnode(u, -1))

        visited = defaultdict(int)

        while q:
            node = q.pop()
            visited[node.asn] = 1

            if self.has_node(node.asn):
                for neighbor in nx.all_neighbors(self, node.asn):
                    if visited[neighbor] != 1:
                        edge_data = self.get_edge_data(node.asn, neighbor)

                        # c2p - p2c link
                        if edge_data["relationship"] == -1:
                            if node.path_type == -1:
                                path_type = 0 if node.asn == edge_data["as2"] else 1
                            else:
                                path_type = node.path_type
                            # c2p
                            if (node.asn == edge_data["as2"] and path_type == 0)\
                                    or (node.asn == edge_data["as1"] and path_type == 1):
                                if neighbor == v:
                                    return True, -1 if path_type == 0 else 1
                                q.append(qnode(neighbor, path_type))
        return False, None

    def get_as_connectivity(self, ixps):
        # Add virtual super node
        super_node = 1000000
        self.add_node(super_node)

        # connect super node to all nodes without provider through p2c
        for np_node in self.no_provider_nodes:
            self.add_edge(super_node, np_node, relationship=-1, as1=super_node, as2=np_node)

        qnode = namedtuple('Node', 'asn providers')

        q = list()
        q.append(qnode(super_node, set()))

        ixp_participants = ixps.keys()

        c2p_connections = defaultdict(set)

        while q:
            node = q.pop()

            providers = set(node.providers)
            if str(node.asn) in ixp_participants:
                c2p_connections[node.asn] = c2p_connections[node.asn].union(providers)

                if not node.providers:
                    providers = set()

                providers.add(node.asn)

            for neighbor in nx.all_neighbors(self, node.asn):
                edge_data = self.get_edge_data(node.asn, neighbor)
                # neighbor is a customer of node
                if edge_data["relationship"] == -1 and edge_data["as1"] == node.asn:
                    # go to next neighbor in chain
                    q.append(qnode(neighbor, providers))

        # Remove virtual node and all edges
        for np_node in self.no_provider_nodes:
            self.remove_edge(super_node, np_node)
        self.remove_node(super_node)

        return c2p_connections

    def get_as_connectivity_fast(self, ixps):
        # Add virtual super node
        super_node = 1000000
        self.add_node(super_node)

        # connect super node to all nodes without provider through c2p
        for np_node in self.no_provider_nodes:
            self.add_edge(super_node, np_node, relationship=-1, as1=super_node, as2=np_node)

        qnode = namedtuple('Node', 'asn providers')

        q = list()
        q.append(qnode(super_node, set()))

        ixp_participants = ixps.keys()

        # temporary dict to keep track of how many providers of the asn we have already checked
        num_providers = dict()
        c2p_connections = defaultdict(set)
        all_providers = defaultdict(set)

        i = 0
        while q:
            node = q.pop()

            # debug output
            if node.asn in self.no_provider_nodes:
                i += 1
                print str(i) + "/" + str(len(self.no_provider_nodes))

            all_providers[node.asn] = all_providers[node.asn].union(node.providers)
            providers = set(all_providers[node.asn])

            if str(node.asn) in ixp_participants:
                c2p_connections[node.asn] = all_providers[node.asn]
                providers.add(node.asn)

            if node.asn not in num_providers:
                num_providers[node.asn] = [self.number_of_connections(node.asn)[1], 1]
            else:
                num_providers[node.asn][1] += 1

            if num_providers[node.asn][1] >= num_providers[node.asn][0]:
                for neighbor in nx.all_neighbors(self, node.asn):
                    edge_data = self.get_edge_data(node.asn, neighbor)
                    # node is a customer of neighbor
                    if edge_data["relationship"] == -1 and edge_data["as1"] == node.asn:
                        # go to next neighbor in chain
                        q.append(qnode(neighbor, providers))

        # Remove virtual node and all edges
        for np_node in self.no_provider_nodes:
            self.remove_edge(super_node, np_node)
        self.remove_node(super_node)

        print "Number of visited nodes: " + str(len(all_providers)) + \
              ", Total number of nodes: " + str(self.number_of_nodes())

        return c2p_connections

    def add_ixp_links(self, ixps, c2p_factor, ixp_mode=0):
        """
        Adds a p2p link between all members of an IXP if there is no c2p connection between the two
        :param ixps: mapping of ixp_id to its participants
        :param c2p_factor: we add a c2p link between two nodes if their number of costumers differs by c2p_factor
        :param ixp_mode:
        :return:
        """

        print "-> Get AS Connectivity"
        c2p_connections = self.get_as_connectivity_fast(ixps)

        # loop through all ixp connections
        print "-> Start Adding the Links"
        i = 0

        pairs = itertools.combinations(ixps.keys(), 2)

        num_p2p_links = 0
        num_c2p_links = 0

        for pair in pairs:
            i += 1
            if i % 1000000 == 0:
                print "--> Processed " + str(i) + " IXP links"

            participant1 = int(pair[0])
            participant2 = int(pair[1])

            # check if those nodes actually exist
            if self.has_node(participant1) and self.has_node(participant2):
                p1_ixps = set(ixps[pair[0]])
                p2_ixps = set(ixps[pair[1]])
                ixp_intersect = p1_ixps.intersection(p2_ixps)
                if len(ixp_intersect) >= 1:
                    if self.has_edge(participant1, participant2):
                        self[participant1][participant2]['ixps'] = list(ixp_intersect)
                    else:
                        if participant1 in c2p_connections[participant2]:
                            num_c2p_links += 1
                            self.add_edge(participant2, participant1, relationship=-1,
                                          ixps=list(ixp_intersect), as1=participant1, as2=participant2)
                        elif participant2 in c2p_connections[participant1]:
                            num_c2p_links += 1
                            self.add_edge(participant1, participant2, relationship=-1,
                                          ixps=list(ixp_intersect), as1=participant2, as2=participant1)
                        else:
                            # mode 0: by default add a p2p link, if there is no c2p connection between the two
                            if ixp_mode == 0:
                                num_p2p_links += 1
                                self.add_edge(participant1, participant2, relationship=0,
                                              ixps=list(ixp_intersect), as1=participant2, as2=participant1)
                            # mode 1: add by default a p2p link, if there is a c2p+ or the number of neighbors
                            # differ in size more than X times
                            else:
                                num_neighbors_1 = float(nx.degree(self, participant1))
                                num_neighbors_2 = float(nx.degree(self, participant2))

                                if num_neighbors_1 == 0 or num_neighbors_2 == 0:
                                    print "\nERROR"
                                    print "Node " + str(participant1) + " has " + str(num_neighbors_1) + " neighbors"
                                    print "Node " + str(participant2) + " has " + str(num_neighbors_2) + " neighbors"
                                    continue

                                if num_neighbors_1/num_neighbors_2 >= c2p_factor:
                                    num_c2p_links += 1
                                    self.add_edge(participant1, participant2, relationship=-1,
                                                  ixps=list(ixp_intersect), as1=participant1, as2=participant2)
                                    # update connection data structure
                                    c2p_connections[participant2] |= c2p_connections[participant1]
                                    c2p_connections[participant2].add(participant1)
                                elif num_neighbors_2/num_neighbors_1 >= c2p_factor:
                                    num_c2p_links += 1
                                    self.add_edge(participant1, participant2, relationship=-1,
                                                  ixps=list(ixp_intersect), as1=participant2, as2=participant1)
                                    # update connection data structure
                                    c2p_connections[participant1] |= c2p_connections[participant2]
                                    c2p_connections[participant1].add(participant2)
                                else:
                                    num_p2p_links += 1
                                    self.add_edge(participant1, participant2, relationship=0,
                                                  ixps=list(ixp_intersect), as1=participant2, as2=participant1)

        print "--> Added a total of " + str(num_c2p_links + num_p2p_links) + " IXP links of which " + \
              str(num_c2p_links) + " were c2p and " + str(num_p2p_links) + " were p2p"

    def count_wrong_p2p_links(self, ixps):
        print "-> Get AS Connectivity"
        c2p_connections = self.get_as_connectivity_fast(ixps)

        print "-> Check the p2p-links"
        pairs = itertools.combinations(ixps.keys(), 2)

        num_p2p_links = 0
        num_false_p2p_links = 0

        i = 0
        for pair in pairs:
            i += 1
            if i % 1000000 == 0:
                print "--> Processed " + str(i) + " IXP links"

            participant1 = int(pair[0])
            participant2 = int(pair[1])

            # check if those nodes actually exist
            if self.has_node(participant1) and self.has_node(participant2):
                p1_ixps = set(ixps[pair[0]])
                p2_ixps = set(ixps[pair[1]])
                ixp_intersect = p1_ixps.intersection(p2_ixps)
                if len(ixp_intersect) >= 1:
                    if self.has_edge(participant1, participant2):
                        edge_data = self.get_edge_data(participant1, participant2)
                        if edge_data["relationship"] == 0:
                            num_p2p_links += 1
                            if participant1 in c2p_connections[participant2] or participant2 in c2p_connections[participant1]:
                                num_false_p2p_links += 1

        return num_p2p_links, num_false_p2p_links

    def test(self):
        test_cases = [
            {
                'name': "Backedge Removal Test 1",
                'topo': [
                    {'as1': 1, 'as2': 2, 'relationship': -1},
                    {'as1': 1, 'as2': 6, 'relationship': 0},
                    {'as1': 2, 'as2': 3, 'relationship': -1},
                    {'as1': 2, 'as2': 4, 'relationship': -1},
                    {'as1': 4, 'as2': 5, 'relationship': -1},
                    {'as1': 5, 'as2': 2, 'relationship': -1},
                    {'as1': 6, 'as2': 7, 'relationship': -1},
                    {'as1': 6, 'as2': 8, 'relationship': -1},
                    {'as1': 7, 'as2': 8, 'relationship': 0},
                    {'as1': 7, 'as2': 9, 'relationship': -1}
                ],
                'backedges': [
                    (5, 2)
                ],
                'c2p_connections': [
                    (1, 5, True), (4, 7, False), (7, 8, False), (9, 6, True),
                ],
                'tier1_threshold': 0,
            },
            {
                'name': "Backedge Removal Test 2",
                'topo': [
                    {'as1': 1, 'as2': 2, 'relationship': -1},
                    {'as1': 2, 'as2': 3, 'relationship': -1},
                    {'as1': 2, 'as2': 4, 'relationship': -1},
                    {'as1': 4, 'as2': 5, 'relationship': -1},
                    {'as1': 5, 'as2': 2, 'relationship': -1},
                    {'as1': 5, 'as2': 6, 'relationship': -1},
                    {'as1': 6, 'as2': 4, 'relationship': -1},
                    {'as1': 6, 'as2': 7, 'relationship': -1},
                    {'as1': 7, 'as2': 5, 'relationship': -1}
                ],
                'backedges': [
                    (5, 2), (6, 4), (7, 5)
                ],
                'c2p_connections': [
                    (3, 7, False), (7, 1, True), (2, 6, True)
                ],
                'tier1_threshold': 0,
            },
            {
                'name': "Add IXPs Test 1",
                'topo': [
                    {'as1': 1, 'as2': 2, 'relationship': -1},
                    {'as1': 1, 'as2': 3, 'relationship': -1},
                    {'as1': 3, 'as2': 6, 'relationship': -1},
                    {'as1': 4, 'as2': 7, 'relationship': -1},
                    {'as1': 5, 'as2': 7, 'relationship': -1},
                    {'as1': 6, 'as2': 5, 'relationship': -1},
                ],
                'ixps': {
                    99: [2, 3, 4, 5],
                    77: [2, 4],
                    55: [3, 7, 2],
                },
                'edges': [
                    (2, 4, [77, 99], 0),
                    (2, 3, [99, 55], 0),
                    (2, 5, [99], 0),
                    (3, 4, [99], 0),
                    (3, 5, [99], -1),
                    (4, 5, [99], 0),
                    (3, 3, [55], -1),
                    (2, 7, [55], 0),
                ],
                'tier1_threshold': 0,
            },
            {
                'name': "Tier 1 Test 1",
                'topo': [
                    {'as1': 1, 'as2': 5, 'relationship': -1},
                    {'as1': 2, 'as2': 4, 'relationship': -1},
                    {'as1': 2, 'as2': 6, 'relationship': -1},
                    {'as1': 3, 'as2': 7, 'relationship': -1},
                    {'as1': 4, 'as2': 8, 'relationship': -1},
                    {'as1': 4, 'as2': 9, 'relationship': -1},
                ],
                'tier1_edges': [
                    (1, 2),
                    (1, 3),
                    (2, 3),
                ],
                'tier1_nodes': [1, 2, 3],
                'tier1_threshold': 0,
            },
            {
                'name': "Tier 1 Test 2",
                'topo': [
                    {'as1': 1, 'as2': 5, 'relationship': -1},
                    {'as1': 2, 'as2': 6, 'relationship': -1},
                    {'as1': 3, 'as2': 7, 'relationship': -1},
                    {'as1': 4, 'as2': 8, 'relationship': -1},
                ],
                'tier1_edges': [
                    (1, 2),
                    (1, 3),
                    (1, 4),
                    (2, 3),
                    (2, 4),
                    (3, 4),
                ],
                'tier1_nodes': [1, 2, 3, 4],
                'tier1_threshold': 0,
            },
            {
                'name': "Tier 1 Test 2",
                'topo': [
                    {'as1': 1, 'as2': 2, 'relationship': -1},
                    {'as1': 1, 'as2': 4, 'relationship': -1},
                    {'as1': 1, 'as2': 5, 'relationship': -1},
                    {'as1': 1, 'as2': 6, 'relationship': -1},
                    {'as1': 2, 'as2': 3, 'relationship': -1},
                    {'as1': 2, 'as2': 7, 'relationship': -1},
                    {'as1': 2, 'as2': 8, 'relationship': -1},
                    {'as1': 2, 'as2': 9, 'relationship': -1},
                    {'as1': 3, 'as2': 10, 'relationship': -1},
                    {'as1': 3, 'as2': 11, 'relationship': -1},
                    {'as1': 3, 'as2': 12, 'relationship': -1},
                    {'as1': 4, 'as2': 13, 'relationship': -1},
                    {'as1': 4, 'as2': 14, 'relationship': -1},
                ],
                'tier1_edges': [
                ],
                'tier1_nodes': [1],
                'tier1_threshold': 0,
            },
            {
                'name': "Tier 1 Test 3",
                'topo': [
                    {'as1': 1, 'as2': 2, 'relationship': -1},
                    {'as1': 2, 'as2': 3, 'relationship': -1},
                    {'as1': 4, 'as2': 5, 'relationship': -1},
                ],
                'tier1_edges': [
                    (1, 4),
                ],
                'tier1_nodes': [1, 4],
                'tier1_threshold': 0,
            },
        ]

        for test_case in test_cases:
            print "Running " + str(test_case['name'])
            self.clear()

            for edge in test_case['topo']:
                self.add_edge(edge['as1'], edge['as2'],
                              relationship=edge['relationship'], as1=edge['as1'], as2=edge['as2'])

            print "--> Built Topology with " + str(self.number_of_nodes()) + " nodes and "\
                  + str(self.number_of_edges()) + " edges and " + str(len(nx.cycle_basis(self))) + " cycles"

            self.tier1_nodes = self.identify_tier1_nodes(test_case['tier1_threshold'])

            print "--> Tier 1 Nodes " + str(self.tier1_nodes)

            self.remove_backedges()

            if 'ixps' in test_case:
                self.add_ixp_links(test_case['ixps'], 100, 0)

            error = False
            if 'backedges' in test_case:
                for backedge in test_case['backedges']:
                    if self.has_edge(backedge[0], backedge[1]):
                        print "--> Failed to remove edge " + str(backedge)
                        error = True

                for connection in test_case['c2p_connections']:
                    if self.c2p_connection(connection[0], connection[1])[0] != connection[2]:
                        print "--> Failed to correctly detect the connection between " + str(connection[0]) + " and " \
                              + str(connection[1])
                        error = True
            if 'ixps' in test_case:
                for edge in test_case['edges']:
                    if self.has_edge(edge[0], edge[1]):
                        if edge[2]:
                            if 'ixps' in self[edge[0]][edge[1]]:
                                if set(self[edge[0]][edge[1]]['ixps']) != set(edge[2]):
                                    print "--> Failed to insert the IXP edge from " + str(edge[0]) + \
                                          " to " + str(edge[1]) + " correctly: " + \
                                          str(self[edge[0]][edge[1]]['ixps']) + " instead of " + str(edge[2])
                                    error = True
                                if self[edge[0]][edge[1]]['relationship'] != edge[3]:
                                    print "--> Failed to insert the IXP edge with type " + str(edge[3]) + \
                                          " instead of " + str(self[edge[0]][edge[1]]['relationship']) + " correctly: "
                                    error = True
                                if self[edge[0]][edge[1]]['relationship'] == -1 and \
                                        (self[edge[0]][edge[1]]['as1'] != edge[0]):
                                    print "--> Failed to insert the IXP edge with the correct orientation from " + \
                                          str(edge[0]) + " to " + str(edge[1])
                                    error = True
                            else:
                                print "--> Failed to add the IXP number to the edge from " + str(edge[0]) + \
                                      " to " + str(edge[1])
                        else:
                            print "--> Added edge from " + str(edge[0]) + " to " + str(edge[1]) + \
                                  " even though a c2p-path exists"
                            error = True

            if 'tier1_edges' in test_case:
                if self.tier1_nodes != test_case['tier1_nodes']:
                    print "--> Failed to identify all tier 1 nodes correctly: Found " + str(self.tier1_nodes) + \
                          " should have found " + str(test_case['tier1_nodes'])
                    error = True

                for edge in test_case['tier1_edges']:
                    if not (self.has_edge(edge[0], edge[1]) and self[edge[0]][edge[1]]['relationship'] == 0):
                        print "--> Failed to add p2p edge " + str(edge)
                        error = True

            if error:
                print "-> Test failed\n"
            else:
                print "-> Test passed\n"

''' main '''
if __name__ == '__main__':
    ASTopo(None, None, None, None, None, None, 0, True)
