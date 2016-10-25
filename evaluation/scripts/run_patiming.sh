#!/bin/bash

# Run Policy Activation Timing Evaluation


for i in 1 5 10 15 20 25 30 40 45 50; do

    example_name="pa_timing_$i"

    cd ~/GitHub/supercharged_sdx/examples/"$example_name"/

    python ~/GitHub/supercharged_sdx/xctrl/xctrl.py "$example_name" 1 -t -nn -pt &
    pid1=$!
    python ~/GitHub/supercharged_sdx/notifier/notifier.py ~/GitHub/supercharged_sdx/examples/"$example_name"/global.cfg ~/GitHub/supercharged_sdx/examples/"$example_name"/notifications/notifications.log &
    pid2=$!
    python ~/GitHub/supercharged_sdx/policy_submitter/policy_sender.py "$example_name" 1 &
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
