#!/usr/bin/env python
#  Author:
#  Rudiger Birkner (Networked Systems Group ETH Zurich)

import sys
import socket
import struct
import binascii
from threading import Thread

from xctrl.lib import XCTRLModule


class ARPProxy(XCTRLModule):
    (ETH_HEADER_LENGTH, ARP_HEADER_LENGTH, ETH_BROADCAST, ETH_TYPE_ARP) = (14, 28, 'ff:ff:ff:ff:ff:ff', 0x0806)

    def __init__(self, config, event_queue, debug, vmac_encoder):
        super(ARPProxy, self).__init__(config, event_queue, debug)

        self.vmac_encoder = vmac_encoder
        
        self.run = False
        
        # open socket
        self.host = socket.gethostbyname(socket.gethostname())
        
        try:
            self.raw_socket = socket.socket( socket.AF_PACKET , socket.SOCK_RAW , socket.ntohs(ARPProxy.ETH_TYPE_ARP))
            self.raw_socket.bind((self.config.arp_proxy.interface, 0))
            self.raw_socket.settimeout(1.0)
        except socket.error as msg:
            self.logger.debug('Failed to create socket. Error Code : ' + str(msg[0]) + ' Message ' + msg[1])
            sys.exit()
        
    def start(self):
        self.run = True
        while self.run:
            # receive arp requests
            try:
                packet = self.raw_socket.recvfrom(65565)

                packet = packet[0]
                
                eth_frame = self.parse_eth_frame(packet[0:ARPProxy.ETH_HEADER_LENGTH])
                arp_packet = self.parse_arp_packet(packet[ARPProxy.ETH_HEADER_LENGTH:(ARPProxy.ETH_HEADER_LENGTH +
                                                                                      ARPProxy.ARP_HEADER_LENGTH)])

                arp_type = struct.unpack("!h", arp_packet["oper"])[0]
                self.logger.debug('ARP-PROXY: received ARP-' + ('REQUEST' if (arp_type == 1) else 'REPLY') + ' SRC: '
                                 + eth_frame['src_mac'] + ' '+arp_packet['src_ip'] + 'DST: ' + eth_frame['dst_mac'] +
                                 ' ' + arp_packet['dst_ip'])

                if arp_type == 1:
                    # check if the arp request stems from one of the participants
                    if eth_frame["src_mac"] in self.config.portmac_2_participant:
                        # then craft reply using VNH to VMAC mapping
                        self.logger.debug('Crafting REPLY for received Request')
                        vmac_addr = self.vmac_encoder.vmac(arp_packet["dst_ip"],
                                         self.config.portmac_2_participant[eth_frame["src_mac"]],
                                         self.config)

                        # only send arp request if a vmac exists
                        if vmac_addr <> "":
                            self.logger.debug('ARP-PROXY: reply with VMAC ' + vmac_addr)

                            data = self.craft_arp_packet(arp_packet, vmac_addr)
                            eth_packet = self.craft_eth_frame(eth_frame, vmac_addr, data)

                            self.raw_socket.send(''.join(eth_packet))
                            
            except socket.timeout:
                self.logger.debug('Socket Timeout Occured')

    def stop(self):
        self.run = False
        self.raw_socket.close()

    @staticmethod
    def parse_eth_frame(frame):
        eth_detailed = struct.unpack("!6s6s2s", frame)
    
        eth_frame = {"dst_mac": ':'.join('%02x' % ord(b) for b in eth_detailed[0]),
                     "src_mac": ':'.join('%02x' % ord(b) for b in eth_detailed[1]),
                     "type": eth_detailed[2]}
        
        return eth_frame

    @staticmethod
    def parse_arp_packet(packet):
        arp_detailed = struct.unpack("2s2s1s1s2s6s4s6s4s", packet)
    
        arp_packet = {"htype": arp_detailed[0],
                      "ptype": arp_detailed[1],
                      "hlen": arp_detailed[2],
                      "plen": arp_detailed[3],
                      "oper": arp_detailed[4],
                      "src_mac": ':'.join('%02x' % ord(b) for b in arp_detailed[5]),
                      "src_ip": socket.inet_ntoa(arp_detailed[6]),
                      "dst_mac": ':'.join('%02x' % ord(b) for b in arp_detailed[7]),
                      "dst_ip": socket.inet_ntoa(arp_detailed[8])}
                      
        return arp_packet

    @staticmethod
    def craft_arp_packet(packet, dst_mac):
        arp_packet = [
            packet["htype"],
            packet["ptype"],
            packet["hlen"],
            packet["plen"],
            struct.pack("!h", 2),
            binascii.unhexlify(dst_mac.replace(':', '')),
            socket.inet_aton(packet["dst_ip"]),
            binascii.unhexlify(packet["src_mac"].replace(':', '')),
            socket.inet_aton(packet["src_ip"])]     
            
        return arp_packet  

    @staticmethod
    def craft_eth_frame(frame, dst_mac, data):
        eth_frame = [
            binascii.unhexlify(frame["src_mac"].replace(':', '')),
            binascii.unhexlify(dst_mac.replace(':', '')),
            frame["type"],
            ''.join(data)]
        
        return eth_frame

    def send_gratuitous_arp(self, changes):
        # then craft reply using VNH to VMAC mapping
        vmac_addr = self.vmac_encoder.vmac(changes["VNH"], changes["participant"])
        
        dst_mac = self.vmac_encoder.vmac_best_path(changes["participant"])

        arp_packet = [
            # HTYPE
            struct.pack("!h", 1),
            # PTYPE (IPv4)
            struct.pack("!h", 0x0800),
            # HLEN
            struct.pack("!B", 6),
            # PLEN
            struct.pack("!B", 4),
            # OPER (reply)
            struct.pack("!h", 2),
            # SHA
            binascii.unhexlify(vmac_addr.replace(':', '')),
            # SPA
            socket.inet_aton(str(changes["VNH"])),
            # THA
            binascii.unhexlify(vmac_addr.replace(':', '')),
            # TPA
            socket.inet_aton(str(changes["VNH"]))
        ]
        eth_frame = [
            # Destination address:
            binascii.unhexlify(dst_mac.replace(':', '')),
            # Source address:
            binascii.unhexlify(vmac_addr.replace(':', '')),
            # Protocol
            struct.pack("!h", ARPProxy.ETH_TYPE_ARP),
            # Data
            ''.join(arp_packet)
        ]
                
        self.raw_socket.send(''.join(eth_frame))


class ARPProxyConfig(object):
    def __init__(self, interface):
        self.interface = interface

        
''' main '''    
if __name__ == '__main__':
    # start arp proxy    
    sdx_ap = ARPProxy()
    ap_thread = Thread(target=sdx_ap.start)
    ap_thread.start()
    
    ap_thread.join()
