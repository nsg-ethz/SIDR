#!/usr/bin/env python
#  Author:
#  Rudiger Birkner (Networked Systems Group ETH Zurich)

import os
import sqlite3
from threading import RLock as lock
from cib_backend import SQLCIB, LocalCIB


# TODO delete entries after changes

class CIB(object):
    def __init__(self, sdx_id):
        self.cib = SQLCIB(sdx_id, ['input', 'local', 'output'])

    def update_in(self, type, ingress_participant, prefix, sender_sdx, sdx_set=False):
        new_entry = {"i_participant": ingress_participant,
                     "prefix": prefix,
                     "sender_sdx": sender_sdx,
                     "sdx_set": sdx_set}

        columns = ['i_participant', 'prefix', 'sender_sdx', 'sdx_set']
        key_items = {
            'i_participant': ingress_participant,
            'prefix': prefix,
            'sender_sdx': sender_sdx
        }
        old_entry = self.cib.get('input', columns, None, key_items, False)

        if type == "withdraw":
            key_items = {
                'i_participant': ingress_participant,
                'prefix': prefix,
                'sender_sdx': sender_sdx
            }
            self.cib.delete('input', key_items)
            return True, old_entry, None
        else:
            sdx_set = list(sdx_set)
            sdx_set.sort()
            if not old_entry or old_entry["sdx_set"] != sdx_set:
                self.cib.add_input(ingress_participant, prefix, sender_sdx, new_entry['sdx_set'])
                return True, old_entry, new_entry
            return False, None, None

    def update_loc(self, ingress_participant, prefix):

        columns = ['i_participant', 'prefix', 'sdx_set']
        key_items = {
            'i_participant': ingress_participant,
            'prefix': prefix
        }
        ci_entries = self.cib.get('input', columns, None, key_items, True)
        old_entry = self.cib.get('local', columns, None, key_items, False)

        if ci_entries:
            new_entry = CIB.merge_ci_entries(ci_entries)
            if not old_entry or new_entry["sdx_set"] != old_entry["sdx_set"]:
                self.cib.add_local(ingress_participant, prefix, new_entry["sdx_set"])
                return True, old_entry, new_entry
        else:
            if old_entry:
                key_items = {
                    'i_participant': ingress_participant,
                    'prefix': prefix
                }
                self.cib.delete('local', key_items)
            return True, old_entry, None
        return False, None, None

    @staticmethod
    def merge_ci_entries(ci_entries):
        merged_entry = dict()
        for entry in ci_entries:
            if not merged_entry:
                merged_entry["i_participant"] = entry["i_participant"]
                merged_entry["prefix"] = entry["prefix"]
                merged_entry["sdx_set"] = set([int(v) for v in entry["sdx_set"].split(';')])
            else:
                merged_entry["sdx_set"] = merged_entry["sdx_set"].union(set([int(v) for v in entry["sdx_set"].split(';')]))

        merged_entry["sdx_set"] = list(merged_entry["sdx_set"])
        merged_entry["sdx_set"].sort()
        return merged_entry

    def update_out(self, egress_participant, prefix, receiver_participant, ingress_participants, sdx_id, policy):

            columns = ['i_participant', 'prefix', 'sdx_set']
            key_items = {
                'prefix': prefix
            }
            key_set = ('i_participant', [int(participant) for participant in list(ingress_participants)])
            cl_entries = self.cib.get('local', columns, key_set, key_items, True)

            columns = ['e_participant', 'prefix', 'receiver_participant', 'sdx_set']
            key_items = {
                'e_participant': egress_participant,
                'prefix': prefix,
            }
            old_entry = self.cib.get('output', columns, None, key_items, False)

            new_entry = CIB.merge_cl_entries(egress_participant, prefix, sdx_id, cl_entries, receiver_participant, policy)

            if new_entry:
                sdx_set = ";".join(str(v) for v in new_entry["sdx_set"])
                if not old_entry or sdx_set != old_entry["sdx_set"] or receiver_participant != old_entry["receiver_participant"]:
                    self.cib.add_output(egress_participant, prefix, receiver_participant, sdx_set)
                    if old_entry and receiver_participant != old_entry["receiver_participant"]:
                        key_items = {
                            'e_participant': egress_participant,
                            'prefix': prefix,
                            'receiver_participant': old_entry["receiver_participant"]
                        }
                        self.cib.delete('output', key_items)
                    return True, old_entry, new_entry
            elif old_entry:
                key_items = {
                    'e_participant': egress_participant,
                    'prefix': prefix,
                }
                self.cib.delete('output', key_items)
                return True, old_entry, None
            return False, None, None

    def delete_out_entry(self, egress_participant, prefix):
        columns = ['e_participant', 'prefix', 'receiver_participant', 'sdx_set']
        key_items = {
            'e_participant': egress_participant,
            'prefix': prefix,
        }
        old_entry = self.cib.get('output', columns, None, key_items, False)

        if old_entry:
            self.cib.delete('output', key_items)
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
                merged_entry["sdx_set"] = merged_entry["sdx_set"].union(set([int(v) for v in entry["sdx_set"].split(';')]))

        merged_entry["sdx_set"] = list(merged_entry["sdx_set"])
        merged_entry["sdx_set"].sort()
        return merged_entry

    def get_cl_entry(self, prefix, ingress_participant):
        columns = ['i_participant', 'prefix', 'sdx_set']
        key_items = {
            'i_participant': ingress_participant,
            'prefix': prefix,
        }
        cl_entry = self.cib.get('local', columns, None, key_items, False)
        return cl_entry


''' main '''
if __name__ == '__main__':
    #TODO Update test
    pass
