#!/usr/bin/env python
#  Author:
#  Rudiger Birkner (Networked Systems Group ETH Zurich)

import json
import Queue

from server import Server

from decision_process import decision_process
from bgp_interface import bgp_update_peers
from xctrl.lib import XCTRLModule, XCTRLEvent
from peer import Peer


class RouteServer(XCTRLModule):
    def __init__(self, config, event_queue, debug):
        super(RouteServer, self).__init__(config, event_queue, debug)
        self.logger.info("Initialize the Route Server")

        self.config = config
        self.event_queue = event_queue

        # build rib for each participant
        self.rib = dict()
        for participant, attributes in self.config.participants.iteritems():
            self.rib[participant] = Peer(attributes.asn)
        
        self.server = Server(self.config.route_server.port, self.config.route_server.key)
        self.run = False
        
    def start(self):
        print "Start Server"
        self.server.start()

        self.run = True
        while self.run:
            # get BGP messages from ExaBGP via stdin
            try:
                route = self.server.receiver_queue.get(True, 1)

                self.logger.debug("Received Route: " + str(route))
                
                route = json.loads(route)

                # process route advertisements - add/remove routes to/from rib of respective participant (neighbor)
                updates = None
                
                if 'neighbor' in route:
                    if 'ip' in route['neighbor']:
                        updates = self.rib[self.config.portip_2_participant[route['neighbor']['ip']]].update(route)
                elif 'notification' in route:
                    for participant in self.config.participants:
                        self.rib[participant].process_notification(route)
                
                if updates is not None:
                    # update local ribs - select best route for each prefix
                    for update in updates:
                        decision_process(self.rib, update)

                    # BGP updates
                    changes = bgp_update_peers(updates, self.config)

                    event = XCTRLEvent("RouteServer", "RIB UPDATE", changes)
                    self.event_queue.put(event)

            except Queue.Empty:
                self.logger.debug("Empty Queue")

    def stop(self):
        self.run = False


class RouteServerConfig(object):
    def __init__(self, ip, port, key, interface):
        self.ip = ip
        self.port = port
        self.key = key
        self.interface = interface
