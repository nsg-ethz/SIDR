#!/usr/bin/env python
#  Author:
#  Muhammad Shahbaz (muhammad.shahbaz@gatech.edu)

import os
import sqlite3
from threading import RLock as lock

from collections import defaultdict, namedtuple
from pymongo import MongoClient

class SQLCIB():
    def __init__(self, sdx_id, names):
        self.lock = lock()
        with self.lock:
            # Create a database in RAM
            # base_path = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "ribs"))
            # self.db = sqlite3.connect(base_path + '/' + str(sdx_id) + '.db', check_same_thread=False)
            self.db = sqlite3.connect(':memory:', check_same_thread=False)
            self.db.row_factory = SQLCIB.dict_factory

            # Get a cursor object
            cursor = self.db.cursor()
            cursor.execute('CREATE TABLE IF NOT EXISTS input (i_participant INT, prefix TEXT, sender_sdx INT, '
                           'sdx_set TEXT, PRIMARY KEY (i_participant, prefix, sender_sdx))')

            cursor.execute('CREATE TABLE IF NOT EXISTS local (i_participant INT, prefix TEXT, sdx_set TEXT, '
                           'PRIMARY KEY (i_participant, prefix))')

            cursor.execute('CREATE TABLE IF NOT EXISTS output (e_participant INT, prefix TEXT, '
                           'receiver_participant INT, sdx_set TEXT, '
                           'PRIMARY KEY (e_participant, prefix, receiver_participant))')
            self.db.commit()

    def __del__(self):

        with self.lock:
            self.db.close()

    def add_input(self, in_participant, prefix, sender_sdx, sdx_set):
        cursor = self.db.cursor()
        cursor.execute('INSERT OR REPLACE INTO input (i_participant, prefix, sender_sdx, sdx_set)'
                       'VALUES (?,?,?,?)',
                       (in_participant, prefix, sender_sdx, ";".join(str(v) for v in sdx_set)))
        self.db.commit()

    def add_local(self, in_participant, prefix, sdx_set):
        cursor = self.db.cursor()
        cursor.execute('INSERT OR REPLACE INTO local (i_participant, prefix, sdx_set) '
                       'VALUES (?,?,?)',
                       (in_participant, prefix, ";".join(str(v) for v in sdx_set)))
        self.db.commit()

    def add_output(self, e_participant, prefix, receiver_participant, sdx_set):
        cursor = self.db.cursor()
        cursor.execute('INSERT OR REPLACE INTO output (e_participant, prefix, receiver_participant, sdx_set) '
                       'VALUES (?,?,?,?)',
                       (e_participant, prefix, receiver_participant, ";".join(str(v) for v in sdx_set)))
        self.db.commit()

    def get(self, name, columns, key_set, key_items, all_entries):
        cursor = self.db.cursor()
        q_columns = '*'
        if columns:
            q_columns = ', '.join(columns)

        query = 'SELECT ' + q_columns + ' FROM ' + name + ' '

        keys = list()
        values = list()
        if key_set:
            keys.append(key_set[0] + ' IN (' + ', '.join(['?' for _ in range(0, len(key_set[1]))]) + ')')
            values.extend(key_set[1])

        if key_items:
            keys.extend([key + ' = ?' for key in key_items.keys()])
            values.extend(key_items.values())

        if key_items or key_set:
            query += ' WHERE '
            query += ' AND '.join([key for key in keys])

            cursor.execute(query, values)
        else:
            cursor.execute(query)

        if not all_entries:
            return cursor.fetchone()
        else:
            return cursor.fetchall()

    def delete(self, name, key_items):
        with self.lock:
            cursor = self.db.cursor()
            query = 'DELETE FROM ' + name
            if key_items:
                keys = key_items.keys()
                values = key_items.values()

                query += ' WHERE '
                query += " AND ".join([key + ' = ?' for key in keys])

                cursor.execute(query, values)
            else:
                cursor.execute(query)

    def commit(self):
        with self.lock:
            self.db.commit()

    def rollback(self):

        with self.lock:
            self.db.rollback()

    @staticmethod
    def dict_factory(cursor, row):
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d


