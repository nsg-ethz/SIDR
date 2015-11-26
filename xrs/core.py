#  Author:
#  Rudiger Birkner (Networked Systems Group ETH Zurich)

## RouteServer-specific imports
import os
import json
from netaddr import *
from peer import peer as Peer

###
### Extended Route Server Object
###

class XRS():
    def __init__(self):
        self.server = None
        self.participants = {}
        self.port_2_participant = {}
        self.participant_2_port = {}
        self.portip_2_participant = {}
        self.participant_2_portip = {}
        self.portmac_2_participant = {}
        self.participant_2_portmac = {}
        self.asn_2_participant = {}
        self.participant_2_asn = {}
        self.supersets = []

        self.num_VNHs_in_use = 0
        
        self.VNH_2_prefix = {}
        self.prefix_2_VNH = {}
        
        # put it in external config file
        self.connection_port = 6000
        self.connection_key = 'xrs'

        self.superset_threshold = 10
        
        self.max_superset_size = 30
        self.best_path_size = 12

        self.bgp_advertisements = "Best Path"
        
        self.VMAC_size = 48

        self.base_url = 'http://localhost:8080'
        self.rest_api_url = 'http://localhost:8080/asdx/supersets'
        
        self.VNHs = IPNetwork('172.0.1.1/24')

        self.interface = "exabgp-eth0"

        self.policy_file = "sdx_policies.cfg"
        
###
### Extended Route Server primary functions
###

def parse_config(base_path, config_file):
    
    # loading config file
    config = json.load(open(config_file, 'r'))
    
    ''' 
        Create RouteServer environment ...
    '''
    
    # create XRS object
    xrs = XRS()

    if ("Route Server" in config):
        if ("Connection Port" in config["Route Server"]):
            xrs.connection_port = config["Route Server"]["Connection Port"]
        if ("Connection Key" in config["Route Server"]):
            xrs.connection_key = config["Route Server"]["Connection Key"]
        if ("Interface" in config["Route Server"]):
            xrs.interface = config["Route Server"]["Interface"]
        if ("BGP Advertisements" in config["Route Server"]):
            xrs.bgp_advertisements = config["Route Server"]["BGP Advertisements"]
            if (xrs.bgp_advertisements == "Policy Based AS Path" or xrs.bgp_advertisements == "Blocking Policy Based AS Path"):
                if ("Policy File" in config):
                    xrs.policy_file = config["Policy File"]
                policies = json.load(open(os.path.join(base_path, "sdx_config", xrs.policy_file), 'r'))
    if ("VMAC Computation" in config):
        if ("Superset ID Size" in config["VMAC Computation"]):
            xrs.superset_id_size = config["VMAC Computation"]["Superset ID Size"]
        if ("Max Superset Size" in config["VMAC Computation"]):
            xrs.max_superset_size = config["VMAC Computation"]["Max Superset Size"]
        if ("Best Path Size" in config["VMAC Computation"]):
            xrs.best_path_size = config["VMAC Computation"]["Best Path Size"]
        if ("VMAC Size" in config["VMAC Computation"]):
            xrs.VMAC_size = config["VMAC Computation"]["VMAC Size"]
        if ("Superset Threshold" in config["VMAC Computation"]):
            xrs.superset_threshold = config["VMAC Computation"]["Superset Threshold"]

    if ("VNHs" in config):
        xrs.VNHs = IPNetwork(config["VNHs"])


    if "Base URL" in config:
        xrs.base_url = config["Base URL"]

    if ("Superset URL" in config):
        xrs.rest_api_url = xrs.base_url + "" + config["Superset URL"]

    if ("Participants" in config):    
        peers_out = {}
        for participant_name in config["Participants"]:
            participant = config["Participants"][participant_name]
        
            for peer in participant["Peers"]:
                if (peer not in peers_out):
                    peers_out[peer] = []
                peers_out[peer].append(int(participant_name))
    
        for participant_name in config["Participants"]:
            participant = config["Participants"][participant_name]
        
            # adding asn and mappings
            asn = participant["ASN"]
            xrs.asn_2_participant[participant["ASN"]] = int(participant_name)
            xrs.participant_2_asn[int(participant_name)] = participant["ASN"]
        
            # adding ports and mappings
            ports = [{"ID": participant["Ports"][i]['Id'],
                         "MAC": participant["Ports"][i]['MAC'],
                     "IP": participant["Ports"][i]['IP']} 
                     for i in range(0, len(participant["Ports"]))]
          
            xrs.participant_2_port[int(participant_name)] = []
            xrs.participant_2_portip[int(participant_name)] = []
            xrs.participant_2_portmac[int(participant_name)] = []
        
            for i in range(0, len(participant["Ports"])):
                xrs.port_2_participant[participant["Ports"][i]['Id']] = int(participant_name)
                xrs.portip_2_participant[participant["Ports"][i]['IP']] = int(participant_name)
                xrs.portmac_2_participant[participant["Ports"][i]['MAC']] = int(participant_name)
                xrs.participant_2_port[int(participant_name)].append(participant["Ports"][i]['Id'])    
                xrs.participant_2_portip[int(participant_name)].append(participant["Ports"][i]['IP'])
                xrs.participant_2_portmac[int(participant_name)].append(participant["Ports"][i]['MAC'])
        
            peers_in = participant["Peers"]
            
            fwd_peers = []
            if xrs.bgp_advertisements == "Policy Based AS Path" or xrs.bgp_advertisements == "Blocking Policy Based AS Path":
                file_path = os.path.join(base_path, "participant_policies", policies[participant_name])
                participant_policies = json.load(open(file_path, 'r'))
        
                if ("outbound" in participant_policies):
                    for policy in participant_policies["outbound"]:
                        if ("fwd" in policy["action"]):
                            if (policy["action"]["fwd"] not in fwd_peers):
                                fwd_peers.append(policy["action"]["fwd"])
 
            # create peer and add it to the route server environment
            xrs.participants[int(participant_name)] = Peer(asn, ports, peers_in, peers_out[int(participant_name)], fwd_peers)

    return xrs
