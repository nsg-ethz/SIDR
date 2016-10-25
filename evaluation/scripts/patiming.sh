#!/bin/bash

# Generate Environment for Policy Activation Timing Evaluation

cd ~/GitHub/supercharged_sdx/

for i in 1 5 10 15 20 25 30 35 40 45 50; do
	
	echo num_prefixes

	let num_prefixes=1000*$i
	
	example_name="pa_timing_$i"
	
	mkdir examples/${example_name}/
	mkdir examples/${example_name}/bgp/
	mkdir examples/${example_name}/sdx_1/
	mkdir examples/${example_name}/notifications/
	
	python evaluation/example_generator/config_generator.py 2 examples/${example_name}/
	
	python evaluation/example_generator/pa_rib_generator.py 1 evaluation/prefixes/prefixes.log "${num_prefixes}" "5000,5100;6000,6100;7000,7100" 2 examples/"${example_name}"/bgp/
	
	python evaluation/example_generator/pa_notification_generator.py 2,3 2 evaluation/prefixes/prefixes.log "${num_prefixes}" 0.5 32 examples/"${example_name}"/notifications/
	
	python evaluation/example_generator/policy_generator.py 2 1 100 62 3 examples/"${example_name}"/sdx_1/
done 
