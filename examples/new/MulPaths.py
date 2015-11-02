#!/usr/bin/python

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.node import RemoteController, OVSSwitch, Node
from sdnip import BgpRouter, SdnipHost

class SDNTopo( Topo ):
    #"TODO: Describe topology"
# 5 participants to the SDX , 2 transienr routers- ASes , 3 routers for 1 AS
    def __init__( self, *args, **kwargs ):
        Topo.__init__( self, *args, **kwargs )
        # Add switch for IXP fabric
        ixpfabric = self.addSwitch( 's1' )

        # Adds Participants to the IXP
        # Each participant consists of 1 quagga router PLUS
        # 1 host per network advertised behind quagga
        self.addParticipant(fabric=ixpfabric, name = 'a1', mac = '08:00:27:89:3b:9f', 
           ip = '172.0.0.01/16', networks = ['140.0.0.0/24'], AS = 200)

        self.addParticipant(fabric=ixpfabric, name = 'b1', mac = '08:00:27:92:18:1f', 
           ip = '172.0.0.2/16', networks = ['150.0.0.0/24'], AS = 300)
        
        self.addParticipant(fabric=ixpfabric, name = 'c1', mac='08:00:27:54:56:ea',
           ip = '172.0.0.3/16', networks = ['130.0.0.0/24'], AS = 400)
        
        self.addParticipant(fabric=ixpfabric, name = 'd1', mac = '08:00:27:bd:f8:b2',
           ip = '172.0.0.4/16', networks = ['120.0.0.0/24'], AS = 100)
 	
     
        self.addParticipant(fabric=ixpfabric, name = 'e1', mac = '08:10:27:bd:f8:b2',
           ip = '172.0.0.6/16', networks = ['110.0.0.0/24'], AS = 500)



##### Routers in the middle

        self.addRouter( name = 'f1', mac = '09:00:27:bd:f8:b2',
                 ip = '172.1.0.1/16', networks = ['172.1.0.0/24'], AS = 500,neighbors=[ { 'address' : 172.0.0.1, 'as' : 200 },{ 'address' : 172.2.0.1, 'as' : 800 } ])

        self.addRouter( name = 'g1', mac = '06:00:27:bd:f8:b2',
           ip = '172.3.0.1/16', networks = ['172.3.0.0/24'], AS = 600,neighbors=[ { 'address' : 172.1.0.2, 'as' : 300 },{ 'address' : 172.2.0.2, 'as' : 800 } ])

###### AS with 3routers

        self.addRouter( name = 'v1', mac = '05:00:27:bd:f8:b2',
           ip = '172.2.0.1/16', networks = ['172.2.0.0/24'], AS = 800,neighbors=[ { 'address' : 172.1.0.1, 'as' : 500 } ])
        self.addRouter(name = 'v2', mac = '03:00:27:bd:f8:b2',
           ip = '172.2.0.2/16', networks = ['172.2.0.0/24'], AS = 800,neighbors=[ { 'address' : 172.3.0.1, 'as' : 600 } ])
        self.addRouter( name = 'v3', mac = '04:00:27:bd:f8:b2',
           ip = '172.2.0.3/16', networks = ['172.2.0.0/24'], AS = 800, neighbors=[ { 'address' : 172.0.0.3, 'as' : 400 } ])
     

        # Add root node for ExaBGP. ExaBGP acts as route server for SDX.
        root = self.addHost('exabgp', ip = '172.0.255.254/16', inNamespace = False)
        self.addLink(root, ixpfabric)
	



	# A -- F
        self.addLink( routers['a1'], routers['f1'] , port1=1, port2=0)
        # F--- V1
        self.addLink( routers['f1'], routers['v1'] , port1=1, port2=0)
        # B -- G
        self.addLink( routers['b1'], routers['g1'] , port1=1, port2=0)
        # G -- V
        self.addLink( routers['g1'], routers['v2'] , port1=1, port2=0)    
        # C -- V
        self.addLink( routers['c1'], routers['v1'] , port1=1, port2=0)
	
    def addParticipant(self,fabric,name,mac,ip,networks,AS):

        SDX_IP='172.0.255.254'
        # Adds the interface to connect the router to the Route server
        #peereth0 = [{ 'vlan' : 1, 'mac' : mac, 'ipAddrs' : [ip] }]
        peereth0 = [{'mac' : mac, 'ipAddrs' : [ip] }]
        intfs = { name+'-eth0' : peereth0}

        # Adds 1 gateway interface for each network connected to the router
        for net in networks:
            eth = { 'ipAddrs' : [ replace_ip( net, '254') ] } # ex.: 100.0.0.254
            i = len( intfs )
            intfs[ name+'-eth'+str(i) ]=eth
        neighbors = [ { 'address' : SDX_IP, 'as' : 65000 } ]

        # Set up the peer router
        peer = self.addHost( name, intfDict=intfs, asNum=AS,
                          neighbors=neighbors, routes=networks, cls=BgpRouter)
	self.addLink( fabric, peer)
        
        # Adds a host connected to the router via the gateway interface
        i=0
        for net in networks:
            i=i+1
            ips = [ replace_ip( net, '1' ) ] # ex.: 100.0.0.1/24
            hostname = 'h' + str(i) + '_' + name # ex.: h1_a1
            host = self.addHost( hostname , cls=SdnipHost, ips=ips, 
                     gateway = replace_ip( net, '254').split('/')[0]) #ex.: 100.0.0.254
            # Set up data plane connectivity
            self.addLink( peer, host )

    def addRouter(self,name,mac,ip,networks,AS,neighbors):

        # Adds the interface to connect the router to the Route server
        #peereth0 = [{ 'vlan' : 1, 'mac' : mac, 'ipAddrs' : [ip] }]
                peereth0 = [{'mac' : mac, 'ipAddrs' : [ip] }]
                intfs = { name+'-eth0' : peereth0}

        # Adds 1 gateway interface for each network connected to the router
        for net in networks:
            eth = { 'ipAddrs' : [ replace_ip( net, '254') ] } # ex.: 100.0.0.254
            i = len( intfs )
            intfs[ name+'-eth'+str(i) ]=eth
        # Set up the peer router
        peer = self.addHost( name, intfDict=intfs, asNum=AS,
                          neighbors=neighbors, routes=networks, cls=BgpRouter)
               # self.addLink( fabric, peer)

        # Adds a host connected to the router via the gateway interface
        i=0
        for net in networks:
            i=i+1
            ips = [ replace_ip( net, '1' ) ] # ex.: 100.0.0.1/24
            hostname = 'h' + str(i) + '_' + name # ex.: h1_a1
            host = self.addHost( hostname , cls=SdnipHost, ips=ips,
                     gateway = replace_ip( net, '254').split('/')[0]) #ex.: 100.0.0.254
            # Set up data plane connectivity
            self.addLink( peer, host )

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

    net = Mininet(topo=topo, controller=RemoteController, switch=OVSSwitch)

    net.start()

    CLI(net)

    net.stop()

    info("done\n")
