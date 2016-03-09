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
    input_files = [args.file0, args.file1, args.file2]

    data = defaultdict(list)

    i = 0
    for in_file in input_files:
        with open(args.paths) as infile:
            for line in infile:
                x = line.split("\n")[0].split("|")

                data[i].append(float(x[1])/float(x[0]))
        i += 1

    P.figure()
    # the histogram of the data

    colors = ['b', 'g', 'r', 'c']
    titles = ['Local BGP Only', 'Our Scheme', 'Full Knowledge']
    rects = list()

    i = 0
    for values in data.values():
        num_bins = 100
        counts, bin_edges = numpy.histogram(values, bins=num_bins, range=(0,1), density=True)
        cdf = numpy.cumsum(counts)
        rects.append(P.plot(bin_edges[1:], cdf, colors[i]))
        i += 1

    plots = [x[0] for x in rects]
    P.legend(plots, titles, loc='center left', bbox_to_anchor=(1, 0.5))

    # add a 'best fit' line
    P.xlabel('Fraction of Deflections')
    P.ylabel('Fraction of Iterations')
    P.title('Safe Deflections according to Scheme')
    P.xlim(0,1)
    P.ylim(0,1)

    # Tweak spacing to prevent clipping of ylabel
    P.subplots_adjust(left=0.15)
    P.savefig('cdf.pdf', bbox_inches='tight')


''' main '''
if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('file_0', help='path to input file 0')
    parser.add_argument('file_1', help='path to input file 1')
    parser.add_argument('file_2', help='path to input file 2')

    args = parser.parse_args()

    main(args)


