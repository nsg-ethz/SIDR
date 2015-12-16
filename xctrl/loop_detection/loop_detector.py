#!/usr/bin/env python
#  Author:
#  Rudiger Birkner (Networked Systems Group ETH Zurich)

import json
from random import randint
from time import time
from collections import defaultdict
from multiprocessing.connection import Listener, Client
from multiprocessing.queues import Queue
from Queue import Empty
from threading import Thread

from xctrl.lib import XCTRLModule, XCTRLEvent

from cib import CIB


class LoopDetector(XCTRLModule):
    def __init__(self, config, event_queue, debug, rib):
        super(LoopDetector, self).__init__(config, event_queue, debug)

        self.cib = CIB()
        self.rib = rib

        # mapping of participant and prefix to list of forbidden forward participants
        self.forbidden_paths = defaultdict(lambda: defaultdict(list))

        self.run = False
        self.listener = Listener((self.config.address, self.config.port), authkey=None)
        self.msg_in_queue = Queue()
        self.msg_out_queue = Queue()

    def start(self):
        msg_in_processor = Thread(target = self.process_correctness_message)
        msg_in_processor.daemon = True
        msg_in_processor.start()

        msg_out_processor = Thread(target = self.correctness_message_sender)
        msg_out_processor.daemon = True
        msg_out_processor.start()

        self.run = True
        while self.run:
            conn = self.listener.accept()
            tmp = conn.recv()
            conn.close()

            self.msg_in_queue.put(json.loads(tmp))

    def stop(self):
        self.run = False

    def activate_policy(self, ingress_participant, egress_participant):
        forbidden_prefixes = list()
        allowed_prefixes = list()

        prefixes = get_all_prefixes_advertised(ingress_participant, egress_participant)
        for prefix in prefixes:
            if egress_participant not in self.forbidden_paths[ingress_participant][prefix]:
                allowed_prefixes.append(prefix)

        if allowed_prefixes:
            ingress_participants = get_ingress_participants(prefix, egress_participant)
            ingress_participants.add(ingress_participant)

            receiver_participant = self.get_first_sdx_participant_on_path(prefix, egress_participant)
            update, old_cib_entry, new_cib_entry = self.cib.update_out(egress_participant, prefix, receiver_participant, ingress_participants)

            random_value = randint(0, self.config.loop_detector.max_random_value)
            timestamp = time()

            self.notify_nh_sdx(old_cib_entry, new_cib_entry, timestamp, random_value)
            return True
        return False

    def process_correctness_message(self):
        while self.run:
            try:
                msg = self.msg_in_queue.get(True, 1)

            except Empty:
                self.logger.debug("Empty Queue")
                continue

            ci_update, old_ci_entry, new_ci_entry = self.cib.update_in(msg["ingress_participant"],
                                                                       msg["prefix"],
                                                                       msg["sender_sdx"],
                                                                       msg["sdx_set"])

            if ci_update:
                cl_update, old_cl_entry, new_cl_entry = self.cib.update_loc(msg["ingress_participant"], msg["prefix"])

                if cl_update:
                    egress_participants = get_egress_participants(msg["ingress_participant"])
                    egress_participants.update(self.rib. get_best_path_participants(msg["ingress_participants"]))

                    for egress_participant in egress_participants:
                        self.update_forbidden_paths(msg["prefix"], None, msg["sdx_set"], msg["ingress_participant"], egress_participant)

                        ingress_participants = get_ingress_participants(msg["prefix"], egress_participant)
                        receiver_participant = self.get_first_sdx_participant_on_path(msg["prefix"], egress_participant)
                        co_update, old_co_entry, new_co_entry = self.cib.update_out(egress_participant, msg["prefix"], receiver_participant, ingress_participants)

                        if co_update:
                            random_value = randint(0, self.config.loop_detector.max_random_value)
                            timestamp = time()

                            self.notify_nh_sdx(old_co_entry, new_co_entry, timestamp, random_value)

    def rib_update(self, update):
        participants = get_all_participants_that_got_prefix_from(update["prefix"], update["participant"])

        for participant in participants:
            self.update_forbidden_paths(update["prefix"], update["AS Path"], None, participant, update["participant"])

        ingress_participants = self.get_ingress_participants(update["prefix"], update["participant"])
        receiver_participant = self.get_first_sdx_participant_on_path(update["prefix"], update["participant"])
        co_update, old_co_entry, new_co_entry = self.cib.update_out(update["participant"], update["prefix"], receiver_participant, ingress_participants)

        random_value = randint(0, self.config.loop_detector.max_random_value)
        timestamp = time()

        self.notify_nh_sdx(co_update, old_co_entry, new_co_entry, timestamp, random_value)

    def is_policy_active(selfs, ingress_participant, egress_participant):
        prefixes = self.rib get_all_prefixes_advertised_from_to(ingress_participant, egress_participant)

        for prefix in prefixes:
            if egress_participant not in self.forbidden_paths[ingress_participant][prefix]:
                return True
        return False

    def correctness_message_sender(self):
        while self.run:
            try:
                msg = self.msg_out_queue.get(True, 1)

            except Empty:
                self.logger.debug("Empty Queue")
                continue

            next_sdx = self.config.sdx_registry[msg[0]]
            conn = Client((next_sdx.address, next_sdx.port))
            conn.send(msg[1])
            conn.close()

    def notify_nh_sdx(self, update, old_cib_entry, new_cib_entry, timestamp, random_value):
        old_sdxes = self.config.loop_detector.asn_2_sdx[old_cib_entry["receiver_participant"]]
        new_sdxes = self.config.loop_detector.asn_2_sdx[new_cib_entry["receiver_participant"]]

        announce_msg = {"type": "announce",
                        "prefix": new_cib_entry["prefix"],
                        "sender_sdx": self.config.id,
                        "sdx_set": new_cib_entry["sdx_set"],
                        "ingress_participant": new_cib_entry["receiver_participant"],
                        "timestamp": timestamp,
                        "random_value": random_value
                        }

        withdraw_msg = {"type": "withdraw",
                        "prefix": new_cib_entry["prefix"],
                        "sender_sdx": self.config.id,
                        "ingress_participant": new_cib_entry["receiver_participant"],
                        "timestamp": timestamp,
                        "random_value": random_value
                        }

        if update:
            if old_cib_entry["receiver_participant"] != new_cib_entry["receiver_participant"]:
                for sdx in old_sdxes:
                    self.msg_out_queue.put((sdx, withdraw_msg))
                for sdx in new_sdxes:
                    self.msg_out_queue.put((sdx, announce_msg))
                    # send announce_msg
                    pass
            else:
                for sdx in old_sdxes:
                    if sdx not in new_sdxes:
                        self.msg_out_queue.put((sdx, withdraw_msg))
                        pass
                for sdx in new_sdxes:
                    self.msg_out_queue.put((sdx, announce_msg))
                    pass
        else:
            intersection = old_sdxes.intersection(new_sdxes)
            old = old_sdxes.difference(intersection)
            new = new_sdxes.difference(intersection)
            for sdx in old:
                self.msg_out_queue.put((sdx, withdraw_msg))
                pass
            for sdx in new:
                self.msg_out_queue.put((sdx, announce_msg))
                pass

    def update_forbidden_paths(self, prefix, as_path, sdx_set, ingress_participant, egress_participant):
        if not as_path:
            as_path = self.rib get_route(prefix, ingress_participant, egress_participant)["as_path"]
        as_path_sdxes = self.get_sdxes_on_path(as_path)
        if not sdx_set:
            sdx_set = self.cib get_cl_entry(prefix, ingress_participant)

        union = sdx_set.union(as_path_sdxes)
        if len(union) > 0:
            self.forbidden_paths[ingress_participant][prefix].append(egress_participant)
        elif egress_participant in self.forbidden_paths[ingress_participant][prefix]:
            self.forbidden_paths[ingress_participant][prefix].remove(egress_participant)

    def get_sdxes_on_path(self, as_path):
        sdxes = set()

        as2 = -1
        for as1 in as_path:
            if as2 != -1:
                as1_sdxes = self.config.loop_detector.asn_2_sdx[as1]
                as2_sdxes = self.config.loop_detector.asn_2_sdx[as2]

                union = as1_sdxes.union(as2_sdxes)
                if len(union) > 0:
                    sdxes = sdxes.union(union)
            as2 = as1
        return sdxes

    def get_first_sdx_participant_on_path(self, prefix):
        as_path = self.rib get_route(prefix, ingress_participant, egress_participant)["as_path"]
        for as1 in as_path:
            as1_sdxes = self.config.loop_detector.asn_2_sdx[as1]
            if len(as1_sdxes) > 0:
                return as1
            else:
                return None


class LoopDetectorConfig(object):
    def __init__(self, sdx_2_asn, asn_2_sdx, max_random_value):
        self.sdx_2_asn = sdx_2_asn
        self.asn_2_sdx = asn_2_sdx
        self.max_random_value = max_random_value