class LocalCIB(object):
    CIBInEntry = namedtuple('CIBInEntry', 'i_participant prefix sender_sdx sdx_set')
    CIBLocEntry = namedtuple('CIBLocEntry', 'i_participant prefix sdx_set')
    CIBOutEntry = namedtuple('CIBOutEntry', 'e_participant prefix receiver_participant sdx_set')

    def __init__(self, sdx_id, names):
        self.tables = defaultdict(dict)
        self.ends = defaultdict(int)
        self.names = names

        self.input_inparticipant_prefix_sender_sdx_to_entry = defaultdict(int)
        self.input_inparticipant_prefix_to_entry = defaultdict(set)
        self.local_inparticipant_prefix_to_entry = defaultdict(int)
        self.output_eparticipant_prefix_to_entry = defaultdict(set)
        self.output_eparticipant_prefix_receiver_participant_to_entry = defaultdict(int)

    def add_input(self, in_participant, prefix, sender_sdx, sdx_set):
        entry = LocalCIB.CIBInEntry(in_participant, prefix, sender_sdx, sdx_set)

        index = self.ends['input']

        self.tables['input'][index] = entry
        self.input_inparticipant_prefix_sender_sdx_to_entry[(in_participant, prefix, sender_sdx)] = index
        self.input_inparticipant_prefix_to_entry[(in_participant, prefix)].add(index)

        self.ends['input'] += 1

    def add_local(self, in_participant, prefix, sdx_set):
        entry = LocalCIB.CIBLocEntry(in_participant, prefix, sdx_set)

        index = self.ends['local']

        self.tables['local'][index] = entry
        self.local_inparticipant_prefix_to_entry[(in_participant, prefix)] = index

        self.ends['local'] += 1

    def add_output(self, e_participant, prefix, receiver_participant, sdx_set):
        entry = LocalCIB.CIBOutEntry(e_participant, prefix, receiver_participant, sdx_set)

        index = self.ends['output']
        self.tables['output'][index] = entry
        self.output_eparticipant_prefix_to_entry[(e_participant, prefix)].add(index)
        self.output_eparticipant_prefix_receiver_participant_to_entry[(e_participant, prefix, receiver_participant)] = index
        self.ends['output'] += 1

    def get(self, name, columns, key_set, key_items, all_entries):
        i_participants = None
        if key_set:
            i_participants = key_set[1]
        elif key_items and 'i_participant' in key_items:
            i_participants = [key_items.pop('i_participant')]

        prefix = None
        sender_sdx = None
        e_participant = None
        receiver_participant = None
        if key_items:
            if 'prefix' in key_items:
                prefix = key_items['prefix']
            if 'sender_sdx' in key_items:
                sender_sdx = key_items['sender_sdx']
            if 'e_participant' in key_items:
                e_participant = key_items['e_participant']
            if 'receiver_participant' in key_items:
                receiver_participant = key_items['receiver_participant']

        keys = set()

        if name == 'input':
            if i_participants and prefix and sender_sdx:
                for i_participant in i_participants:
                    if (i_participant, prefix, sender_sdx) in self.input_inparticipant_prefix_sender_sdx_to_entry:
                        keys.add(self.input_inparticipant_prefix_sender_sdx_to_entry[(i_participant, prefix, sender_sdx)])
                        if not all_entries:
                            break
            elif i_participants and prefix:
                for i_participant in i_participants:
                    if (i_participant, prefix) in self.input_inparticipant_prefix_to_entry:
                        keys.update(self.input_inparticipant_prefix_to_entry[(i_participant, prefix)])
                        if not all_entries:
                            break

        if name == 'local':
            if i_participants and prefix:
                for i_participant in i_participants:
                    if (i_participant, prefix) in self.local_inparticipant_prefix_to_entry:
                        keys.add(self.local_inparticipant_prefix_to_entry[(i_participant, prefix)])
                        if not all_entries:
                            break

        if name == 'output':
            if e_participant and prefix and receiver_participant:
                if (e_participant, prefix, receiver_participant) in self.output_eparticipant_prefix_receiver_participant_to_entry:
                    keys.add(self.output_eparticipant_prefix_receiver_participant_to_entry[(e_participant, prefix, receiver_participant)])

            elif e_participant and prefix:
                if (e_participant, prefix) in self.input_inparticipant_prefix_to_entry:
                    keys.update(self.output_eparticipant_prefix_to_entry[(e_participant, prefix)])

        results = None
        if all_entries:
            results = list()
            tmp_keys = set(keys)
            for key in tmp_keys:
                if key in self.tables[name]:
                    results.append(self.tables[name][key]._asdict())
        else:
            tmp_keys = set(keys)
            for key in tmp_keys:
                if key in self.tables[name]:
                    results = self.tables[name][key]._asdict()
                    break

        return results

    def delete(self, name, key_items):
        i_participant = None
        prefix = None
        sender_sdx = None
        e_participant = None
        receiver_participant = None
        if key_items:
            if 'i_participant' in key_items:
                i_participant = key_items['i_participant']
            if 'prefix' in key_items:
                prefix = key_items['prefix']
            if 'sender_sdx' in key_items:
                sender_sdx = key_items['sender_sdx']
            if 'e_participant' in key_items:
                e_participant = key_items['e_participant']
            if 'receiver_participant' in key_items:
                receiver_participant = key_items['receiver_participant']

        keys = set()
        if name == 'input':
            if i_participant and prefix and sender_sdx and (i_participant, prefix, sender_sdx) in self.input_inparticipant_prefix_sender_sdx_to_entry:
                keys.add(self.input_inparticipant_prefix_sender_sdx_to_entry[(i_participant, prefix, sender_sdx)])
        elif name == 'local':
            if i_participant and prefix and (i_participant, prefix) in self.local_inparticipant_prefix_to_entry:
                keys.add(self.local_inparticipant_prefix_to_entry[(i_participant, prefix)])

        elif name == 'output':
            if e_participant and prefix and receiver_participant and (e_participant, prefix, receiver_participant) in self.output_eparticipant_prefix_receiver_participant_to_entry:
                    keys.add(self.output_eparticipant_prefix_receiver_participant_to_entry[(e_participant, prefix, receiver_participant)])
            elif e_participant and prefix:
                if (e_participant, prefix) in self.input_inparticipant_prefix_to_entry:
                    keys.update(self.output_eparticipant_prefix_to_entry[(e_participant, prefix)])
     
        if keys:
            tmp_keys = set(keys)
            for key in tmp_keys:
                entry = self.tables[name][key]

                if name == 'input':
                    if (entry.i_participant, entry.prefix, entry.sender_sdx) in self.input_inparticipant_prefix_sender_sdx_to_entry:
                        del self.input_inparticipant_prefix_sender_sdx_to_entry[(entry.i_participant, entry.prefix, entry.sender_sdx)]
                elif name == 'local':
                    if (entry.i_participant, entry.prefix) in self.local_inparticipant_prefix_to_entry:
                        del self.local_inparticipant_prefix_to_entry[(entry.i_participant, entry.prefix)]
                elif name == 'output':
                    if (entry.e_participant, entry.prefix, entry.receiver_participant) in self.output_eparticipant_prefix_receiver_participant_to_entry:
                        del self.output_eparticipant_prefix_receiver_participant_to_entry[(entry.e_participant, entry.prefix, entry.receiver_participant)]
                    self.output_eparticipant_prefix_to_entry[(entry.e_participant, entry.prefix)].remove(key)
                if key in self.tables[name]:
                    del self.tables[name][key]

    def commit(self):
        pass

    def rollback(self):
        pass


