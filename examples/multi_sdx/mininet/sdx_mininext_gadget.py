#!/usr/bin/python

"Multi SDX topology to observer forwarding anomalities"

import inspect, os, sys, atexit
# Import topo from Mininext
from mininext.topo import Topo
# Import quagga service from examples
from mininext.services.quagga import QuaggaService
# Other Mininext specific imports
from mininext.net import MiniNExT as Mininext
from mininext.cli import CLI
import mininext.util
# Imports from Mininet
import mininet.util
mininet.util.isShellBuiltin = mininext.util.isShellBuiltin
sys.modules['mininet.util'] = mininet.util

from mininet.util import dumpNodeConnections
from mininet.node import RemoteController
from mininet.node import Node
from mininet.node import OVSSwitch
from mininet.link import Link
from mininet.log import setLogLevel, info
from collections import namedtuple
#from mininet.term import makeTerm, cleanUpScreens
QuaggaHost = namedtuple("QuaggaHost", "name ip mac sdx sdx_port")
net = None

k0 = RemoteController('k0', ip='127.0.0.1', port=7733)
k1 = RemoteController('k1', ip='127.0.0.1', port=5533)
cmap = { 's1' : k0, 's2' : k1 }

class SDXSwitch( OVSSwitch ):
    "Custom Switch that connects to allows to connect to several Controllers"
    def start( self, controllers ):
        return OVSSwitch.start( self, [ cmap[ self.name ] ] )

class QuaggaTopo( Topo ):
    "Quagga topology example."

    def __init__( self ):

        "Initialize topology"
        Topo.__init__( self )

        "Directory where this file / script is located"
        scriptdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))) # script directory

        "Initialize a service helper for Quagga with default options"
        quaggaSvc = QuaggaService(autoStop=False)

        "Path configurations for mounts"
        quaggaBaseConfigPath=scriptdir + '/configs/'

        "List of Quagga host configs"
        quaggaHosts = []
        ## AS A
        quaggaHosts.append(QuaggaHost(name = 'a1', ip = '172.0.0.1/16', mac = '08:00:27:89:3b:9f', sdx = 1, sdx_port = 1))
        ## AS B
        quaggaHosts.append(QuaggaHost(name = 'b1', ip = '172.0.0.2/16', mac = '08:00:27:92:18:1f', sdx = 1, sdx_port = 2))
        ## AS C
        quaggaHosts.append(QuaggaHost(name = 'c1', ip = '172.0.0.3/16', mac = '08:00:27:54:56:ea', sdx = 1, sdx_port = 3))
        ## AS D
        quaggaHosts.append(QuaggaHost(name = 'd1', ip = '172.255.0.1/16', mac = '08:00:27:bd:f8:b2', sdx = 2, sdx_port = 1))
        ## AS E
        quaggaHosts.append(QuaggaHost(name = 'e1', ip = '172.255.0.2/16', mac = '08:00:27:11:ff:aa', sdx = 2, sdx_port = 2))
        ## AS F
        quaggaHosts.append(QuaggaHost(name = 'f1', ip = '172.255.0.3/16', mac = '08:00:27:22:3b:34', sdx = 2, sdx_port = 3))
        ## AS X
        quaggaHosts.append(QuaggaHost(name = 'x1', ip = '172.2.0.2/16', mac = None, sdx = 0, sdx_port = 0))
        ## AS Z
        quaggaHosts.append(QuaggaHost(name = 'z1', ip = '172.1.0.2/16', mac = None, sdx = 0, sdx_port = 0))

        ## SDX 1
        "Add switch for fabric of SDX 1"
        sdx1_fabric = self.addSwitch( 's1' )

        " Add root node for route server of SDX 1 - exaBGP - and connect it to the fabric. "
        sdx1_rs = self.addHost('rs1', ip = '172.0.255.254/16', inNamespace = False)
        self.addLink(sdx1_rs, sdx1_fabric, port2 = 4)

        ## SDX 2
        "Add switch for fabric of SDX 2"
        sdx2_fabric = self.addSwitch( 's2' )

        " Add root node for route server of SDX 2 - exaBGP - and connect it to the fabric. "
        sdx2_rs = self.addHost('rs2', ip = '172.255.255.254/16', inNamespace = False)
        self.addLink(sdx2_rs, sdx2_fabric, port2 = 4)
   
        ## AS Border Routers
        "Setup each legacy router, add a link between it and the IXP fabric"
        routers = {}

        for host in quaggaHosts:
            "Set Quagga service configuration for this node"
            quaggaSvcConfig = \
            { 'quaggaConfigPath' : scriptdir + '/configs/' + host.name }

            routers[host.name] = self.addHost( name=host.name,
                                              ip=host.ip,
					      mac=host.mac,
                                              privateLogDir=True,
                                              privateRunDir=True,
                                              inMountNamespace=True,
                                              inPIDNamespace=True)
            self.addNodeService(node=host.name, service=quaggaSvc,
                                nodeConfig=quaggaSvcConfig)
            "Attach the quaggaContainer to the IXP Fabric Switch"
            if (host.sdx == 1):
                self.addLink( routers[host.name], sdx1_fabric , port1=0, port2=host.sdx_port)
            elif (host.sdx == 2):
                self.addLink( routers[host.name], sdx2_fabric , port1=0, port2=host.sdx_port)

        "Connect border routers"
        # A -- Z
        self.addLink( routers['a1'], routers['z1'] , port1=1, port2=0)
        # Z -- D
        self.addLink( routers['d1'], routers['z1'] , port1=1, port2=1)
        # B -- X
        self.addLink( routers['b1'], routers['x1'] , port1=1, port2=0)
        # E -- X
        self.addLink( routers['e1'], routers['x1'] , port1=1, port2=1)
        # C -- F
        self.addLink( routers['c1'], routers['f1'] , port1=1, port2=1)
 

