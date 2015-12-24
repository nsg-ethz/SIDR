#!/usr/bin/env python
#  Author:
#  Rudiger Birkner (ETH Zurich)

import random
import json
import argparse

import cPickle as pickle

from random import shuffle
from collections import defaultdict


class PolicyGenerator(object):
    def __init__(self, sdx_structure, fraction, output_file, ports_file):
        self.sdx_structure = sdx_structure
        self.output_file = output_file
        self.ports_file = ports_file
        self.fraction = fraction

        # parse ports file
        self.ports = {}
        with open(self.ports_file) as infile:
            for line in infile:
                self.ports = json.loads(line)

        self.port_counts = defaultdict(dict)
        self.port_counts["udp"]["src"] = sum(self.ports["UDP"]["src"].itervalues())
        self.port_counts["udp"]["src"] = sum(self.ports["UDP"]["dst"].itervalues())
        self.port_counts["udp"]["total"] = sum(self.port_counts["udp"].itervalues())

        self.port_counts["tcp"]["src"] = sum(self.ports["TCP"]["src"].itervalues())
        self.port_counts["tcp"]["dst"] = sum(self.ports["TCP"]["dst"].itervalues())
        self.port_counts["tcp"]["total"] = sum(self.port_counts["tcp"].itervalues())

        # generate_policies
        with open(output_file, 'w') as output:
            for sdx_id in sdx_structure:
                for in_participant, out_participants in sdx_structure[sdx_id]:
                    fwds = list(out_participants.keys())
                    shuffle(fwds)

                    i = 0

                    for fwd in fwds:
                        # stop if we have a policy for half of the eyeballs
                        if i >= len(fwds)/self.fraction:
                            break
                        op = self.get_match()
                        output.write(str(sdx_id) + "|" + str(in_participant) + "|" + str(fwd) + "|" + str(op) + "\n")

    def get_match(self):
        # pick protocol
        proto_pick = random.uniform(0, self.port_counts["udp"]["totals"] + self.port_counts["tcp"]["totals"])
        if proto_pick <= self.port_counts["udp"]["totals"]:
            proto = 'udp'
        else:
            proto = 'tcp'

        # pick src/dst port
        src_dst_pick = random.uniform(0, self.port_counts[proto]['src'] + self.port_counts[proto]['dst'])
        if src_dst_pick <= self.port_counts[proto]['src']:
            src_dst = 'src'
        else:
            src_dst = 'dst'

        port = self.weighted_pick(proto, src_dst)

        return {proto + "_" + src_dst: port, 'eth_type': 0x0800, 'ip_proto': 6 if proto == 'tcp' else 17}

    def weighted_pick(self, proto, src_dst):
        port_stats = {}

        if proto == 'udp':
            if src_dst == 'src':
                port_stats = self.ports['UDP']['src']
            else:
                port_stats = self.ports['UDP']['dst']
        if proto == 'tcp':
            if src_dst == 'src':
                port_stats = self.ports['TCP']['src']
            else:
                port_stats = self.ports['TCP']['dst']

        r = random.uniform(0, sum(port_stats.itervalues()))
        s = 0.0
        for k, w in port_stats.iteritems():
            s += w
            if r < s:
                return k
        return k

def main(argv):
    sdx_structure = pickle.load(argv.sdx)[0]

    PolicyGenerator(sdx_structure, argv.fraction, argv.output, argv.ports)


''' main '''
if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('sdx', help='path to pickled sdx_structure file')
    parser.add_argument('ports', help='path to ports file')
    parser.add_argument('fraction', help='fraction of outgoing policies')
    parser.add_argument('output', help='path of output file')

    args = parser.parse_args()

    main(args)