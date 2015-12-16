#!/usr/bin/env python
#  Author:
#  Rudiger Birkner (Networked Systems Group ETH Zurich)

import os
import sqlite3
from threading import RLock as lock


# TODO add withdraw and new announce

class CIB(object):
    def __init__(self):
        self.lock = lock()
        with self.lock:
            base_path = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)),"cibs"))
            self.db = sqlite3.connect(base_path+'/cib.db',check_same_thread=False)
            self.db.row_factory = sqlite3.Row

            # Get a cursor object
            cursor = self.db.cursor()
            cursor.execute('CREATE TABLE input (i_participant INT, prefix TEXT, sender_sdx TEXT, sdx_set TEXT, '
                           'PRIMARY KEY (i_participant, prefix, sender_sdx))')

            cursor.execute('CREATE TABLE local (i_participant INT, prefix TEXT, sdx_set TEXT, '
                           'PRIMARY KEY (i_participant, prefix))')

            cursor.execute('CREATE TABLE output (e_participant INT, prefix TEXT, receiver_participant TEXT, sdx_set TEXT, '
                           'PRIMARY KEY (e_participant, prefix, receiver_participant))')

            self.db.commit()

    def commit(self):

        with self.lock:
            self.db.commit()

    def rollback(self):

        with self.lock:
            self.db.rollback()

    def update_in(self, ingress_participant, prefix, sender_sdx, sdx_set):
        new_entry = {"i_participant": ingress_participant,
                     "prefix": prefix,
                     "sender_sdx": sender_sdx,
                     "sdx_set": sdx_set}

        with self.lock:
            cursor = self.db.cursor()

            old_entry = cursor.execute('SELECT i_participant, prefix, sender_sdx, sdx_set FROM input '
                                       'WHERE i_participant = ? AND prefix = ? AND sender_sdx = ?',
                                       (ingress_participant, prefix, sender_sdx))

            sdx_set = list(sdx_set).sort()
            if not old_entry or old_entry["sdx_set"] != sdx_set:
                cursor.execute('INSERT OR REPLACE INTO input (i_participant, prefix, sender_sdx, sdx_set) '
                               'VALUES (?,?,?,?)', (ingress_participant, prefix, sender_sdx, sdx_set))

                return True, old_entry, new_entry
            return False, None, None

    def update_loc(self, ingress_participant, prefix):
        with self.lock:
            cursor = self.db.cursor()

            cursor.execute('SELECT i_participant, prefix, sdx_set FROM input WHERE i_participant = ? AND prefix = ?',
                           (ingress_participant, prefix))
            ci_entries = cursor.fetchall()

            new_entry = CIB.merge_ci_entries(ci_entries)
            old_entry = cursor.execute('SELECT i_participant, prefix, sdx_set FROM local '
                                       'WHERE i_participant = ? AND prefix = ?',
                                       (ingress_participant, prefix))

            if not old_entry or new_entry["sdx_set"] != old_entry["sdx_set"]:
                cursor.execute('INSERT OR REPLACE INTO local (i_participant, prefix, sdx_set) '
                               'VALUES (?,?,?,?)', (ingress_participant, prefix, new_entry["sdx_set"]))

                return True, old_entry, new_entry
            return False, None, None

    @staticmethod
    def merge_ci_entries(ci_entries):
        merged_entry = dict()
        for entry in ci_entries:
            if not merged_entry:
                merged_entry["i_participant"] = entry["i_participant"]
                merged_entry["prefix"] = entry["prefix"]
                merged_entry["sdx_set"] = set(entry["sdx_set"].split(';'))
            else:
                merged_entry["sdx_set"] = merged_entry["sdx_set"].union(set(entry["sdx_set"].split(';')))

        merged_entry["sdx_set"] = list(merged_entry["sdx_set"])
        merged_entry["sdx_set"].sort()
        return merged_entry

    def update_out(self, egress_participant, prefix, receiver_participant, ingress_participants):
        with self.lock:
            placeholders = ', '.join('?' for _ in ingress_participants)
            query = 'SELECT i_participant, prefix, sdx_set FROM local WHERE i_participant IN (%s) AND prefix = ?' \
                    % placeholders
            cursor = self.db.cursor()
            cursor.execute(query, (ingress_participants, prefix))
            cl_entries = cursor.fetchall()

            new_entry = CIB.merge_cl_entries(egress_participant, self.config.id, cl_entries)
            old_entry = cursor.execute('SELECT e_participant, prefix, sdx_set FROM output '
                                       'WHERE e_participant = ? AND prefix = ?',
                                       (egress_participant, prefix))

            if not old_entry or new_entry["sdx_set"] != old_entry["sdx_set"]:
                cursor.execute('INSERT OR REPLACE INTO output (e_participant, prefix, receiver_participant, sdx_set) '
                               'VALUES (?,?,?,?,?)', (egress_participant, prefix, receiver_participant, new_entry["sdx_set"]))

                return True, old_entry, new_entry
            return False, None, None

    @staticmethod
    def merge_cl_entries(egress_participant, prefix, sdx_id, cl_entries):
        merged_entry = dict()
        merged_entry["e_participant"] = egress_participant
        merged_entry["prefix"] = prefix
        merged_entry["sdx_set"] = set(sdx_id)

        for entry in cl_entries:

                merged_entry["sdx_set"] = merged_entry["sdx_set"].union(set(entry["sdx_set"].split(';')))

        merged_entry["sdx_set"] = list(merged_entry["sdx_set"])
        merged_entry["sdx_set"].sort()
        return merged_entry

''' main '''
if __name__ == '__main__':
    #TODO Update test
    pass
