# Test Example

## Run xctrl

```bash
$ cd ~/supercharged_sdx/xctrl
$ sudo python xctrl.py test 1 -d
```

## Submit Policy Activation Requests

```bash
$ cd ~/supercharged_sdx/policy_submitter
$ python policy_sender.py test 1
```

## Clean Up

```bash
$ sudo rm ~/supercharged_sdx/xctrl/loop_detection/cibs/*
$ sudo rm ~/supercharged_sdx/xctrl/route_server/ribs/*
```