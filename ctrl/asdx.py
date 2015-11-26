#  Author:
#  Rudiger Birkner (Networked Systems Group ETH Zurich)

import os

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.ofproto import ether
from ryu.ofproto import inet
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.app.wsgi import WSGIApplication
from ryu import cfg

from core import SDX
from lib import vmac_best_path_match, vmac_participant_match, create_cookie, create_cookie_mask
from rest import aSDXController

from correctness import ForwardCorrectness

LOG = False

##
BGP = 179
BROADCAST = "ff:ff:ff:ff:ff:ff"

# TABLES
MAIN_TABLE = 0
OUTBOUND_TABLE = 1
INBOUND_TABLE = 2
ARP_BGP_TABLE = 3

# PRIORITIES
FLOW_MISS_PRIORITY = 0
PARTICIPANT_TAGGING_PRIORITY = 1
ARP_BGP_PRIORITY = 2

BEST_PATH_PRIORITY = 1
OUTBOUND_POLICY_PRIORITY = 2

DEFAULT_INBOUND_PRIORITY = 1
INBOUND_POLICY_PRIORITY = 2

DEFAULT_PRIORITY = 1
VNH_ARP_REQ_PRIORITY = 2
GRATUITOUS_ARP_PRIORITY = 3

# COOKIE TYPES
NO_COOKIE = 0

BEST_PATH = 1
OUTBOUND_POLICY = 2

DEFAULT_INBOUND = 3
INBOUND_POLICY = 4

# Fabric Manager ID
FABRIC_MANAGER_ID = 0


