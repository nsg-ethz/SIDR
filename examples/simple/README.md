## Simple Example

### Fabric Manager 

```bash
$ ryu-manager ~/SIDR/refmon/refmon.py --refmon-config ~/SIDR/examples/simple/global.cfg --refmon-instance 1 --ofp-tcp-listen-port 6633 --wsapi-port 2101
```

### Mininet
 
```bash
$ sudo python ~/SIDR/examples/simple/mininet/topo.py
```

### SDX Controller

```bash
$ sudo python ~/SIDR/xctrl/xctrl.py simple 1 -d
```

### ExaBGP

```bash
$ exabgp ~/SIDR/examples/simple/sdx_1/bgp.conf --env ~/SIDR/examples/simple/sdx_1/exabgp.env
```

### Clean Up

Be sure to remove the deflection table (CIB) and RIBs.

```bash
$ rm ~/SIDR/xctrl/loop_detection/cibs/*
$ rm ~/SIDR/xctrl/route_server/ribs/*
```

    
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
	
Install the policies:

```bash
$ python ~/SIDR/policy_submitter/policy_sender.py simple 1
```
	

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
