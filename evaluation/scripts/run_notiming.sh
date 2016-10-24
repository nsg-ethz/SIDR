#!/bin/bash

# Run Notification Timing Evaluation

let experiment=$1
example_name="not_timing_$1"

python ~/GitHub/supercharged_sdx/xctrl/xctrl.py "$example_name" 1 -t -nn -nt &
python ~/GitHub/supercharged_sdx/policy_submitter/policy_sender.py "$example_name" 1 &
python ~/GitHub/supercharged_sdx/notifier/notifier.py ~/GitHub/supercharged_sdx/examples/"$example_name"/global.cfg ~/GitHub/supercharged_sdx/examples/"$example_name"/notifications/notifications.log &

echo "Going to sleep for 450s - $(date +"%T")"
sleep 450s
echo "DONE - now you have to cleanup - $(date +"%T")"
