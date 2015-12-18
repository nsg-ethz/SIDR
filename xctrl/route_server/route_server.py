#!/usr/bin/env python
#  Author:
#  Rudiger Birkner (Networked Systems Group ETH Zurich)

import json
import Queue

#from server import Server
from test_server import Server

from decision_process import decision_process
from bgp_interface import bgp_update_peers
from lib import XCTRLModule, XCTRLEvent
from peer import Peer
from rib_interface import RIBInterface


class RouteServer(XCTRLModule):
    def __init__(self, config, event_queue, debug, vmac_encoder):
        super(RouteServer, self).__init__(config, event_queue, debug)
        self.logger.info("Initialize the Route Server")

        self.config = config
        self.event_queue = event_queue

        self.vmac_encoder = vmac_encoder

        # build rib for each participant
        self.rib = dict()
        for participant, attributes in self.config.participants.iteritems():
            self.rib[participant] = Peer(attributes.asn)

        self.server = Server(self.config.base_path, self.config.id)
        # self.server = Server(self.config.route_server.port, self.config.route_server.key)
        self.run = False

        self.rib_interface = RIBInterface(self.config, self.rib)
        
    def start(self):
        self.logger.debug("Start ExaBGP Interface")
        self.server.start()

        self.run = True
        while self.run:
            # get BGP messages from ExaBGP via stdin
            try:
                route = self.server.receiver_queue.get(True, 1)

                self.logger.debug("Received Route")
                
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

                    event = XCTRLEvent("RouteServer", "RIB UPDATE", updates)
                    self.event_queue.put(event)

                    # TODO Has to be done after VNH Assignment
                    # BGP updates
                    # changes = bgp_update_peers(updates, self.config)

                    # event = XCTRLEvent("RouteServer", "RIB UPDATE", changes)
                    # self.event_queue.put(event)

            except Queue.Empty:
                #self.logger.debug("Empty Queue")
                pass

    def stop(self):
        self.run = False


class RouteServerConfig(object):
    def __init__(self, ip, port, key, fabric_port, interface):
        self.ip = ip
        self.port = port
        self.key = key
        self.fabric_port = fabric_port
        self.interface = interface
