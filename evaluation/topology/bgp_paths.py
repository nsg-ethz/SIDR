#!/usr/bin/env python
#  Author:
#  Rudiger Birkner(ETH Zurich)

import networkx as nx
import math
import json
import argparse

from collections import namedtuple, defaultdict

from mpi4py import MPI

Node = namedtuple('Node', 'asn path')


def build_paths(name, topo, originator_ases, exceptions, ixp_participants, output_path, testing):
    """
    Implements the routing tree algorithm according to http://www.cs.yale.edu/homes/schapira/BGPAttack.pdf
    appendix B.1. The method augments the networkx graph by adding node labels (origin and corresponding path)
    :param topo: networkx graph augmented with edge labels (type of edge)
    :param originator_ases: mapping of asn to all the advertised prefixes
    :return: None
    """

    paths = defaultdict(dict)

    div = 20 if len(originator_ases) > 20 else len(originator_ases)

    i = 0

    q1 = list()
    q2 = list()

    for originator in originator_ases:

        i += 1
        print "Process " + str(name) + ": " + str(i) + " of " + str(len(originator_ases))

        if topo.has_node(originator):

            # init queues
            del q1[:]
            q1.append(Node(originator, []))

            del q2[:]
            q2.append(Node(originator, []))

            paths[originator][originator] = []

            # Stage 1 - add c2p links
            while q1:
                node = q1.pop(0)

                if topo.has_node(node.asn):

                    path = list(node.path)
                    path.append(node.asn)

                    neighbors = nx.all_neighbors(topo, node.asn)

                    for neighbor in neighbors:

                        edge_data = topo.get_edge_data(node.asn, neighbor)
                        neighbor_asn = int(neighbor)

                        if neighbor_asn not in path:
                            # if a node is in exceptions, it prefers peers over customers and advertises these routes
                            # as if they were customer routes
                            if (edge_data["relationship"] == -1 and edge_data["as2"] == node.asn) or \
                                    (neighbor_asn in exceptions and edge_data["relationship"] == 0):

                                # check if we have already visited that node
                                if originator not in paths[neighbor_asn]:
                                    paths[neighbor_asn][originator] = [path]

                                    item = Node(neighbor_asn, list(path))

                                    q1.append(item)
                                    q2.append(item)

                                else:
                                    paths[neighbor_asn][originator].append(path)

            # Stage 2 - add p2p links
            len_q2 = len(q2)

            for j in range(0, len_q2):
                node = q2[j]

                if topo.has_node(node.asn):

                    path = list(node.path)
                    path.append(node.asn)

                    neighbors = nx.all_neighbors(topo, node.asn)

                    for neighbor in neighbors:

                        edge_data = topo.get_edge_data(node.asn, neighbor)
                        neighbor_asn = int(neighbor)

                        if neighbor_asn not in path:
                            # check if we have already visited that node
                            if edge_data["relationship"] == 0:
                                if originator not in paths[neighbor_asn]:
                                    paths[neighbor_asn][originator] = [path]

                                    item = Node(neighbor_asn, list(path))
                                    q2.append(item)

                                else:
                                    paths[neighbor_asn][originator].append(path)

            # Stage 3 - add p2c
            while q2:
                node = q2.pop(0)

                if topo.has_node(node.asn):

                    path = list(node.path)
                    path.append(node.asn)

                    neighbors = nx.all_neighbors(topo, node.asn)
                    for neighbor in neighbors:

                        edge_data = topo.get_edge_data(node.asn, neighbor)
                        neighbor_asn = int(neighbor)

                        if neighbor_asn not in path:
                            if edge_data["relationship"] == -1 and edge_data["as1"] == node.asn:

                                # check if we have already visited that node
                                if originator not in paths[neighbor_asn]:
                                    paths[neighbor_asn][originator] = [path]

                                    item = Node(neighbor_asn, list(path))
                                    q2.append(item)

                                else:
                                    paths[neighbor_asn][originator].append(path)

        if i % div == 0 or i == len(originator_ases):
            if not testing:
                with open(output_path + 'paths-' + str(name) + '.log', 'a', 102400) as output:
                    for asn, data in paths.iteritems():
                        if asn in ixp_participants or not ixp_participants:
                            for origin, path in data.iteritems():
                                output.write(str(asn) + "|" + str(origin) + "|" +
                                             ";".join([str(",".join(str(w) for w in reversed(v))) for v in path]) +
                                             "\n")
                paths = defaultdict(dict)
    if testing:
        return paths


