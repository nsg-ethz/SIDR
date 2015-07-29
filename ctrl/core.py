#  Author:
#  Rudiger Birkner (Networked Systems Group ETH Zurich)

## RouteServer-specific imports
import json
import os

from netaddr import *
from collections import defaultdict

from ryu.ofproto import ether
from ryu.ofproto import inet

###
### Extended Route Server Object
###

class SDX():
    def __init__(self):
        self.participants = {}
        self.dst_participant_2_policies = defaultdict(list)
        
        self.rs_outport = 5
        self.superset_id_size = 6
        self.max_superset_size = 30
        self.best_path_size = 12
        self.VMAC_size = 48
        self.VNHs = IPNetwork('172.0.1.1/24')
        self.rest_api_url = '/asdx/supersets'
        
###
### Extended Route Server primary functions
###

def parse_config(base_path, config_file, policy_file):
    
    # loading config file
    config = json.load(open(config_file, 'r'))
    
    # loading policies
    policies = json.load(open(policy_file, 'r'))
    
    # create SDX object
    sdx = SDX()

    if ("Route Server" in config):
        if ("Outport" in config["Route Server"]):
            sdx.rs_outport = config["Route Server"]["Outport"]
        if ("IP" in config["Route Server"]):
            sdx.rs_ip = config["Route Server"]["IP"]

    if ("VMAC Computation" in config):
        if ("Superset ID Size" in config["VMAC Computation"]):
            sdx.superset_id_size = config["VMAC Computation"]["Superset ID Size"]
        if ("Max Superset Size" in config["VMAC Computation"]):
            sdx.max_superset_size = config["VMAC Computation"]["Max Superset Size"]
        if ("Best Path Size" in config["VMAC Computation"]):
            sdx.best_path_size = config["VMAC Computation"]["Best Path Size"]
        if ("VMAC Size" in config["VMAC Computation"]):
            sdx.VMAC_size = config["VMAC Computation"]["VMAC Size"]

    if ("VNHs" in config):
        sdx.VNHs = IPNetwork(config["VNHs"])

    if ("REST API URL" in config):
        if ("Short" in config["REST API URL"]):
            sdx.rest_api_url = config["REST API URL"]["Short"]

    if ("Participants" in config):
        for participant_name in config["Participants"]:        
            participant = config["Participants"][participant_name]
        
            file_path = os.path.join(base_path, "participant_policies", policies[participant_name])
            participant_policies = validate_policies(json.load(open(file_path, 'r')))
        
            if ("outbound" in participant_policies):
                for policy in participant_policies["outbound"]:
                
                    policy["in_port"] = int(participant_name)
                    if ("fwd" in policy["action"]):
                        sdx.dst_participant_2_policies[policy["action"]["fwd"]].append(policy)
            
            # adding ports and mappings
            ports = [{"ID": participant["Ports"][i]['Id'],
                      "MAC": participant["Ports"][i]['MAC'],
                      "IP": participant["Ports"][i]['IP']} 
                      for i in range(0, len(participant["Ports"]))]
                      
            sdx.participants[int(participant_name)] = {"policies": participant_policies, "ports": ports}

    return sdx
    
def validate_policies(all_policies):
    validated_policies = {}
    
    for target, policies in all_policies.iteritems():
        temp_policies = []    
        for policy in policies:
            temp_policy = {}
            temp_policy["match"] = validate_match(policy["match"])
            temp_policy["action"] = validate_action(policy["action"])
            if temp_policy["match"] and temp_policy["action"]:
                temp_policies.append(temp_policy)
        validated_policies[target] = temp_policies
        
    return validated_policies
    
def validate_match(matches):
    validated_matches = {}
    
    for match, value in matches.iteritems():
        if match == "ipv4_src":
            validated_matches[match] = value
            if "eth_type" not in validated_matches:
                validated_matches["eth_type"] = ether.ETH_TYPE_IP
        elif match == "ipv4_dst":
            validated_matches[match] = value
            if "eth_type" not in validated_matches:
                validated_matches["eth_type"] = ether.ETH_TYPE_IP
        elif match == "tcp_src":
            validated_matches[match] = value
            if "eth_type" not in validated_matches:
                validated_matches["eth_type"] = ether.ETH_TYPE_IP
            if "ip_proto" not in validated_matches:
                validated_matches["ip_proto"] = inet.IPPROTO_TCP
        elif match == "tcp_dst":
            validated_matches[match] = value
            if "eth_type" not in validated_matches:
                validated_matches["eth_type"] = ether.ETH_TYPE_IP
            if "ip_proto" not in validated_matches:
                validated_matches["ip_proto"] = inet.IPPROTO_TCP
        elif match == "udp_src":
            validated_matches[match] = value
            if "eth_type" not in validated_matches:
                validated_matches["eth_type"] = ether.ETH_TYPE_IP
            if "ip_proto" not in validated_matches:
                validated_matches["ip_proto"] = inet.IPPROTO_UDP
        elif match == "udp_dst":
            validated_matches[match] = value
            if "eth_type" not in validated_matches:
                validated_matches["eth_type"] = ether.ETH_TYPE_IP
            if "ip_proto" not in validated_matches:
                validated_matches["ip_proto"] = inet.IPPROTO_UDP
            
    return validated_matches
        
def validate_action(actions):
    validated_actions = {}
    
    for action, value in actions.iteritems():
        if action == "fwd":
            validated_actions[action] = value
            
    return validated_actions   
    
    
    
    
