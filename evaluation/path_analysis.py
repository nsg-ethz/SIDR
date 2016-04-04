#!/usr/bin/env python
#  Author:
#  Rudiger Birkner (ETH Zurich)

import argparse
import json
import time
import itertools
import networkx as nx


from collections import defaultdict


def main(argv):

    print "Read Graph File"
    start = time.clock()
    as_topo = nx.read_gpickle(argv.graph)
    print "--> Execution Time: " + str(time.clock() - start) + "s\n"

    print "Read IXP File"
    tmp_start = time.clock()
    ixps_2_participants = defaultdict(list)
    participants_2_ixps = defaultdict(list)

    with open(argv.ixps) as infile:
        data = json.loads(infile.read())
        for k, v in data['ixp_2_asn'].iteritems():
            if isinstance(k, int) or k.isdigit():
                for y in v:
                    if isinstance(y, int) or y.isdigit():
                        ixps_2_participants[int(k)].append(int(y))

        for k, v in data['asn_2_ixp'].iteritems():
            if isinstance(k, int) or k.isdigit():
                for y in v:
                    if isinstance(y, int) or y.isdigit():
                        participants_2_ixps[int(k)].append(int(y))

    print "--> Execution Time: " + str(time.clock() - tmp_start) + "s\n"

    print "Analyze Paths"
    tmp_start = time.clock()

    with open(argv.paths) as infile:
        for line in infile:
            # read data from file: FROM|TO|PATH1;PATH2;PATH3;... where PATH = 1,2,3,4,...,TO
            x = line.split("\n")[0].split("|")
            in_participant = int(x[0])
            destination = int(x[1])

            # catch the case when there is no path to the destination or FROM == TO
            if x[2] == "":
                continue

            # prepare paths for further processing
            path_strings = x[2].split(";")
            paths = [p.split(",") for p in path_strings]



            with open(argv.output + 'pa_num.log', 'a', 102400) as output:
                output.write(str(in_participant) + "|" + str(destination) + "|" +
                             str(len(paths)) + "\n")

            j = 0
            for path in paths:

                # convert string paths to ints
                for i in range(0, len(path)):
                    path[i] = int(path[i])
                path.insert(0, in_participant)

                sdxes, link_types, shortcuts = analyze_path(participants_2_ixps, path, as_topo)

                if shortcuts:
                    path_string = ""
                    for i in range(0, len(path)):
                        if i == len(path) - 1:
                            path_string += str(path[i])
                        else:
                            sdx_string = ",".join([str(x) for x in list(sdxes[i][1])])
                            path_string += str(path[i]) + "-" + sdx_string + "/" + str(link_types[i]) + "-"

                    path_type = "A"
                    if j == 0:
                        path_type = "B"

                    shortcut_string = ";".join(shortcuts)

                    with open(argv.output + 'pa_shortcuts.log', 'a', 102400) as output:
                        output.write(str(in_participant) + "|" + str(destination) + "|" + path_type + "|" +
                                     path_string + "|" + shortcut_string + "\n")
                j += 1

    print "--> Execution Time: " + str(time.clock() - tmp_start) + "s\n"
    print "-> Total Execution Time: " + str(time.clock() - start) + "s\n"


def analyze_path(participants_2_ixps, as_path, topo):
    sdxes = list()
    link_types = list()

    for i in range(0, len(as_path) - 1):
        as1 = as_path[i]
        as2 = as_path[i + 1]

        # get the link type
        edge_data = topo.get_edge_data(as1, as2)

        if edge_data["relationship"] == -1 and edge_data["as2"] == as1:
            link_types.append(-1)
        elif edge_data["relationship"] == -1 and edge_data["as2"] == as2:
            link_types.append(1)
        elif edge_data["relationship"] == 0:
            link_types.append(0)
        else:
            link_types.append(9)

        # get all ixps on the path
        if as1 in participants_2_ixps:
            as1_sdxes = set(participants_2_ixps[as1])
        else:
            as1_sdxes = set()
        if as2 in participants_2_ixps:
            as2_sdxes = set(participants_2_ixps[as2])
        else:
            as2_sdxes = set()

        sdxes.append((i, as1_sdxes.intersection(as2_sdxes)))

    # check whether multiple links cross the same ixp and whether there would have been a shortcut.
    shortcuts = list()
    for pair in itertools.combinations(sdxes, 2):
        index1 = pair[0][0]
        sdxes1 = pair[0][1]
        index2 = pair[1][0]
        sdxes2 = pair[1][1]

        as1 = as_path[index1]
        as2 = as_path[index2 + 1]

        intersection = sdxes1.intersection(sdxes2)
        if len(intersection) > 0:
            if topo.has_edge(as1, as2):
                # get the link type
                edge_data = topo.get_edge_data(as1, as2)

                if edge_data["relationship"] == -1 and edge_data["as2"] == as1:
                    link_type = -1
                elif edge_data["relationship"] == -1 and edge_data["as2"] == as2:
                    link_type = 1
                elif edge_data["relationship"] == 0:
                    link_type = 0
                else:
                    link_type = 9

                sdx_string = ",".join([str(x) for x in list(intersection)])

                shortcuts.append(str(as1) + "-" + sdx_string + "/"
                                 + str(link_type) + "-" + str(as2))
    return sdxes, link_types, shortcuts


''' main '''
if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    # mode == 1 means that we always pick only a single IXP if there are multiple possible
    parser.add_argument('mode', help='mode of operation')
    parser.add_argument('paths', help='path to paths file')
    parser.add_argument('ixps', help='path to ixp file')
    parser.add_argument('graph', help='path of graph file')
    parser.add_argument('output', help='path of output file')

    args = parser.parse_args()

    main(args)
