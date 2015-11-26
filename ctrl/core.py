#  Author:
#  Rudiger Birkner (Networked Systems Group ETH Zurich)

# RouteServer-specific imports
import json
import os

from netaddr import *
from collections import defaultdict

from ryu.ofproto import ether
from ryu.ofproto import inet


# Extended Route Server Object

class SDX(object):
    def __init__(self, base_path, config_file):
        self.participants = defaultdict(Participant)
        self.dst_participant_2_policies = defaultdict(list)
        
        self.rs_outport = 0
        self.rs_ip = ""
        self.base_url = ""
        self.VNHs = IPNetwork('172.0.1.1/24')
        self.superset_url = '/asdx/supersets'
        self.policy_file = 'sdx_policies.cfg'

        # VMAC
        self.superset_id_size = 0
        self.max_superset_size = 0
        self.best_path_size = 0
        self.VMAC_size = 0

        # Mapping of participant id to list of all superset indexes and positions within the superset
        self.supersets = defaultdict(list)

        # Correctness
        self.id = 0
        self.correctness_url = '/asdx/correctness'
        self.participant_2_nh_sdx = defaultdict(list)
        self.nh_sdx_2_participant = defaultdict(list)
        self.correctness_mode = 0
        self.nh_sdxes = defaultdict(NextHopSDX)

        self.parse_config(base_path, config_file)

    def parse_config(self, base_path, config_file):
        # loading config file
        config = json.load(open(config_file, 'r'))

        if "SDX ID" in config:
            self.id = int(config["SDX ID"])

        if "Base URL" in config:
            self.base_url = config["Base URL"]

        if "Correctness Mode" in config:
            self.correctness_mode = config["Correctness Mode"]

        if "SDX Registry" in config:
            file_path = os.path.join(base_path, "sdx_config", config["SDX Registry"])
            next_hop_sdxes = json.load(open(file_path, 'r'))
            for key, value in next_hop_sdxes.iteritems():
                key = int(key)
                self.nh_sdxes[key] = NextHopSDX(key, value["ip"], value["port"])

        if "Correctness URL" in config:
            self.correctness_url = config["Correctness URL"]

        # loading policies
        if "Policy File" in config:
            self.policy_file = config["Policy File"]
        participant_policy_files = json.load(open(os.path.join(base_path, "sdx_config", self.policy_file), 'r'))
        
        if "Route Server" in config:
            if "Outport" in config["Route Server"]:
                self.rs_outport = config["Route Server"]["Outport"]
            if "IP" in config["Route Server"]:
                self.rs_ip = config["Route Server"]["IP"]

        if "VNHs" in config:
            self.VNHs = IPNetwork(config["VNHs"])

        if "Superset URL" in config:
            self.superset_url = config["Superset URL"]
    
        if "VMAC Computation" in config:
            if "Superset ID Size" in config["VMAC Computation"]:
                self.superset_id_size = config["VMAC Computation"]["Superset ID Size"]
            if "Max Superset Size" in config["VMAC Computation"]:
                self.max_superset_size = config["VMAC Computation"]["Max Superset Size"]
            if "Best Path Size" in config["VMAC Computation"]:
                self.best_path_size = config["VMAC Computation"]["Best Path Size"]
            if "VMAC Size" in config["VMAC Computation"]:
                self.VMAC_size = config["VMAC Computation"]["VMAC Size"]

        if "Participants" in config:
            for participant_name in config["Participants"]:
                participant_id = int(participant_name)
                participant = config["Participants"][participant_name]
            
                file_path = os.path.join(base_path, "participant_policies", participant_policy_files[participant_name])

                participant_policies = json.load(open(file_path, 'r'))

                validated_policies = defaultdict(list)

                for policy_type, policies in participant_policies.iteritems():
                    for policy in policies:
                        if policy_type == "outbound":
                            pol = Policy(participant_id, policy_type, policy)
                            if "fwd" in policy["action"]:
                                self.dst_participant_2_policies[policy["action"]["fwd"]].append(pol)

                        validated_policies[policy_type].append(pol)
                
                # adding ports and mappings
                ports = [Port(participant["Ports"][i]['Id'],
                              participant["Ports"][i]['MAC'],
                              participant["Ports"][i]['IP'])
                         for i in range(0, len(participant["Ports"]))]
                          
                self.participants[int(participant_name)] = Participant(int(participant_name),
                                                                       ports, validated_policies)

                self.participant_2_nh_sdx[participant_id] = participant["Next Hop SDX"]

        for participant, nh_sdxes in self.participant_2_nh_sdx.iteritems():
            for nh_sdx in nh_sdxes:
                if participant not in self.nh_sdx_2_participant[nh_sdx]:
                    self.nh_sdx_2_participant[nh_sdx].append(participant)


class Participant(object):
    def __init__(self, name, ports, policies):
        self.name = name
        self.ports = ports
        self.policies = policies
        self.activated_policies = list()


class Port(object):
    def __init__(self, port_id, mac, ip):
        self.id = port_id
        self.mac = mac
        self.ip = ip


class Policy(object):
    def __init__(self, participant, policy_type, policy):
        self.participant_id = int(participant)
        self.type = policy_type
        self.match = self.validate_match(policy["match"])
        self.action = self.validate_action(policy["action"])

    @staticmethod
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

    @staticmethod
    def validate_action(actions):
        validated_actions = {}

        for action, value in actions.iteritems():
            if action == "fwd":
                validated_actions[action] = value

        return validated_actions


class NextHopSDX(object):
    def __init__(self, sdx_id, ip, port):
        self.id = sdx_id
        self.ip = ip
        self.port = port
