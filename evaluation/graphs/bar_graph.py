#!/usr/bin/env python
#  Author:
#  Rudiger Birkner (ETH Zurich)

import argparse
import json

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import rc_file
rc_file('~/GitHub/supercharged_sdx/evaluation/graphs/matplotlibrc')
import numpy as np


def main(argv):
    infile = argv.infile

    safe1 = list()
    safe2 = list()
    safe_total = list()
    loops = list()

    with open(infile) as input:
        for line in input:
            case, tmp_total, tmp_safe1, tmp_loop, tmp_safe2 = [float(x) for x in line.strip().split('|')]

            #if case == 0:
            #    continue

            safe1.append((100.0*tmp_safe1)/tmp_total)
            safe2.append((100.0*tmp_safe2)/tmp_total)
            safe_total.append((100.0*(tmp_safe2+tmp_safe1))/tmp_total)
            loops.append((100.0*tmp_loop)/tmp_total)

    # plot it
    N = 3
    ind = np.arange(N)  # the x locations for the groups
    width = 0.5  # the width of the bars: can also be len(x) sequence

    p1 = plt.bar(0.5 + ind, safe1, width, color='#348ABD', linewidth=0.5)
    p2 = plt.bar(0.5 + ind, safe2, width, color='#A60628', linewidth=0.5, bottom=safe1)
    p3 = plt.bar(0.5 + ind, loops, width, color='#7A68A6', linewidth=0.5, bottom=safe_total)

    plt.ylabel('Fraction of Policies')
    plt.xticks(0.5 + ind + width / 2., ('Same', 'Traffic', 'Random'))
    plt.yticks(np.arange(0, 125, 25))
    plt.xlim(0, 3.5)
    plt.legend((p3[0], p2[0], p1[0]), ('Loop Policies', 'False Positives', 'Safe Policies'), loc=4)

    plt.savefig('loops.pdf', bbox_inches='tight')

''' main '''
if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('infile', help='path of file')

    args = parser.parse_args()

    main(args)
