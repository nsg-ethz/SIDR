# Multi-SDX Deployment

## Usage
__Mininet__ 
```bash
$ cd ~/supercharged_sdx/examples/multi_sdx/mininet  
$ sudo ./sdx_mininext_gadget.py  
```

### SDX 1
Start __Ryu__ - The Controller  

```bash
$ ryu-manager ~/supercharged_sdx/ctrl/asdx.py --asdx-dir multi_sdx --asdx-controller 1
```

Start the __Route Server__  

```bash
$ cd ~/supercharged_sdx/xrs
$ sudo ./route_server.py multi_sdx 1
```

Start __ExaBGP__  

```bash
$ exabgp ~/supercharged_sdx/examples/multi_sdx/controller-1/sdx_config/bgp.conf --env ~/supercharged_sdx/examples/multi_sdx/controller-1/sdx_config/exabgp.env
```

### SDX 2
Start __Ryu__ - The Controller

```bash
$ ryu-manager ~/supercharged_sdx/ctrl/asdx.py --asdx-dir multi_sdx --asdx-controller 2
```

Start the __Route Server__

```bash
$ cd ~/supercharged_sdx/xrs
$ sudo ./route_server.py multi_sdx 2
```

Start __ExaBGP__

```bash
$ exabgp ~/supercharged_sdx/examples/multi_sdx/controller-2/sdx_config/bgp.conf --env ~/supercharged_sdx/examples/multi_sdx/controller-2/sdx_config/exabgp.env
```

After using it, make sure to __remove__ old RIBs  

```bash
$ sudo rm ~/sdx-ryu/xrs/ribs/172.0.0.* 
```
    
## Test the "multi_sdx" Example

### Policies

The participants have specified the following policies:  

_Participant A - outbound:_

    matcht(dstport=80) >> fwd(C)

_Participant F - outbound:_

    match(dstport = 80) >>  fwd(D)

### Tests

#### 1  

    mininext> x1 iperf -s -B 10.0.0.1 -p 80 &  
    mininext> a1 iperf -c 30.0.0.1 -B 20.0.0.1 -p 80 -t 2    

#### 2  

    mininext> x1 iperf -s -B 10.0.0.1 -p 4321 &  
    mininext> a1 iperf -c 30.0.0.1 -B 20.0.0.1 -p 4321 -t 2    

#### 3

    mininext> d1 iperf -s -B 30.0.0.1 -p 4322 &
    mininext> a1 iperf -c 30.0.0.1 -B 20.0.0.1 -p 4322 -t 2

In case the `iperf` connection is not successful, you should see the message, `connect failed: Connection refused.`
