#!/usr/bin/env python
#  Author:
#  Rudiger Birkner (ETH Zurich)

import random
import json
import argparse
import time

import cPickle as pickle

from random import shuffle
from collections import defaultdict


class PolicyGenerator(object):
    def __init__(self, sdx_structure, fraction, output_file, ports_file):
        self.sdx_structure = sdx_structure
        self.output_file = output_file
        self.ports_file = ports_file
        self.fraction = fraction

        print "Generate Policies"
        tmp_start = time.clock()

        # parse ports file
        self.ports = {}
        with open(self.ports_file) as infile:
            for line in infile:
                self.ports = json.loads(line)

        self.port_counts = defaultdict(dict)
        self.port_counts["udp"]["src"] = sum(self.ports["UDP"]["src"].itervalues())
        self.port_counts["udp"]["dst"] = sum(self.ports["UDP"]["dst"].itervalues())
        self.port_counts["udp"]["total"] = sum(self.port_counts["udp"].itervalues())

        self.port_counts["tcp"]["src"] = sum(self.ports["TCP"]["src"].itervalues())
        self.port_counts["tcp"]["dst"] = sum(self.ports["TCP"]["dst"].itervalues())
        self.port_counts["tcp"]["total"] = sum(self.port_counts["tcp"].itervalues())

        print "--> Execution Time: " + str(time.clock() - tmp_start) + "s\n"

        # generate_policies
        with open(output_file, 'w') as output:
            for sdx_id in sdx_structure:
                for in_participant, data in sdx_structure[sdx_id].iteritems():
                    fwds = list(data["out_participants"])
                    shuffle(fwds)

                    i = 0

                    for fwd in fwds:
                        # stop if we have a policy for half of the eyeballs
                        if i >= len(fwds)/self.fraction:
                            break

                        # install between 1 and 4 policies per participant and fwd
                        x = random.randrange(1, 5)
                        for _ in range(0, x):
                            op = self.get_match()
                            output.write(str(sdx_id) + "|" +
                                         str(in_participant) + "|" +
                                         str(fwd) + "|" +
                                         json.dumps(op) + "\n")
                        i += 1

    def get_match(self):
        # pick protocol
        proto_pick = random.uniform(0, self.port_counts["udp"]["total"] + self.port_counts["tcp"]["total"])
        if proto_pick <= self.port_counts["udp"]["total"]:
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
                return int(k)
        return int(k)


def main(argv):
    print "Read sdx_participants and sdx_structure from file"
    start = time.clock()

    with open(argv.sdx, 'r') as sdx_input:
        sdx_structure = pickle.load(sdx_input)[0]

    print "--> Execution Time: " + str(time.clock() - start) + "s\n"
    print "Generate Policies"
    tmp_start = time.clock()

    PolicyGenerator(sdx_structure, int(argv.fraction), argv.output, argv.ports)

    print "--> Execution Time: " + str(time.clock() - tmp_start) + "s\n"
    print "-> Total Execution Time: " + str(time.clock() - start) + "s\n"


''' main '''
if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('sdx', help='path to pickled sdx_structure file')
    parser.add_argument('ports', help='path to ports file')
    parser.add_argument('fraction', help='fraction of outgoing policies')
    parser.add_argument('output', help='path of output file')

    args = parser.parse_args()

    main(args)
