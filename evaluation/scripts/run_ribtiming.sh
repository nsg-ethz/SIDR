#!/bin/bash

# Run RIB Update Timing Evaluation

let experiment=$1
example_name="rib_timing_$1"

cd ~/GitHub/supercharged_sdx/examples/"$example_name"/

python ~/GitHub/supercharged_sdx/xctrl/xctrl.py "$example_name" 1 -t -nn -rt &
python ~/GitHub/supercharged_sdx/notifier/notifier.py ~/GitHub/supercharged_sdx/examples/"$example_name"/global.cfg ~/GitHub/supercharged_sdx/examples/"$example_name"/notifications/notifications.log &
python ~/GitHub/supercharged_sdx/policy_submitter/policy_sender.py "$example_name" 1 &

echo "Going to sleep for 400s - $(date +"%T")"
sleep 400s
echo "DONE - now you have to cleanup - $(date +"%T")"