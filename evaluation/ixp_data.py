#!/usr/bin/env python
#  Author:
#  Rudiger Birkner (ETH Zurich)

import argparse
import json
import time
import random

import cPickle as pickle

from collections import defaultdict


def main(argv):

    print "Read IXP File"
    start = time.clock()

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

    print "Num IXPS: " + str(len(ixps_2_participants)) + ", Num Participants: " + str(len(participants_2_ixps))


''' main '''
if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    # mode == 1 means that we always pick only a single IXP if there are multiple possible
    parser.add_argument('ixps', help='path to ixp file')

    args = parser.parse_args()

    main(args)
