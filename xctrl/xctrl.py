#!/usr/bin/env python
#  Author:
#  Rudiger Birkner (Networked Systems Group ETH Zurich)

import os
import argparse

import logging
from threading import Thread
from lib import Config, XCTRLEvent

from multiprocessing import Queue
from Queue import Empty

from arp_proxy.arp_proxy import ARPProxy
from route_server.route_server import RouteServer


class XCTRL(object):
    def __init__(self, base_path, config_file, debug):
        self.logger = logging.getLogger(__name__)
        self.debug = debug
        if self.debug:
            self.logger.setLevel(logging.DEBUG)
        self.logger.info('init')

        # Parse Config
        self.config = Config(base_path, config_file)

        # Event Queue
        self.event_queue = Queue()

        self.run = False

        self.modules = dict()
        self.threads = dict()

    def start(self):
        # Start all modules

        # route server
        self.modules["route_server"] = RouteServer(self.config, self.event_queue, self.debug)
        self.threads["route_server"] = Thread(target=self.modules["route_server"].start)
        self.threads["route_server"].start()

        # arp proxy - needs access to VMAC encoder
        self.modules["arp_proxy"] = ARPProxy(self.config, self.event_queue, self.modules["vmac_encoder"], self.debug)
        self.threads["arp_proxy"] = Thread(target=self.modules["arp_proxy"].start)
        self.threads["arp_proxy"].start()

        # loop detection - needs access to RIB

        # VMAC encoder - needs access to RIB, CIB

        # policies - needs access to Correctness, VMAC encoder

        # Process all incoming events
        self.run = True
        event = None
        while self.run:
            try:
                event = self.event_queue.get(True, 1)

            except Empty:
                self.logger.debug('stop')
                continue

            if isinstance(event, XCTRLEvent):
                if event.type == "RIB UPDATE":
                    # update vnh assignment
                    self.modules["vmac_encoder"].vnh_assignment(event.data)

                    # update supersets
                    self.modules["vmac_encoder"].update_supersets(event.data)

                if event.type == "SUPERSET CHANGE":
                    # notify policy module about superset change
                    self.modules["policies"].supersets_changed(event.data)

                    # Send Gratuitous ARPs
                    for change in event.data:
                        self.modules["arp_proxy"].send_gratuitous_arp(event.data)

    def stop(self):
        self.run = False

        # Stop all Modules and Join all Threads
        for module in self.modules.values():
            module.stop()

        for thread in self.threads.values():
            thread.join()


def main(argv):
    # locate config file
    base_path = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)),"..","examples",
                                             argv.dir,"controller-"+args.controller))
    config_file = os.path.join(base_path, "sdx_config", "sdx_global.cfg")

    # start route server
    xctrl_instance = XCTRL(argv.sdxid, config_file, argv.debug)
    xctrl_thread = Thread(target=xctrl_instance.start)
    xctrl_thread.start()

    while xctrl_thread.is_alive():
        try:
            xctrl_thread.join(1)
        except KeyboardInterrupt:
            xctrl_instance.stop()

''' main '''
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('dir', help='the directory of the example')
    parser.add_argument('sdxid', help='SDX identifier')
    parser.add_argument('-d', '--debug', help='enable debug output', action='store_true')
    args = parser.parse_args()

    main(args)
