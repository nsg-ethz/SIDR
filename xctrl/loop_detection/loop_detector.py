#!/usr/bin/env python
#  Author:
#  Rudiger Birkner (Networked Systems Group ETH Zurich)

import json

from random import randint
from time import time, clock
from collections import defaultdict
from multiprocessing.connection import Listener, Client
from multiprocessing.queues import Queue
from Queue import Empty
from threading import Thread

from lib import XCTRLModule, XCTRLEvent

from cib import CIB

LOG = False


class LoopDetector(XCTRLModule):
    def __init__(self, config, event_queue, debug, rib, policy_handler, test, no_notifications, rib_timing, notification_timing):
        super(LoopDetector, self).__init__(config, event_queue, debug)

        self.config = config

        self.cib = CIB(self.config.id)
        self.rib = rib
        self.policy_handler = policy_handler

        # mapping of participant and prefix to list of forbidden forward participants
        self.forbidden_paths = defaultdict(lambda: defaultdict(list))

        self.run = False
        self.listener = Listener((self.config.sdx.address, self.config.loop_detector.port), authkey=None)
        self.msg_in_queue = Queue(1000)
        self.msg_out_queue = Queue(1000)

        self.no_notifications = no_notifications

        self.rib_timing = rib_timing
        if self.rib_timing:
            self.rib_timing_file = 'rib_timing_' + str(int(time())) + '.log'

        self.notification_timing = notification_timing
        if self.notification_timing:
            self.notification_timing_file = 'notification_timing_' + str(int(time())) + '.log'

    def start(self):
        self.run = True

        msg_in_processor = Thread(target=self.process_correctness_message)
        msg_in_processor.daemon = True
        msg_in_processor.start()

        msg_out_processor = Thread(target=self.correctness_message_sender)
        msg_out_processor.daemon = True
        msg_out_processor.start()

        while self.run:
            conn = self.listener.accept()
            tmp = conn.recv()
            conn.close()

            if tmp == 'DONE':
                print 'DONE RECEIVED ' + str(time())
                self.msg_in_queue.put(tmp)
                continue

            self.msg_in_queue.put(json.loads(tmp))

    def stop(self):
        self.run = False

    def activate_policy(self, ingress_participant, egress_participant):
        """
        check whether a policy from ingress_participant to egress_participant can safely be installed. The CIB
        is accordingly updated and all other SDXes are notified.
        :param ingress_participant: int
        :param egress_participant: int
        :return:True if safe to install the policy
        """

        self.logger.debug("Received Activation Request from " + str(ingress_participant) +
                          " to " + str(egress_participant))

        # get all participants that use egress_participant in a policy
        # NOTE: We make the assumption that if egress_participant decides to advertise to another participant, it
        # advertises all of its prefixes and not only selection
        policy_in_participants = self.policy_handler.get_ingress_participants(egress_participant)

        # Check for each prefix separately whether the policy is safe
        active_policies = True
        allowed_prefixes = False
        prefixes = self.rib.get_all_prefixes_advertised(egress_participant, ingress_participant)

        for prefix in prefixes:
            if egress_participant not in self.forbidden_paths[ingress_participant][prefix]:
                allowed_prefixes = True

                # remove all participants from in_participants that have a direct route to prefix
                best_path_in_participants = self.rib.get_all_participants_using_best_path(prefix, egress_participant)
                in_participants = policy_in_participants.union(best_path_in_participants)
                filter_participants = self.rib.get_all_participants_advertising(prefix)
                ingress_participants = in_participants.difference(filter_participants)

                ingress_participants.add(ingress_participant)
                receiver_participant = self.get_first_sdx_participant_on_path(prefix, egress_participant)

                if receiver_participant:
                    update, old_cib_entry, new_cib_entry = self.cib.update_out(egress_participant,
                                                                               prefix,
                                                                               receiver_participant,
                                                                               ingress_participants,
                                                                               self.config.id,
                                                                               active_policies)

                    random_value = randint(0, self.config.loop_detector.max_random_value)
                    timestamp = time()

                    self.notify_nh_sdx(update, old_cib_entry, new_cib_entry, timestamp, random_value)

        return allowed_prefixes

    def process_correctness_message(self):
        """
        processes a correctness message that has been received from another SDX. The CIB is updated accordingly
        and other SDXes are notified if necessary
        :return:None
        """

        while self.run:
            try:
                messages = self.msg_in_queue.get(True, 1)

            except Empty:
                # self.logger.debug("Empty Queue")
                continue

            if messages == 'DONE':
                print 'DONE Processed ' + str(time())
                continue

            if not isinstance(messages, list):
                messages = [messages]
            else:
                messages = messages

            for msg in messages:

                self.logger.debug("Received Correctness Message from " + str(msg["sender_sdx"]) +
                                  " concerning " + str(msg["prefix"]))

                if self.notification_timing:
                    start_time = clock()

                changes = list()
                ingress_participant = self.config.asn_2_participant[msg["ingress_participant"]]

                ci_update, old_ci_entry, new_ci_entry = self.cib.update_in(msg["type"],
                                                                           ingress_participant,
                                                                           msg["prefix"],
                                                                           msg["sender_sdx"],
                                                                           msg["sdx_set"])

                if ci_update:
                    cl_update, old_cl_entry, new_cl_entry = self.cib.update_loc(ingress_participant, msg["prefix"])

                    if cl_update:
                        egress_participants = self.policy_handler.get_egress_participants(ingress_participant)
                        best_participants = self.rib.get_best_path_participants(ingress_participant)
                        egress_participants = egress_participants.union(best_participants)
                        filter_participants = self.rib.get_all_participants_advertising(msg["prefix"])
                        egress_participants = egress_participants.intersection(filter_participants)

                        for filter_participant in filter_participants:
                            changes.append(self.update_forbidden_paths(msg["prefix"],
                                                                       None,
                                                                       set(msg["sdx_set"]),
                                                                       ingress_participant,
                                                                       filter_participant))

                        for egress_participant in egress_participants:
                            ingress_participants = self.policy_handler.get_ingress_participants(egress_participant)
                            active_policies = True if ingress_participants else False
                            ingress_participants.update(self.rib.get_all_participants_using_best_path(msg["prefix"],
                                                                                                      egress_participant))
                            filter_participants_2 = self.rib.get_all_receiver_participants(msg["prefix"],
                                                                                           egress_participant)
                            ingress_participants = ingress_participants.intersection(filter_participants_2)
                            ingress_participants = ingress_participants.difference(filter_participants)

                            receiver_participant = self.get_first_sdx_participant_on_path(msg["prefix"], egress_participant)

                            if receiver_participant:
                                co_update, old_co_entry, new_co_entry = self.cib.update_out(egress_participant,
                                                                                            msg["prefix"],
                                                                                            receiver_participant,
                                                                                            ingress_participants,
                                                                                            self.config.id,
                                                                                            active_policies)

                                random_value = randint(0, self.config.loop_detector.max_random_value)
                                timestamp = time()

                                self.notify_nh_sdx(co_update, old_co_entry, new_co_entry, timestamp, random_value)

                        if changes:
                            event = XCTRLEvent("LoopDetector", "FORBIDDEN PATHS CHANGE", changes)
                            self.event_queue.put(event)

                if self.notification_timing:
                    end_time = clock()
                    with open(self.notification_timing_file, "a") as outfile:
                        outfile.write(str(end_time - start_time) + '\n')

    def rib_update(self, updates):
        """
        Updates the CIB and notifies all neighbor SDXes after a change in the RIB
        :param updates:
        :return:None
        """

        self.logger.debug("RIB Update")

        if self.rib_timing:
            start_time = clock()

        for tmp_update in updates:
            if 'announce' in tmp_update:
                update = tmp_update["announce"]
            elif 'withdraw' in tmp_update:
                update = tmp_update["withdraw"]
                update["as_path"] = None
            else:
                self.logger.debug("Got invalid update from route server")
                return

            advertising_participant = self.config.portip_2_participant[update["next_hop"]]
            participants = self.config.participants[advertising_participant].peers_in

            for participant in participants:
                self.update_forbidden_paths(update["prefix"],
                                            update["as_path"],
                                            None,
                                            participant,
                                            advertising_participant)

            if 'announce' in tmp_update:
                ingress_participants = self.policy_handler.get_ingress_participants(advertising_participant)
                active_policies = True if ingress_participants else False
                ingress_participants.update(self.rib.get_all_participants_using_best_path(update["prefix"],
                                                                                          advertising_participant))

                filter_participants = self.rib.get_all_receiver_participants(update["prefix"], advertising_participant)

                ingress_participants = ingress_participants.intersection(filter_participants)
                filter_participants = self.rib.get_all_participants_advertising(update["prefix"])
                ingress_participants = ingress_participants.difference(filter_participants)

                if ingress_participants:
                    receiver_participant = self.get_first_sdx_participant_on_path(update["prefix"], advertising_participant)

                    if receiver_participant:
                        co_update, old_co_entry, new_co_entry = self.cib.update_out(advertising_participant,
                                                                                    update["prefix"],
                                                                                    receiver_participant,
                                                                                    ingress_participants,
                                                                                    self.config.id,
                                                                                    active_policies)
                        random_value = randint(0, self.config.loop_detector.max_random_value)
                        timestamp = time()

                        self.notify_nh_sdx(co_update, old_co_entry, new_co_entry, timestamp, random_value)
            else:
                co_update, old_co_entry, new_co_entry = self.cib.delete_out_entry(advertising_participant,
                                                                            update["prefix"])
                random_value = randint(0, self.config.loop_detector.max_random_value)
                timestamp = time()

                self.notify_nh_sdx(co_update, old_co_entry, new_co_entry, timestamp, random_value)

        if self.rib_timing:
            end_time = clock()
            with open(self.rib_timing_file, "a") as outfile:
                outfile.write(str(end_time - start_time) + '\n')

        self.logger.debug("Done processing RIB Update")

    def is_policy_active(self, ingress_participant, egress_participant):
        """
        checks whether policies from ingress_participant to egress_participant are active for at least one
        prefix
        :param ingress_participant:
        :param egress_participant:
        :return:True if there is at least one prefix for which the policy is active
        """
        prefixes = self.rib.get_all_prefixes_advertised(ingress_participant, egress_participant)

        for prefix in prefixes:
            if egress_participant not in self.forbidden_paths[ingress_participant][prefix]:
                return True
        return False

    def correctness_message_sender(self):
        """
        retrieves messages from the queue and send them to the respective neighbor SDX
        :return:None
        """
        while self.run:
            try:
                msg = self.msg_out_queue.get(True, 1)

            except Empty:
                # self.logger.debug("Empty Queue")
                continue

            if msg[0] in self.config.sdx_registry:
                next_sdx = self.config.sdx_registry[msg[0]]
                conn = Client((next_sdx.address, next_sdx.port))
                conn.send(json.dumps(msg[1]))
                conn.close()
            else:
                self.logger.debug("Error: SDX " + str(msg[0]) + " is not in the SDX registry")

    def notify_nh_sdx(self, update, old_cib_entry, new_cib_entry, timestamp, random_value):
        """
        Creates the messages for the neighbor SDXes based on the changes in the CIB and puts them on the queue
        :param update:
        :param old_cib_entry:
        :param new_cib_entry:
        :param timestamp:
        :param random_value:
        :return:None
        """

        if not self.no_notifications:
            old_sdxes = set()
            new_sdxes = set()
            if not old_cib_entry and not new_cib_entry:
                return
            if old_cib_entry:
                old_sdxes = self.config.loop_detector.asn_2_sdx[old_cib_entry["receiver_participant"]]
                withdraw_msg = {"type": "withdraw",
                                "prefix": old_cib_entry["prefix"],
                                "sender_sdx": self.config.id,
                                "sdx_set": [],
                                "ingress_participant": old_cib_entry["receiver_participant"],
                                "timestamp": timestamp,
                                "random_value": random_value
                                }
            if new_cib_entry:
                new_sdxes = self.config.loop_detector.asn_2_sdx[new_cib_entry["receiver_participant"]]
                announce_msg = {"type": "announce",
                                "prefix": new_cib_entry["prefix"],
                                "sender_sdx": self.config.id,
                                "sdx_set": new_cib_entry["sdx_set"],
                                "ingress_participant": new_cib_entry["receiver_participant"],
                                "timestamp": timestamp,
                                "random_value": random_value
                                }
            if new_cib_entry and old_cib_entry:
                old_sdxes = old_sdxes.difference(new_sdxes)
                if not update:
                    new_sdxes = new_sdxes.difference(old_sdxes)

            for sdx in old_sdxes:
                self.msg_out_queue.put((sdx, withdraw_msg))
            for sdx in new_sdxes:
                self.msg_out_queue.put((sdx, announce_msg))

    def update_forbidden_paths(self, prefix, as_path, sdx_set, ingress_participant, egress_participant):
        """
        Updates the forbidden_paths structure.
        :param prefix:
        :param as_path:
        :param sdx_set:
        :param ingress_participant:
        :param egress_participant:
        :return:None
        """

        change = dict()

        if not as_path:
            route = self.rib.get_route(prefix, egress_participant)
            if route:
                as_path = route["as_path"]
            else:
                if egress_participant in self.forbidden_paths[ingress_participant][prefix]:
                    self.forbidden_paths[ingress_participant][prefix].remove(egress_participant)
                self.logger.debug("update forbidden paths for " + str(ingress_participant) + " - " + str(prefix) +
                                  " results in " + str(self.forbidden_paths[ingress_participant][prefix]))

                change["participant"] = ingress_participant
                change["prefix"] = prefix

                return change
        as_path_sdxes = self.get_sdxes_on_path([int(v) for v in as_path.split(" ")])
        if not sdx_set:
            cl_entry = self.cib.get_cl_entry(prefix, ingress_participant)
            if cl_entry:
                sdx_set = set([int(v) for v in cl_entry["sdx_set"].split(";")])
            else:
                sdx_set = set()

        intersection = sdx_set.intersection(as_path_sdxes)

        if len(intersection) > 0:
            if egress_participant not in self.forbidden_paths[ingress_participant][prefix]:
                self.forbidden_paths[ingress_participant][prefix].append(egress_participant)
        elif egress_participant in self.forbidden_paths[ingress_participant][prefix]:
            self.forbidden_paths[ingress_participant][prefix].remove(egress_participant)

        self.logger.debug("update forbidden paths for " + str(ingress_participant) + " - " +
                          str(prefix) + " results in " + str(self.forbidden_paths[ingress_participant][prefix]))

        change["participant"] = ingress_participant
        change["prefix"] = prefix

        return change

    def get_sdxes_on_path(self, as_path):
        """
        Finds all the potential SDXes on the AS path
        :param as_path:
        :return:set
        """
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

        sdxes = sdxes.difference({self.config.id})

        return sdxes

    def get_first_sdx_participant_on_path(self, prefix, egress_participant):
        """
        Finds the first participant on the AS path that is a member of an IXP
        :param prefix:
        :param egress_participant:
        :return:int
        """

        entry = self.rib.get_route(prefix, egress_participant)

        if entry:
            as_path = [int(n) for n in entry["as_path"].split(" ")]
            for i in range(0, len(as_path) - 1):
                as1 = as_path[i]
                as2 = as_path[i + 1]
                as1_sdxes = self.config.loop_detector.asn_2_sdx[as1]
                as2_sdxes = self.config.loop_detector.asn_2_sdx[as2]
                as1_sdxes = as1_sdxes.intersection(as2_sdxes)
                if len(as1_sdxes) > 0:
                    return as1
        return None


class LoopDetectorConfig(object):
    def __init__(self, sdx_2_asn, asn_2_sdx, max_random_value, port):
        self.sdx_2_asn = sdx_2_asn
        self.asn_2_sdx = asn_2_sdx
        self.max_random_value = max_random_value
        self.port = port
