#!/usr/bin/env python
#  Author:
#  Rudiger Birkner (ETH Zurich)

import argparse
import json
from collections import defaultdict


def main(argv):
    input_files = [argv.eval_0, argv.eval_1, argv.eval_2]

    results = defaultdict(dict)

    j = 0
    for input_file in input_files:
        with open(input_file) as input:
            i = 0
            for line in input:
                # skip header
                if i == 0:
                    i += 1
                    continue

                x = line.split("\n")[0].split("|")

                if j == 0:
                    results[i-1]["total"] = int(x[0])
                    results[i-1]["bgp_only"] = dict()
                    results[i-1]["bgp_only"]["safe"] = int(x[1])
                    results[i-1]["bgp_only"]["frac1"] = float(x[1])/float(x[0])
                elif j == 1:
                    if results[i-1]["total"] != int(x[0]):
                        print "Error: Total doesn't match " + str(i) + "/" + str(j)
                    results[i-1]["our_scheme"] = dict()
                    results[i-1]["our_scheme"]["safe"] = int(x[1])
                    results[i-1]["our_scheme"]["frac1"] = float(x[1])/float(x[0])
                elif j == 2:
                    if results[i-1]["total"] != int(x[0]):
                        print "Error: Total doesn't match " + str(i) + "/" + str(j)
                    results[i-1]["full_knowledge"] = dict()
                    results[i-1]["full_knowledge"]["safe"] = int(x[1])
                    results[i-1]["full_knowledge"]["frac1"] = float(x[1])/float(x[0])
                i += 1
        j += 1

    for k in range(0, i-1):
        results[k]["bgp_only"]["frac2"] = float(results[k]["bgp_only"]["safe"]) / \
                                            float(results[k]["full_knowledge"]["safe"])
        results[k]["our_scheme"]["frac2"] = float(results[k]["our_scheme"]["safe"]) / \
                                              float(results[k]["full_knowledge"]["safe"])
        results[k]["full_knowledge"]["frac2"] = float(results[k]["full_knowledge"]["safe"]) / \
                                                  float(results[k]["full_knowledge"]["safe"])

    with open(argv.output, 'w') as outfile:
        json.dump(results, outfile)

''' main '''
if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('eval_0', help='path to evaluation 0 log')
    parser.add_argument('eval_1', help='path to evaluation 1 log')
    parser.add_argument('eval_2', help='path to evaluation 2 log')
    parser.add_argument('output', help='path of output file')

    args = parser.parse_args()

    main(args)

