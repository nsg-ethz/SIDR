#!/usr/bin/env python
#  Author:
#  Muhammad Shahbaz (muhammad.shahbaz@gatech.edu)

from threading import Thread
from multiprocessing import Queue
from multiprocessing.connection import Listener
from Queue import Empty


class Server(object):
    def __init__(self, port, key):
        self.listener = Listener(('localhost', port), authkey=str(key))
        
        self.sender_queue = Queue()
        self.receiver_queue = Queue()
        
    def start(self):
        conn = self.listener.accept()
        print 'Connection accepted from', self.listener.last_accepted
        
        sender = Thread(target=_sender, args=(conn, self.sender_queue))
        sender.start()
        
        receiver = Thread(target=_receiver, args=(conn, self.receiver_queue))
        receiver.start()
    

def _sender(conn, queue):
    while True:
        try:
            line = queue.get()
            conn.send(line)
        except Empty:
            pass
        

def _receiver(conn, queue):
    while True:
        try:
            line = conn.recv()
            queue.put(line)
        except Empty:
            pass
