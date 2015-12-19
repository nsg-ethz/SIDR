#!/usr/bin/env python
#  Author:
#  Muhammad Shahbaz (muhammad.shahbaz@gatech.edu)

import os
import time
import json
from threading import Thread
from multiprocessing import Queue
from collections import defaultdict


class Server(object):
    def __init__(self, base_path, id):
        self.sender_queue = Queue()
        self.receiver_queue = Queue()

        self.base_path = base_path
        self.file = os.path.join(base_path, "bgp", str(id) + ".log")

        self.routes = self.parse_route_log()
        
    def start(self):
        receiver = Thread(target=_receiver, args=(self.routes, self.receiver_queue))
        receiver.start()

    def parse_route_log(self):
        # file format
        # time|sender ip|sender asn| receiver ip|receiver asn|as path|prefix

        routes = defaultdict(list)
        with open(self.file, 'r') as f:
            for line in f:
                items = line.replace("\n", "").split("|")
                k = int(items[0])
                msg = dict()
                msg["exabgp"] = "3.4.8"
                msg["type"] = "update"
                msg["neighbor"] = dict()
                msg["neighbor"]["ip"] = items[2]
                msg["neighbor"]["address"] = dict()
                msg["neighbor"]["address"]["local"] = items[4]
                msg["neighbor"]["address"]["peer"] = items[2]
                msg["neighbor"]["asn"] = dict()
                msg["neighbor"]["asn"]["local"] = items[5]
                msg["neighbor"]["asn"]["peer"] = items[3]
                msg["neighbor"]["message"] = dict()
                msg["neighbor"]["message"]["update"] = dict()
                if items[1] == "announce":
                    msg["neighbor"]["message"]["update"]["attribute"] = dict()
                    msg["neighbor"]["message"]["update"]["attribute"]["origin"] = "igp"
                    msg["neighbor"]["message"]["update"]["attribute"]["as-path"] = [int(v) for v in items[6].split(",")]
                    msg["neighbor"]["message"]["update"]["attribute"]["confederation-path"] = []
                    msg["neighbor"]["message"]["update"]["attribute"]["med"] = 0
                    msg["neighbor"]["message"]["update"]["announce"] = dict()
                    msg["neighbor"]["message"]["update"]["announce"]["ipv4 unicast"] = dict()
                    msg["neighbor"]["message"]["update"]["announce"]["ipv4 unicast"][items[2]] = dict()
                    msg["neighbor"]["message"]["update"]["announce"]["ipv4 unicast"][items[2]][items[7]] = dict()
                else:
                    msg["neighbor"]["message"]["update"]["withdraw"] = dict()
                    msg["neighbor"]["message"]["update"]["withdraw"]["ipv4 unicast"] = dict()
                    msg["neighbor"]["message"]["update"]["withdraw"]["ipv4 unicast"][items[2]] = dict()
                    msg["neighbor"]["message"]["update"]["withdraw"]["ipv4 unicast"][items[2]][items[7]] = dict()
                routes[k].append(msg)
        return routes


def _receiver(time_2_policy, queue):
    max_time = max(time_2_policy.keys())
    for ind in range(1, max_time+1):
        if ind in time_2_policy:
            for data in time_2_policy[ind]:
                queue.put(json.dumps(data))
        time.sleep(1)

