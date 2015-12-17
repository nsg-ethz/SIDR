#  Author:
#  Arpit Gupta (Princeton)

import json
import time

from multiprocessing.connection import Client

POLICY_FNAME = "policy_in.log"
POLICY_SOCKET = ("localhost", 5551)
LOG = True

def parse_policy_log(fname):
    out = {}
    with open(fname,'r') as f:
        policies = json.load(f)
        for policy in policies:
            k = policy['time']
            policy.pop('time', None)
            if k not in out:
                out[k] = []
            out[k].append(policy)
    return out


def send_policy(time_2_policy):
    max_time = max(time_2_policy.keys())
    if LOG: print "This script will run for ", max_time, " seconds"
    for ind in range(1,max_time+1):
        if ind in time_2_policy:
            if LOG: print "Sending policy items at time ", ind
            policy_socket = Client(POLICY_SOCKET)
            data = {ind:time_2_policy[ind]}
            policy_socket.send(json.dumps(data))
            recv = policy_socket.recv()
            if LOG: print "response received: ", recv
            policy_socket.close()
    time.sleep(1)


''' main '''
if __name__ == '__main__':
    time_2_policy = parse_policy_log(POLICY_FNAME)
    print time_2_policy.keys()
    send_policy(time_2_policy)
