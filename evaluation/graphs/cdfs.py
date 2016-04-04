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

    colors = ['g', 'b']
    titles = ['SIDR', 'Full Disclosure']

    # MESSAGES
    if True:
        messages1 = defaultdict(int)
        messages2 = defaultdict(int)
        max_num_messages = 0

        with open(args.messages1) as infile:
            for line in infile:
                x = line.split("\n")[0].split(",")
                for y in x:
                    if y == "":
                        continue
                    messages1[int(y)] += 1
                    if int(y) > max_num_messages:
                        max_num_messages = int(y)

        print "1: Max Num Messages: " + str(max_num_messages)
    
        with open(args.messages2) as infile:
            for line in infile:
                x = line.split("\n")[0].split(",")
                for y in x:
                    if y == "":
                        continue
                    messages2[int(y)] += 1
                    if int(y) > max_num_messages:
                        max_num_messages = int(y)    

        print "2: Max Num Messages: " + str(max_num_messages)


        # the histogram of the data
        rects = list()

        i = 0
        
        data = (messages1.keys(), messages2.keys())
        #bins = numpy.logspace(-1, numpy.log10(max_num_messages), 50)
        bins = max_num_messages
        bins = 10 ** numpy.linspace(numpy.log10(1.0), numpy.ceil(numpy.log10(max_num_messages)), 50)
        weights = (messages1.values(), messages2.values())

        fig, ax = P.subplots()
        # the histogram of the data
        ax.hist(data, bins, normed=1, weights=weights, cumulative=True, histtype='step', color=colors, label=titles)
        ax.legend(loc='center left', bbox_to_anchor=(1, 0.5), frameon=False)

        # add a 'best fit' line
        ax.set_xscale('log')

        ax.set_xlabel('Number of Messages')
        ax.set_ylabel('CDF')
        #ax.set_title('Number of Sent Messages per SDX and Policy Installation')
        ax.set_xlim(0,max_num_messages)
        ax.set_ylim(0,1)

        # Tweak spacing to prevent clipping of ylabel
        P.subplots_adjust(left=0.15)
        P.savefig('sent_messages_cdf.pdf', bbox_inches='tight')

    if True:
        # LOOPS
        loop_length1 = defaultdict(int)
        loop_length2 = defaultdict(int)
        max_num_loop_length = 0

        with open(args.loop_length1) as infile:
            for line in infile:
                x = line.split("\n")[0]
                for y in x.split(","):
                    if y == "":
                        continue
                    loop_length1[int(y)] += 1
                    if int(y) > max_num_loop_length:
                        max_num_loop_length = int(y)

        print "1: Max Num Loop Length: " + str(max_num_loop_length)
        max_num_loop_length = 0

        with open(args.loop_length2) as infile:
            for line in infile:
                x = line.split("\n")[0]
                for y in x.split(","):
                    if y == "":
                        continue
                    loop_length2[int(y)] += 1
                    if int(y) > max_num_loop_length:
                        max_num_loop_length = int(y)

        print "2: Max Num Loop Length: " + str(max_num_loop_length)

        # the histogram of the data
        rects = list()

        i = 0

        x = (loop_length1.keys(), loop_length2.keys()) 
        num_bins = max_num_loop_length
        weights = (loop_length1.values(), loop_length2.values())

        fig, ax = P.subplots()
        # the histogram of the data
        ax.hist(x[1], num_bins, normed=1, weights=weights[1], cumulative=True, histtype='step', color=colors[1], label=titles[1])
        # ax.legend(loc='center left', bbox_to_anchor=(1, 0.5), frameon=False)

        # add a 'best fit' line
        ax.set_xlabel('Number of SDXes')
        ax.set_ylabel('CDF')
        #ax.set_title('Number of Hops in a Loop')
        ax.set_ylim(0,1)
        ax.set_xlim(1,max_num_loop_length)

        # Tw    eak spacing to prevent clipping of ylabel
        P.subplots_adjust(left=0.15)
        P.savefig('loop_cdf.pdf', bbox_inches='tight')

    # HOPS
    if True:
        hops1 = defaultdict(int)
        hops2 = defaultdict(int)
        max_num_hops = 0

        with open(args.hops1) as infile:
            for line in infile:
                x = line.split("\n")[0]
                if x == "":
                    continue
                tmp_hops = int(x)
                hops1[tmp_hops] += 1
                if tmp_hops > max_num_hops:
                    max_num_hops = tmp_hops

        print "1: Max Num Hops: " + str(max_num_hops)

        with open(args.hops2) as infile:
            for line in infile:
                x = line.split("\n")[0]
                if x == "":
                    continue
                tmp_hops = int(x)
                hops2[tmp_hops] += 1
                if tmp_hops > max_num_hops:
                    max_num_hops = tmp_hops

        print "2: Max Num Hops: " + str(max_num_hops)
    
        # the histogram of the data

        rects = list()

        i = 0

        x = (hops1.keys(), hops2.keys())
        num_bins = max_num_hops
        weights = (hops1.values(), hops2.values())

        fig, ax = P.subplots()

        # the histogram of the data
        ax.hist(x, num_bins, normed=1, weights=weights, cumulative=True, histtype='step', color=colors, label=titles)
        ax.legend(loc='center left', bbox_to_anchor=(1, 0.5), frameon=False)

        # add a 'best fit' line
        ax.set_xlabel('Tree Depth')
        ax.set_ylabel('CDF')
        #ax.set_title('Maximum Number of Hops per Policy Installation')
        ax.set_ylim(0,1)
        ax.set_xlim(0,max_num_hops)

        # Tweak spacing to prevent clipping of ylabel
        P.subplots_adjust(left=0.15)
        P.savefig('hops_cdf.pdf', bbox_inches='tight')


''' main '''
if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('messages1', help='path to input file 0')
    parser.add_argument('messages2', help='path to input file 1')
    parser.add_argument('loop_length1', help='path to input file 0')
    parser.add_argument('loop_length2', help='path to input file 1')
    parser.add_argument('hops1', help='path to input file 2')
    parser.add_argument('hops2', help='path to input file 2')

    args = parser.parse_args()

    main(args)



