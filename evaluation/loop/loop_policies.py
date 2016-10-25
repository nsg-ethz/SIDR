#!/usr/bin/env python
#  Author:
#  Rudiger Birkner (ETH Zurich)

import json
import argparse
import random
import sys
import os

from collections import defaultdict

sys.path.insert(1, os.path.join(sys.path[0], '..'))

from header_bitstring import HeaderBitString


class PolicyGenerator(object):
    def __init__(self, ports_file, iterations, max_loop_size, output):

        # parse ports file
        self.ports = {}
        with open(ports_file) as infile:
            for line in infile:
                self.ports = json.loads(line)

        self.port_counts = defaultdict(dict)
        self.port_counts["udp"]["src"] = sum(self.ports["UDP"]["src"].itervalues())
        self.port_counts["udp"]["dst"] = sum(self.ports["UDP"]["dst"].itervalues())
        self.port_counts["udp"]["total"] = sum(self.port_counts["udp"].itervalues())

        self.port_counts["tcp"]["src"] = sum(self.ports["TCP"]["src"].itervalues())
        self.port_counts["tcp"]["dst"] = sum(self.ports["TCP"]["dst"].itervalues())
        self.port_counts["tcp"]["total"] = sum(self.port_counts["tcp"].itervalues())

        self.max_loop_size = max_loop_size
        self.iterations = iterations

        modes = [0,1,2]

        for mode in modes:
            total, no_loops = self.generate_policies(mode)

            with open(output, "a") as outfile:
                outfile.write(str(mode) + '|' + str(total) + '|' + str(no_loops) + '\n')

    def generate_policies(self, mode):
        num_no_loop = 0

        for j in range(0, self.iterations):
            loop_size = random.choice(range(2, self.max_loop_size + 1))

            header_bitstring = None

            for i in range(0, loop_size):
                match = self.get_match(mode)

                tmp_hb = HeaderBitString(match=match)

                if header_bitstring:
                    header_bitstring = HeaderBitString.combine(header_bitstring, tmp_hb)
                else:
                    header_bitstring = tmp_hb

                if not header_bitstring:
                    num_no_loop += 1
                    break

        return self.iterations, num_no_loop

    def get_match(self, mode):
        # all policies have exactly the same match
        if mode == 0:
            return {"ip_proto": 6, "eth_type": 2048, "tcp_dst": 80}
        # match field is drawn according to distribution in specified file
        elif mode == 1:
            return self.get_weighted_match()
        elif mode == 2:
            return self.get_random_match()

    @staticmethod
    def get_random_match():
        port = random.randint(1,65537)
        rnd = random.randint(0,4)
        if rnd == 0:
            return {"tcp_dst": port, 'eth_type': 0x0800, 'ip_proto': 6}
        if rnd == 1:
            return {"tcp_src": port, 'eth_type': 0x0800, 'ip_proto': 6}
        if rnd == 2:
            return {"udp_dst": port, 'eth_type': 0x0800, 'ip_proto': 17}
        else:
            return {"udp_src": port, 'eth_type': 0x0800, 'ip_proto': 17}

    def get_weighted_match(self):
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

    def transform_match_to_int(self, match):
        """
        This method creates a bitstring from a high-level match dictionary.
        :param match: high-level match dictionary (e.g. {'tcp_dst': 179})
        :return: corresponding bit string
        """

        if ('tcp_src' in match or 'tcp_dst' in match) and ('udp_src' in match or 'udp_dst' in match):
            return None

        ip_proto = '{0:016b}'.format(2**16-1)
        proto_src = '{0:032b}'.format(2**32-1)
        proto_dst = '{0:032b}'.format(2**32-1)

        if 'tcp_src' in match or 'tcp_dst' in match:
            ip_proto = self.transform_bitstring('{0:08b}'.format(6))
            if 'tcp_src' in match:
                proto_src = self.transform_bitstring('{0:016b}'.format(match['tcp_src']))
            if 'tcp_dst' in match:
                proto_dst = self.transform_bitstring('{0:016b}'.format(match['tcp_dst']))
        if 'udp_src' in match or 'udp_dst' in match:
            ip_proto = self.transform_bitstring('{0:08b}'.format(17))
            if 'udp_src' in match:
                proto_src = self.transform_bitstring('{0:016b}'.format(match['udp_src']))
            if 'udp_dst' in match:
                proto_dst = self.transform_bitstring('{0:016b}'.format(match['udp_dst']))

        # combine all fields
        return int(''.join([ip_proto, proto_src, proto_dst]), 2)

    @staticmethod
    def transform_bitstring(bitstring):
        """
        Transforms an ordinary bitstring to a bitstring, where each 0 is replaced by 01, and each 1 by 10
        :param bitstring: bitstring of any length to be converted
        :return: converted string
        """

        result = ''

        for bit in bitstring:
            if bit == '0':
                result += '01'
            else:
                result += '10'

        return result


def main(argv):
    PolicyGenerator(argv.ports, int(argv.iterations), int(argv.max_loop_size), argv.output)


''' main '''
if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('ports', help='path to ports file')
    parser.add_argument('iterations', help='fraction of outgoing policies')
    parser.add_argument('max_loop_size', help='maximum loop size')
    parser.add_argument('output', help='path of output file')

    args = parser.parse_args()

    main(args)
