#!/usr/bin/env python
#  Author:
#  Rudiger Birkner (ETH Zurich)

import logging
import pickle
import json

from collections import namedtuple

from header_bitstring import HeaderBitString

# SDX Structure
# sdx_id - int
#   participant_id - int
#     out_participants - list of ints
#     policies
#       out_participant
#         list of policies

# Participant Structure
# participant_id - int
#   all
#     out_participant_id
#       destination
#         path
#   best
#     destination
#       path
#   ixps
#     ixp_ids - list of ints


class Evaluator(object):
    def __init__(self, mode, sdx_structure_file, policy_file, debug=False):
        self.logger = logging.getLogger("Evaluator")
        if debug:
            self.logger.setLevel(logging.DEBUG)

        self.policy_file = policy_file
        self.sdx_structure_file = sdx_structure_file

        if 0 <= mode < 4:
            self.mode = mode
        else:
            self.logger.error("invalid mode specified")

        self.sdx_structure, self.sdx_participants = pickle.load(sdx_structure_file)

        self.dfs_node = namedtuple("DFS Node", "sdx_id in_participant destination match")


    def run_evaluation(self):
        total_policies = 0
        installed_policies = 0

        with open(self.policy_file, 'r') as policies:
            for policy in policies:
                x = policy.split("\n")[0].split("|")
                sdx_id = x[0]
                from_participant = x[1]
                to_participant = x[2]
                tmp_match = json.loads(x[3])
                match = HeaderBitString(match=tmp_match)

                if self.mode == 0:
                    tmp_total, tmp_installed = self.install_policy_no_bgp(sdx_id,
                                                                          from_participant,
                                                                          to_participant,
                                                                          match)
                elif self.mode == 1:
                    tmp_total, tmp_installed = self.install_policy_our_scheme(sdx_id,
                                                                              from_participant,
                                                                              to_participant,
                                                                              match)
                else:
                    tmp_total, tmp_installed = self.install_policy_full_knowledge(sdx_id,
                                                                                  from_participant,
                                                                                  to_participant,
                                                                                  match)
                total_policies += tmp_total
                installed_policies += tmp_installed

        print "Tried to install a total of " + total_policies + ", managed to safely install " + installed_policies

    def install_policy_no_bgp(self, sdx_id, from_participant, to_participant, match):
        # get all paths that to_participant advertised to from_participant
        paths = self.sdx_participants[from_participant]["all"][to_participant]

        i = 0
        j = 0

        # for each path check if there is an sdx on the as path, the policy can be installed if there is none
        for destination, path in paths.iteritems():
            i += 1
            sdxes = self.get_sdxes_on_path(path)
            if len(sdxes) == 0:
                j += 1
                self.sdx_structure[sdx_id][from_participant]["policies"][to_participant] = match
        return i, j

    def install_policy_our_scheme(self, sdx_id, from_participant, to_participant, match):
        j = 0

        # check for each destination/prefix whether the policy is safe
        destinations = self.sdx_participants[from_participant]["all"][to_participant]
        for destination, path in destinations.iteritems():
            # init queue
            # TODO what to do when we have a set of sdxes and sdx_id is in it as well
            dfs_queue = list()
            sdxes, in_participant = self.get_first_sdxes_on_path(destination[1])
            if sdxes:
                if sdx_id in sdxes:
                    continue
                for sdx in sdxes:
                    dfs_queue.append(self.dfs_node(sdx, in_participant, destination, None))

            if self.traversal_our_scheme(sdx_id, destination, dfs_queue):
                j += 1
                self.sdx_structure[sdx_id][from_participant]["policies"][to_participant] = match
        return len(destinations), j

    def traversal_our_scheme(self, sdx_id, destination, dfs_queue):
        # start traversal
        while dfs_queue:
            n = dfs_queue.pop()

            # get all outgoing paths
            out_participants = self.sdx_structure[n.sdx_id]["policies"].keys()
            best_path = self.sdx_participants["best"][n.destination]

            # check if best path goes through that SDX and if so add it
            if best_path[0] in self.sdx_structure[n.sdx_id]["out_participants"]:
                sdxes, in_participant = self.get_first_sdxes_on_path(destination[1])
                if sdxes:
                    if sdx_id in sdxes:
                        return False
                    for sdx in sdxes:
                        dfs_queue.append(self.dfs_node(sdx, in_participant, destination, None))

            # add all policy activated paths
            for participant in out_participants:
                # only add it, if it is not the best path
                if participant != best_path[0]:
                    if destination in self.sdx_participants[n.in_participant]["all"][participant]:
                        path = self.sdx_participants[n.in_participant]["all"][participant][destination]
                        sdxes, in_participant = self.get_first_sdxes_on_path(path)
                        if sdxes:
                            if sdx_id in sdxes:
                                return False
                            for sdx in sdxes:
                                dfs_queue.append(self.dfs_node(sdx, in_participant, destination, None))
        return True

    def install_policy_full_knowledge(self, sdx_id, from_participant, to_participant, match):
        j = 0

        # check for each destination/prefix whether the policy is safe
        destinations = self.sdx_participants[from_participant]["all"][to_participant]
        for destination, path in destinations.iteritems():
            # init queue
            # TODO what to do when we have a set of sdxes and sdx_id is in it as well
            dfs_queue = list()
            sdxes, in_participant = self.get_first_sdxes_on_path(destination[1])
            if sdxes:
                if sdx_id in sdxes:
                    continue
                for sdx in sdxes:
                    dfs_queue.append(self.dfs_node(sdx, in_participant, destination, match))

            if self.traversal_full_knowledge(sdx_id, destination, dfs_queue):
                j += 1
                self.sdx_structure[sdx_id][from_participant]["policies"][to_participant] = match
        return len(destinations), j

    def traversal_full_knowledge(self, sdx_id, destination, dfs_queue):
        # start traversal
        while dfs_queue:
            n = dfs_queue.pop()

            # get all outgoing paths
            out_participants = self.sdx_structure[n.sdx_id]["policies"].keys()
            best_path = self.sdx_participants["best"][n.destination]

            # check if best path goes through that SDX and if so add it
            if best_path[0] in self.sdx_structure[n.sdx_id]["out_participants"]:
                sdxes, in_participant = self.get_first_sdxes_on_path(destination[1])
                if sdxes:
                    if sdx_id in sdxes:
                        return False
                    for sdx in sdxes:
                        dfs_queue.append(self.dfs_node(sdx, in_participant, destination, n.match))

            # add all policy activated paths
            for participant in out_participants:
                if destination in self.sdx_participants[n.in_participant]["all"][participant]:
                    for match in self.sdx_structure[n.in_participant]["policies"][participant]:
                        # check if policies overlap
                        new_match = HeaderBitString.combine(n.match, match)
                        if new_match:
                            path = self.sdx_participants[n.in_participant]["all"][participant][destination]
                            sdxes, in_participant = self.get_first_sdxes_on_path(path)
                            if sdxes:
                                if sdx_id in sdxes:
                                    return False
                                for sdx in sdxes:
                                    dfs_queue.append(self.dfs_node(sdx, in_participant, destination, new_match))
        return True

    def get_first_sdxes_on_path(self, as_path):
        sdxes = set()

        as2 = -1
        for as1 in as_path:
            if as2 != -1:
                as1_sdxes = set(self.sdx_participants[as1]["ixps"])
                as2_sdxes = set(self.sdx_participants[as2]["ixps"])

                sdxes = as1_sdxes.union(as2_sdxes)
                if len(sdxes) > 0:
                    break
            as2 = as1
        return sdxes, as1

    def get_sdxes_on_path(self, as_path):
        sdxes = set()

        as2 = -1
        for as1 in as_path:
            if as2 != -1:
                as1_sdxes = set(self.sdx_participants[as1]["ixps"])
                as2_sdxes = set(self.sdx_participants[as2]["ixps"])

                union = as1_sdxes.union(as2_sdxes)
                if len(union) > 0:
                    sdxes = sdxes.union(union)
            as2 = as1
        return sdxes


def main(argv):
    # logging - log level
    logging.basicConfig(level=logging.INFO)