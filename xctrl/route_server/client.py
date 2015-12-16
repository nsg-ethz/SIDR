#!/usr/bin/env python
#  Author:
#  Muhammad Shahbaz (muhammad.shahbaz@gatech.edu)
#  Arpit Gupta

import sys
from threading import Thread
from multiprocessing.connection import Client
import os
import argparse


'''Write output to stdout'''
def _write(stdout,data):
    stdout.write(data + '\n')
    stdout.flush()


''' Sender function '''
def _sender(conn,stdin,log):
    # Warning: when the parent dies we are seeing continual newlines, so we only access so many before stopping
    counter = 0

    while True:
        try:
            line = stdin.readline().strip()
            
            if line == "":
                counter += 1
                if counter > 100:
                    break
                continue
            counter = 0

            conn.send(line)
						
            log.write(line + '\n')
            log.flush()
		
        except:
            pass
	
''' Receiver function '''
def _receiver(conn,stdout,log):
	
    while True:
        try:
            line = conn.recv()
	
            if line == "":
                continue
			
            _write(stdout, line) 
            ''' example: announce route 1.2.3.4 next-hop 5.6.7.8 as-path [ 100 200 ] '''
            
            log.write(line + '\n')
            log.flush()
		
        except:
            pass

''' main '''	
if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, help="port to connect to route server")
    parser.add_argument("--key", help="authentication key to connect to route server")
    args = parser.parse_args()

    port = args.port if args.port else 6000
    key = args.key if args.key else 'xrs'
	
    log = open(logfile, "w")
    log.write('Open Connection \n')
    
    conn = Client(('localhost', port), authkey=key)
    
    sender = Thread(target=_sender, args=(conn,sys.stdin,log))
    sender.start()
    
    receiver = Thread(target=_receiver, args=(conn,sys.stdout,log))
    receiver.start()
    
    sender.join()
    receiver.join()
    
    log.close()
