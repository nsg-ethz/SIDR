# Multi-SDX Deployment

## Usage

### Fabric Manager 

```bash
$ ryu-manager ~/supercharged_sdx/refmon/refmon.py --refmon-config ~/supercharged_sdx/examples/multi_sdx/global.cfg --refmon-instance 1 --ofp-tcp-listen-port 2001 --wsapi-port 2101
```

```bash
$ ryu-manager ~/supercharged_sdx/refmon/refmon.py --refmon-config ~/supercharged_sdx/examples/multi_sdx/global.cfg --refmon-instance 2 --ofp-tcp-listen-port 2002 --wsapi-port 2102
```

### Mininet
 
```bash
$ sudo python ~/supercharged_sdx/examples/multi_sdx/mininet/topo.py
```

### SDX Controller

```bash
$ sudo python ~/supercharged_sdx/xctrl/xctrl.py multi_sdx 1 -d
```

```bash
$ sudo python ~/supercharged_sdx/xctrl/xctrl.py multi_sdx 2 -d
```

### ExaBGP

```bash
$ exabgp ~/supercharged_sdx/examples/multi_sdx/sdx_1/bgp.conf --env ~/supercharged_sdx/examples/multi_sdx/sdx_1/exabgp.env
```

```bash
$ exabgp ~/supercharged_sdx/examples/multi_sdx/sdx_2/bgp.conf --env ~/supercharged_sdx/examples/multi_sdx/sdx_2/exabgp.env
```

### Clean Up

Be sure to remove the deflection table (CIB) and RIBs.

```bash
$ rm ~/supercharged_sdx/xctrl/loop_detection/cibs/*
$ rm ~/supercharged_sdx/xctrl/route_server/ribs/*
```

## Test the "multi_sdx" Example

### Policies

The participants have specified the following policies:  

_Participant A - outbound:_

    matcht(dstport=80) >> fwd(C)

_Participant F - outbound:_

    match(dstport = 80) >>  fwd(D)

### Tests

First, we try to install a policy at SDX1 to forward all HTTP-traffic (TCP port 80) from participant A to participant C.

```bash
$ python ~/supercharged_sdx/policy_submitter/policy_sender.py multi_sdx 1
```

Second, we try to install a policy at SDX2 to forward all HTTP-traffic (TCP port 80) from participant F to participant D. These policies are conflicting and lead to a loop. SIDR should detect the conflict and block all affected prefixes from being affected by the second policy.

```bash
$ python ~/supercharged_sdx/policy_submitter/policy_sender.py multi_sdx 2
```

#### 1  

    mininext> h1_x1 iperf -s -B 10.0.0.1 -p 80 &  
    mininext> h1_a1 iperf -c 10.0.0.1 -B 20.0.0.1 -p 80 -t 2    

#### 2  

    mininext> h1_x1 iperf -s -B 10.0.0.1 -p 4321 &  
    mininext> h1_a1 iperf -c 10.0.0.1 -B 20.0.0.1 -p 4321 -t 2    

In case the `iperf` connection is not successful, you should see the message, `connect failed: Connection refused.`
