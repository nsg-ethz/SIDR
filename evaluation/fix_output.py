#!/usr/bin/env python
#  Author:
#  Rudiger Birkner (ETH Zurich)

import argparse

from collections import defaultdict


def main(argv):
    previous1 = [0, 0, 0]
    previous2 = [0, 0, 0]

    with open(argv.output, 'w') as output:
        with open(argv.input, 'r') as input:
            i = 0
            for line in input:
                # skip header
                if i == 0:
                    output.write(line + "\n")
                    i += 1
                    continue

                x = line.split("\n")[0].split("|")

                previous1 = [int(x[0]), int(x[1]), int(x[2])]

                output.write(str(previous1[0] - previous2[0]) + "|" +
                             str(previous1[1] - previous2[1]) + "|" +
                             str(previous1[2] - previous2[2]) + "\n")

                previous2 = previous1

                i += 1


''' main '''
if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('input', help='path to evaluation 0 log')
    parser.add_argument('output', help='path of output file')

    args = parser.parse_args()

    main(args)