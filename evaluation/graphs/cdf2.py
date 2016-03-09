#!/usr/bin/env python
#  Author:
#  Rudiger Birkner (ETH Zurich)

import argparse
from collections import defaultdict
import numpy

import matplotlib
matplotlib.use('Agg')

import pylab as P

from bisect import bisect_left

def main(args):

    # MESSAGES
    messages1 = defaultdict(int)
    messages2 = defaultdict(int)
    max_num_messages = 0

    with open(args.messages1) as infile:
        for line in infile:
            x = line.split("\n")[0]
            messages1[int(x)] += 1
            if int(x) > max_num_messages:
                max_num_messages = int(x)

    with open(args.messages2) as infile:
        for line in infile:
            x = line.split("\n")[0]
            messages2[int(x)] += 1
            if int(x) > max_num_messages:
                max_num_messages = int(x)

    P.figure()
    # the histogram of the data

    colors = ['b', 'g', 'r', 'c']
    titles = ['Our Scheme', 'Full Knowledge']
    rects = list()

    i = 0

    x = messages1.keys()
    num_bins = max_num_messages
    weights = messages1.values()

    P.figure()
    # the histogram of the data
    rects.append(P.hist(x, num_bins, normed=1, weights=weights, cumulative=True, histtype='step', color=colors[1]))

    x = messages2.keys()
    weights = messages2.values()
    rects.append(P.hist(x, num_bins, normed=1, weights=weights, cumulative=True, histtype='step', color=colors[2]))

    plots = [x[0] for x in rects]
    P.legend(plots, titles, loc='center left', bbox_to_anchor=(1, 0.5))

    # add a 'best fit' line
    P.xlabel('Number of Messages')
    P.ylabel('Fraction of Policy Installations')
    P.title('Number of Messages sent per Policy Installation')
    P.xlim(0,1)
    P.ylim(0,1)

    # Tweak spacing to prevent clipping of ylabel
    P.subplots_adjust(left=0.15)
    P.savefig('messages_cdf.pdf', bbox_inches='tight')

    # HOPS
    hops1 = defaultdict(int)
    hops2 = defaultdict(int)
    max_num_hops = 0

    with open(args.hops1) as infile:
        for line in infile:
            x = line.split("\n")[0].split(", ")
            for num_hops in x:
                tmp_hops = int(num_hops)
                hops1[tmp_hops] += 1
                if tmp_hops > max_num_hops:
                    max_num_hops = tmp_hops

    with open(args.hops2) as infile:
        for line in infile:
            x = line.split("\n")[0].split(", ")
            for num_hops in x:
                tmp_hops = int(num_hops)
                hops2[tmp_hops] += 1
                if tmp_hops > max_num_hops:
                    max_num_hops = tmp_hops

    P.figure()
    # the histogram of the data

    titles = ['Our Scheme', 'Full Knowledge']
    rects = list()

    i = 0

    x = hops1.keys()
    num_bins = max_num_hops
    weights = hops1.values()

    P.figure()
    # the histogram of the data
    rects.append(P.hist(x, num_bins, normed=1, weights=weights, cumulative=True, histtype='step', color=colors[1]))

    x = hops2.keys()
    weights = hops2.values()
    rects.append(P.hist(x, num_bins, normed=1, weights=weights, cumulative=True, histtype='step', color=colors[2]))

    plots = [x[0] for x in rects]
    P.legend(plots, titles, loc='center left', bbox_to_anchor=(1, 0.5))

    # add a 'best fit' line
    P.xlabel('Number of Hops')
    P.ylabel('Fraction of Policy Installations')
    P.title('Maximum Number of Hops per Policy Installation')
    P.xlim(0,1)
    P.ylim(0,1)

    # Tweak spacing to prevent clipping of ylabel
    P.subplots_adjust(left=0.15)
    P.savefig('messages_cdf.pdf', bbox_inches='tight')


''' main '''
if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('messages1', help='path to input file 0')
    parser.add_argument('messages2', help='path to input file 1')
    parser.add_argument('hops1', help='path to input file 2')
    parser.add_argument('hops2', help='path to input file 2')

    args = parser.parse_args()

    main(args)


