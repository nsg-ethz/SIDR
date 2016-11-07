# Microbenchmarks

### Test: Policy Activation Timing

In this test, we want to measure how long it takes for a policy activation request to be processed. For this we need to
generate a file to feed to the route server, a file with notifications from remote SDXes, and finally a file with all
the policy activation requests.

The following script generate the necessary files:

```bash
$ bash patiming.sh
```

The following script runs the tests:

```bash
$ bash run_patiming.sh
```

### Test: RIB Update Timing

In this test, we want to measure how long it takes for a rib update to be processed.

The following script generate the necessary files:

```bash
$ bash ribtiming.sh
```

The following script runs the tests:

```bash
$ bash run_ribtiming.sh
```

### Test: Notification Timing

In this test, we want to measure how long it takes for a notification to be processed.

The following script generate the necessary files:

```bash
$ bash notiming.sh
```

The following script runs the tests:

```bash
$ bash run_notiming.sh
```

### Failure

In case a test crashes, you need to clean up (remove the ribs and cibs) before running the next test.

The following script does this task for you:

```bash
$ bash cleanup.sh
```


