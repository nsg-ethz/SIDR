# run the evaluation

Build SDX Dataset
```bash 
$ python sdx_dataset.py <file with all routes> <ixp file> <sdx dataset output file>
$ python sdx_dataset.py test/routes.txt test/ixp_file.json test/sdx_dataset.log
```

Build Policies
```bash
$ python policy_generator.py <sdx dataset file> <ports file> <X> <sdx policy output file>
$ python policy_generator.py test/sdx_dataset.log test/port_distribution.log 1 test/policies.log
```
for each participant, between 1 and 4 policies are created for 1/X of the outgoing participants

Evaluate Policies
```bash
$ python evaluation.py <mode> <sdx dataset file> <policies file>
$ python evaluation.py 0 test/sdx_dataset.log test/policies.log
```

* mode 0: local BGP only
* mode 1: our scheme
* mode 2: perfect knowledge






