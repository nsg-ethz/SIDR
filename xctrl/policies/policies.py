#!/usr/bin/env python
#  Author:
#  Rudiger Birkner (Networked Systems Group ETH Zurich)

import json
import argparse
import logging

from multiprocessing.connection import Listener
from collections import defaultdict

from flowmodsender import FlowModSender # REST API
from gss import GSSmT


class PolicyHandler(object):
    def __init__(self, config, event_queue, debug, supersets, loop_detector):
        super(PolicyHandler, self).__init__(config, event_queue, debug)
        self.logger = logging.getLogger('xctrl')
        self.logger.info('init')

        self.supersets = supersets
        self.loop_detector = loop_detector

        self.policies = defaultdict(dict)

        self.client = FlowModSender(self.config.refmon["url"]) # REST API

        self.controller = GSSmT(self.client, self.config)
        self.logger.info('mode GSSmT - OF v1.3')

        self.run = False
        self.listener = None

    def start(self):
        self.logger.info('start')
        self.controller.start()

        self.listener = Listener((self.config.policy_handler.address, self.config.policy_handler.port), authkey=None)
        self.run = True
        while self.run:
            conn = self.listener.accept()
            tmp = conn.recv()

            policy = json.loads(tmp)

            if policy["type"] == "outbound":
                safe_to_install = self.loop_detector.activate_policy(policy["participant"], policy["action"]["fwd"])
            else:
                safe_to_install = True

            if safe_to_install:
                self.policies[policy["participant"]][policy["type"]] = Policy(policy["match"],
                                                                              policy["action"],
                                                                              policy["action"]["fwd"])
                reply = "Policy Accepted"
            else:
                reply = "Policy Rejected"

            conn.send(reply)
            conn.close()

            if safe_to_install:
                # push flow rule to switch
                pass

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


class PolicyHandlerConfig(object):
    def __init__(self, address, port):
        self.address
        self.port


class Policy(object):
    def __init__(self, match, action, forward_participant):
        self.match = match
        self.action = action
        self.forward_participant = forward_participant
