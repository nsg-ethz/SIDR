# Simple Example with Hosts Attached to the Routers

## Usage
__Mininet__ 

    $ cd ~/supercharged_sdx/examples/simple_h/mininet  
    $ sudo ./topo.py  

Start __Ryu__ - The Controller  

    $ ryu-manager ~/supercharged_sdx/ctrl/asdx.py --asdx-dir simple_h --asdx-controller 1

Start the __Route Server__  

    $ cd ~/supercharged_sdx/xrs
    $ sudo ./route_server.py simple_h 1

Start __ExaBGP__  

    $ exabgp ~/supercharged_sdx/examples/simple_h/controller-1/sdx_config/bgp.conf

After using it, make sure to __remove__ old RIBs  

    $ sudo rm ~/supercharged_sdx/xrs/ribs/172.0.0.* 
    
## Run the "simple_h" Example
Check if the route server has correctly advertised the routes  

    mininext> a1 route -n  
    Kernel IP routing table  
    Destination     Gateway         Genmask         Flags Metric Ref    Use Iface  
    140.0.0.0       172.0.1.3       255.255.255.0   UG    0      0        0 a1-eth0  
    150.0.0.0       172.0.1.4       255.255.255.0   UG    0      0        0 a1-eth0  
    172.0.0.0       0.0.0.0         255.255.0.0     U     0      0        0 a1-eth0  

Testing the Policies

The participants have specified the following policies:  

_Participant A - outbound:_

    matcht(dstport=80) >> fwd(B) + match(dstport=4321/4322) >> fwd(C)

_Participant C - inbound:_

    match(dstport = 4321) >>  fwd(C1) + match(dstport=4322) >> fwd(C2)

Starting the  `iperf` servers:  

    mininext> h1_b1 iperf -s -B 140.0.0.1 -p 80 &  
    mininext> h1_c1 iperf -s -B 140.0.0.1 -p 4321 &  
    mininext> h1_c2 iperf -s -B 140.0.0.1 -p 4322 &  

Starting the  `iperf` clients:  

    mininext> h1_a1 iperf -c 140.0.0.1 -B 100.0.0.1 -p 80 -t 2  
    mininext> h1_a1 iperf -c 140.0.0.1 -B 100.0.0.1 -p 4321 -t 2  
    mininext> h1_a1 iperf -c 140.0.0.1 -B 100.0.0.1 -p 4322 -t 2  

Successful `iperf` connections should look like this:  

    mininext> h1_c2 iperf -s -B 140.0.0.1 -p 4322 &  
    mininext> h1_a1 iperf -c 140.0.0.1 -B 100.0.0.1 -p 4322 -t 2  
    ------------------------------------------------------------  
    Client connecting to 140.0.0.1, TCP port 4322  
    Binding to local address 100.0.0.1  
    TCP window size: 85.3 KByte (default)  
    ------------------------------------------------------------  
    [  3] local 100.0.0.1 port 4322 connected with 140.0.0.1 port 4322  
    [ ID] Interval       Transfer     Bandwidth  
    [  3]  0.0- 2.0 sec  1.53 GBytes  6.59 Gbits/sec  

In case the `iperf` connection is not successful, you should see the message, `connect failed: Connection refused.`
