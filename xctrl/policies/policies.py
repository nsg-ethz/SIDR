#!/usr/bin/env python
#  Author:
#  Rudiger Birkner (Networked Systems Group ETH Zurich)

import json
import argparse
import logging

from multiprocessing.connection import Listener

from flowmodsender import FlowModSender # REST API
from gss import GSSmT


class Policy(object):
    def __init__(self, config, event_queue, debug, supersets, loop_detector):
        super(Policy, self).__init__(config, event_queue, debug)
        self.logger = logging.getLogger('xctrl')
        self.logger.info('init')

        self.supersets = supersets
        self.loop_detector = loop_detector

        self.policies = None

        self.client = FlowModSender(self.config.refmon["url"]) # REST API

        self.controller = GSSmT(self.client, self.config)
        self.logger.info('mode GSSmT - OF v1.3')

        self.run = False
        self.listener = None

    def start(self):
        self.logger.info('start')
        self.controller.start()

        self.listener = Listener((self.config.policy.address, self.config.policy.port), authkey=None)
        self.run = True
        while self.run:
            conn = self.listener.accept()
            tmp = conn.recv()

            policy_request = json.loads(tmp)

            self.loop_detector.activate_policy(ingress_participant, egress_participant)

            conn.send(reply)

            conn.close()

    def stop(self):
        self.logger.info('stop')

    
''' main '''    
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('config', help='path of config file')
    args = parser.parse_args() 
    
    main(args)
