#!/usr/bin/env python
#  Author:
#  Rudiger Birkner (ETH Zurich)

import argparse
import json

from collections import defaultdict


import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import pylab as P

def main(args):


    with open(args.paths) as infile:
        for line in infile:
            data = json.loads(line)

    # prepare data
    total = sum(data.values())

    print str(data)


    data2 = {}
    for key, value in data.iteritems():
        data2[int(key)] = float(value)/total


    print str(data2)

    x = data2.keys()
    num_bins = data2.keys()
    weights = data2.values()

    P.figure()
    # the histogram of the data
    ts = P.hist(x, num_bins, normed=1, weights=weights, cumulative=True, histtype='step')
    # add a 'best fit' line
    P.xlabel('Number of IXPs per Path')
    P.ylabel('Fraction of Paths')
    P.title(r'CDF of the Number of IXPs per Path')

    # Tweak spacing to prevent clipping of ylabel
    P.subplots_adjust(left=0.15)
    P.savefig('cdf.pdf', bbox_inches='tight')


''' main '''
if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('paths', help='path to paths file')

    args = parser.parse_args()

    main(args)


