# run the evaluation

### Build the AS-level graph

```bash 
$ python topology/as-topo.py as-topo.conf
```

all the settings have to be specified in as-topo.conf

* **Topology File:** path to CAIDA/UCLA topology file - only tested with CAIDA
* **Topology Format:** 0 for CAIDA, 1 for UCLA
* **Topology Backedges Removed:** True if the backedges have already been removed, False if not
* **IXP File:** path to the combined IXP dataset
* **IXP Mode:** 0 to always add an p2p link between two IXP participants if they are not indirectly connected through a c2p-chain, 1 to also add a c2p link when one AS has C2P Factor more connections than the other.
* **C2P Factor:** See above
* **Output Path:** path to output directory
* **Tier 1 Connection Threshold** number of customers an AS has to have to be considered tier 1

### Compute the Paths

```bash 
$ python topology/bgp_paths.py <path> <outpath> <destinations> <exceptions> <ixpparticipants> <-t>
```

this script is written to run as an MPI job on a cluster - see the paths.script

* **path:** path of the graph file
* **outpath:** path of the output directory
* **destination:** path of the file containing a list of destinations to compute the path to
* **exceptions:** path of the file containing a list of ASes that do not differ between peer and customer routes (GR exception)
* **ixpparticipants:** path of the file containing a list of ASes that are participants of an IXP
* **-t** if -t is specified some tests are run - this does not require MPI

### Build the SDX Dataset
```bash 
$ python sdx_dataset_im.py <mode> <path file> <ixp file> <sdx dataset output file> <max num paths>
$ python sdx_dataset_im.py test/routes.txt test/ixp_file.json test/sdx_dataset.log
```

* **mode:** if the specified mode is 1, we randomly pick one sdx if there are multiple candidates for the first sdx on the path, else we just use all of them (very inefficient)

* **path file:** path to the file that contains all the computed paths

* **ixp file:** path to the file of the combined ixp dataset

* **output:** path of the output file

* **max num paths:** limit the number of paths that an AS has for a single destination to max num paths
 
### Build Policies
```bash
$ python policy_generator.py <mode> <sdx dataset file> <ports file> <fraction> <maximum> <path to policy output file> <number of iterations>
$ python policy_generator.py test/sdx_dataset.log test/port_distribution.log 1 test/ 1
```

* **mode** 
  * mode 0: all matches are tcp_dst=80
  * mode 1: ports to match on are picked according to distribution in ports file
  * mode 2: random selection of ports
* **sdx dataset file** path of sdx file
* **ports file** path of port distribution file
* **fraction** fraction of neighbors at an sdx a policy is created for
* **maximum** maximum number of neighbors at an sdx a policy is created for
* **output** path to output directory
* **number of iterations** number of policy sets to generate

for each participant, between 1 and 4 policies are created for *fraction* of the outgoing participants

### Evaluate Policies
```bash
$ python evaluation.py <mode> <sdx dataset file> <policies file> <number of iterations> <start> <output file>
$ python evaluation.py 0 test/sdx_dataset.log test/ 1 test/evaluation_0.log
```
* **mode** 
  * mode 0: local BGP only - full privacy
  * mode 1: SIDR
  * mode 2: perfect knowledge - full disclosure
* **sdx dataset file** path of sdx dataset file
* **policies** path of the directory containing all the policy files
* **iterations** the number of iterations to run - for each iteration one policy file is required
* **start** the number of the policy file to start with
* **output** path to the output directory

### Cluster

Note the dataset, policy and evaluation scripts were run on a cluster. The according .script files in this directory were used to run the jobs.