def test():
    print "Tests:"

    # test cases
    tests = [
        {
            'name': "General Topology Test",
            'topo': [
                {'as1': 1, 'as2': 2, 'relationship': -1},
                {'as1': 1, 'as2': 3, 'relationship': -1},
                {'as1': 2, 'as2': 3, 'relationship': 0},
                {'as1': 2, 'as2': 4, 'relationship': -1},
                {'as1': 2, 'as2': 5, 'relationship': -1},
                {'as1': 3, 'as2': 5, 'relationship': -1},
                {'as1': 3, 'as2': 6, 'relationship': -1},
                {'as1': 4, 'as2': 5, 'relationship': 0},
                {'as1': 4, 'as2': 7, 'relationship': -1},
                {'as1': 5, 'as2': 8, 'relationship': -1},
                {'as1': 5, 'as2': 9, 'relationship': -1},
                {'as1': 6, 'as2': 10, 'relationship': -1},
            ],
            'originators': [7, 10, 3],
            'paths': {
                1: {3: [[3]], 7: [[7, 4, 2]], 10: [[10, 6, 3]]},
                2: {3: [[3], [3, 1]], 7: [[7, 4]], 10: [[10, 6, 3], [10, 6, 3, 1]]},
                3: {3: [], 7: [[7, 4, 2], [7, 4, 2, 1]], 10: [[10, 6]]},
                4: {3: [[3, 2]], 7: [[7]], 10: [[10, 6, 3, 2]]},
                5: {3: [[3], [3, 2]], 7: [[7, 4], [7, 4, 2], [7, 4, 2, 3]], 10: [[10, 6, 3], [10, 6, 3, 2]]},
                6: {3: [[3]], 7: [[7, 4, 2, 3]], 10: [[10]]},
                7: {3: [[3, 2, 4]], 7: [], 10: [[10, 6, 3, 2, 4]]},
                8: {3: [[3, 5]], 7: [[7, 4, 5]], 10: [[10, 6, 3, 5]]},
                9: {3: [[3, 5]], 7: [[7, 4, 5]], 10: [[10, 6, 3, 5]]},
                10: {3: [[3, 6]], 7: [[7, 4, 2, 3, 6]], 10: []}
            }
        },
        {
            'name': "Valley Free Test",
            'topo': [
                {'as1': 1, 'as2': 2, 'relationship': 0},
                {'as1': 1, 'as2': 4, 'relationship': -1},
                {'as1': 1, 'as2': 5, 'relationship': -1},
                {'as1': 2, 'as2': 3, 'relationship': 0},
                {'as1': 2, 'as2': 5, 'relationship': -1},
                {'as1': 2, 'as2': 6, 'relationship': -1},
                {'as1': 3, 'as2': 7, 'relationship': -1},
            ],
            'originators': [4, 6, 7],
            'paths': {
                1: {4: [[4]], 6: [[6, 2]]},
                2: {4: [[4, 1]], 6: [[6]], 7: [[7, 3]]},
                3: {6: [[6, 2]], 7: [[7]]},
                4: {4: [], 6: [[6, 2, 1]]},
                5: {4: [[4, 1], [4, 1, 2]], 6: [[6, 2], [6, 2, 1]], 7: [[7, 3, 2]]},
                6: {4: [[4, 1, 2]], 6: [], 7: [[7, 3, 2]]},
                7: {6: [[6, 2, 3]], 7: []}
            }
        },
        {
            'name': "Customer Route Preference",
            'topo': [
                {'as1': 1, 'as2': 8, 'relationship': -1},
                {'as1': 1, 'as2': 9, 'relationship': -1},
                {'as1': 1, 'as2': 10, 'relationship': -1},
                {'as1': 2, 'as2': 1, 'relationship': -1},
                {'as1': 3, 'as2': 2, 'relationship': -1},
                {'as1': 4, 'as2': 3, 'relationship': -1},
                {'as1': 5, 'as2': 4, 'relationship': -1},
                {'as1': 6, 'as2': 5, 'relationship': -1},
                {'as1': 6, 'as2': 10, 'relationship': -1},
                {'as1': 6, 'as2': 9, 'relationship': 0},
                {'as1': 7, 'as2': 1, 'relationship': -1},
                {'as1': 7, 'as2': 6, 'relationship': 0},
                {'as1': 8, 'as2': 6, 'relationship': -1},
            ],
            'originators': [1],
            'paths': {
                1: {1: []},
                2: {1: [[1]]},
                3: {1: [[1, 2]]},
                4: {1: [[1, 2, 3]]},
                5: {1: [[1, 2, 3, 4]]},
                6: {1: [[1, 2, 3, 4, 5], [1, 7]]},
                7: {1: [[1], [1, 2, 3, 4, 5, 6]]},
                8: {1: [[1, 2, 3, 4, 5, 6], [1]]},
                9: {1: [[1, 2, 3, 4, 5, 6], [1]]},
                10: {1: [[1], [1, 2, 3, 4, 5, 6]]}
            }
        },
        {
            'name': "Dragon Paper Test",
            'topo': [
                {'as1': 1, 'as2': 2, 'relationship': 0},
                {'as1': 1, 'as2': 5, 'relationship': -1},
                {'as1': 2, 'as2': 3, 'relationship': -1},
                {'as1': 2, 'as2': 4, 'relationship': -1},
                {'as1': 3, 'as2': 5, 'relationship': -1},
                {'as1': 3, 'as2': 6, 'relationship': -1},
                {'as1': 4, 'as2': 6, 'relationship': -1}
            ],
            'originators': [6, 4],
            'paths': {
                1: {4: [[4, 2]], 6: [[6, 3, 2]]},
                2: {4: [[4]], 6: [[6, 3], [6, 4]]},
                3: {4: [[4, 2]], 6: [[6]]},
                4: {4: [], 6: [[6], [6, 3, 2]]},
                5: {4: [[4, 2, 1], [4, 2, 3]], 6: [[6, 3], [6, 3, 2, 1]]},
                6: {4: [[4], [4, 2, 3]], 6: []}
            }
        }
    ]

    for test_case in tests:
        print "Running " + str(test_case['name'])
    
        topo = nx.Graph()
        for edge in test_case['topo']:
            topo.add_edge(edge['as1'], edge['as2'],
                          relationship=edge['relationship'], as1=edge['as1'], as2=edge['as2'])
     
        print "--> Built Topology with " + str(topo.number_of_nodes()) + " nodes and "\
              + str(topo.number_of_edges()) + " edges"

        result = build_paths(0, topo, test_case['originators'], "../", True)

        error = False

        for node, paths in test_case['paths'].iteritems():
            for origin, path in paths.iteritems():
                if path:
                    if result[node][origin] != path:
                        print "Error: Path to " + str(origin) + " of node " + str(node) + " is "\
                              + str(result[node][origin]) + " should be " + str(path)
                        error = True
        if error:
            print "-> Test failed\n"
        else:
            print "-> Test passed\n"


