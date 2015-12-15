#  Author:
#  Rudiger Birkner (Networked Systems Group ETH Zurich)

## RouteServer-specific imports
import json
import os

from netaddr import *
from collections import defaultdict

from lib import validate_policies, validate_match, validate_action

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
        self.policy_file = 'sdx_policies.cfg'
        
###
### Extended Route Server primary functions
###

def parse_config(base_path, config_file):
    
    # create SDX object
    sdx = SDX()

    # loading config file
    config = json.load(open(config_file, 'r'))
    
    # loading policies
    if ("Policy File" in config):
        sdx.policy_file = config["Policy File"]
    policies = json.load(open(os.path.join(base_path, "sdx_config", sdx.policy_file), 'r'))
    
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
