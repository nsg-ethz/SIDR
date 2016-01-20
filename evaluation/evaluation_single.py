#!/usr/bin/env python
#  Author:
#  Rudiger Birkner (ETH Zurich)

import argparse
import logging
import pickle
import time

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
    def __init__(self, mode, sdx_structure_file, policy_path, iterations, output, debug=False):
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
        self.output = output
        with open(self.output, 'w', 102400) as output:
            output.write("Total Submitted Policies | Safe Policies \n")

        with open(sdx_structure_file, 'r') as sdx_input:
            self.sdx_structure, self.sdx_participants = pickle.load(sdx_input)

        self.dfs_node = namedtuple("DFSNode", "sdx_id in_participant destination match hop")

    def run_evaluation(self):
        start = time.clock()

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
                        tmp_total, tmp_installed, tmp_communication = self.install_policy_no_bgp(sdx_id,
                                                                                                 from_participant,
                                                                                                 to_participant,
                                                                                                 match)
                    else:
                        if self.mode == 1:
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
                             str(installed_policies) + "\n")

            # prepare for next iteration
            for sdx_id, participant_data in self.sdx_structure.iteritems():
                for participant, data in participant_data.iteritems():
                    data["policies"] = defaultdict(dict)

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
        if len(paths) > 1:
            return 1, 0, 0
        else:
            return 1, 1, 0

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
        total_num_messages = 0
        total_cycle_length = 0
        num_cycles = 0
        longest_cycle = 0
        shortest_cycle = 100000
        unique_messages = defaultdict(lambda: defaultdict(set))
        max_hops = 0

        simple_loops = 0

        for destination, sdx_info in paths.iteritems():
            if destination == "other":
                continue

            in_participant = sdx_info[0]
            next_sdx = sdx_info[1]

            if sdx_id == next_sdx:
                simple_loops += 1
                # in case we see the sdx_id of the sdx that wants to install the policy, we skip the policy
                return 1, 0

            # init queue for BFS
            dfs_queue = list()

            # add all next hop sdxes to the queue
            dfs_queue.append(self.dfs_node(next_sdx, in_participant, destination, None, 1))
            # count the message
            unique_messages[next_sdx][sdx_id].add(in_participant)
            total_num_messages += 1

            # start the traversal of the sdx graph for each next hop sdx
            safe, msgs, cycle_length = self.traversal_our_scheme(sdx_id, destination, dfs_queue, unique_messages)
            if not safe:
                return 1, 0

        for destination, sdx_info in paths.iteritems():
            if destination == "other":
                continue

            if to_participant not in self.sdx_structure[sdx_id][from_participant]["policies"][destination]:
                self.sdx_structure[sdx_id][from_participant]["policies"][destination][to_participant] = list()
            self.sdx_structure[sdx_id][from_participant]["policies"][destination][to_participant].append(match)

        return 1, 1

    def traversal_our_scheme(self, sdx_id, destination, dfs_queue, uniq_msgs):
        num_msgs = 0
        max_hop = 0

        # start traversal of SDX graph
        while dfs_queue:
            n = dfs_queue.pop()

            # get all outgoing paths for the in_participant
            out_participants = self.sdx_structure[n.sdx_id][n.in_participant]["policies"][n.destination].keys()

            check = list()

            hop = n.hop + 1
            if hop > max_hop:
                max_hop = hop

            # check if best path goes through that SDX and if so, consider it as well
            if n.destination in self.sdx_participants[n.in_participant]["best"]:
                out_participant, sdx_info = self.sdx_participants[n.in_participant]["best"][n.destination]

                if out_participant in self.sdx_structure[n.sdx_id][n.in_participant]["out_participants"]:
                    # check if the intial sdx is on the path, if so, a loop is created
                    if sdx_id == sdx_info[1]:
                        return False, num_msgs, hop

                    dfs_queue.append(self.dfs_node(sdx_info[1], sdx_info[0], destination, None, hop))
                    num_msgs += 1
                    check.append((sdx_info[0], sdx_info[1]))

                    # count the message
                    uniq_msgs[sdx_info[1]][n.sdx_id].add(sdx_info[0])

            # check all policy activated paths
            for participant in out_participants:
                # only check it, if it is not the best path
                if destination in self.sdx_participants[n.in_participant]["all"][participant]:
                    sdx_info = self.sdx_participants[n.in_participant]["all"][participant][destination]

                    # check if the intial sdx is on the path, if so, a loop is created
                    if sdx_id == sdx_info[1]:
                        return False, num_msgs, hop

                    if (sdx_info[0], sdx_info[1]) in check:
                        continue
                    else:
                        check.append((sdx_info[0], sdx_info[1]))
                        dfs_queue.append(self.dfs_node(sdx_info[1], sdx_info[0], destination, None, hop))

                        # count the message
                        uniq_msgs[sdx_info[1]][n.sdx_id].add(sdx_info[0])
                        num_msgs += 1
        return True, num_msgs, max_hop

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
        total_num_messages = 0
        unique_messages = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))
        simple_loops = 0

        for destination, sdx_info in paths.iteritems():
            if destination == "other":
                continue

            in_participant = sdx_info[0]
            next_sdx = sdx_info[1]

            if sdx_id == next_sdx and from_participant == in_participant:
                simple_loops += 1
                # in case we see the sdx_id of the sdx that wants to install the policy, we skip the policy
                return 1, 0

            # init queue
            dfs_queue = list()

            # add all next hop sdxes to the queue
            dfs_queue.append(self.dfs_node(sdx_info[1], in_participant, destination, match, 1))
            # count the message
            unique_messages[sdx_info[1]][sdx_id][in_participant].add(match)
            total_num_messages += 1

            # start the traversal of the sdx graph for each next hop sdx
            safe, msgs, cycle_length = self.traversal_full_knowledge(sdx_id, from_participant, destination, dfs_queue, unique_messages)

            if not safe:
                return 1, 0

        for destination, sdx_info in paths.iteritems():
            if to_participant not in self.sdx_structure[sdx_id][from_participant]["policies"][destination]:
                self.sdx_structure[sdx_id][from_participant]["policies"][destination][to_participant] = list()
            self.sdx_structure[sdx_id][from_participant]["policies"][destination][to_participant].append(match)

        return 1, 1

    def traversal_full_knowledge(self, sdx_id, from_participant, destination, dfs_queue, uniq_msgs):
        num_msgs = 0
        max_hop = 0

        # start traversal
        while dfs_queue:
            n = dfs_queue.pop()

            hop = n.hop + 1
            if hop > max_hop:
                max_hop = hop

            # get all outgoing paths for the in_participant
            out_participants = self.sdx_structure[n.sdx_id][n.in_participant]["policies"][destination].keys()

            # check if best path goes through that SDX and if so, consider it as well
            if n.destination in self.sdx_participants[n.in_participant]["best"]:
                out_participant, sdx_info = self.sdx_participants[n.in_participant]["best"][n.destination]
                if out_participant in self.sdx_structure[n.sdx_id][n.in_participant]["out_participants"]:
                    # check if the intial sdx is on the path, if so, a loop is created
                    if sdx_id == sdx_info[1] and from_participant == sdx_info[0]:
                        return False, num_msgs, hop

                    dfs_queue.append(self.dfs_node(sdx_info[1], sdx_info[0], destination, n.match, hop))
                    uniq_msgs[sdx_info[1]][n.sdx_id][sdx_info[0]].add(n.match)
                    num_msgs += 1

            # check all policy activated paths
            for participant in out_participants:
                # only check it, if it is not the best path
                if destination in self.sdx_participants[n.in_participant]["all"][participant]:
                    for match in self.sdx_structure[n.sdx_id][n.in_participant]["policies"][destination][participant]:
                        new_match = Evaluator.combine(n.match, match)
                        if new_match:
                            sdx_info = self.sdx_participants[n.in_participant]["all"][participant][destination]
                            # check if the intial sdx is on the path, if so, a loop is created
                            if sdx_id == sdx_info[1] and from_participant == sdx_info[0]:
                                return False, num_msgs, hop

                            dfs_queue.append(self.dfs_node(sdx_info[1], sdx_info[0], destination, new_match, hop))
                            uniq_msgs[sdx_info[1]][n.sdx_id][sdx_info[0]].add(new_match)
                            num_msgs += 1

        return True, num_msgs, max_hop

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

    args = parser.parse_args()

    main(args)
