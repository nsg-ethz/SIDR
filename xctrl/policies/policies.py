#!/usr/bin/env python
#  Author:
#  Rudiger Birkner (Networked Systems Group ETH Zurich)

import json
import logging

from multiprocessing.connection import Listener
from collections import defaultdict
from gss import GSSmT
from flowmodsender import FlowModSender
from lib import XCTRLModule


class PolicyHandler(XCTRLModule):
    def __init__(self, config, event_queue, debug, vmac_encoder, loop_detector, test):
        super(PolicyHandler, self).__init__(config, event_queue, debug)
        self.logger = logging.getLogger('xctrl')
        self.logger.info('init')

        self.test = test

        self.loop_detector = loop_detector
        self.vmac_encoder = vmac_encoder

        self.sender = FlowModSender(self.config.refmon_url)

        self.policies = defaultdict(lambda: defaultdict(list))

        self.controller = GSSmT(self.sender, self.config, self.vmac_encoder)

        self.logger.info('init')

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
            for policy in policies:
                if policy["type"] == "outbound":
                    safe_to_install = self.loop_detector.activate_policy(policy["participant"], policy["action"]["fwd"])
                    fwd = policy["action"]["fwd"]
                else:
                    safe_to_install = True
                    fwd = policy["action"]["fwd"]

                if safe_to_install:
                    if not self.test:
                        cookie = self.controller.add_flow_rule(policy["participant"],
                                                               policy["type"],
                                                               policy["match"],
                                                               fwd)
                    else:
                        cookie = 0

                    self.policies[policy["participant"]][policy["type"]].append(Policy(cookie,
                                                                                       policy["match"],
                                                                                       policy["action"],
                                                                                       fwd))

                    i += 1

            reply = "Total Received Policies: " + str(len(policies)) + " Accepted Policies: " + str(i)
            conn.send(reply)
            conn.close()

    def stop(self):
        self.logger.info('stop')
        self.run = False

    def get_egress_participants(self, ingress_participant):
        egress_participants = set()
        for policy in self.policies[ingress_participant]["outbound"]:
            egress_participants.add(policy.forward_participant)
        return egress_participants

    def get_ingress_participants(self, egress_participant):
        ingress_participants = set()
        for participant in self.policies:
            for policy in self.policies[participant]["outbound"]:
                if policy.forward_participant == egress_participant:
                    ingress_participants.add(participant)
        return ingress_participants

    def update_policies(self):
        # after change of supersets, update policies in the dataplane, only outbound policies need to be changed
        for policies in self.policies.values():
            for policy in policies["outbound"]:
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
