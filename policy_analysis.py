#!/usr/bin/env python
#  Author:
#  Rudiger Birkner (ETH Zurich)

import argparse
import json

from collections import defaultdict

def main(argv):

    analysis = defaultdict(lambda: defaultdict(int))

    for i in range(0, int(argv.numfiles)):
        with open(argv.path + "policies_" + str(i) + ".log", 'r') as policies:
            for policy in policies:
                to_participant = policy.split("\n")[0].split("|")[2]
                analysis[i][int(to_participant)] += 1

    with open(argv.output) as output:
        data = json.dumps(analysis)
        output.write(data)


''' main '''
if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('path', help='input path')
    parser.add_argument('numfiles', help='num files')
    parser.add_argument('output', help='path of output file')

    args = parser.parse_args()

    main(args)