# run the evaluation

Build SDX Dataset
```bash 
$ python sdx_dataset.py <file with all routes> <ixp file> <sdx dataset output file>
$ python sdx_dataset.py test/routes.txt test/ixp_file.json test/sdx_dataset.log
```

Build Policies
```bash
$ python policy_generator.py <sdx dataset file> <ports file> <sdx policy output file>
$ python policy_generator.py test/sdx_dataset.log test/port_distribution.log 1 test/policies.log
```

Evaluate Policies
```bash
$ python evaluation.py <mode> <sdx dataset file> <policies file>
$ python evaluation.py 0 test/sdx_dataset.log test/policies.log
```

* mode 0: local BGP only
* mode 1: our scheme
* mode 2: perfect knowledge