class aSDX(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {'wsgi': WSGIApplication}

    def __init__(self, *args, **kwargs):
        super(aSDX, self).__init__(*args, **kwargs)

        wsgi = kwargs['wsgi']
        wsgi.register(aSDXController, self)

        self.mac_to_port = {}
        self.datapath = None
        
        self.metadata_mask = 4095
        
        # parse aSDX config
        conf = cfg.CONF
        directory = conf['asdx']['dir']
        controller = conf['asdx']['controller']
        base_path = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                                 "..", "examples", directory, "controller-"+controller))
        config_file = os.path.join(base_path, "sdx_config", "sdx_global.cfg")
        
        self.config = SDX(base_path, config_file)

        if self.config.correctness_mode == 0:
            self.correctness_module = ForwardCorrectness(self)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        self.datapath = datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        # install table-miss flow entry
        #
        # We specify NO BUFFER to max_len of the output action due to
        # OVS bug. At this moment, if we specify a lesser number, e.g.,
        # 128, OVS will send Packet-In with invalid buffer_id and
        # truncated packet data. In that case, we cannot output packets
        # correctly.  The bug has been fixed in OVS v2.1.0.
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        no_cookie = create_cookie(FABRIC_MANAGER_ID, NO_COOKIE, 0)
        no_cookie_mask = create_cookie_mask(True, True, True)

        self.add_flow(datapath, no_cookie, no_cookie_mask, MAIN_TABLE, FLOW_MISS_PRIORITY, match, actions)
        self.add_flow(datapath, no_cookie, no_cookie_mask, OUTBOUND_TABLE, FLOW_MISS_PRIORITY, match, actions)
        self.add_flow(datapath, no_cookie, no_cookie_mask, INBOUND_TABLE, FLOW_MISS_PRIORITY, match, actions)
        self.add_flow(datapath, no_cookie, no_cookie_mask, ARP_BGP_TABLE, FLOW_MISS_PRIORITY, match, actions)

        self.logger.debug("INIT: Set up ARP handling")
           
        # set up ARP handler
        match = parser.OFPMatch(eth_type=ether.ETH_TYPE_ARP)
        instructions = [parser.OFPInstructionGotoTable(ARP_BGP_TABLE)]
        self.add_flow(datapath, no_cookie, no_cookie_mask, MAIN_TABLE, ARP_BGP_PRIORITY, match, None, instructions)

        # send all ARP requests for VNHs to the route server
        match = parser.OFPMatch(arp_tpa=(str(self.config.VNHs.network), str(self.config.VNHs.netmask)))
        out_port = self.config.rs_outport
        actions = [parser.OFPActionOutput(out_port)]
        self.add_flow(datapath, no_cookie, no_cookie_mask, ARP_BGP_TABLE, VNH_ARP_REQ_PRIORITY, match, actions)
        
        # add gratuitous ARP rules - makes sure that the participant specific gratuitous ARPs are 
        # only sent to the respective participant
        for participant_name in self.config.participants:
            participant = self.config.participants[participant_name]
            # check if participant specified inbound policies
            vmac_bitmask = vmac_best_path_match(2**self.config.best_path_size-1, self.config)
            vmac = vmac_best_path_match(participant_name, self.config)
            
            match = parser.OFPMatch(in_port=self.config.rs_outport, eth_dst=(vmac, vmac_bitmask))
            
            actions = [parser.OFPActionSetField(eth_dst=BROADCAST)]
            for port in participant.ports:
                out_port = port.id
                actions.append(parser.OFPActionOutput(out_port))
                                
            self.add_flow(datapath, no_cookie, no_cookie_mask, ARP_BGP_TABLE, GRATUITOUS_ARP_PRIORITY, match, actions)

        self.logger.debug("INIT: Set up BGP handling")
            
        # set up BGP handler
        match = parser.OFPMatch(eth_type=ether.ETH_TYPE_IP, ip_proto=inet.IPPROTO_TCP, tcp_src=BGP)
        instructions = [parser.OFPInstructionGotoTable(ARP_BGP_TABLE)]
        self.add_flow(datapath,
                      no_cookie, no_cookie_mask,
                      MAIN_TABLE,
                      ARP_BGP_PRIORITY,
                      match,
                      None,
                      instructions)
        
        match = parser.OFPMatch(eth_type=ether.ETH_TYPE_IP, ip_proto=inet.IPPROTO_TCP, tcp_dst=BGP)
        instructions = [parser.OFPInstructionGotoTable(ARP_BGP_TABLE)]
        self.add_flow(datapath,
                      no_cookie, no_cookie_mask,
                      MAIN_TABLE,
                      ARP_BGP_PRIORITY,
                      match,
                      None,
                      instructions)

        self.logger.debug("INIT: Participant Tagging")
        
        # set up participant tagging
        for participant_name in self.config.participants:
            participant = self.config.participants[participant_name]
            for port in participant.ports:
                match = parser.OFPMatch(in_port=port.id)
                instructions = [parser.OFPInstructionWriteMetadata(participant_name, self.metadata_mask),
                                parser.OFPInstructionGotoTable(OUTBOUND_TABLE)]
                
                self.add_flow(datapath,
                              no_cookie, no_cookie_mask,
                              MAIN_TABLE,
                              PARTICIPANT_TAGGING_PRIORITY,
                              match,
                              None,
                              instructions)

        self.logger.debug("INIT: Install default best routes")
                
        # outbound - flow rules - flow table 1
        # install default best routes
        for participant_name in self.config.participants:
            vmac_bitmask = vmac_best_path_match(2**self.config.best_path_size-1, self.config)
            vmac = vmac_best_path_match(participant_name, self.config)
            
            match = parser.OFPMatch(eth_dst=(vmac, vmac_bitmask))

            instructions = [parser.OFPInstructionWriteMetadata(participant_name, self.metadata_mask),
                            parser.OFPInstructionGotoTable(INBOUND_TABLE)]

            best_path_cookie = create_cookie(FABRIC_MANAGER_ID, BEST_PATH, 0)
            best_path_cookie_mask = create_cookie_mask(True, True, True)
            
            self.add_flow(datapath,
                          best_path_cookie, best_path_cookie_mask,
                          OUTBOUND_TABLE,
                          BEST_PATH_PRIORITY,
                          match,
                          None,
                          instructions)

        self.logger.debug("INIT: Install inbound flow rules")
            
        # inbound - flow rules - flow table 2
        for participant_name in self.config.participants:
            participant = self.config.participants[participant_name]
            # check if participant specified inbound policies
            if 'inbound' in participant.policies:
                policies = participant.policies["inbound"]
                i = 0
                for policy in policies:
                    i += 1
                    match_args = policy.match
                    match_args["metadata"] = participant_name
                    match = parser.OFPMatch(**match_args) 
                    
                    if policy.action["fwd"] < len(participant.ports):
                        dst_mac = participant.ports[policy.action["fwd"]].mac
                        out_port = participant.ports[policy.action["fwd"]].id
                    else:
                        dst_mac = participant.ports[0].mac
                        out_port = participant.ports[0].id
                                
                    actions = [parser.OFPActionSetField(eth_dst=dst_mac), 
                               parser.OFPActionOutput(out_port)]

                    inbound_policy_cookie = create_cookie(participant.id, INBOUND_POLICY, i)
                    inbound_policy_cookie_mask = create_cookie_mask(True, True, True)
                    
                    self.add_flow(datapath,
                                  inbound_policy_cookie, inbound_policy_cookie_mask,
                                  INBOUND_TABLE,
                                  INBOUND_POLICY_PRIORITY,
                                  match,
                                  actions)

            # default inbound policies
            match = parser.OFPMatch(metadata=participant_name)
                
            out_port = participant.ports[0].id
            dst_mac = participant.ports[0].mac
                
            actions = [parser.OFPActionSetField(eth_dst=dst_mac), 
                       parser.OFPActionOutput(out_port)]

            default_inbound_policy_cookie = create_cookie(FABRIC_MANAGER_ID, DEFAULT_INBOUND, 0)
            default_inbound_policy_cookie_mask = create_cookie_mask(True, True, True)
                
            self.add_flow(datapath,
                          default_inbound_policy_cookie, default_inbound_policy_cookie_mask,
                          INBOUND_TABLE,
                          DEFAULT_PRIORITY,
                          match,
                          actions)
    
    def supersets_changed(self, update):
        if not self.datapath:
            self.logger.error("No switch connected - Superset Update cannot be handled")
            return

        parser = self.datapath.ofproto_parser

        # Update Superset Structure
        if update["type"] == 'new':
            self.config.supersets.clear()

        for change in update['changes']:
            self.config.supersets[int(change["participant_id"])].append((int(change["superset"]),
                                                                        int(change["position"])))

        # If supersets changed, delete all rules and continue
        if update["type"] == "new":
            match = parser.OFPMatch()

            outbound_policy_cookie = create_cookie(0, OUTBOUND_POLICY, 0)
            outbound_policy_cookie_mask = create_cookie_mask(False, True, False)

            self.delete_flows(self.datapath, outbound_policy_cookie, outbound_policy_cookie_mask, OUTBOUND_TABLE, match)

        self.logger.debug("SUPERSETS_CHANGED: changes - %s", update)
            
        # add flow rules according to new supersets
        changes = update["changes"]
        for change in changes:
            if "participant_id" in change:
                for policy in self.config.dst_participant_2_policies[change["participant_id"]]:
                    src_participant_name = policy.participant_id
                    dst_participant_name = policy.action["fwd"]
                    nh_sdxes = self.config.participant_2_nh_sdx[dst_participant_name]
                    participant = self.config.participants[src_participant_name]
                    policy_id = participant.policies["outbound"].index(policy)
                    if self.correctness_module.check_policy(nh_sdx=nh_sdxes):
                        # vmac bitmask - superset id and bit at position of participant
                        superset_id = change["superset"]
                        participant_index = change["position"]

                        vmac_bitmask = vmac_participant_match(2**self.config.superset_id_size-1,
                                                              participant_index, self.config)
                        vmac = vmac_participant_match(superset_id, participant_index, self.config)

                        match_args = policy.match
                        match_args["metadata"] = src_participant_name
                        match_args["eth_dst"] = (vmac, vmac_bitmask)
                        match = parser.OFPMatch(**match_args)

                        instructions = [parser.OFPInstructionWriteMetadata(dst_participant_name, self.metadata_mask),
                                        parser.OFPInstructionGotoTable(INBOUND_TABLE)]

                        self.logger.debug("SUPERSETS_CHANGED: Install new flow rule according to outbound policy")
                        self.logger.debug("SUPERSETS_CHANGED: policy - %s", policy)

                        outbound_policy_cookie = create_cookie(src_participant_name, OUTBOUND_POLICY, policy_id)
                        outbound_policy_cookie_mask = create_cookie_mask(True, True, True)

                        self.add_flow(self.datapath,
                                      outbound_policy_cookie, outbound_policy_cookie_mask,
                                      OUTBOUND_TABLE,
                                      OUTBOUND_POLICY_PRIORITY,
                                      match,
                                      None,
                                      instructions)

                        participant.activated_policies.append(policy_id)

        return changes

    def check_policies(self, nh_sdx):
        if not self.datapath:
            self.logger.error("No switch connected - No policies can be installed")
            return

        parser = self.datapath.ofproto_parser

        for participant_id in self.config.nh_sdx_2_participant[nh_sdx]:
            for policy in self.config.dst_participant_2_policies[participant_id]:
                    src_participant_name = policy.participant_id
                    dst_participant_name = policy.action["fwd"]

                    participant = self.config.participants[src_participant_name]
                    policy_id = participant.policies.index(policy)

                    activated = policy_id in participant.activated_policies

                    if self.correctness_module.check_policy(nh_sdx=nh_sdx):
                        if not activated:
                            for superset in self.config.supersets[participant_id]:
                                vmac_bitmask = vmac_participant_match(2**self.config.superset_id_size-1,
                                                                      superset[1], self.config)
                                vmac = vmac_participant_match(superset[0], superset[1], self.config)

                                match_args = policy.match
                                match_args["metadata"] = src_participant_name
                                match_args["eth_dst"] = (vmac, vmac_bitmask)
                                match = parser.OFPMatch(**match_args)

                                instructions = [parser.OFPInstructionWriteMetadata(dst_participant_name,
                                                                                   self.metadata_mask),
                                                parser.OFPInstructionGotoTable(INBOUND_TABLE)]

                                outbound_policy_cookie = create_cookie(src_participant_name, OUTBOUND_POLICY, policy_id)
                                outbound_policy_cookie_mask = create_cookie_mask(True, True, True)

                                self.add_flow(self.datapath,
                                              outbound_policy_cookie, outbound_policy_cookie_mask,
                                              OUTBOUND_TABLE,
                                              OUTBOUND_POLICY_PRIORITY,
                                              match,
                                              None,
                                              instructions)

                            participant.activated_policies.append(policy_id)
                    elif activated:
                        match = parser.OFPMatch()

                        cookie = create_cookie(src_participant_name, OUTBOUND_POLICY, policy_id)
                        cookie_mask = create_cookie_mask(True, True, True)

                        self.delete_flows(self.datapath, cookie, cookie_mask, OUTBOUND_TABLE, match)

                        participant.activated_policies.remove(policy_id)

    @staticmethod
    def add_flow(datapath, cookie, cookie_mask, table, priority, match, actions, instructions=None, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        if actions:
            inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        else:
            inst = []

        if instructions is not None:
            inst.extend(instructions)
  
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath,
                                    cookie=cookie, cookie_mask=cookie_mask,
                                    table_id=table,
                                    buffer_id=buffer_id,
                                    priority=priority,
                                    match=match,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath,
                                    cookie=cookie, cookie_mask=cookie_mask,
                                    table_id=table,
                                    priority=priority,
                                    match=match,
                                    instructions=inst)
        datapath.send_msg(mod)

    @staticmethod
    def delete_flows(datapath, cookie, cookie_mask, table, match):
        parser = datapath.ofproto_parser

        mod = parser.OFPFlowMod(datapath=datapath,
                                cookie=cookie, cookie_mask=cookie_mask,
                                table_id=table,
                                command=ofproto_v1_3.OFPFC_DELETE,
                                out_group=ofproto_v1_3.OFPG_ANY,
                                out_port=ofproto_v1_3.OFPP_ANY,
                                match=match)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        # If you hit this you might want to increase
        # the "miss_send_length" of your switch
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes",
                              ev.msg.msg_len, ev.msg.total_len)
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        table_id = msg.table_id

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        dst = eth.dst
        src = eth.src
        
        if eth.ethertype == 2048:
            eth_type = "IPv4"
        elif eth.ethertype == 2054: 
            eth_type = "ARP"
        elif eth.ethertype == 34525: 
            eth_type = "IPv6"
        else:
            eth_type = "unknown"

        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})

        self.logger.debug("PACKET_IN: packet in dpid: %s, table: %s, eth_type: %s, src: %s, dst: %s, in_port: %s",
                          dpid, table_id, eth_type, src, dst, in_port)

        # learn a mac address to avoid FLOOD next time.
        self.mac_to_port[dpid][src] = in_port

        if table_id == ARP_BGP_TABLE:
            if dst in self.mac_to_port[dpid]:
                out_port = self.mac_to_port[dpid][dst]
            else:
                out_port = ofproto.OFPP_FLOOD

            actions = [parser.OFPActionOutput(out_port)]

            # install a flow to avoid packet_in next time
            if out_port != ofproto.OFPP_FLOOD:
                match = parser.OFPMatch(in_port=in_port, eth_dst=dst)

                no_cookie = create_cookie(FABRIC_MANAGER_ID, NO_COOKIE, 0)
                no_cookie_mask = create_cookie_mask(True, True, True)
                # verify if we have a valid buffer_id, if yes avoid to send both
                # flow_mod & packet_out
                if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                    self.add_flow(datapath, no_cookie, no_cookie_mask, table_id, DEFAULT_PRIORITY, match, actions, None, msg.buffer_id)
                    return
                else:
                    self.add_flow(datapath, no_cookie, no_cookie_mask, table_id, DEFAULT_PRIORITY, match, actions)
            data = None
            if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                data = msg.data

            out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                      in_port=in_port, actions=actions, data=data)
            datapath.send_msg(out)
