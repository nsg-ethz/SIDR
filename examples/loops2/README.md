# Test Example

## Run xctrl

```bash
$ cd ~/supercharged_sdx/xctrl
$ python xctrl.py test 1 -d
$ python xctrl.py test 2 -d
$ python xctrl.py test 3 -d
```

## Submit Policy Activation Requests

```bash
$ cd ~/supercharged_sdx/policy_submitter
$ python policy_sender.py test 1
$ python policy_sender.py test 2
$ python policy_sender.py test 3
```

## Clean Up

```bash
$ sudo rm ~/supercharged_sdx/xctrl/loop_detection/cibs/*
$ sudo rm ~/supercharged_sdx/xctrl/route_server/ribs/*
```