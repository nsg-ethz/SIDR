#  Author:
#  Arpit Gupta (Princeton)

import json
import time
import os
import argparse

from multiprocessing.connection import Client

LOG = True


def parse_policy_log(fname):
    out = {}
    with open(fname, 'r') as f:
        policies = json.load(f)
        for policy in policies:
            k = policy['time']
            policy.pop('time', None)
            if k not in out:
                out[k] = []
            out[k].append(policy)
    return out


def send_policy(time_2_policy, address, port):
    if time_2_policy:
        max_time = max(time_2_policy.keys())
        if LOG:
            print "This script will run for ", max_time, " seconds"
        for ind in range(1, max_time+1):
            if ind in time_2_policy:
                if LOG:
                    print "Sending policy items at time ", ind
                policy_socket = Client((address, port))
                data = time_2_policy[ind]
                print str(data)
                policy_socket.send(json.dumps(data))
                recv = policy_socket.recv()
                if LOG:
                    print "response received: ", recv
                policy_socket.close()
            time.sleep(1)


def parse_config(sdx_id):
    config = json.load(open(config_file, 'r'))

    tmp_address = None
    tmp_port = None

    if "SDXes" in config:
        sdx = config["SDXes"][sdx_id]
        if "Policy Handler" in sdx:
            if "Address" in sdx["Policy Handler"]:
                tmp_address = sdx["Policy Handler"]["Address"]
            if "Port" in sdx["Policy Handler"]:
                tmp_port = sdx["Policy Handler"]["Port"]
    return tmp_address, tmp_port


''' main '''
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('dir', help='the directory of the example')
    parser.add_argument('sdxid', help='SDX identifier')
    args = parser.parse_args()

    base_path = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "examples",
                                             args.dir,))
    config_file = os.path.join(base_path, "config", "sdx_global.cfg")
    policy_file = os.path.join(base_path, "policies", str(args.sdxid) + ".log")

    address, port = parse_config(args.sdxid)
    time_2_policy = parse_policy_log(policy_file)
    print time_2_policy.keys()
    send_policy(time_2_policy, address, port)
