#!/usr/bin/env python
#  Author:
#  Rudiger Birkner (ETH Zurich)

import logging
import pickle

# SDX Structure
# sdx_id - int
#   participant_id - int
#     out_participants - list of ints
#     policies - list

# Participant Structure
# participant_id - int
#   all
#     out_participant_id
#       (destination, path)
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

        self.sdx_structure, self.sdx_participants = pickle.load(sdx_structure_file)

        self.logger.error("invalid mode specified")

    def run_evaluation(self):
        total_policies = 0
        installed_policies = 0

        with open(self.policy_file, 'r') as policies:
            for policy in policies:
                x = policy.split("\n")[0].split("|")
                sdx_id = x[0]
                from_participant = x[1]
                to_participant = x[2]
                match = x[3]

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
        for path in paths:
            i += 1
            sdxes = self.get_sdxes_on_path(path[0])
            if len(sdxes) == 0:
                j += 1
                self.sdx_structure[sdx_id][from_participant]["policies"] = (from_participant, to_participant, match)
        return i, j

    def install_policy_our_scheme(self, sdx_id, from_participant, to_participant, match):
        return 0, 0

    def install_policy_full_knowledge(self, sdx_id, from_participant, to_participant, match):
        return 0, 0

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

    def get_first_sdxes_on_path(self):
        pass

    def get_first_sdx_participant_on_path(self):
        pass


def main(argv):
    # logging - log level
    logging.basicConfig(level=logging.INFO)