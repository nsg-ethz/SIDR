#!usr/bin/env python
#  Author:
#  Muhammad Shahbaz (muhammad.shahbaz@gatech.edu)
#  Arpit Gupta (arpitg@cs.princeton.edu)

import socket, struct
from pymongo import MongoClient


MONGODB_HOST = "localhost"
MONGODB_PORT = 27017


def ip_to_long(ip):
    return struct.unpack('!L', socket.inet_aton(ip))[0]


class rib():
    def __init__(self, table_suffix, names, path):
        self.suffix = table_suffix
        self.names = names
        self.client = MongoClient(MONGODB_HOST, MONGODB_PORT)
        self.db = self.client['demo']
        self.sessions = dict()

        for name in names:
            table_name = name + "_" + str(table_suffix)
            self.sessions[name] = self.db[table_name]

    def __del__(self):
        # self.cluster.shutdown()
        pass

    def add(self, name, key, item):
        key = str(key)
        if isinstance(item, tuple) or isinstance(item, list):
            assert (len(item) == 7)
            # Use cassandra session object
            in_stmt = {"prefix": key, "neighbor": item[0],
                       "next_hop": item[1], "origin": item[2],
                       "as_path": item[3], "communities": item[4],
                       "med": item[5], "atomic_aggregate": item[6]}
            # print "Insert data", self.name ,in_stmt
            row = self.sessions[name].insert_one(in_stmt)
        elif isinstance(item, dict):
            in_stmt = item
            in_stmt['prefix'] = key

            self.sessions[name].insert_one(in_stmt)
            # TODO: Add support for selective update

    def add_many(self,name,items):

        if isinstance(items, list):
            self.sessions[name].insert_many(items)

    def get(self,name,key):

        key = str(key)
        rows = self.sessions[name].find({"prefix": key})
        output_rows = None

        if "input" in name:
            output_rows = []
            for row in rows:
                output_rows.append(row)
        else:
            if rows.count() > 0:
                output_rows = rows[0]
        return output_rows

    def get_all(self, name, key=None):

        rows = []
        if key is not None:
            rows = self.sessions[name].find({"prefix": key})
        else:
            rows = self.sessions[name].find()
        output_rows = None

        if "input" in name:
            output_rows = []
            for row in rows:
                output_rows.append(row)
        else:
            if len(rows) > 0:
                output_rows = rows[0]

        return output_rows

    def filter(self, name, item, value):

        rows = self.sessions[name].find_one({item: value})
        return rows

    def update(self, name, key, item, value):

        rows = self.sessions[name].update_one({"prefix": key}, {"$set": {item: value}})

    def delete(self, name, key):

        # TODO: Add more granularity in the delete process i.e., instead of just prefix,
        # it should be based on a conjunction of other attributes too.
        rows = self.sessions[name].delete_many({"prefix": key})

    def delete_all(self, name):
        rows = self.sessions[name].delete_many()

    def commit(self):
        pass

    def rollback(self):
        print "previous rollback, does nothing"


''' main '''
if __name__ == '__main__':
    # TODO Update test

    myrib = rib('ashello', 'test', False)
    print type(myrib)
    # (prefix, neighbor, next_hop, origin, as_path, communities, med,atomic_aggregate)
    myrib['100.0.0.1/16'] = ('172.0.0.2', '172.0.0.2', 'igp', '100, 200, 300', '0', 0, 'false')
    # myrib['100.0.0.1/16'] = ['172.0.0.2', 'igp', '100, 200, 300', '0', 'false']
    # myrib['100.0.0.1/16'] = {'next_hop':'172.0.0.2', 'origin':'igp', 'as_path':'100, 200, 300',
    #                          'med':'0', 'atomic_aggregate':'false'}
    myrib.commit()

    myrib.update('100.0.0.1/16', 'next_hop', '190.0.0.2')
    myrib.commit()

    val = myrib.filter('prefix', '100.0.0.1/16')
    print val
    print val['next_hop']
    val2 = myrib.get_prefix_neighbor('100.0.0.1/16', '172.0.0.2')
    print val2