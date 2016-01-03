#!/usr/bin/env python
#  Author:
#  Rudiger Birkner (ETH Zurich)

import argparse
import json

import cPickle as pickle

from collections import defaultdict


def main(argv):
    ixps_2_participants = dict()
    participants_2_ixps = dict()

    with open(argv.ixps) as infile:
        data = json.loads(infile.read())
        for k, v in data['ixp_2_asn'].iteritems():
            ixps_2_participants[int(k)] = [int(y) for y in v]

        for k, v in data['asn_2_ixp'].iteritems():
            participants_2_ixps[int(k)] = [int(y) for y in v]

    sdx_structure = dict()
    sdx_participants = dict()

    with open(argv.paths) as infile:
        i = 0
        for line in infile:
            i += 1
            x = line.split("\n")[0].split("|")
            in_participant = int(x[0])
            if in_participant in participants_2_ixps:
                in_ixps = set(participants_2_ixps[in_participant])
                if in_participant not in sdx_participants:
                    sdx_participants[in_participant] = {"all": dict(), "best": dict()}
                destination = int(x[1])
                tmp_paths = x[2].split(";")
                paths = [p.split(",") for p in tmp_paths]

                for path in paths:
                    for i in range(0, len(path)):
                        path[i] = int(path[i])
                    out_participant = path[0]
                    if out_participant in participants_2_ixps:
                        out_ixps = set(participants_2_ixps[out_participant])
                        if len(in_ixps.intersection(out_ixps)) > 0:
                            if out_participant not in sdx_participants[in_participant]["all"]:
                                sdx_participants[in_participant]["all"][out_participant] = dict()
                            sdx_participants[in_participant]["all"][out_participant][destination] = path
                sdx_participants[in_participant]["best"][destination] = paths[0]

    for participant in sdx_participants.keys():
        sdx_participants[participant]["ixps"] = participants_2_ixps[participant]

    for sdx_id, participants in ixps_2_participants.iteritems():
        if sdx_id not in sdx_structure:
            sdx_structure[sdx_id] = dict()
        filter = set(participants)
        for participant in participants:
            if participant not in sdx_structure[sdx_id]:
                sdx_structure[sdx_id][participant] = dict()
            out_participants = set(sdx_participants[participant]["all"].keys())
            sdx_structure[sdx_id][participant]["out_participants"] = out_participants.intersection(filter)
            sdx_structure[sdx_id][participant]["policies"] = defaultdict(list)

    # write to a file
    data = (sdx_structure, sdx_participants)

    with open(argv.output, 'w') as output:
        data_string = pickle.dump(data, output)


''' main '''
if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('paths', help='path to paths file')
    parser.add_argument('ixps', help='path to ixp file')
    parser.add_argument('output', help='path of output file')

    args = parser.parse_args()

    main(args)
