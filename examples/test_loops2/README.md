# Loops2 Test

## Setup
![Loops2 Setup](https://drive.google.com/open?id=0B273jByxJR-IdF9yblRVOFFLaEE)

The two loop tests test how SIDR handles two incoming correcntess messages.

We have four SDXes with three participants each and one with five participants. The participants at an SDX are peering with each other. 100, 400, 700, 1400 and 1700 are advertising the prefix 100/24. We only care for these ASes 300, 600, 900, 1300, 1600 and 1900. They all try to install the following policies:

| ID | SDX | From | To  | Match                    |
|----|-----|------|-----|--------------------------|
| 1  | 1   | 300  | 200 | TCP destination port 443 |
| 2  | 1   | 1300  | 1200 | TCP destination port 443 |
| 3  | 2   | 600  | 500 | TCP destination port 443 |
| 4  | 3   | 900  | 800 | TCP destination port 443 |
| 5  | 12  | 1600  | 1500 | TCP destination port 443 |
| 5  | 13   | 1900  | 1800 | TCP destination port 443 |


## Run Test

### Run xctrl

```bash
$ cd 
$ python ~/supercharged_sdx/xctrl/xctrl.py test_loops2 1 -d -t
$ python ~/supercharged_sdx/xctrl/xctrl.py test_loops2 2 -d -t
$ python ~/supercharged_sdx/xctrl/xctrl.py test_loops2 3 -d -t
$ python ~/supercharged_sdx/xctrl/xctrl.py test_loops2 12 -d -t
$ python ~/supercharged_sdx/xctrl/xctrl.py test_loops2 13 -d -t
```

### Submit Policy Activation Requests

```bash
$ python ~/supercharged_sdx/policy_submitter/policy_sender.py test_loops2 1
$ python ~/supercharged_sdx/policy_submitter/policy_sender.py test_loops2 2
$ python ~/supercharged_sdx/policy_submitter/policy_sender.py test_loops2 3
$ python ~/supercharged_sdx/policy_submitter/policy_sender.py test_loops2 12
$ python ~/supercharged_sdx/policy_submitter/policy_sender.py test_loops2 13
```

### Clean Up

```bash
$ sudo rm ~/supercharged_sdx/xctrl/loop_detection/cibs/*
$ sudo rm ~/supercharged_sdx/xctrl/route_server/ribs/*
```
