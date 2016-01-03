#!/usr/bin/env python
#  Author:
#  Rudiger Birkner (ETH Zurich)

import argparse
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

        self.mode = 0
        if 0 <= mode < 4:
            self.mode = mode
        else:
            self.logger.error("invalid mode specified")

        with open(sdx_structure_file, 'r') as sdx_input:
            self.sdx_structure, self.sdx_participants = pickle.load(sdx_input)

        self.dfs_node = namedtuple("DFSNode", "sdx_id in_participant destination match")

    def run_evaluation(self):
        total_policies = 0
        installed_policies = 0

        with open(self.policy_file, 'r') as policies:
            for policy in policies:
                x = policy.split("\n")[0].split("|")
                sdx_id = int(x[0])
                from_participant = int(x[1])
                to_participant = int(x[2])
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

        self.logger.info("Tried to install a total of " + str(total_policies) + ", managed to safely install " +
                         str(installed_policies))
        return total_policies, installed_policies

    def install_policy_no_bgp(self, sdx_id, from_participant, to_participant, match):
        """
        Checks whether a policy can safely be installed in case of local BGP knowledge only
        :param sdx_id: identifier of SDX at which policy is installed
        :param from_participant: AS Number of the participant that wants to install the policy
        :param to_participant: AS Number of the participant to which the policy forwards
        :param match: policy match
        :return: number of total policies and number of actually installed policies
        """

        # get all paths that to_participant advertised to from_participant
        paths = self.sdx_participants[from_participant]["all"][to_participant]

        i = 0
        j = 0

        # check for each destination/prefix separately whether the policy is safe
        for destination, path in paths.iteritems():
            i += 1

            # check if there is an sdx on the path to the destination. if there is none, the policy can be installed
            sdxes = self.get_sdxes_on_path(path)
            if len(sdxes) == 0:
                j += 1
                self.sdx_structure[sdx_id][from_participant]["policies"][to_participant] = match

                self.logger.debug("accepted " + str(match.get_match()) + " at SDX " + str(sdx_id) + " from " +
                                  str(from_participant) + " to " + str(to_participant) + " for " + str(destination))
            else:
                self.logger.debug("rejected " + str(match.get_match()) + " at SDX " + str(sdx_id) + " from " +
                                  str(from_participant) + " to " + str(to_participant) + " for " + str(destination))
        return i, j

    def install_policy_our_scheme(self, sdx_id, from_participant, to_participant, match):
        """
        Checks whether a policy can safely be installed in case of limited information exchange (forwarding sets)
        :param sdx_id: identifier of SDX at which policy is installed
        :param from_participant: AS Number of the participant that wants to install the policy
        :param to_participant: AS Number of the participant to which the policy forwards
        :param match: policy match
        :return: number of total policies and number of actually installed policies
        """

        j = 0

        # check for each destination/prefix separately whether the policy is safe
        destinations = self.sdx_participants[from_participant]["all"][to_participant]
        for destination, path in destinations.iteritems():
            # init queue - with all first SDXes on the path
            dfs_queue = list()
            sdxes, in_participant = self.get_first_sdxes_on_path(path)
            if sdxes:
                if sdx_id in sdxes:
                    # in case we see the sdx_id of the sdx that wants to install the policy, we skip the policy
                    self.logger.debug("rejected " + str(match.get_match()) + " at SDX " + str(sdx_id) + " from " +
                                      str(from_participant) + " to " + str(to_participant) + " for " + str(destination))
                    continue
                for sdx in sdxes:
                    dfs_queue.append(self.dfs_node(sdx, in_participant, destination, None))

            if self.traversal_our_scheme(sdx_id, destination, dfs_queue):
                j += 1
                self.sdx_structure[sdx_id][from_participant]["policies"][to_participant].append(match)

                self.logger.debug("accepted " + str(match.get_match()) + " at SDX " + str(sdx_id) + " from " +
                                  str(from_participant) + " to " + str(to_participant) + " for " + str(destination))
            else:
                self.logger.debug("rejected " + str(match.get_match()) + " at SDX " + str(sdx_id) + " from " +
                                  str(from_participant) + " to " + str(to_participant) + " for " + str(destination))
        return len(destinations), j

    def traversal_our_scheme(self, sdx_id, destination, dfs_queue):
        # start traversal of SDX graph
        while dfs_queue:
            n = dfs_queue.pop()

            # get all outgoing paths for the in_participant
            out_participants = self.sdx_structure[n.sdx_id][n.in_participant]["policies"].keys()

            # check if best path goes through that SDX and if so, consider it as well
            best_path = self.sdx_participants[n.in_participant]["best"][n.destination]
            if best_path[0] in self.sdx_structure[n.sdx_id][n.in_participant]["out_participants"]:
                sdxes, in_participant = self.get_first_sdxes_on_path(best_path)
                if sdxes:
                    # check if the intial sdx is on the path, if so, a loop is created
                    if sdx_id in sdxes:
                        return False
                    for sdx in sdxes:
                        dfs_queue.append(self.dfs_node(sdx, in_participant, destination, None))

            # check all policy activated paths
            for participant in out_participants:
                # only check it, if it is not the best path
                if participant != best_path[0]:
                    if destination in self.sdx_participants[n.in_participant]["all"][participant]:
                        path = self.sdx_participants[n.in_participant]["all"][participant][destination]
                        sdxes, in_participant = self.get_first_sdxes_on_path(path)
                        if sdxes:
                            # check if the intial sdx is on the path, if so, a loop is created
                            if sdx_id in sdxes:
                                return False
                            for sdx in sdxes:
                                dfs_queue.append(self.dfs_node(sdx, in_participant, destination, None))
        return True

    def install_policy_full_knowledge(self, sdx_id, from_participant, to_participant, match):
        """
        Checks whether a policy can safely be installed in case of full knowledge
        :param sdx_id: identifier of SDX at which policy is installed
        :param from_participant: AS Number of the participant that wants to install the policy
        :param to_participant: AS Number of the participant to which the policy forwards
        :param match: policy match
        :return: number of total policies and number of actually installed policies
        """
        j = 0

        # check for each destination/prefix whether the policy is safe
        destinations = self.sdx_participants[from_participant]["all"][to_participant]
        for destination, path in destinations.iteritems():
            # init queue
            dfs_queue = list()
            sdxes, in_participant = self.get_first_sdxes_on_path(path)
            if sdxes:
                if sdx_id in sdxes:
                    self.logger.debug("rejected " + str(match.get_match()) + " at SDX " + str(sdx_id) + " from " +
                                      str(from_participant) + " to " + str(to_participant) + " for " + str(destination))
                    continue
                for sdx in sdxes:
                    dfs_queue.append(self.dfs_node(sdx, in_participant, destination, match))

            if self.traversal_full_knowledge(sdx_id, destination, dfs_queue):
                j += 1
                self.sdx_structure[sdx_id][from_participant]["policies"][to_participant].append(match)

                self.logger.debug("accepted " + str(match.get_match()) + " at SDX " + str(sdx_id) + " from " +
                                  str(from_participant) + " to " + str(to_participant) + " for " + str(destination))
            else:
                self.logger.debug("rejected " + str(match.get_match()) + " at SDX " + str(sdx_id) + " from " +
                                  str(from_participant) + " to " + str(to_participant) + " for " + str(destination))

        return len(destinations), j

    def traversal_full_knowledge(self, sdx_id, destination, dfs_queue):
        # start traversal
        while dfs_queue:
            n = dfs_queue.pop()

            # get all outgoing paths
            out_participants = self.sdx_structure[n.sdx_id][n.in_participant]["policies"].keys()
            best_path = self.sdx_participants[n.in_participant]["best"][n.destination]

            # check if best path goes through that SDX and if so add it
            if best_path[0] in self.sdx_structure[n.sdx_id][n.in_participant]["out_participants"]:
                sdxes, in_participant = self.get_first_sdxes_on_path(best_path)
                if sdxes:
                    if sdx_id in sdxes:
                        return False
                    for sdx in sdxes:
                        dfs_queue.append(self.dfs_node(sdx, in_participant, destination, n.match))

            # add all policy activated paths
            for participant in out_participants:
                if destination in self.sdx_participants[n.in_participant]["all"][participant]:
                    for match in self.sdx_structure[n.sdx_id][n.in_participant]["policies"][participant]:
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
                if as1 in self.sdx_participants:
                    as1_sdxes = set(self.sdx_participants[as1]["ixps"])
                else:
                    as1_sdxes = set()
                if as2 in self.sdx_participants:
                    as2_sdxes = set(self.sdx_participants[as2]["ixps"])
                else:
                    as2_sdxes = set()

                sdxes = as1_sdxes.intersection(as2_sdxes)
                if len(sdxes) > 0:
                    break
            as2 = as1
        return sdxes, as2

    def get_sdxes_on_path(self, as_path):
        sdxes = set()

        as2 = -1
        for as1 in as_path:
            if as2 != -1:
                if as1 in self.sdx_participants:
                    as1_sdxes = set(self.sdx_participants[as1]["ixps"])
                else:
                    as1_sdxes = set()
                if as2 in self.sdx_participants:
                    as2_sdxes = set(self.sdx_participants[as2]["ixps"])
                else:
                    as2_sdxes = set()

                intersection = as1_sdxes.intersection(as2_sdxes)
                if len(intersection) > 0:
                    sdxes = sdxes.union(intersection)
            as2 = as1
        return sdxes


def main(argv):
    # logging - log level
    logging.basicConfig(level=logging.INFO)

    evaluator = Evaluator(int(argv.mode), argv.sdx, argv.policies, True)
    total_policies, installed_policies = evaluator.run_evaluation()


''' main '''
if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('mode', help='evaluation mode')
    parser.add_argument('sdx', help='path to pickled sdx_structure file')
    parser.add_argument('policies', help='path to ports file')

    args = parser.parse_args()

    main(args)
