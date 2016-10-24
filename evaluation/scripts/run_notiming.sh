#!/bin/bash

# Run Notification Timing Evaluation

let experiment=$1
example_name="not_timing_$i"

python ~/supercharged_sdx/xctrl/xctrl.py "example_name" 1 -t -nn -nt &
python ~/supercharged_sdx/policy_submitter/policy_sender.py "example_name" 1 &
python ~/supercharged_sdx/notifier/notifier.py examples/"example_name"/sdx_global.cfg examples/"example_name"/notifications/notifications.log
