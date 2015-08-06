#  Author:
#  Rudiger Birkner (Networked Systems Group ETH Zurich)

from netaddr import *

from ryu.ofproto import ether
from ryu.ofproto import inet

#                
### VMAC BUILDER
#

def vmac_participant_match(superset_id, participant_index, sdx):
    
    # add superset identifier
    vmac_bitstring = '{num:0{width}b}'.format(num=int(superset_id), width=(sdx.superset_id_size))
        
    # set bit of participant
    vmac_bitstring += '{num:0{width}b}'.format(num=1, width=(participant_index+1))
    vmac_bitstring += '{num:0{width}b}'.format(num=0, width=(sdx.VMAC_size-len(vmac_bitstring)))

    # convert bitstring to hexstring and then to a mac address
    vmac_addr = '{num:0{width}x}'.format(num=int(vmac_bitstring,2), width=sdx.VMAC_size/4)
    vmac_addr = ':'.join([vmac_addr[i]+vmac_addr[i+1] for i in range(0,sdx.VMAC_size/4,2)])
        
    return vmac_addr

def vmac_best_path_match(participant_name, sdx):
        
    # add participant identifier
    vmac_bitstring = '{num:0{width}b}'.format(num=participant_name, width=(sdx.VMAC_size))

    # convert bitstring to hexstring and then to a mac address
    vmac_addr = '{num:0{width}x}'.format(num=int(vmac_bitstring,2), width=sdx.VMAC_size/4)
    vmac_addr = ':'.join([vmac_addr[i]+vmac_addr[i+1] for i in range(0,sdx.VMAC_size/4,2)])
            
    return vmac_addr
   
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

