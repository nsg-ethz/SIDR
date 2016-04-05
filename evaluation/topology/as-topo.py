#!/usr/bin/env python
#  Author:
#  Rudiger Birkner(ETH Zurich)

import argparse
import json
import time

import networkx as nx

from collections import defaultdict

from topo_builder import ASTopo


class Config(object):
    def __init__(self, config_file, test=False):
        # settings
        # backedges already removed?
        self.backedges_removed = True
        # topology file
        self.topology_file = ""
        # topology format 0 = CAIDA, 1 = UCLA
        self.topology_format = 0
        # tier 1 connection threshold - all ASes with more than the specified number of connections
        # are considered tier1s
        self.tier1_threshold = 50

        # ixp_file -
        self.ixp_file = ""
        self.ixp_mode = 0
        self.c2p_factor = 5
        # ixps_2_participants = {ixp_id: [participant_ids]}
        self.ixps_2_participants = {}
        self.participants_2_ixps = {}

        self.parse_settings_file(config_file)

        if test:
            self.test()

        self.parse_ixp_file()

    def parse_settings_file(self, config_file):
        with open(config_file) as infile:
            for line in infile:
                if line.startswith("#"):
                    continue
                else:
                    x = line.split("\n")[0].split(":")
                    if x[0] == "Topology File":
                        self.topology_file = x[1]
                    elif x[0] == "Topology Format":
                        self.topology_format = int(x[1])
                    elif x[0] == "Topology Backedges Removed":
                        self.backedges_removed = True if x[1] == 'True' else False
                    elif x[0] == "Tier 1 Connection Threshold":
                        self.tier1_threshold = int(x[1])
                    elif x[0] == "IXP File":
                        self.ixp_file = x[1]
                    elif x[0] == "IXP Mode":
                        self.ixp_mode = int(x[1])
                    elif x[0] == "C2P Factor":
                        self.c2p_factor = float(x[1])
                    elif x[0] == "Output Path":
                        self.output_path = x[1]

    def parse_ixp_file(self):
        with open(self.ixp_file) as infile:
            for line in infile:
                data = json.loads(line)

                self.ixps_2_participants = data['ixp_2_asn']
                self.participants_2_ixps = data['asn_2_ixp']

        print "# Loaded IXP Data with " + str(len(self.ixps_2_participants)) + " IXPs, " \
              + str(len(self.participants_2_ixps)) + " ASNs"

    def test(self):
        print "# Topology File: " + str(self.topology_file)
        print "# Topology Format: " + str(self.topology_format)
        print "# Topology Backedges Removed: " + str(self.backedges_removed)
        print "# IXP File: " + str(self.ixp_file)
        print "# Output Path: " + str(self.output_path)


def main(argv):

    start = time.clock()

    print "-> Parse Config"
    config = Config(argv.config, argv.test)

    print "-> Build Topology"
    tmp_start = time.clock()
    as_topo = ASTopo(config.topology_file, config.topology_format, config.backedges_removed,
                     config.tier1_threshold, config.participants_2_ixps, config.c2p_factor,
                     config.ixp_mode, argv.debug)
    print "--> Execution Time: " + str(time.clock() - tmp_start) + "s\n"

    nx.write_gpickle(as_topo, config.output_path + "as_graph.gpickle")

    print "-> Total Execution Time: " + str(time.clock() - start) + "s\n"


''' main '''
if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('config', help='path to config file')
    parser.add_argument('-d', '--debug', help='enable debug output', action="store_true")
    parser.add_argument('-t', '--test', help='test the config parser', action="store_true")
   
    args = parser.parse_args()

    main(args)
