#!/usr/bin/env python
#  Author:
#  Rudiger Birkner (ETH Zurich)

import argparse
import json

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main(argv):
    infile = argv.infile

    total = list()
    no_loops = list()

    with open(infile) as input:
        for line in input:
            case, tmp1, tmp2 = [float(x) for x in line.strip().split('|')]
            if case == 0:
                continue
            total.append((100.0*(tmp1-tmp2))/tmp1)
            no_loops.append((100.0*tmp2)/tmp1)

    # plot it
    N = 2
    ind = np.arange(N)  # the x locations for the groups
    width = 0.25  # the width of the bars: can also be len(x) sequence

    p1 = plt.bar(1 + ind, no_loops, width, color='g')
    p2 = plt.bar(1 + ind, total, width, color='r',
                 bottom=no_loops)

    plt.ylabel('Loops [%]')
    plt.xticks(1 + ind + width / 2., ('Same', 'Ports', 'Random'))
    plt.yticks(np.arange(0, 110, 10))
    plt.legend((p1[0], p2[0]), ('Safe Loops', 'Total Number of Loops'), loc=4)

    plt.savefig('loops.pdf', bbox_inches='tight')

''' main '''
if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('infile', help='path of file')

    args = parser.parse_args()

    main(args)
