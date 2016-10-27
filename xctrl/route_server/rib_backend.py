#!/usr/bin/env python
#  Author:
#  Muhammad Shahbaz (muhammad.shahbaz@gatech.edu)

import os
import sqlite3
from threading import RLock as lock

from collections import defaultdict, namedtuple
from pymongo import MongoClient

class SQLRIB():
    def __init__(self, sdx_id, names):
        self.lock = lock()
        with self.lock:
            # Create a database in RAM
            # base_path = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "ribs"))
            # self.db = sqlite3.connect(base_path + '/' + str(sdx_id) + '.db', check_same_thread=False)
            self.db = sqlite3.connect(':memory:', check_same_thread=False)
            self.db.row_factory = SQLRIB.dict_factory

            # Get a cursor object
            cursor = self.db.cursor()
            for name in names:
                cursor.execute(
                    'CREATE TABLE IF NOT EXISTS ' + str(name) + ' (participant INT, prefix TEXT, next_hop TEXT, '
                    'origin TEXT, as_path TEXT, communities TEXT, med INT, atomic_aggregate BOOLEAN, '
                    'PRIMARY KEY (participant, prefix))')

            self.db.commit()

    def __del__(self):

        with self.lock:
            self.db.close()

    def add(self, name, participant, prefix, item):
        with self.lock:
            cursor = self.db.cursor()

            if isinstance(item, tuple) or isinstance(item, list):
                cursor.execute('INSERT OR REPLACE INTO ' + name + '(participant, prefix, next_hop, origin, as_path, '
                               'communities, med, atomic_aggregate) VALUES(?,?,?,?,?,?,?,?)',
                               (participant, prefix, item[0], item[1], item[2], item[3], item[4], item[5]))
            elif isinstance(item, dict) or isinstance(item, sqlite3.Row):
                cursor.execute('INSERT OR REPLACE INTO ' + name + '(participant, prefix, next_hop, origin, as_path, '
                               'communities, med, atomic_aggregate) VALUES(?,?,?,?,?,?,?,?)',
                               (participant, prefix, item['next_hop'], item['origin'], item['as_path'],
                                item['communities'], item['med'], item['atomic_aggregate']))

    def get(self, name, columns, key_set, key_items, all_entries):
        with self.lock:
            cursor = self.db.cursor()

            q_columns = '*'
            if columns:
                q_columns = ', '.join(columns)

            query = 'SELECT ' + q_columns + ' FROM ' + name

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


