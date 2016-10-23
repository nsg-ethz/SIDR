# Microbenchmarks

### Test: Policy Activation Timing

In this test, we want to measure how long it takes for a policy activation request to be processed. For this we need to
generate a file to feed to the route server, a file with notifications from remote SDXes, and finally a file with all
the policy activation requests.

The following scripts generate the necessary files:

#### Generate RIB entries

```bash
$ python pa_rib_generator.py <from_participant> <prefix_file> <num_prefixes> <as_paths> <start_time> <out_path>
```

* **from_participant** ASN of the participant which announces these routes
* **prefix_file** file containing the prefixes
* **num_prefixes** number of prefixes that should be used
* **as_paths** a list of AS paths separated by semi-colons from which one is chosen randomly for each announcement (e.g., 1,2,3;2,5,6;3,1;5)
* **start_time** time when the system should start sending the announcements to the route server
* **out_path:** path to the output file

#### Generate Notifications

```bash
$ python pa_notification_generator.py <path> <outpath> <destinations> <exceptions> <ixpparticipants> <-t>
```

* **sender_sdxes** list of remote sdxes (e.g., 2,3)
* **ingress_participant** ASN of ingress participant
* **prefix_file** file containing the prefixes
* **num_prefixes** number of prefixes that should be used
* **probability** probability with which a notification for a specific prefix is generated
* **start_time** time when the system should start sending the announcements to the route server
* **out_path:** path to the output file

#### Generate Policies
```bash
$ python policy_generator.py <from_participants> <to_participants> <start_time> <interval> <out_path>
```

* **from_participants** ASN of ingress participant
* **to_participants** file containing the prefixes
* **start_time** time when the system should start sending the announcements to the route server
* **interval** time between to policy activation requests
* **out_path:** path to the output file


### Test: RIB Update Timing

In this test, we want to measure how long it takes for a rib update to be processed.

The following scripts generate the necessary files:

#### Generate Route Announcements and Withdraws

```bash
$ python rib_generator.py <from_participants> <prefix> <as_paths> <start_time> <interval> <out_path>

$ python rib_generator.py 100 10.0.0.0/8 5001,5002;6001,6002;7001,7002 30 5 examples/test/
```

* **from_participants** ASN of the participant which announces these routes
* **prefix** prefix to be announced
* **as_paths** a list of AS paths separated by semi-colons from which one is chosen randomly for each announcement (e.g., 1,2,3;2,5,6;3,1;5)
* **start_time** time when the system should start sending the announcements to the route server
* **interval** time between two route announcements/withdraws
* **out_path:** path to the output file

#### Generate Notifications

```bash
$ python notification_generator.py <sender_sdxes> <ingress_participants> <prefix> <num_notifications> <start_time> <interval> <out_path>
```

* **sender_sdxes** list of remote sdxes - one is randomly chosen (e.g., 2,3)
* **ingress_participants** range of ASNs of ingress participants (e.g., 2:100)
* **prefix** notification for this prefix
* **num_notifications** number of notifications to send per ingress participant
* **start_time** time when the system should start sending the announcements to the route server
* **interval** time between two notifications
* **out_path:** path to the output file

#### Generate Policies
```bash
$ python policy_generator.py <from_participants> <to_participants> <start_time> <interval> <out_path>
```

* **from_participants** range of ASNs of ingress participants (e.g., 2:100)
* **to_participants** ASN of the participant
* **start_time** time when the system should start sending the announcements to the route server
* **interval** time between to policy activation requests
* **out_path:** path to the output file


### Test: Notification Timing

In this test, we want to measure how long it takes for a notification to be processed.

The following scripts generate the necessary files:

#### Generate Route Announcements and Withdraws

```bash
$ python rib_generator.py <from_participants> <prefix> <as_paths> <start_time> <interval> <out_path>

$ python rib_generator.py 100 10.0.0.0/8 5001,5002;6001,6002;7001,7002 30 5 examples/test/
```

* **from_participants** range of ASNs of ingress participants (e.g., 2:100)
* **prefix** prefix to be announced
* **as_paths** a list of AS paths separated by semi-colons from which one is chosen randomly for each announcement (e.g., 1,2,3;2,5,6;3,1;5)
* **start_time** time when the system should start sending the announcements to the route server
* **interval** time between two route announcements/withdraws
* **out_path:** path to the output file

#### Generate Notifications

```bash
$ python notification_generator.py <sender_sdxes> <ingress_participants> <prefix> <num_notifications> <start_time> <interval> <out_path>
```

* **sender_sdxes** list of remote sdxes - one is randomly chosen (e.g., 2,3)
* **ingress_participants** ASN of ingress participant
* **prefix** notification for this prefix
* **num_notifications** number of notifications to send per ingress participant
* **start_time** time when the system should start sending the announcements to the route server
* **interval** time between two notifications
* **out_path:** path to the output file

#### Generate Policies
```bash
$ python policy_generator.py <from_participants> <to_participants> <start_time> <interval> <out_path>
```

* **from_participants** ASN of the participant
* **to_participants** range of ASNs of ingress participants (e.g., 2:100)
* **start_time** time when the system should start sending the announcements to the route server
* **interval** time between to policy activation requests
* **out_path:** path to the output file
