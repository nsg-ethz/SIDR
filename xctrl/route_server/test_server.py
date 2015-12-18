#!/usr/bin/env python
#  Author:
#  Muhammad Shahbaz (muhammad.shahbaz@gatech.edu)

import os
from threading import Thread
from multiprocessing import Queue
from multiprocessing.connection import Listener
from Queue import Empty


class Server(object):
    def __init__(self, base_path, id):
        self.sender_queue = Queue()
        self.receiver_queue = Queue()

        self.base_path = base_path
        self.file = os.path.join(base_path, "bgp", str(id) + ".log")
        
    def start(self):
        sender = Thread(target=_sender, args=(self.file, self.sender_queue))
        sender.start()
        
        receiver = Thread(target=_receiver, args=(self.file, self.receiver_queue))
        receiver.start()
    

def _sender(file, queue):
    while True:
        try:
            line = queue.get()
            print "Announce: " + str(line)
        except Empty:
            pass
        

def _receiver(file, queue):
    with open(file, 'r') as f:
        for line in f:
            queue.put(line)
