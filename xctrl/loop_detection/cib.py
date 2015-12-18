#!/usr/bin/env python
#  Author:
#  Rudiger Birkner (Networked Systems Group ETH Zurich)

import os
import sqlite3
from threading import RLock as lock


# TODO delete entries after changes

class CIB(object):
    def __init__(self):
        self.lock = lock()
        with self.lock:
            base_path = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)),"cibs"))
            self.db = sqlite3.connect(base_path+'/cib.db',check_same_thread=False)
            self.db.row_factory = sqlite3.Row

            # Get a cursor object
            cursor = self.db.cursor()
            cursor.execute('CREATE TABLE IF NOT EXISTS input (i_participant INT, prefix TEXT, sender_sdx INT, sdx_set TEXT, '
                           'PRIMARY KEY (i_participant, prefix, sender_sdx))')

            cursor.execute('CREATE TABLE IF NOT EXISTS local (i_participant INT, prefix TEXT, sdx_set TEXT, '
                           'PRIMARY KEY (i_participant, prefix))')

            cursor.execute('CREATE TABLE IF NOT EXISTS output (e_participant INT, prefix TEXT, receiver_participant INT, sdx_set TEXT, '
                           'PRIMARY KEY (e_participant, prefix, receiver_participant))')

            self.db.commit()

    def commit(self):

        with self.lock:
            self.db.commit()

    def rollback(self):

        with self.lock:
            self.db.rollback()

    def update_in(self, type, ingress_participant, prefix, sender_sdx, sdx_set=False):
        new_entry = {"i_participant": ingress_participant,
                     "prefix": prefix,
                     "sender_sdx": sender_sdx,
                     "sdx_set": sdx_set}

        with self.lock:
            cursor = self.db.cursor()

            cursor.execute('SELECT i_participant, prefix, sender_sdx, sdx_set FROM input '
                           'WHERE i_participant = ? AND prefix = ? AND sender_sdx = ?',
                           (ingress_participant, prefix, sender_sdx))
            old_entry = cursor.fetchone()
            if type == "withdraw":
                cursor.execute('DELETE FROM input WHERE i_participant = ? AND prefix = ? AND sender_sdx = ?',
                               (ingress_participant, prefix, sender_sdx))
                self.db.commit()
            else:
                sdx_set = list(sdx_set)
                sdx_set.sort()
                if not old_entry or old_entry["sdx_set"] != sdx_set:
                    cursor.execute('INSERT OR REPLACE INTO input (i_participant, prefix, sender_sdx, sdx_set)'
                                       'VALUES (?,?,?,?)', (ingress_participant, prefix, sender_sdx, sdx_set))
                    self.db.commit()

                    return True, old_entry, new_entry
            return False, None, None

    def update_loc(self, ingress_participant, prefix):
        with self.lock:
            cursor = self.db.cursor()

            cursor.execute('SELECT i_participant, prefix, sdx_set FROM input WHERE i_participant = ? AND prefix = ?',
                           (ingress_participant, prefix))
            ci_entries = cursor.fetchall()

            cursor.execute('SELECT i_participant, prefix, sdx_set FROM local '
                           'WHERE i_participant = ? AND prefix = ?',
                           (ingress_participant, prefix))
            old_entry = cursor.fetchone()

            if ci_entries:
                new_entry = CIB.merge_ci_entries(ci_entries)
                if not old_entry or new_entry["sdx_set"] != old_entry["sdx_set"]:
                    cursor.execute('INSERT OR REPLACE INTO local (i_participant, prefix, sdx_set) '
                                   'VALUES (?,?,?,?)', (ingress_participant, prefix, new_entry["sdx_set"]))
                    self.db.commit()

                    return True, old_entry, new_entry
            else:
                if old_entry:
                    cursor.execute('DELETE FROM local WHERE i_participant = ? AND prefix = ?',
                                   (ingress_participant, prefix))
                    self.db.commit()
                return True, old_entry, None
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

    def update_out(self, egress_participant, prefix, receiver_participant, ingress_participants, sdx_id):
        with self.lock:
            placeholders = ', '.join('?' for _ in ingress_participants)
            query = 'SELECT i_participant, prefix, sdx_set FROM local WHERE i_participant IN (%s) AND prefix = ?' \
                    % placeholders
            cursor = self.db.cursor()
            args = list(ingress_participants)
            args.append(prefix)
            cursor.execute(query, args)
            cl_entries = cursor.fetchall()

            cursor.execute('SELECT e_participant, prefix, receiver_participant, sdx_set FROM output '
                           'WHERE e_participant = ? AND prefix = ?',
                           (egress_participant, prefix))
            old_entry = cursor.fetchone()

            active_policy = True if ingress_participants else False
            new_entry = CIB.merge_cl_entries(egress_participant, prefix, sdx_id, cl_entries, receiver_participant, active_policy)

            if new_entry:
                if not old_entry or new_entry["sdx_set"] != old_entry["sdx_set"]:
                    cursor.execute('INSERT OR REPLACE INTO output (e_participant, prefix, receiver_participant, sdx_set) '
                                   'VALUES (?,?,?,?)', (egress_participant, prefix, receiver_participant, ";".join(str(v) for v in new_entry["sdx_set"])))
                    self.db.commit()
                    return True, old_entry, new_entry
            elif old_entry:
                cursor.execute('DELETE FROM output WHERE e_participant = ? AND prefix = ?',
                                (egress_participant, prefix))
                self.db.commit()
                return True, old_entry, None
            return False, None, None

    @staticmethod
    def merge_cl_entries(egress_participant, prefix, sdx_id, cl_entries, receiver_participant, policy):
        if not policy and not cl_entries:
            return None

        merged_entry = dict()
        merged_entry["e_participant"] = egress_participant
        merged_entry["prefix"] = prefix
        merged_entry["receiver_participant"] = receiver_participant
        merged_entry["sdx_set"] = set()
        merged_entry["sdx_set"].add(sdx_id)
        if cl_entries:
            for entry in cl_entries:
                merged_entry["sdx_set"] = merged_entry["sdx_set"].union(set(entry["sdx_set"].split(';')))

        merged_entry["sdx_set"] = list(merged_entry["sdx_set"])
        merged_entry["sdx_set"].sort()
        return merged_entry

    def get_cl_entry(self, prefix, ingress_participant):
        with self.lock:
            cursor = self.db.cursor()
            query = 'SELECT i_participant, prefix, sdx_set FROM local WHERE i_participant = ? AND prefix = ?'
            cursor.execute(query, (ingress_participant, prefix))
            cl_entry = cursor.fetchone()
        return cl_entry


''' main '''
if __name__ == '__main__':
    #TODO Update test
    pass