def main(argv):
    # run test cases
    if argv.test:
        test()

    # start routing tree algorithm using MPI
    else:
        comm = MPI.COMM_WORLD
        size = comm.Get_size()
        rank = comm.Get_rank()

        as_topo = nx.read_gpickle(argv.path + "as_graph.gpickle")

        nodes = list()
        if argv.destination == "-1":
            nodes = as_topo.nodes()
        else:
            with open(argv.outpath + argv.destination) as infile:
                nodes = json.loads(infile.read())
        nodes.sort()

        chunk_size = math.ceil(len(nodes)/size)
        start = int(rank*chunk_size)
        stop = int((rank+1)*chunk_size)
        chunk = nodes[start:stop]

        exceptions = list()
        if argv.exceptions != "-1":
            with open(argv.path + argv.exceptions) as infile:
                exceptions = json.loads(infile.read())

        ixp_participants = list()
        if argv.ixpparticipants != "-1":
            with open(argv.ixpparticipants) as infile:
                data = infile.read()
                ixp_dataset = json.loads(data)
                tmp_ixp_participants = ixp_dataset['asn_2_ixp'].keys()

            ixp_participants = [int(x) for x in tmp_ixp_participants]

        print "Start process " + str(rank) + " of " + str(size) + " working on origins from " + str(start) + " to " + str(stop)
        build_paths(rank, as_topo, chunk, exceptions, ixp_participants, argv.outpath, False)

''' main '''
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('path', help='path to graph file')
    parser.add_argument('outpath', help='path to output')
    parser.add_argument('destination', help='file of destinations')
    parser.add_argument('exceptions', help='file of GR exceptions')
    parser.add_argument('ixpparticipants', help='file of ixp participants')
    parser.add_argument('-t', '--test', help='test the config parser', action="store_true")

    args = parser.parse_args()

    main(args)
