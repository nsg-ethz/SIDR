#!/usr/bin/env python
#  Author:
#  Muhammad Shahbaz (muhammad.shahbaz@gatech.edu)

import os
import sqlite3
from threading import RLock as lock

import socket, struct
from pymongo import MongoClient


class SQLRIB():
    def __init__(self, sdx_id, names):
        self.lock = lock()
        with self.lock:
            # Create a database in RAM
            base_path = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "ribs"))
            self.db = sqlite3.connect(base_path + '/' + str(sdx_id) + '.db', check_same_thread=False)
            self.db.row_factory = SQLRIB.dict_factory

            # Get a cursor object
            cursor = self.db.cursor()
            for name in names:
                cursor.execute(
                    'CREATE TABLE IF NOT EXISTS ' + str(name) + ' (participant TEXT, prefix TEXT, next_hop TEXT, '
                    'origin TEXT, as_path TEXT, communities TEXT, med INTEGER, atomic_aggregate BOOLEAN, '
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
                               'communities, med, atomic_aggregate) VALUES(?,?,?,?,?,?,?)',
                               (participant, prefix, item[0], item[1], item[2], item[3], item[4], item[5]))
            elif isinstance(item, dict) or isinstance(item, sqlite3.Row):
                cursor.execute('INSERT OR REPLACE INTO ' + name + '(prefix, next_hop, origin, as_path, communities, '
                               'med, atomic_aggregate) VALUES(?,?,?,?,?,?,?)',
                               (participant, prefix, item['next_hop'], item['origin'], item['as_path'],
                                item['communities'], item['med'], item['atomic_aggregate']))

    def get(self, name, key_items, all_entries):
        with self.lock:
            cursor = self.db.cursor()
            query = 'SELECT * FROM ' + name
            if key_items:
                keys = key_items.keys()
                values = key_items.values()

                query += ' WHERE '
                query += " AND ".join([key + ' = ?' for key in keys])

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

    def get(self, name, key_items, all_entries):
        table_name = name + "_" + str(self.sdx_id)

        if all_entries:
            rows = self.sessions[table_name].find(key_items)
            output_rows = list(rows)

        else:
            rows = self.sessions[table_name].find_one(key_items)
            output_rows = rows
        return output_rows

    def delete(self, name, key_items):
        table_name = name + "_" + str(self.sdx_id)
        self.sessions[table_name].delete_many(key_items)

    def commit(self):
        pass

    def rollback(self):
        print "previous rollback, does nothing"

''' main '''
if __name__ == '__main__':
    # TODO Update test

    myrib = rib()

    myrib['100.0.0.1/16'] = ('172.0.0.2', 'igp', '100, 200, 300', '0', 'false')
    # myrib['100.0.0.1/16'] = ['172.0.0.2', 'igp', '100, 200, 300', '0', 'false']
    # myrib['100.0.0.1/16'] = {'next_hop':'172.0.0.2', 'origin':'igp', 'as_path':'100, 200, 300',
    #                          'med':'0', 'atomic_aggregate':'false'}
    myrib.commit()

    myrib.update('100.0.0.1/16', 'next_hop', '190.0.0.2')
    myrib.commit()

    val = myrib.filter('as_path', '300')

    print val[0]['next_hop']