class LocalRIB(object):
    RIBEntry = namedtuple('RIBEntry', 'participant prefix next_hop origin as_path communities med atomic_aggregate')

    def __init__(self, sdx_id, names):
        self.tables = defaultdict(dict)
        self.ends = defaultdict(int)
        self.names = names

        self.participant_to_entry = defaultdict(set)
        self.prefix_to_entry = defaultdict(set)
        self.next_hop_to_entry = defaultdict(set)
        self.participant_and_prefix_to_entry = dict()
        self.prefix_and_next_hop_to_entry = defaultdict(set)

    def add(self, name, participant, prefix, item):
        valid = False
        if isinstance(item, tuple) or isinstance(item, list):
            valid = True
            next_hop = item[0]
            origin = item[1]
            as_path = item[2]
            communities = item[3]
            med = item[4]
            atomic_aggregate = item[5]
        elif isinstance(item, dict) or isinstance(item, sqlite3.Row):
            valid = True
            next_hop = item['next_hop']
            origin = item['origin']
            as_path = item['as_path']
            communities = item['communities']
            med = item['med']
            atomic_aggregate = item['atomic_aggregate']

        if valid:
            rib_entry = LocalRIB.RIBEntry(participant, prefix, next_hop, origin, as_path, communities, med, atomic_aggregate)

            self.tables[name][self.ends[name]] = rib_entry
            self.participant_to_entry[(name, participant)].add(self.ends[name])
            self.prefix_to_entry[(name, prefix)].add(self.ends[name])
            self.participant_and_prefix_to_entry[name, participant, prefix] = self.ends[name]
            self.prefix_and_next_hop_to_entry[(name, prefix, next_hop)].add(self.ends[name])
            self.ends[name] += 1

    def get(self, name, columns, key_set, key_items, all_entries):
        participants = None
        if key_set:
            participants = key_set[1]
        elif key_items and 'participant' in key_items:
            participants = [key_items.pop('participant')]

        next_hop = None
        prefix = None
        if key_items:
            if 'prefix' in key_items:
                prefix = key_items['prefix']

            if 'next_hop' in key_items:
                next_hop = key_items['next_hop']

        keys = set()

        if prefix and next_hop and not participants:
            if (name, prefix, next_hop) in self.prefix_and_next_hop_to_entry:
                keys = self.prefix_and_next_hop_to_entry[(name, prefix, next_hop)]

        elif prefix and not next_hop and not participants:
            if (name, prefix) in self.prefix_to_entry:
                keys = self.prefix_to_entry[(name, prefix)]

        elif prefix and not next_hop and participants:
            for participant in participants:
                if (name, participant, prefix) in self.participant_and_prefix_to_entry:
                    keys.add(self.participant_and_prefix_to_entry[(name, participant, prefix)])
                    if not all_entries:
                        break

        elif not prefix and not next_hop and participants:
            for participant in participants:
                if (name, participant) in self.participant_to_entry:
                    keys.update(self.participant_to_entry[(name, participant)])
                    if not all_entries:
                        break

        results = None
        if all_entries:
            results = list()
            for key in keys:
                if key in self.tables[name]:
                    results.append(self.tables[name][key]._asdict())
        else:
            for key in keys:
                if key in self.tables[name]:
                    results = self.tables[name][key]._asdict()
                    break

        return results

    def delete(self, name, key_items):
        participant = None
        if 'participant' in key_items:
            participant = key_items['participant']

        prefix = None
        if 'prefix' in key_items:
            prefix = key_items['prefix']

        keys = None
        if prefix and not participant and (name, prefix) in self.prefix_to_entry:
            keys = self.prefix_to_entry[(name, prefix)]

        elif prefix and participant and (name, participant, prefix) in self.participant_and_prefix_to_entry:
            keys = [self.participant_and_prefix_to_entry[(name, participant, prefix)]]

        elif not prefix and participant and (name, participant) in self.participant_to_entry:
            keys = self.participant_to_entry[(name, participant)]
     
        if keys:
            tmp_keys = set(keys)
            for key in tmp_keys:
                entry = self.tables[name][key]

                if (name, entry.participant) in self.participant_to_entry:
                    self.participant_to_entry[(name, entry.participant)].remove(key)

                if (name, entry.prefix) in self.prefix_to_entry:
                    self.prefix_to_entry[(name, entry.prefix)].remove(key)

                if (name, entry.participant, entry.prefix) in self.participant_and_prefix_to_entry:
                    del self.participant_and_prefix_to_entry[name, entry.participant, entry.prefix]

                if (name, entry.prefix, entry.next_hop) in self.prefix_and_next_hop_to_entry:
                    self.prefix_and_next_hop_to_entry[(name, entry.prefix, entry.next_hop)].remove(key)

                if key in self.tables[name]:
                    del self.tables[name][key]

    def commit(self):
        pass

    def rollback(self):
        pass


class MongoDBRIB():
    def __init__(self, sdx_id, names):
        self.sdx_id = sdx_id
        self.names = names
        self.client = MongoClient("localhost", 27017)
        self.db = self.client['demo']
        self.sessions = dict()

        for name in names:
            table_name = name + "_" + str(self.sdx_id)
            self.sessions[name] = self.db[table_name]

    def add(self, name, participant, prefix, attributes):
        table_name = name + "_" + str(self.sdx_id)

        values = {
            "participant": participant,
            "prefix": prefix
        }

        if isinstance(attributes, tuple) or isinstance(attributes, list):
            values["next_hop"] = attributes[1]
            values["origin"] = attributes[2]
            values["as_path"] = attributes[3]
            values["communities"] = attributes[4]
            values["med"] = attributes[5]
            values["atomic_aggregate"] = attributes[6]

        elif isinstance(attributes, dict):
            values = values.update(attributes)

        self.sessions[name].insert_one(values)

    def get(self, name, columns, key_set, key_items, all_entries):
        table_name = name + "_" + str(self.sdx_id)

        query = {'$and': []}

        if key_set:
            conditions = list()
            for participant in key_set[1]:
                conditions.append({'participant': participant})
            query['$and'].append({
                '$or': conditions
            })

        if key_items:
            query['$and'].append(key_items)

        filter = None
        if columns:
            filter = dict()
            for col in columns:
                filter[col] = 1

        if all_entries:
            rows = self.sessions[table_name].find(key_items, filter)
            output_rows = list(rows)

        else:
            rows = self.sessions[table_name].find_one(key_items, filter)
            output_rows = rows
        return output_rows

    def delete(self, name, key_items):
        table_name = name + "_" + str(self.sdx_id)
        self.sessions[table_name].delete_many(key_items)

    def commit(self):
        pass

    def rollback(self):
        print "previous rollback, does nothing"


