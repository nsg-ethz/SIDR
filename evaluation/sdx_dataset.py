#!/usr/bin/env python
#  Author:
#  Rudiger Birkner (ETH Zurich)

import argparse
import json
import time

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

    print "--> Execution Time: " + str(time.clock() - start) + "s\n"
    print "Build sdx_participants"
    tmp_start = time.clock()

    sdx_structure = dict()
    sdx_participants = dict()

    with open(argv.paths) as infile:
        for line in infile:
            x = line.split("\n")[0].split("|")
            in_participant = int(x[0])
            if in_participant in participants_2_ixps:
                in_ixps = set(participants_2_ixps[in_participant])
                if in_participant not in sdx_participants:
                    sdx_participants[in_participant] = {"all": dict(), "best": dict()}
                destination = int(x[1])
                if x[2] == "":
                    continue
                tmp_paths = x[2].split(";")
                paths = [p.split(",") for p in tmp_paths]

                j = 0
                for path in paths:
                    for i in range(0, len(path)):
                        path[i] = int(path[i])
                    out_participant = path[0]
                    if out_participant in participants_2_ixps:
                        out_ixps = set(participants_2_ixps[out_participant])
                        if len(in_ixps.intersection(out_ixps)) > 0:
                            if out_participant not in sdx_participants[in_participant]["all"]:
                                sdx_participants[in_participant]["all"][out_participant] = dict()
                                sdx_participants[in_participant]["all"][out_participant]["other"] = 0

                            sdx_info = get_first_sdxes_on_path(participants_2_ixps, path)
                            if len(sdx_info[1]) == 0:
                                sdx_participants[in_participant]["all"][out_participant]["other"] += 1
                            else:
                                sdx_participants[in_participant]["all"][out_participant][destination] = sdx_info
                                if j == 0:
                                    sdx_participants[in_participant]["best"][destination] = (out_participant, sdx_info)
                    j += 1

    for participant in sdx_participants.keys():
        sdx_participants[participant]["ixps"] = participants_2_ixps[participant]

    print "--> Execution Time: " + str(time.clock() - tmp_start) + "s\n"
    print "Build sdx_structure"
    tmp_start = time.clock()

    for sdx_id, participants in ixps_2_participants.iteritems():
        if sdx_id not in sdx_structure:
            sdx_structure[sdx_id] = dict()
        filter = set(participants)
        for participant in participants:
            if participant not in sdx_participants:
                print "there are no paths to AS " + str(participant)
                continue
            if participant not in sdx_structure[sdx_id]:
                sdx_structure[sdx_id][participant] = dict()
            out_participants = set(sdx_participants[participant]["all"].keys())
            sdx_structure[sdx_id][participant]["out_participants"] = out_participants.intersection(filter)
            sdx_structure[sdx_id][participant]["policies"] = defaultdict(list)

    print "--> Execution Time: " + str(time.clock() - tmp_start) + "s\n"
    print "Write sdx_participants and sdx_structure to a file"
    tmp_start = time.clock()

    # write to a file
    data = (sdx_structure, sdx_participants)

    with open(argv.output, 'w') as output:
        data_string = pickle.dump(data, output)

    print "--> Execution Time: " + str(time.clock() - tmp_start) + "s\n"
    print "-> Total Execution Time: " + str(time.clock() - start) + "s\n"


def get_first_sdxes_on_path(participants_2_ixps, as_path):
    sdxes = set()

    as2 = -1
    for as1 in as_path:
        if as2 != -1:
            if as1 in participants_2_ixps:
                as1_sdxes = set(participants_2_ixps[as1])
            else:
                as1_sdxes = set()
            if as2 in participants_2_ixps:
                as2_sdxes = set(participants_2_ixps[as2])
            else:
                as2_sdxes = set()

            sdxes = as1_sdxes.intersection(as2_sdxes)
            if len(sdxes) > 0:
                break
        as2 = as1
    return as2, sdxes


''' main '''
if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('paths', help='path to paths file')
    parser.add_argument('ixps', help='path to ixp file')
    parser.add_argument('output', help='path of output file')

    args = parser.parse_args()

    main(args)
