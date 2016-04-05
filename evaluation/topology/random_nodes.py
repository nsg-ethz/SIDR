#!/usr/bin/env python
#  Author:
#  Rudiger Birkner(ETH Zurich)

import networkx as nx
import random
import json
import argparse

def main(argv):
    nodes = list()

    as_topo = nx.read_gpickle(argv.input)
    nodes = as_topo.nodes()

    n = [100, 500, 1000, 2500, 5000, 10000]

    for x in n:
        random.shuffle(nodes)
        random_selection = nodes[0:x]
        with open(str(argv.output) + 'rnd_destinations_' + str(x) + '.json', 'w') as outfile:
            json.dump(random_selection, outfile)

''' main '''
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('input', help='graph file')
    parser.add_argument('output', help='path to output directory')

    args = parser.parse_args()

    main(args)
