#!/bin/bash

# Run Policy Activation Timing Evaluation

let experiment=$1
example_name="pa_timing_$1"

python ~/GitHub/supercharged_sdx/xctrl/xctrl.py "$example_name" 1 -t -nn -pt &
python ~/GitHub/supercharged_sdx/notifier/notifier.py ~/GitHub/supercharged_sdx/examples/"$example_name"/global.cfg ~/GitHub/supercharged_sdx/examples/"$example_name"/notifications/notifications.log &
python ~/GitHub/supercharged_sdx/policy_submitter/policy_sender.py "$example_name" 1 &

echo "Going to sleep for 450s"
sleep 450s
echo "DONE - don't forget to cleanup"