def addInterfacesForSDXNetwork( net ):
    hosts=net.hosts
    print "Configuring participating ASs\n\n"
    for host in hosts:
        print "Host name: ", host.name
        if host.name=='a1':
            host.cmd('sudo ifconfig lo:20 20.0.0.1 netmask 255.255.255.0 up')
            host.cmd('sudo ifconfig a1-eth1 172.1.0.1 netmask 255.255.255.0 up')
            host.cmd('sysctl net.ipv4.ip_forward=1')
            host.cmd('sysctl net.ipv4.conf.all.rp_filter=0')
            host.cmd('sysctl net.ipv4.conf.a1-eth0.rp_filter=0')
            host.cmd('sysctl net.ipv4.conf.a1-eth1.rp_filter=0')
            host.cmd('ifconfig a1-eth0 down && ifconfig a1-eth0 up')
            host.cmd('ifconfig a1-eth1 down && ifconfig a1-eth1 up')
        if host.name=='b1':
            host.cmd('sudo ifconfig b1-eth1 172.2.0.1 netmask 255.255.255.0 up')
            host.cmd('sysctl net.ipv4.ip_forward=1')
            host.cmd('sysctl net.ipv4.conf.all.rp_filter=0')
            host.cmd('sysctl net.ipv4.conf.b1-eth0.rp_filter=0')
            host.cmd('sysctl net.ipv4.conf.b1-eth1.rp_filter=0')
            host.cmd('ifconfig b1-eth0 down && ifconfig b1-eth0 up')
            host.cmd('ifconfig b1-eth1 down && ifconfig b1-eth1 up')
        if host.name=='c1':
            #host.cmd('sudo ifconfig lo:40 40.0.0.1 netmask 255.255.255.0 up')
            host.cmd('sudo ifconfig c1-eth1 172.3.0.1 netmask 255.255.255.0 up')
            host.cmd('sysctl net.ipv4.ip_forward=1')
            host.cmd('sysctl net.ipv4.conf.all.rp_filter=0')
            host.cmd('sysctl net.ipv4.conf.c1-eth0.rp_filter=0')
            host.cmd('sysctl net.ipv4.conf.c1-eth1.rp_filter=0')
            host.cmd('ifconfig c1-eth0 down && ifconfig c1-eth0 up')
            host.cmd('ifconfig c1-eth1 down && ifconfig c1-eth1 up')
        if host.name=='d1':
            host.cmd('sudo ifconfig lo:30 30.0.0.1 netmask 255.255.255.0 up')
            host.cmd('sudo ifconfig d1-eth1 172.4.0.1 netmask 255.255.255.0 up')
            host.cmd('sysctl net.ipv4.ip_forward=1')
            host.cmd('sysctl net.ipv4.conf.all.rp_filter=0')
            host.cmd('sysctl net.ipv4.conf.d1-eth0.rp_filter=0')
            host.cmd('sysctl net.ipv4.conf.d1-eth1.rp_filter=0')
            host.cmd('ifconfig d1-eth0 down && ifconfig d1-eth0 up')
            host.cmd('ifconfig d1-eth1 down && ifconfig d1-eth1 up')
        if host.name=='e1':
            host.cmd('sudo ifconfig e1-eth1 172.5.0.1 netmask 255.255.255.0 up')
            host.cmd('sysctl net.ipv4.ip_forward=1')
            host.cmd('sysctl net.ipv4.conf.all.rp_filter=0')
            host.cmd('sysctl net.ipv4.conf.e1-eth0.rp_filter=0')
            host.cmd('sysctl net.ipv4.conf.e1-eth1.rp_filter=0')
            host.cmd('ifconfig e1-eth0 down && ifconfig e1-eth0 up')
            host.cmd('ifconfig e1-eth1 down && ifconfig e1-eth1 up')
        if host.name=='f1':
            #host.cmd('sudo ifconfig lo:50 50.0.0.1 netmask 255.255.255.0 up')
            host.cmd('sudo ifconfig f1-eth1 172.3.0.2 netmask 255.255.255.0 up')
            host.cmd('sysctl net.ipv4.ip_forward=1')
            host.cmd('sysctl net.ipv4.conf.all.rp_filter=0')
            host.cmd('sysctl net.ipv4.conf.f1-eth0.rp_filter=0')
            host.cmd('sysctl net.ipv4.conf.f1-eth1.rp_filter=0')
            host.cmd('ifconfig f1-eth0 down && ifconfig f1-eth0 up')
            host.cmd('ifconfig f1-eth1 down && ifconfig f1-eth1 up')
        if host.name=='x1':
            host.cmd('sudo ifconfig x1-eth1 172.5.0.2 netmask 255.255.255.0 up')
            host.cmd('sudo ifconfig lo:10 10.0.0.1 netmask 255.255.255.0 up')
            host.cmd('sysctl net.ipv4.ip_forward=1')
            host.cmd('sysctl net.ipv4.conf.all.rp_filter=0')
            host.cmd('sysctl net.ipv4.conf.x1-eth0.rp_filter=0')
            host.cmd('sysctl net.ipv4.conf.x1-eth1.rp_filter=0')
            host.cmd('ifconfig x1-eth0 down && ifconfig x1-eth0 up')
            host.cmd('ifconfig x1-eth1 down && ifconfig x1-eth1 up')
        if host.name=='z1':
            host.cmd('sudo ifconfig z1-eth1 172.4.0.2 netmask 255.255.255.0 up')
            host.cmd('sysctl net.ipv4.ip_forward=1')
            host.cmd('sysctl net.ipv4.conf.all.rp_filter=0')
            host.cmd('sysctl net.ipv4.conf.z1-eth0.rp_filter=0')
            host.cmd('sysctl net.ipv4.conf.z1-eth1.rp_filter=0')
            host.cmd('ifconfig z1-eth0 down && ifconfig z1-eth0 up')
            host.cmd('ifconfig z1-eth1 down && ifconfig z1-eth1 up')
        if host.name == "rs1":
            host.cmd( 'route add -net 172.0.0.0/16 dev rs1-eth0')
        if host.name == "rs2":
            host.cmd( 'route add -net 172.255.0.0/16 dev rs2-eth0')


def startNetwork():
    info( '** Creating Quagga network topology\n' )
    topo = QuaggaTopo()
    global net
    net = Mininext(topo=topo, switch=SDXSwitch, build=False)

    "Controller"
    net.addController(k0)
    net.addController(k1)

    net.build()
    
    info( '** Starting the network\n' )
    net.start()
        
    info( '**Adding Network Interfaces for SDX Setup\n' )    
    addInterfacesForSDXNetwork(net)
    
    info( '** Running CLI\n' )
    CLI( net )

def stopNetwork():
    if net is not None:
        info( '** Tearing down Quagga network\n' )
        net.stop()

if __name__ == '__main__':
    # Force cleanup on exit by registering a cleanup function
    atexit.register(stopNetwork)

    # Tell mininet to print useful information
    setLogLevel('info')
    startNetwork()
