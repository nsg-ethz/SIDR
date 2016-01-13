#!/usr/bin/env python
#  Author:
#  Rudiger Birkner (ETH Zurich)

import argparse
import logging
import pickle
import time
import json

from collections import namedtuple, defaultdict

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
    def __init__(self, mode, sdx_structure_file, policy_path, iterations, output_file, messages_file, hops_file, debug=False):
        self.logger = logging.getLogger("Evaluator")
        if debug:
            self.logger.setLevel(logging.DEBUG)

        self.policy_path = policy_path
        self.sdx_structure_file = sdx_structure_file

        self.mode = 0
        if 0 <= mode < 4:
            self.mode = mode
        else:
            self.logger.error("invalid mode specified")

        self.iterations = iterations
        self.output = output_file
        with open(self.output, 'w', 102400) as output:
            output.write("Total Submitted Policies | Safe Policies | messages | hops \n")

        self.messages_file = messages_file
        self.hops_file = hops_file

        with open(sdx_structure_file, 'r') as sdx_input:
            self.sdx_structure, self.sdx_participants = pickle.load(sdx_input)

        self.dfs_node = namedtuple("DFSNode", "sdx_id in_participant destination match hop")

    def run_evaluation(self):
        start = time.clock()

        received_messages = defaultdict(int)
        num_hops = defaultdict(int)

        for j in range(0, self.iterations):
            # run evaluation
            total_policies = 0
            installed_policies = 0

            with open(self.policy_path + "policies_" + str(j) + ".log", 'r') as policies:
                i = 0
                for policy in policies:
                    i += 1

                    x = policy.split("\n")[0].split("|")
                    sdx_id = int(x[0])
                    from_participant = int(x[1])
                    to_participant = int(x[2])
                    match = int(x[4])

                    if self.mode == 0:
                        tmp_total, tmp_installed = self.install_policy_no_bgp(sdx_id,
                                                                              from_participant,
                                                                              to_participant,
                                                                              match)
                    else:
                        if self.mode == 1:
                            tmp_total, tmp_installed, tmp_received_messages, tmp_num_hops = \
                                self.install_policy_our_scheme(sdx_id,
                                                               from_participant,
                                                               to_participant,
                                                               match)
                        else:
                            tmp_total, tmp_installed, tmp_received_messages, tmp_num_hops = \
                                self.install_policy_full_knowledge(sdx_id,
                                                                   from_participant,
                                                                   to_participant,
                                                                   match)

                        for hop in tmp_num_hops:
                            num_hops[hop] += 1

                        for msgs in tmp_received_messages:
                            received_messages[msgs] += 1

                    total_policies += tmp_total
                    installed_policies += tmp_installed

                    if i % 1000 == 0:
                        self.logger.debug(str(time.clock() - start) + " - tried to install a total of " +
                                          str(total_policies) + ", managed to safely install " +
                                          str(installed_policies))

            # output
            self.logger.info("Total Policies: " + str(total_policies) +
                             ", Safe Policies: " + str(installed_policies))

            # store results
            with open(self.output, 'a', 102400) as output:
                output.write(str(total_policies) + "|" +
                             str(installed_policies) + "|" +
                             ",".join([str(x) for x in received_messages]) + "|" +
                             ",".join([str(x) for x in num_hops]) + "\n")

            # prepare for next iteration
            for sdx_id, participant_data in self.sdx_structure.iteritems():
                for participant, data in participant_data.iteritems():
                    data["policies"] = defaultdict(dict)

        with open(self.messages_file, 'w', 102400) as output:
            data = json.dumps(received_messages)
            output.write(data)

        with open(self.hops_file, 'w', 102400) as output:
            data = json.dumps(num_hops)
            output.write(data)

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

        # check for each destination/prefix separately whether the policy is safe
        i = len(paths) - 1 + paths['other']
        j = paths['other']

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
        total_num_policies = len(paths) - 1 + paths['other']
        num_safe_policies = paths['other']

        unique_messages = defaultdict(lambda: defaultdict(set))
        hops = list()

        num_received_messages = list()

        for destination, sdx_info in paths.iteritems():
            if destination == "other":
                continue

            if sdx_id in sdx_info[1]:
                # in case we see the sdx_id of the sdx that wants to install the policy, we skip the policy
                continue

            # init queue for BFS
            dfs_queue = list()

            # add all next hop sdxes to the queue
            for sdx in sdx_info[1]:
                dfs_queue.append(self.dfs_node(sdx, sdx_info[0], destination, None, 1))
                unique_messages[sdx][sdx_id].add(sdx_info[0])

            # start the traversal of the sdx graph for each next hop sdx
            safe, num_hops = self.traversal_our_scheme(sdx_id, destination, dfs_queue, unique_messages)

            if safe:
                num_safe_policies += 1

                if to_participant not in self.sdx_structure[sdx_id][from_participant]["policies"][destination]:
                    self.sdx_structure[sdx_id][from_participant]["policies"][destination][to_participant] = list()
                self.sdx_structure[sdx_id][from_participant]["policies"][destination][to_participant].append(match)

            hops.append(num_hops)

            for x in unique_messages.values():
                for y in x.values():
                    num_received_messages.append(len(y))

        return total_num_policies, num_safe_policies, num_received_messages, hops

    def traversal_our_scheme(self, sdx_id, destination, dfs_queue, unique_messages):

        # start traversal of SDX graph
        while dfs_queue:
            n = dfs_queue.pop()

            # get all outgoing paths for the in_participant
            out_participants = self.sdx_structure[n.sdx_id][n.in_participant]["policies"][n.destination].keys()

            hop = n.hop + 1

            check = list()

            # check if best path goes through that SDX and if so, consider it as well
            if n.destination in self.sdx_participants[n.in_participant]["best"]:
                out_participant, sdx_info = self.sdx_participants[n.in_participant]["best"][n.destination]

                if out_participant in self.sdx_structure[n.sdx_id][n.in_participant]["out_participants"]:
                    # check if the intial sdx is on the path, if so, a loop is created
                    if sdx_id in sdx_info[1]:
                        return False, hop
                    for sdx in sdx_info[1]:
                        dfs_queue.append(self.dfs_node(sdx, sdx_info[0], destination, None, hop))
                        check.append((sdx_info[0], sdx))

                        # count the message
                        unique_messages[sdx][n.sdx_id].add(sdx_info[0])

            # check all policy activated paths
            for participant in out_participants:
                # only check it, if it is not the best path
                if destination in self.sdx_participants[n.in_participant]["all"][participant]:
                    sdx_info = self.sdx_participants[n.in_participant]["all"][participant][destination]

                    # check if the intial sdx is on the path, if so, a loop is created
                    if sdx_id in sdx_info[1]:
                        return False, hop
                    for sdx in sdx_info[1]:
                        if (sdx_info[0], sdx) in check:
                            continue
                        else:
                            check.append((sdx_info[0], sdx))
                            dfs_queue.append(self.dfs_node(sdx, sdx_info[0], destination, None, hop))
                            # count the message
                            unique_messages[sdx][n.sdx_id].add(sdx_info[0])

        return True, hop

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
        total_num_policies = len(paths) - 1 + paths['other']
        num_safe_policies = paths['other']

        unique_messages = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))
        num_hops = list()
        num_received_messages = list()

        for destination, sdx_info in paths.iteritems():
            if destination == "other":
                continue

            if sdx_id in sdx_info[1]:
                # in case we see the sdx_id of the sdx that wants to install the policy, we skip the policy
                continue

            # init queue
            dfs_queue = list()

            # add all next hop sdxes to the queue
            for sdx in sdx_info[1]:
                dfs_queue.append(self.dfs_node(sdx, sdx_info[0], destination, match, 1))
                unique_messages[sdx][sdx_id][sdx_info[0]].add(match)

            # start the traversal of the sdx graph for each next hop sdx
            safe, hops = self.traversal_full_knowledge(sdx_id, destination, dfs_queue, unique_messages)

            if safe:
                num_safe_policies += 1

                if to_participant not in self.sdx_structure[sdx_id][from_participant]["policies"][destination]:
                    self.sdx_structure[sdx_id][from_participant]["policies"][destination][to_participant] = list()
                self.sdx_structure[sdx_id][from_participant]["policies"][destination][to_participant].append(match)

            for x in unique_messages.values():
                for y in x.values():
                    for z in y.values():
                        num_received_messages.append(len(z))

            num_hops.append(hops)

        return total_num_policies, num_safe_policies, num_received_messages, num_hops

    def traversal_full_knowledge(self, sdx_id, destination, dfs_queue, unique_messages):

        # start traversal
        while dfs_queue:
            n = dfs_queue.pop()

            hop = n.hop + 1

            # get all outgoing paths for the in_participant
            out_participants = self.sdx_structure[n.sdx_id][n.in_participant]["policies"][destination].keys()

            # check if best path goes through that SDX and if so, consider it as well
            if n.destination in self.sdx_participants[n.in_participant]["best"]:
                out_participant, sdx_info = self.sdx_participants[n.in_participant]["best"][n.destination]
                if out_participant in self.sdx_structure[n.sdx_id][n.in_participant]["out_participants"]:
                    # check if the intial sdx is on the path, if so, a loop is created
                    if sdx_id in sdx_info[1]:
                        return False, hop
                    for sdx in sdx_info[1]:
                        dfs_queue.append(self.dfs_node(sdx, sdx_info[0], destination, n.match, hop))
                        unique_messages[sdx][n.sdx_id][sdx_info[0]].add(n.match)

            # check all policy activated paths
            for participant in out_participants:
                # only check it, if it is not the best path
                if destination in self.sdx_participants[n.in_participant]["all"][participant]:
                    for match in self.sdx_structure[n.sdx_id][n.in_participant]["policies"][destination][participant]:
                        new_match = Evaluator.combine(n.match, match)
                        if new_match:
                            sdx_info = self.sdx_participants[n.in_participant]["all"][participant][destination]
                            # check if the intial sdx is on the path, if so, a loop is created
                            if sdx_id in sdx_info[1]:
                                return False, hop
                            for sdx in sdx_info[1]:
                                dfs_queue.append(self.dfs_node(sdx, sdx_info[0], destination, new_match, hop))
                                unique_messages[sdx][n.sdx_id][sdx_info[0]].add(n.match)
        return True, hop

    @staticmethod
    def combine(match1, match2):
        combined_match = match1 & match2
        if Evaluator.contains_impossible_bit(combined_match):
            return None
        else:
            return combined_match

    @staticmethod
    def contains_impossible_bit(match):
        bitstring = '{0:080b}'.format(match)
        bits = [bitstring[i:i+2] for i in range(0, 80, 2)]
        for bit in bits:
            if bit == '00':
                return True
        return False


def main(argv):
    # logging - log level
    logging.basicConfig(level=logging.INFO)

    print "Init Evaluator"
    start = time.clock()

    evaluator = Evaluator(int(argv.mode), argv.sdx, argv.policies, int(argv.iterations), argv.output, False)

    print "--> Execution Time: " + str(time.clock() - start) + "s\n"
    print "Evaluate Policies"
    tmp_start = time.clock()

    evaluator.run_evaluation()

    print "--> Execution Time: " + str(time.clock() - tmp_start) + "s\n"
    print "-> Total Execution Time: " + str(time.clock() - start) + "s\n"


''' main '''
if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('mode', help='evaluation mode')
    parser.add_argument('sdx', help='path to pickled sdx_structure file')
    parser.add_argument('policies', help='path to policy files')
    parser.add_argument('iterations', help='number of iterations')
    parser.add_argument('output', help='path of output file')
    parser.add_argument('messages', help='path of messages output file')
    parser.add_argument('length', help='path of length output file')

    args = parser.parse_args()

    main(args)
