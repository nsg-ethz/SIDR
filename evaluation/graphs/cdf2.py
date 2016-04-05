#!/usr/bin/env python
#  Author:
#  Rudiger Birkner (ETH Zurich)

import argparse
from collections import defaultdict
import numpy

import matplotlib
matplotlib.use('Agg')

import pylab as P


def main(args):

    # SENT MESSAGES
    sent_messages1 = defaultdict(int)
    sent_messages2 = defaultdict(int)
    max_num_sent_messages = 0

    with open(args.sent_messages1) as infile:
        for line in infile:
            x = line.split("\n")[0]
            for y in x.split(","):
                sent_messages1[int(y)] += 1
                if int(y) > max_num_sent_messages:
                    max_num_sent_messages = int(y)

    with open(args.sent_messages2) as infile:
        for line in infile:
            x = line.split("\n")[0]
            for y in x.split(","):
                sent_messages2[int(y)] += 1
                if int(y) > max_num_sent_messages:
                    max_num_sent_messages = int(y)

    P.figure()
    # the histogram of the data

    colors = ['b', 'g', 'r', 'c']
    titles = ['Our Scheme', 'Full Knowledge']
    rects = list()

    i = 0

    x = sent_messages1.keys()
    num_bins = max_num_sent_messages
    weights = sent_messages1.values()

    P.figure()
    # the histogram of the data
    rects.append(P.hist(x, num_bins, normed=1, weights=weights, cumulative=True, histtype='step', color=colors[1]))

    x = sent_messages2.keys()
    weights = sent_messages2.values()
    rects.append(P.hist(x, num_bins, normed=1, weights=weights, cumulative=True, histtype='step', color=colors[2]))

    plots = [x[0] for x in rects]
    P.legend(plots, titles, loc='center left', bbox_to_anchor=(1, 0.5))

    # add a 'best fit' line
    P.xlabel('Number of Messages')
    P.ylabel('CDF')
    P.title('Number of Sent Messages per SDX and Policy Installation')
    P.xlim(0,1)
    P.ylim(0,1)

    # Tweak spacing to prevent clipping of ylabel
    P.subplots_adjust(left=0.15)
    P.savefig('sent_messages_cdf.pdf', bbox_inches='tight')


    # RECEIVED MESSAGES
    received_messages1 = defaultdict(int)
    received_messages2 = defaultdict(int)
    max_num_received_messages = 0

    with open(args.received_messages1) as infile:
        for line in infile:
            x = line.split("\n")[0]
            for y in x.split(","):
                received_messages1[int(y)] += 1
                if int(y) > max_num_received_messages:
                    max_num_received_messages = int(y)

    with open(args.received_messages2) as infile:
        for line in infile:
            x = line.split("\n")[0]
            for y in x.split(","):
                received_messages2[int(y)] += 1
                if int(y) > max_num_received_messages:
                    max_num_received_messages = int(y)

    P.figure()
    # the histogram of the data

    colors = ['b', 'g', 'r', 'c']
    titles = ['Our Scheme', 'Full Knowledge']
    rects = list()

    i = 0

    x = received_messages1.keys()
    num_bins = max_num_received_messages
    weights = received_messages1.values()

    P.figure()
    # the histogram of the data
    rects.append(P.hist(x, num_bins, normed=1, weights=weights, cumulative=True, histtype='step', color=colors[1]))

    x = received_messages2.keys()
    weights = received_messages2.values()
    rects.append(P.hist(x, num_bins, normed=1, weights=weights, cumulative=True, histtype='step', color=colors[2]))

    plots = [x[0] for x in rects]
    P.legend(plots, titles, loc='center left', bbox_to_anchor=(1, 0.5))

    # add a 'best fit' line
    P.xlabel('Number of Messages')
    P.ylabel('CDF')
    P.title('Number of Received Messages per SDX and Policy Installation')
    P.xlim(0,1)
    P.ylim(0,1)

    # Tweak spacing to prevent clipping of ylabel
    P.subplots_adjust(left=0.15)
    P.savefig('received_messages_cdf.pdf', bbox_inches='tight')

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
            x = line.split("\n")
            tmp_hops = int(num_hops)
            hops2[tmp_hops] += 1
            if tmp_hops > max_num_hops:
                max_num_hops = tmp_hops

    P.figure()
    # the histogram of the data

    titles = ['SIDR', 'Full Disclosure']
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
    P.ylabel('CDF')
    P.title('Maximum Number of Hops per Policy Installation')
    P.xlim(0,1)
    P.ylim(0,1)

    # Tweak spacing to prevent clipping of ylabel
    P.subplots_adjust(left=0.15)
    P.savefig('hops_cdf.pdf', bbox_inches='tight')


''' main '''
if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('sent_messages1', help='path to input file 0')
    parser.add_argument('sent_messages2', help='path to input file 1')
    parser.add_argument('received_messages1', help='path to input file 0')
    parser.add_argument('received_messages2', help='path to input file 1')
    parser.add_argument('hops1', help='path to input file 2')
    parser.add_argument('hops2', help='path to input file 2')

    args = parser.parse_args()

    main(args)


