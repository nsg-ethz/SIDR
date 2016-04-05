#!/usr/bin/env python
#  Author:
#  Rudiger Birkner (Networked Systems Group ETH Zurich)

import logging

from flowmodmsg import FlowModMsgBuilder

# Priorities
BGP_PRIORITY = 6
ARP_PRIORITY = 6
VNH_ARP_PRIORITY = 5
ARP_BROADCAST_PRIORITY = 5
OUTBOUND_PRIORITY = 4
FORWARDING_PRIORITY = 4
INBOUND_FORWARDING_PRIORITY = 5

DEFAULT_PRIORITY = 1

PARTICIPANT_OUTBOUND = 2
PARTICIPANT_INBOUND = 4
TAGGING_PRIORITY = 2

# Ports
BGP = 179

# ETH Types
ETH_TYPE_ARP = 0x0806

# MAC Addresses
MAC_BROADCAST = "ff:ff:ff:ff:ff:ff"

# OF Special Ports
OFPP_MAX = 0xffffff00
OFPP_IN_PORT = 0xfffffff8       # Send the packet out the input port. This
                                # virtual port must be explicitly used
                                # in order to send back out of the input
                                # port.
OFPP_TABLE = 0xfffffff9         # Perform actions in flow table.
                                # NB: This can only be the destination
                                # port for packet-out messages.
OFPP_NORMAL = 0xfffffffa        # Process with normal L2/L3 switching.
OFPP_FLOOD = 0xfffffffb         # All physical ports except input port and
                                # those disabled by STP.
OFPP_ALL = 0xfffffffc           # All physical ports except input port.
OFPP_CONTROLLER = 0xfffffffd    # Send to controller.
OFPP_LOCAL = 0xfffffffe         # Local openflow "port".
OFPP_ANY = 0xffffffff               # Not associated with a physical port.


