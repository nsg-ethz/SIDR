#!/usr/bin/env python
#  Author:
#  Rudiger Birkner (Networked Systems Group ETH Zurich)

import os
import argparse

import logging
from threading import Thread
from config import Config
from lib import XCTRLEvent

from multiprocessing import Queue
from Queue import Empty

from arp_proxy.arp_proxy import ARPProxy
from route_server.route_server import RouteServer
from vmac_encoder.supersets import SuperSetEncoder
from loop_detection.loop_detector import LoopDetector
from policies.policies import PolicyHandler


class XCTRL(object):
    def __init__(self,
                 sdx_id,
                 base_path,
                 config_file,
                 debug,
                 test,
                 no_superset,
                 rib_timing,
                 policy_timing,
                 notification_timing,
                 no_notifications):

        self.logger = logging.getLogger("XCTRL")
        self.debug = debug
        self.test = test
        self.no_notifications = no_notifications
        self.no_superset = no_superset

        self.rib_timing = rib_timing
        self.policy_timing = policy_timing
        self.notification_timing = notification_timing
        if self.debug:
            self.logger.setLevel(logging.DEBUG)
        self.logger.info('init')

        # Parse Config
        self.config = Config(sdx_id, base_path, config_file)

        # Event Queue
        self.event_queue = Queue()

        self.run = False

        if self.test:
            self.thread_modules = ["route_server", "loop_detection", "policy_handler"]
        else:
            self.thread_modules = ["route_server", "loop_detection", "policy_handler", "arp_proxy"]

        self.modules = dict()
        self.threads = dict()

    def start(self):
        # Start all modules
        # route server
        self.modules["route_server"] = RouteServer(self.config, self.event_queue, self.debug, self.test)

        # loop detection - needs access to RIB
        self.modules["loop_detection"] = LoopDetector(self.config,
                                                      self.event_queue,
                                                      self.debug,
                                                      self.modules["route_server"].rib,
                                                      None,
                                                      self.test,
                                                      self.no_notifications,
                                                      self.rib_timing,
                                                      self.notification_timing)

        # VMAC encoder - needs access to RIB, CIB
        self.modules["vmac_encoder"] = SuperSetEncoder(self.config,
                                                       self.event_queue,
                                                       self.debug,
                                                       self.modules["route_server"].rib,
                                                       self.modules["loop_detection"].forbidden_paths,
                                                       self.test)

        # policies - needs access to Correctness, VMAC encoder
        self.modules["policy_handler"] = PolicyHandler(self.config,
                                                       self.event_queue,
                                                       self.debug,
                                                       self.modules["vmac_encoder"],
                                                       self.modules["loop_detection"],
                                                       self.test,
                                                       self.policy_timing)

        self.modules["loop_detection"].policy_handler = self.modules["policy_handler"]

        # arp proxy - needs access to VMAC encoder
        self.modules["arp_proxy"] = ARPProxy(self.config,
                                             self.event_queue,
                                             self.debug,
                                             self.modules["vmac_encoder"],
                                             self.test)

        for name in self.thread_modules:
            if self.modules[name]:
                self.threads[name] = Thread(target=self.modules[name].start)
                self.threads[name].daemon = True
                self.threads[name].start()

        # Process all incoming events
        self.run = True
        while self.run:
            try:
                event = self.event_queue.get(True, 1)

            except Empty:
                #self.logger.debug('Event Queue Empty')
                continue

            if isinstance(event, XCTRLEvent):
                if event.type == "RIB UPDATE":

                    # update vnh assignment
                    self.modules["vmac_encoder"].vnh_assignment(event.data)

                    # update supersets
                    sdx_messages = self.modules["vmac_encoder"].update_supersets(event.data)

                    # update policies if supersets changed
                    if sdx_messages["type"] == "new":
                        # policy module
                        self.modules["policy_handler"].update_policies()

                    # loop detection
                    self.modules["loop_detection"].rib_update(event.data)

                    # notify all participants about the RIB changes
                    changes = self.modules["route_server"].update_neighbors(event.data)

                    # Renew ARP
                    for change in changes:
                        self.modules["arp_proxy"].send_gratuitous_arp(change)

                elif event.type == "FORBIDDEN PATHS UPDATE":
                    # Renew ARP
                    for change in changes:
                        self.modules["arp_proxy"].send_gratuitous_arp(change)

    def stop(self):
        self.run = False

        # Stop all Modules and Join all Threads
        for name in self.thread_modules:
            if self.modules[name]:
                self.modules[name].stop()

        for thread in self.threads.values():
            thread.join()


def main(argv):
    # logging - log level
    logging.basicConfig(level=logging.INFO)

    # locate config file
    base_path = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "examples",
                                             argv.dir))
    config_file = os.path.join(base_path, "global.cfg")

    # start route server
    xctrl_instance = XCTRL(int(argv.sdxid),
                           base_path,
                           config_file,
                           argv.debug,
                           argv.test,
                           argv.nosuperset,
                           argv.ribtiming,
                           argv.policytiming,
                           argv.notificationtiming,
                           argv.nonotifications)
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
    parser.add_argument('-t', '--test', help='test mode', action='store_true')
    parser.add_argument('-ns', '--nosuperset', help='deactivate superset computation', action='store_true')
    parser.add_argument('-nn', '--nonotifications', help='no notifications', action='store_true')
    parser.add_argument('-rt', '--ribtiming', help='rib update timing', action='store_true')
    parser.add_argument('-pt', '--policytiming', help='policy activation timing', action='store_true')
    parser.add_argument('-nt', '--notificationtiming', help='notification timing', action='store_true')
    args = parser.parse_args()

    main(args)