def pretty_print(rib_entry, filter=None):
    if rib_entry:
        if isinstance(rib_entry, list):
            for entry in rib_entry:
                print '|'
                for key, value in entry.iteritems():
                    if not filter or (filter and key in filter):
                        print '-> ' + str(key) + ': ' + str(value)
        else:
            for key, value in rib_entry.iteritems():
                if not filter or (filter and key in filter):
                    print '-> ' + str(key) + ': ' + str(value)

''' main '''
if __name__ == '__main__':
    mycib = LocalCIB(1, ['input'])

    entries = [
        {
            'table': 'input',
            'i_participant': 1,
            'prefix': '100.0.0.0/8',
            'sender_sdx': 55,
            'sdx_set': [1,2,3,4]
        },
        {
            'table': 'input',
            'i_participant': 3,
            'prefix': '100.0.0.0/8',
            'sender_sdx': 56,
            'sdx_set': [1,2,3,4]
        },
        {
            'table': 'input',
            'i_participant': 3,
            'prefix': '100.0.0.0/8',
            'sender_sdx': 55,
            'sdx_set': [1,2,3,4]
        },
        {
            'table': 'input',
            'i_participant': 3,
            'prefix': '90.0.0.0/8',
            'sender_sdx': 57,
            'sdx_set': [1,2,3,4]
        },
        {
            'table': 'input',
            'i_participant': 1,
            'prefix': '100.0.0.0/8',
            'sender_sdx': '172.0.0.1',
            'sdx_set': [1,2,3,4]
        },
        {
            'table': 'local',
            'i_participant': 1,
            'prefix': '90.0.0.0/8',
            'sdx_set': [4,7,5]
        },
        {
            'table': 'local',
            'i_participant': 3,
            'prefix': '90.0.0.0/8',
            'sdx_set': [3,4,5]
        },
        {
            'table': 'local',
            'i_participant': 2,
            'prefix': '90.0.0.0/8',
            'sdx_set': [1,4,5]
        },
        {
            'table': 'output',
            'e_participant': 3,
            'prefix': '90.0.0.0/8',
            'receiver_participant': 99,
            'sdx_set': [3,4]
        },
        {
            'table': 'output',
            'e_participant': 3,
            'prefix': '90.0.0.0/8',
            'receiver_participant': 95,
            'sdx_set': [3,4]
        },
        {
            'table': 'output',
            'e_participant': 2,
            'prefix': '80.0.0.0/8',
            'receiver_participant': 99,
            'sdx_set': [3,4]
        },
        {
            'table': 'output',
            'e_participant': 1,
            'prefix': '80.0.0.0/8',
            'receiver_participant': 99,
            'sdx_set': [3,4]
        }
    ]

    for entry in entries:
        if entry['table'] == 'input':
            mycib.add_input(entry['i_participant'], entry['prefix'], entry['sender_sdx'], entry['sdx_set'])
        if entry['table'] == 'local':
            mycib.add_local(entry['i_participant'], entry['prefix'], entry['sdx_set'])
        if entry['table'] == 'output':
            mycib.add_output(entry['e_participant'], entry['prefix'], entry['receiver_participant'], entry['sdx_set'])

    # INPUT

    column_p = ['i_participant', 'prefix', 'sender_sdx', 'sdx_set']
    results2 = mycib.get('input', column_p, None, {'i_participant': 3, 'prefix': '90.0.0.0/8', 'sender_sdx': 57}, True)
    pretty_print(results2, column_p)
    print "+++++++++++++++++++++++++++++++++"
    column_p = ['i_participant', 'prefix', 'sender_sdx', 'sdx_set']
    results2 = mycib.get('input', column_p, None, {'i_participant': 3, 'prefix': '100.0.0.0/8'}, True)
    pretty_print(results2, column_p)
    print "+++++++++++++++++++++++++++++++++"
    column_p = ['i_participant', 'prefix', 'sender_sdx', 'sdx_set']
    results2 = mycib.get('input', column_p, None, {'i_participant': 3, 'prefix': '90.0.0.0/8'}, False)
    pretty_print(results2, column_p)
    print "+++++++++++++++++++++++++++++++++"
    results4 = mycib.get('input', None, None, {'i_participant': 3, 'prefix': '100.0.0.0/8'}, True)
    pretty_print(results4)

    mycib.delete('input', {'i_participant': 3, 'prefix': '100.0.0.0/8', 'sender_sdx': 55})

    results4 = mycib.get('input', None, None, {'i_participant': 3, 'prefix': '100.0.0.0/8'}, True)
    pretty_print(results4)
    print "+++++++++++++++++++++++++++++++++"

    # LOCAL
    column_p = ['i_participant', 'prefix', 'sdx_set']
    results2 = mycib.get('local', column_p, ('i_participant', [2,3,4]), {'prefix': '90.0.0.0/8'}, True)
    pretty_print(results2, column_p)
    print "+++++++++++++++++++++++++++++++++"
    column_p = ['i_participant', 'prefix', 'sdx_set']
    results2 = mycib.get('local', column_p, ('i_participant', [2,3,4]), {'prefix': '90.0.0.0/8'}, False)
    pretty_print(results2, column_p)
    print "+++++++++++++++++++++++++++++++++"
    mycib.delete('local', {'i_participant': 2, 'prefix': '90.0.0.0/8'})
    column_p = ['i_participant', 'prefix', 'sdx_set']
    results2 = mycib.get('local', column_p, ('i_participant', [2,3,4]), {'prefix': '90.0.0.0/8'}, True)
    pretty_print(results2, column_p)
    print "+++++++++++++++++++++++++++++++++"

    # OUTPUT

    column_p = ['e_participant', 'prefix', 'receiver_participant', 'sdx_set']
    results2 = mycib.get('output', column_p, None, {'e_participant': 3, 'prefix': '90.0.0.0/8'}, True)
    pretty_print(results2, column_p)
    print "+++++++++++++++++++++++++++++++++"
    column_p = ['e_participant', 'prefix', 'receiver_participant', 'sdx_set']
    results2 = mycib.get('output', column_p, None, {'e_participant': 3, 'prefix': '90.0.0.0/8'}, False)
    pretty_print(results2, column_p)
    print "+++++++++++++++++++++++++++++++++"
    mycib.delete('output', {'e_participant': 3, 'prefix': '90.0.0.0/8'})
    column_p = ['e_participant', 'prefix', 'receiver_participant', 'sdx_set']
    results2 = mycib.get('output', column_p, None, {'e_participant': 3, 'prefix': '90.0.0.0/8'}, True)
    pretty_print(results2, column_p)
    print "+++++++++++++++++++++++++++++++++"
    column_p = ['e_participant', 'prefix', 'receiver_participant', 'sdx_set']
    results2 = mycib.get('output', column_p, None, {'e_participant': 1, 'prefix': '80.0.0.0/8', 'receiver_participant': 99}, True)
    pretty_print(results2, column_p)
    print "+++++++++++++++++++++++++++++++++"
    mycib.delete('output', {'e_participant': 1, 'prefix': '80.0.0.0/8', 'receiver_participant': 99})
    column_p = ['e_participant', 'prefix', 'receiver_participant', 'sdx_set']
    results2 = mycib.get('output', column_p, None, {'e_participant': 1, 'prefix': '80.0.0.0/8', 'receiver_participant': 99}, True)
    pretty_print(results2, column_p)
    print "+++++++++++++++++++++++++++++++++"