class GSS(object):
    def __init__(self, sender, config, vmac_builder):
        self.sender = sender
        self.config = config
        self.fm_builder = None
        self.vmac_builder = vmac_builder

    def handle_bgp(self, rule_type):
        # BGP traffic to route server
        port = self.config.route_server.fabric_port
        action = {"fwd": [port.id]}
        match = {"eth_dst": port.mac, "tcp_src": BGP}
        self.fm_builder.add_flow_mod("insert", rule_type, BGP_PRIORITY, match, action)

        match = {"eth_dst": port.mac, "tcp_dst": BGP}
        self.fm_builder.add_flow_mod("insert", rule_type, BGP_PRIORITY, match, action)

        # BGP traffic to participants
        for participant in self.config.participants.values():
            for port in participant.ports:
                match = {"eth_dst": port.mac, "tcp_src": BGP}
                action = {"fwd": [port.id]}
                self.fm_builder.add_flow_mod("insert", rule_type, BGP_PRIORITY, match, action)
                match = {"eth_dst": port.mac, "tcp_dst": BGP}
                self.fm_builder.add_flow_mod("insert", rule_type, BGP_PRIORITY, match, action)

    def handle_arp(self, rule_type):
        # direct ARP requests for VNHs to ARP proxy
        port = self.config.arp_proxy.port
        match = {"eth_type": ETH_TYPE_ARP,
                 "arp_tpa": (str(self.config.vmac_encoder.vnhs.network), str(self.config.vmac_encoder.vnhs.netmask))}
        action = {"fwd": [port.id]}
        self.fm_builder.add_flow_mod("insert", rule_type, VNH_ARP_PRIORITY, match, action)

        # direct all ARP requests for the route server to it
        port = self.config.route_server.fabric_port
        match = {"eth_type": ETH_TYPE_ARP, "eth_dst": port.mac}
        action = {"fwd": [port.id]}
        self.fm_builder.add_flow_mod("insert", rule_type, ARP_PRIORITY, match, action)

        for participant in self.config.participants.values():
            # make sure ARP replies reach the participants
            for port in participant.ports:
                match = {"eth_type": ETH_TYPE_ARP, "eth_dst": port.mac}
                action = {"fwd": [port.id]}
                self.fm_builder.add_flow_mod("insert", rule_type, ARP_PRIORITY, match, action)

            # direct gratuituous ARPs only to the respective participant
            vmac = self.vmac_builder.best_path_match(participant.id)
            vmac_mask = self.vmac_builder.best_path_mask()
            match = {"in_port": self.config.arp_proxy.port.id, "eth_type": ETH_TYPE_ARP, "eth_dst": (vmac, vmac_mask)}
            action = {"set_eth_dst": MAC_BROADCAST}
            fwd = []
            for port in participant.ports:
                fwd.append(port.id)
            action["fwd"] = fwd
            self.fm_builder.add_flow_mod("insert", rule_type, ARP_PRIORITY, match, action)

        # flood ARP requests - but only on non switch-switch ports
        match = {"eth_type": ETH_TYPE_ARP, "eth_dst": MAC_BROADCAST}
        ports = []
        for participant in self.config.participants.values():
            for port in participant.ports:
                ports.append(port.id)
        ports.append(self.config.arp_proxy.port.id)
        ports.append(self.config.route_server.fabric_port.id)

        action = {"fwd": ports}
        self.fm_builder.add_flow_mod("insert", rule_type, ARP_BROADCAST_PRIORITY, match, action)

    def tagging(self, rule_type):
        for participant in self.config.participants.values():
            # multiple ports match
            tag_mac = participant.ports[0].mac

            for i in range(1, len(participant.ports)):
                port_id = participant.ports[i].id
                match = {"in_port": port_id}
                action = {"set_eth_src": tag_mac, "fwd": ["outbound"]}
                self.fm_builder.add_flow_mod("insert", rule_type, TAGGING_PRIORITY, match, action)

    def default_forwarding(self, rule_type):
        for participant in self.config.participants.values():
            # multiple ports match
            for i in range(1, len(participant.ports)):
                port = participant.ports[i]
                vmac = self.vmac_builder.participant_port_match(participant.id, i)
                vmac_mask = self.vmac_builder.participant_port_mask()
                match = {"eth_dst": (vmac, vmac_mask)}
                action = {"set_eth_dst": port.mac, "fwd": [port.id]}
                self.fm_builder.add_flow_mod("insert", rule_type, INBOUND_FORWARDING_PRIORITY, match, action)

            # default forwarding
            vmac = self.vmac_builder.best_path_match(participant.id)
            vmac_mask = self.vmac_builder.best_path_mask()
            port = participant.ports[0]
            match = {"eth_dst": (vmac, vmac_mask)}
            action = {"set_eth_dst": port.mac, "fwd": [port.id]}
            self.fm_builder.add_flow_mod("insert", rule_type, FORWARDING_PRIORITY, match, action)

    def match_any_fwd(self, rule_type, dst):
        match = {}
        action = {"fwd": [dst]}
        self.fm_builder.add_flow_mod("insert", rule_type, DEFAULT_PRIORITY, match, action)

    def delete_flow_rule(self, rule_type, cookie):
        self.fm_builder.delete_flow_mod("remove", rule_type, cookie)
        self.sender.send(self.fm_builder.get_msg())

    def add_flow_rule(self, participant, rule_type, match, fwd):
        if rule_type == "outbound":
            priority = PARTICIPANT_OUTBOUND
            action = self.get_outbound_action(fwd)
            action["fwd"] = ["inbound"]

            # augment match with vmac to ensure correctness
            vmac_match = self.vmac_builder.participant_bit_match(fwd)
            vmac_match_mask = self.vmac_builder.participant_bit_mask(fwd)
            match["eth_dst"] = (vmac_match, vmac_match_mask)

            # match on mac tag to ensure isolation
            tag_mac = self.config.participants[participant].ports[0].mac
            match["eth_src"] = tag_mac
        elif rule_type == "inbound":
            priority = PARTICIPANT_INBOUND
            action = self.get_inbound_action(participant, fwd)
            action["fwd"] = ["main-out"]

            # augment match with vmac to ensure correctness
            vmac_match = self.vmac_builder.best_path_match(participant)
            vmac_match_mask = self.vmac_builder.best_path_mask()
            match["eth_dst"] = (vmac_match, vmac_match_mask)
        else:
            return -1

        cookie = self.fm_builder.add_flow_mod("insert", rule_type, priority, match, action)
        msg = self.fm_builder.get_msg()
        print str(msg)
        self.sender.send(msg)
        return cookie

    def update_flow_rule(self, participant, rule_type, cookie, match, fwd_participant):
        self.delete_flow_rule(rule_type, cookie)
        cookie = self.add_flow_rule(participant, rule_type, match, fwd_participant)
        return cookie

    def get_inbound_action(self, participant, port):
        vmac = self.vmac_builder.participant_port_match(participant, port)
        return {"set_eth_dst": vmac}

    def get_outbound_action(self, participant):
        vmac = self.vmac_builder.best_path_match(participant)
        return {"set_eth_dst": vmac}


class GSSmT(GSS):
    def __init__(self, sender, config, vmac_builder):
        super(GSSmT, self).__init__(sender, config, vmac_builder)
        self.logger = logging.getLogger('GSSmT')
        self.fm_builder = FlowModMsgBuilder()

    def start(self):
        self.logger.info('start')
        self.init_fabric()

    def init_fabric(self):
        self.logger.info('init fabric')

        # MAIN-IN TABLE
        # handle BGP traffic
        self.logger.info('create flow mods to handle BGP traffic')
        self.handle_bgp("main-in")

        # handle ARP traffic
        self.logger.info('create flow mods to handle ARP traffic')
        self.handle_arp("main-in")

        # tag participant packets
        self.logger.info('create flow mods to handle participant traffic')
        self.tagging("main-in")

        # whatever doesn't match on any other rule, send to outbound switch
        self.match_any_fwd("main-in", "outbound")

        # OUTBOUND SWITCH
        # whatever doesn't match on any other rule, send to inbound switch
        self.match_any_fwd("outbound", "inbound")

        # INBOUND SWITCH
        # send all other packets to main
        self.match_any_fwd("inbound", "main-out")

        # MAIN-OUT TABLE
        # default forwarding
        self.default_forwarding("main-out")

        self.sender.send(self.fm_builder.get_msg())

        self.logger.info('sent flow mods to reference monitor')
