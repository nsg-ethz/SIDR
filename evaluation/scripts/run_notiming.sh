#!/bin/bash

# Run Notification Timing Evaluation


for i in 50 100 150 200 250 300 350 400 450 500; do

    example_name="not_timing_$i"

    cd ~/GitHub/supercharged_sdx/examples/"$example_name"/

    python ~/GitHub/supercharged_sdx/xctrl/xctrl.py "$example_name" 1 -t -nn -nt -ns &
    pid1=$!
    python ~/GitHub/supercharged_sdx/policy_submitter/policy_sender.py "$example_name" 1 &
    pid2=$!
    python ~/GitHub/supercharged_sdx/notifier/notifier.py ~/GitHub/supercharged_sdx/examples/"$example_name"/global.cfg ~/GitHub/supercharged_sdx/examples/"$example_name"/notifications/notifications.log &
    pid3=$!

    echo "Going to sleep for 400s - $(date +"%T")"
    sleep 400s
    echo "DONE - now you have to cleanup - $(date +"%T")"

    sudo kill -9 "$pid1"
    sudo kill -9 "$pid2"
    sudo kill -9 "$pid3"

    rm ~/GitHub/supercharged_sdx/xctrl/route_server/ribs/*
    rm ~/GitHub/supercharged_sdx/xctrl/loop_detection/cibs/*

    sleep 5s

done
