#!/usr/bin/python

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.node import RemoteController, OVSSwitch, Node
from sdnip import BgpRouter, SdnipHost, SDXSwitch

class SDNTopo( Topo ):
    #"TODO: Describe topology"

    def __init__( self, *args, **kwargs ):
        Topo.__init__( self, *args, **kwargs )

        self.routers = {}

        k1 = RemoteController('k1', ip='127.0.0.1', port=2001)

        # Add sdx1 fabric
        sdx1_fabric = {
            'name': 'SDX 1',
            'switch': self.addSwitch( 's1', controller=k1, cls=SDXSwitch ),
            'route_server': '172.1.255.254',
            'as': 65000
        }

        k2 = RemoteController('k2', ip='127.0.0.1', port=2002)

        # Add sdx1 fabric
        sdx2_fabric = {
            'name': 'SDX 2',
            'switch': self.addSwitch( 's2', controller=k2, cls=SDXSwitch ),
            'route_server': '172.2.255.254',
            'as': 65500 
        }        

        # Adds Participants to the IXP
        # Each participant consists of 1 quagga router PLUS
        # 1 host per network advertised behind quagga
        self.routers['a1'] = self.addAutonomousSystem(
            sdx_fabric=sdx1_fabric,
            name = 'a1',
            sdx_interface = {'ip': '172.1.0.1/16', 'mac': '08:00:27:89:3b:9f'},
            other_interfaces = [
                {'ip': '172.3.0.1/16'},
            ],
            networks = ['20.0.0.0/24'],
            AS = 100,
            neighbors = [ {'name': 'z1', 'address': '172.3.0.2', 'as': 800} ]
        )

        self.routers['b1'] = self.addAutonomousSystem(
            sdx_fabric=sdx1_fabric,
            name = 'b1',
            sdx_interface = {'ip': '172.1.0.2/16', 'mac': '08:00:27:92:18:1f'},
            other_interfaces = [
                {'ip': '172.4.0.1/16'},
            ],
            networks = None,
            AS = 200,
            neighbors = [ {'name': 'x1', 'address': '172.4.0.2', 'as': 700} ]
        )
        
        self.routers['c1'] = self.addAutonomousSystem(
            sdx_fabric=sdx1_fabric,
            name = 'c1',
            sdx_interface = {'ip': '172.1.0.3/16', 'mac': '08:00:27:54:56:ea'},
            other_interfaces = [
                {'ip': '172.5.0.1/16'},
            ],
            networks = None,
            AS = 300,
            neighbors = [{'name': 'f1', 'address': '172.5.0.2', 'as': 600, 'local_pref': 500}]
        )
        
        self.routers['d1'] = self.addAutonomousSystem(
            sdx_fabric=sdx2_fabric,
            name = 'd1',
            sdx_interface = {'ip': '172.2.0.1/16', 'mac': '08:00:27:bd:f8:b2'},
            other_interfaces = [
                {'ip': '172.6.0.1/16'},
            ],
            networks = ['30.0.0.0/24'],
            AS = 400,
            neighbors = [{'name': 'z1', 'address': '172.6.0.2', 'as': 800, 'local_pref': 500}]
        )

        self.routers['e1'] = self.addAutonomousSystem(
            sdx_fabric=sdx2_fabric,
            name = 'e1',
            sdx_interface = {'ip': '172.2.0.2/16', 'mac': '08:00:27:11:ff:aa'},
            other_interfaces = [
                {'ip': '172.7.0.1/16'},
            ],
            networks = None,
            AS = 500,
            neighbors = [{'name': 'x1', 'address': '172.7.0.2', 'as': 700}]
        )

        self.routers['f1'] = self.addAutonomousSystem(
            sdx_fabric=sdx2_fabric,
            name = 'f1',
            sdx_interface = {'ip': '172.2.0.3/16', 'mac': '08:00:27:22:3b:34'},
            other_interfaces = [
                {'ip': '172.5.0.2/16'},
            ],
            networks = None,
            AS = 600,
            neighbors = [{'name': 'c1', 'address': '172.5.0.1', 'as': 300}])

        self.routers['x1'] = self.addAutonomousSystem(
            sdx_fabric=None,
            name = 'x1',
            sdx_interface=None,
            other_interfaces = [
                {'ip': '172.4.0.2/16'},
                {'ip': '172.7.0.2/16'},
            ],
            networks = ['10.0.0.0/8'],
            AS = 700,
            neighbors = [
                {'name': 'b1', 'address': '172.4.0.1', 'as': 200},
                {'name': 'e1', 'address': '172.7.0.1', 'as': 500},
            ]
        )
      
        self.routers['z1'] = self.addAutonomousSystem(
            sdx_fabric=None,
            name = 'z1',
            sdx_interface=None,
            other_interfaces = [
                {'ip': '172.3.0.2/16'},
                {'ip': '172.6.0.2/16'}
            ],
            networks = None,
            AS = 800,
            neighbors = [
                {'name': 'a1', 'address': '172.3.0.1', 'as': 100, 'local_pref': 500},
                {'name': 'd1', 'address': '172.6.0.1', 'as': 400},
            ]
        )

        # Add root node for route server of SDX 1 - exaBGP - and connect it to the fabric
        sdx1_rs = self.addHost('rs1', ip = '172.1.255.254/16', mac='08:00:27:89:33:dd', inNamespace = False)
        self.addLink(sdx1_rs, sdx1_fabric['switch'])

        # Add root node for route server of SDX 2 - exaBGP - and connect it to the fabric
        sdx2_rs = self.addHost('rs2', ip = '172.2.255.254/16', mac='08:00:27:89:33:ff', inNamespace = False)
        self.addLink(sdx2_rs, sdx2_fabric['switch'])

    def addAutonomousSystem(self, sdx_fabric, name, sdx_interface, other_interfaces, networks, AS, neighbors):

        # Adds the interface to connect the router to the Route server
        #peereth0 = [{ 'vlan' : 1, 'mac' : mac, 'ipAddrs' : [ip] }]

        intfs = {}

        if sdx_interface:
            peereth0 = [{'ipAddrs' : [sdx_interface['ip']] }]
            if 'mac' in sdx_interface:
                peereth0[0]['mac'] = sdx_interface['mac']
            intfs[name+'-eth0'] = peereth0

        # Adds 1 gateway interface for each network connected to the router
        if networks:
            for net in networks:
                eth = { 'ipAddrs' : [ replace_ip( net, '254') ] } # ex.: 100.0.0.254
                i = len(intfs)
                intfs[ name+'-eth'+str(i) ]=eth

        for interface in other_interfaces:
            peereth0 = [{'ipAddrs' : [interface['ip']] }]
            if 'mac' in interface:
                peereth0[0]['mac'] = interface['mac']
            i = len(intfs)
            intfs[name+'-eth'+str(i)] = peereth0

        if not neighbors:
            neighbors = []

        if sdx_fabric:
            neighbors.insert(0, { 'name': sdx_fabric['name'], 'address' : sdx_fabric['route_server'], 
                                  'as' : sdx_fabric['as'] })

        # Set up the peer router
        peer = self.addHost(name, intfDict=intfs, asNum=AS, neighbors=neighbors, routes=networks, cls=BgpRouter)
        
        if sdx_fabric:
            self.addLink(sdx_fabric['switch'], peer)
        
        # Adds a host connected to the router via the gateway interface
        if networks:
            i=0
            for net in networks:
                i=i+1
                ips = [ replace_ip( net, '1' ) ] # ex.: 100.0.0.1/24
                hostname = 'h' + str(i) + '_' + name # ex.: h1_a1
                host = self.addHost( hostname , cls=SdnipHost, ips=ips, 
                         gateway = replace_ip( net, '254').split('/')[0]) #ex.: 100.0.0.254
                # Set up data plane connectivity
                self.addLink( peer, host )

        # Add connections to neighbors
        for neighbor in neighbors:
            print "CONNECT"
            if neighbor['name'] in self.routers:
                print "YES"
                self.addLink(peer, self.routers[neighbor['name']])

        return peer


def replace_ip(network,ip):
    net,subnet=network.split('/')
    gw=net.split('.')
    gw[3]=ip
    gw='.'.join(gw)
    gw='/'.join([gw,subnet])
    return gw


if __name__ == "__main__":
    setLogLevel('info')
    topo = SDNTopo()

    net = Mininet(topo=topo, controller=RemoteController, switch=SDXSwitch)

    net.start()

    CLI(net)

    net.stop()

    info("done\n")
