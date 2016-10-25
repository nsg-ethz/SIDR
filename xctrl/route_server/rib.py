#!/usr/bin/env python
#  Author:
#  Muhammad Shahbaz (muhammad.shahbaz@gatech.edu)

import os
import sqlite3
from threading import RLock as lock


class rib():
    
    def __init__(self, asn, names):
        self.lock = lock()
        with self.lock:
            # Create a database in RAM
            base_path = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)),"ribs"))
            self.db = sqlite3.connect(base_path+'/'+str(asn)+'.db',check_same_thread=False)
            self.db.row_factory = rib.dict_factory
            self.names = names
        
            # Get a cursor object
            for name in self.names:
                cursor = self.db.cursor()
                cursor.execute('''
                            create table if not exists '''+name+''' (prefix text, next_hop text,
                                   origin text, as_path text, communities text, med integer, atomic_aggregate boolean, primary key (prefix))
                ''')

            self.db.commit()
    
    def __del__(self):
            
        with self.lock:
            self.db.close()
        
    def add(self,name,key,item):
        
        with self.lock:
            cursor = self.db.cursor()
        
            if isinstance(item,tuple) or isinstance(item,list):
                cursor.execute('''insert or replace into ''' + name + ''' (prefix, next_hop, origin, as_path, communities, med,
                        atomic_aggregate) values(?,?,?,?,?,?,?)''', 
                        (key,item[0],item[1],item[2],item[3],item[4],item[5]))
            elif isinstance(item,dict) or isinstance(item,sqlite3.Row):
                cursor.execute('''insert or replace into ''' + name + ''' (prefix, next_hop, origin, as_path, communities, med,
                        atomic_aggregate) values(?,?,?,?,?,?,?)''', 
                        (key,item['next_hop'],item['origin'],item['as_path'],item['communities'],item['med'],item['atomic_aggregate']))
            
        #TODO: Add support for selective update
            
    def add_many(self,name,items):
        
        with self.lock:
            cursor = self.db.cursor()
        
            if (isinstance(items,list)):
                cursor.execute('''insert or replace into ''' + name + ''' (prefix, next_hop, origin, as_path, communities, med,
                        atomic_aggregate) values(?,?,?,?,?,?,?)''', items)
            
    def get(self,name,key):
        with self.lock:
            cursor = self.db.cursor()
            cursor.execute('''select * from ''' + name + ''' where prefix = ?''', (key,))
        
            return cursor.fetchone()
    
    def get_all(self,name,key=None):
        
        with self.lock:
            cursor = self.db.cursor()
        
            if (key is not None):
                cursor.execute('''select * from ''' + name + ''' where prefix = ?''', (key,))
            else:
                cursor.execute('''select * from ''' + name)
        
            return cursor.fetchall()
    
    def filter(self,name,item,value):
            
        with self.lock:
            cursor = self.db.cursor()
        
            script = "select * from " + name + " where " + item + " = '" + value + "'"
        
            cursor.execute(script)
        
            return cursor.fetchall()
    
    def update(self,name,key,item,value):
        
        with self.lock:
            cursor = self.db.cursor()
        
            script = "update " + name + " set " + item + " = '" + value + "' where prefix = '" + key + "'"
        
            cursor.execute(script)
            
    def update_many(self,name,key,item):
        
        with self.lock:
            cursor = self.db.cursor()
        
            if (isinstance(item,tuple) or isinstance(item,list)):
                cursor.execute('''update ''' + name + ''' set next_hop = ?, origin = ?, as_path = ?,
                            communities = ?, med = ?, atomic_aggregate = ? where prefix = ?''',
                            (item[0],item[1],item[2],item[3],item[4],item[5],key))
            elif (isinstance(item,dict) or isinstance(item,sqlite3.Row)):
                cursor.execute('''update ''' + name + ''' set next_hop = ?, origin = ?, as_path = ?,
                            communities = ?, med = ?, atomic_aggregate = ? where prefix = ?''', 
                            (item['next_hop'],item['origin'],item['as_path'],item['communities'],item['med'],
                             item['atomic_aggregate'],key))
        
    def delete(self,name,key):
        
        with self.lock:
            # TODO: Add more granularity in the delete process i.e., instead of just prefix, 
            # it should be based on a conjunction of other attributes too.
        
            cursor = self.db.cursor()
        
            cursor.execute('''delete from ''' + name + ''' where prefix = ?''', (key,))
        
    def delete_all(self,name):
        
        with self.lock:
            cursor = self.db.cursor()
        
            cursor.execute('''delete from ''' + name)
    
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

''' main '''     
if __name__ == '__main__':
    
    #TODO Update test
    
    myrib = rib()
    
    myrib['100.0.0.1/16'] = ('172.0.0.2', 'igp', '100, 200, 300', '0', 'false')
    #myrib['100.0.0.1/16'] = ['172.0.0.2', 'igp', '100, 200, 300', '0', 'false']
    #myrib['100.0.0.1/16'] = {'next_hop':'172.0.0.2', 'origin':'igp', 'as_path':'100, 200, 300',
    #                          'med':'0', 'atomic_aggregate':'false'}
    myrib.commit()
    
    myrib.update('100.0.0.1/16', 'next_hop', '190.0.0.2')
    myrib.commit()
    
    val = myrib.filter('as_path', '300')
    
    print val[0]['next_hop']
