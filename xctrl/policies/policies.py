#!/usr/bin/env python
#  Author:
#  Rudiger Birkner (Networked Systems Group ETH Zurich)

import json
import logging
import time

from multiprocessing.connection import Listener
from collections import defaultdict
from gss import GSSmT
from flowmodsender import FlowModSender
from lib import XCTRLModule


class PolicyHandler(XCTRLModule):
    def __init__(self, config, event_queue, debug, vmac_encoder, loop_detector, test, timing):
        super(PolicyHandler, self).__init__(config, event_queue, debug)
        self.logger = logging.getLogger('xctrl')
        self.logger.info('init')

        self.test = test
        self.timing = timing
        if self.timing:
            self.timing_file = 'policy_timing_' + str(int(time.time())) + '.log'

        self.loop_detector = loop_detector
        self.vmac_encoder = vmac_encoder

        self.sender = FlowModSender(self.config.refmon_url)

        self.policies = defaultdict(lambda: defaultdict(list))

        self.controller = GSSmT(self.sender, self.config, self.vmac_encoder)

        self.logger.info('init')

        self.ingress_participants = defaultdict(set)
        self.egress_participants = defaultdict(set)


        self.run = False
        self.listener = None

    def start(self):
        """
        Receives policiy installation requests, checks the request with the loop detection module and installs it.
        :return:
        """
        self.logger.info('start')

        self.listener = Listener((self.config.policy_handler.address, self.config.policy_handler.port), authkey=None)
        self.run = True

        if not self.test:
            self.controller.start()

        while self.run:
            conn = self.listener.accept()
            tmp = conn.recv()

            policies = json.loads(tmp)

            i = 0

            if self.timing:
                start_time = time.clock()

            for policy in policies:

                ingress_participant = policy["participant"]
                egress_participant = policy["action"]["fwd"]
                type = policy["type"]
                match = policy["match"]
                action = policy["action"]

                if type == "outbound":
                    safe_to_install = self.loop_detector.activate_policy(ingress_participant, egress_participant)
                else:
                    safe_to_install = True

                if safe_to_install:
                    if not self.test:
                        cookie = self.controller.add_flow_rule(ingress_participant,
                                                               type,
                                                               match,
                                                               egress_participant)
                    else:
                        cookie = 0

                    self.policies[ingress_participant][type].append(Policy(cookie,
                                                                           match,
                                                                           action,
                                                                           egress_participant))

                    # update structures
                    if type == "outbound":
                        self.ingress_participants[egress_participant].add(ingress_participant)
                        self.egress_participants[ingress_participant].add(egress_participant)

                    i += 1

            if self.timing:
                end_time = time.clock()
                with open(self.timing_file, "a") as outfile:
                    outfile.write(str(end_time - start_time) + '\n')

            reply = "Total Received Policies: " + str(len(policies)) + " Accepted Policies: " + str(i)
            conn.send(reply)
            conn.close()

    def stop(self):
        self.logger.info('stop')
        self.run = False

    def get_egress_participants(self, ingress_participant):
        return self.egress_participants[ingress_participant]

    def get_ingress_participants(self, egress_participant):
        return self.ingress_participants[egress_participant]

    def update_policies(self):
        # after change of supersets, update policies in the dataplane, only outbound policies need to be changed
        for policies in self.policies.values():
            for policy in policies["outbound"]:
                if not self.test:
                    cookie = self.controller.update_flow_rule("outbound",
                                                              policy.cookie,
                                                              policy.match,
                                                              policy.forward_participant)


class PolicyHandlerConfig(object):
    def __init__(self, address, port):
        self.address = address
        self.port = port


class Policy(object):
    def __init__(self, cookie, match, action, forward_participant):
        self.match = match
        self.action = action
        self.forward_participant = forward_participant
        self.cookie = cookie