def pretty_print(rib_entry, filter=None):
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
    myrib = LocalRIB(1, ['input'])

    routes = [
        {
            'table': 'input',
            'participant': 1,
            'prefix': '100.0.0.0/8',
            'next_hop': '172.0.0.1',
            'origin': 'igp',
            'as_path': '7000,7100',
            'communities': '',
            'med': '',
            'atomic_aggregate': ''
        },
        {
            'table': 'input',
            'participant': 1,
            'prefix': '90.0.0.0/8',
            'next_hop': '172.0.0.1',
            'origin': 'igp',
            'as_path': '7000,7100',
            'communities': '',
            'med': '',
            'atomic_aggregate': ''
        },
        {
            'table': 'input',
            'participant': 1,
            'prefix': '80.0.0.0/8',
            'next_hop': '172.0.0.3',
            'origin': 'igp',
            'as_path': '7000,7100',
            'communities': '',
            'med': '',
            'atomic_aggregate': ''
        },
        {
            'table': 'input',
            'participant': 1,
            'prefix': '70.0.0.0/8',
            'next_hop': '172.0.0.1',
            'origin': 'igp',
            'as_path': '7000,7100',
            'communities': '',
            'med': '',
            'atomic_aggregate': ''
        },
        {
            'table': 'input',
            'participant': 2,
            'prefix': '100.0.0.0/8',
            'next_hop': '172.0.0.3',
            'origin': 'igp',
            'as_path': '7000,7100',
            'communities': '',
            'med': '',
            'atomic_aggregate': ''
        },
        {
            'table': 'input',
            'participant': 3,
            'prefix': '100.0.0.0/8',
            'next_hop': '172.0.0.1',
            'origin': 'igp',
            'as_path': '7000,7100',
            'communities': '',
            'med': '',
            'atomic_aggregate': ''
        },
        {
            'table': 'input',
            'participant': 4,
            'prefix': '100.0.0.0/8',
            'next_hop': '172.0.0.3',
            'origin': 'igp',
            'as_path': '7000,7100',
            'communities': '',
            'med': '',
            'atomic_aggregate': ''
        },
        {
            'table': 'input',
            'participant': 4,
            'prefix': '110.0.0.0/8',
            'next_hop': '172.0.0.1',
            'origin': 'igp',
            'as_path': '7000,7100',
            'communities': '',
            'med': '',
            'atomic_aggregate': ''
        },
    ]

    for route in routes:
        myrib.add(route['table'], route['participant'], route['prefix'], route)

    column_p = ['participant']
    results2 = myrib.get('input', column_p, None, {'prefix': '100.0.0.0/8'}, True)
    pretty_print(results2, ['participant'])

    print "+++++++++++++++++++++++++++++++++"

    results3 = myrib.get('input', ['participant', 'prefix', 'as_path'], None, {'prefix': '100.0.0.0/8'}, False)
    pretty_print(results3, ['participant', 'prefix', 'as_path'])

    print "+++++++++++++++++++++++++++++++++"

    results4 = myrib.get('input', None, ('participant', [2,3,4]), {'prefix': '100.0.0.0/8'}, True)
    pretty_print(results4)

    print "+++++++++++++++++++++++++++++++++"

    results4 = myrib.get('input', None, None, {'next_hop': '172.0.0.3', 'prefix': '100.0.0.0/8'}, True)
    pretty_print(results4)

    print "+++++++++++++++++++++++++++++++++"

    results4 = myrib.get('input', None, None, {'prefix': '100.0.0.0/8'}, True)
    pretty_print(results4)

    print "+++++++++++++++++++++++++++++++++"

    myrib.delete('input', {'participant': 4, 'prefix': '100.0.0.0/8'})
    results4 = myrib.get('input', None, None, {'prefix': '100.0.0.0/8'}, True)
    pretty_print(results4)

    print "+++++++++++++++++++++++++++++++++"

    results4 = myrib.get('input', None, None, {'participant': 1}, True)
    pretty_print(results4)

    print 'delete'

    myrib.delete('input', {'participant': 1})


    results4 = myrib.get('input', None, None, {'participant': 1}, True)
    pretty_print(results4)

    print "+++++++++++++++++++++++++++++++++"
