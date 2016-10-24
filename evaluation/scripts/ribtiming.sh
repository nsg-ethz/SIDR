#!/bin/bash

# Generate Environment for RIB Update Timing Evaluation

cd ~/GitHub/supercharged_sdx/

for i in 2 50 100 150 250 300 350 400 450 500; do

	let num_participants=$i+1
	let max_participant=101+$i
	
	example_name="rib_timing_$i"
	
	mkdir examples/${example_name}/
	mkdir examples/${example_name}/bgp/
	mkdir examples/${example_name}/sdx_1/
	mkdir examples/${example_name}/notifications/
	
	python evaluation/example_generator/config_generator.py "$num_participants" examples/${example_name}/
	
	python evaluation/example_generator/rib_generator.py 101 100 100.0.0.0/16 "5000,5100;6000,6100;7000,7100" 62 3 examples/"${example_name}"/bgp/
	
	python evaluation/example_generator/notification_generator.py 2,3 102:"$max_participant" 100.0.0.0/16 1 2 0 examples/"${example_name}"/notifications/
	
	python evaluation/example_generator/policy_generator.py 102:"$max_participant" 101 1 32 0 examples/"${example_name}"/sdx_1/

done 