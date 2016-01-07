#!/usr/bin/env python
#  Author:
#  Rudiger Birkner (ETH Zurich)

import argparse
import logging
import pickle
import json
import time

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

        i = 0

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

                i += 1
                if i%1000 == 0:
                    self.logger.info("Tried install a total of " + str(total_policies) + ", managed to safely install " +
                                     str(installed_policies))

        self.logger.info("Final Result: Tried to install a total of " + str(total_policies) + ", managed to safely install " +
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
        i = len(paths) - 1 + paths['other']
        j = paths['other']

        if j > 0:
            self.sdx_structure[sdx_id][from_participant]["policies"][to_participant] = match

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

        # check for each destination/prefix separately whether the policy is safe
        paths = self.sdx_participants[from_participant]["all"][to_participant]
        i = len(paths) - 1 + paths['other']
        j = paths['other']

        for destination, sdx_info in paths.iteritems():
            if destination == "other":
                continue

            # init queue
            dfs_queue = list()

            if sdx_id in sdx_info[1]:
                # in case we see the sdx_id of the sdx that wants to install the policy, we skip the policy
                continue

            # add all next hop sdxes to the queue
            for sdx in sdx_info[1]:
                dfs_queue.append(self.dfs_node(sdx, sdx_info[0], destination, None))

            # start the traversal of the sdx graph for each next hop sdx
            if self.traversal_our_scheme(sdx_id, destination, dfs_queue):
                j += 1
            else:
                self.logger.debug("rejected " + str(match.get_match()) + " at SDX " + str(sdx_id) + " from " +
                                  str(from_participant) + " to " + str(to_participant) + " for " + str(destination))

        if j > 0:
            self.sdx_structure[sdx_id][from_participant]["policies"][to_participant].append(match)
        return i, j

    def traversal_our_scheme(self, sdx_id, destination, dfs_queue):
        # start traversal of SDX graph
        while dfs_queue:
            n = dfs_queue.pop()

            # get all outgoing paths for the in_participant
            out_participants = self.sdx_structure[n.sdx_id][n.in_participant]["policies"].keys()

            check = list()

            # check if best path goes through that SDX and if so, consider it as well
            if n.destination in self.sdx_participants[n.in_participant]["best"]:
                out_participant, sdx_info = self.sdx_participants[n.in_participant]["best"][n.destination]
                if out_participant in self.sdx_structure[n.sdx_id][n.in_participant]["out_participants"]:
                    # check if the intial sdx is on the path, if so, a loop is created
                    if sdx_id in sdx_info[1]:
                        return False
                    for sdx in sdx_info[1]:
                        dfs_queue.append(self.dfs_node(sdx, sdx_info[0], destination, None))
                        check.append((sdx_info[0], sdx))

            # check all policy activated paths
            for participant in out_participants:
                # only check it, if it is not the best path
                if destination in self.sdx_participants[n.in_participant]["all"][participant]:
                    sdx_info = self.sdx_participants[n.in_participant]["all"][participant][destination]
                    # check if the intial sdx is on the path, if so, a loop is created
                    if sdx_id in sdx_info[1]:
                        return False
                    for sdx in sdx_info[1]:
                        if (sdx_info[0], sdx) in check:
                            continue
                        else:
                            check.append((sdx_info[0], sdx))
                            dfs_queue.append(self.dfs_node(sdx, sdx_info[0], destination, None))
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

        # check for each destination/prefix separately whether the policy is safe
        paths = self.sdx_participants[from_participant]["all"][to_participant]
        i = len(paths) - 1 + paths['other']
        j = paths['other']

        for destination, sdx_info in paths.iteritems():
            if destination == "other":
                continue

            # init queue
            dfs_queue = list()

            if sdx_id in sdx_info[1]:
                # in case we see the sdx_id of the sdx that wants to install the policy, we skip the policy
                continue

            # add all next hop sdxes to the queue
            for sdx in sdx_info[1]:
                dfs_queue.append(self.dfs_node(sdx, sdx_info[0], destination, match))

            # start the traversal of the sdx graph for each next hop sdx
            if self.traversal_full_knowledge(sdx_id, destination, dfs_queue):
                j += 1
            else:
                self.logger.debug("rejected " + str(match.get_match()) + " at SDX " + str(sdx_id) + " from " +
                                  str(from_participant) + " to " + str(to_participant) + " for " + str(destination))

        if j > 0:
            self.sdx_structure[sdx_id][from_participant]["policies"][to_participant].append(match)

        return i, j

    def traversal_full_knowledge(self, sdx_id, destination, dfs_queue):
        # start traversal

        while dfs_queue:
            n = dfs_queue.pop()

            # get all outgoing paths for the in_participant
            out_participants = self.sdx_structure[n.sdx_id][n.in_participant]["policies"].keys()

            # check if best path goes through that SDX and if so, consider it as well
            if n.destination in self.sdx_participants[n.in_participant]["best"]:
                out_participant, sdx_info = self.sdx_participants[n.in_participant]["best"][n.destination]
                if out_participant in self.sdx_structure[n.sdx_id][n.in_participant]["out_participants"]:
                    # check if the intial sdx is on the path, if so, a loop is created
                    if sdx_id in sdx_info[1]:
                        return False
                    for sdx in sdx_info[1]:
                        dfs_queue.append(self.dfs_node(sdx, sdx_info[0], destination, n.match))

            # check all policy activated paths
            for participant in out_participants:
                # only check it, if it is not the best path
                if destination in self.sdx_participants[n.in_participant]["all"][participant]:
                    for match in self.sdx_structure[n.sdx_id][n.in_participant]["policies"][participant]:
                        new_match = HeaderBitString.combine(n.match, match)
                        if new_match:
                            sdx_info = self.sdx_participants[n.in_participant]["all"][participant][destination]
                            # check if the intial sdx is on the path, if so, a loop is created
                            if sdx_id in sdx_info[1]:
                                return False
                            for sdx in sdx_info[1]:
                                dfs_queue.append(self.dfs_node(sdx, sdx_info[0], destination, new_match))
        return True


def main(argv):
    # logging - log level
    logging.basicConfig(level=logging.INFO)

    print "Init Evaluator"
    start = time.clock()

    evaluator = Evaluator(int(argv.mode), argv.sdx, argv.policies, True)

    print "--> Execution Time: " + str(time.clock() - start) + "s\n"
    print "Evaluate Policies"
    tmp_start = time.clock()

    total_policies, installed_policies = evaluator.run_evaluation()

    print "--> Execution Time: " + str(time.clock() - tmp_start) + "s\n"
    print "-> Total Execution Time: " + str(time.clock() - start) + "s\n"


''' main '''
if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('mode', help='evaluation mode')
    parser.add_argument('sdx', help='path to pickled sdx_structure file')
    parser.add_argument('policies', help='path to ports file')

    args = parser.parse_args()

    main(args)
