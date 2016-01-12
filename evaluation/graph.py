#!/usr/bin/env python
#  Author:
#  Rudiger Birkner (ETH Zurich)

import argparse
import json

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from collections import defaultdict


def main(argv):
    input_files = [(500, argv.data500), (1000, argv.data1000), (5000, argv.data5000), (10000, argv.data10000)]

    total = defaultdict(list)
    safe = defaultdict(list)
    communication = defaultdict(list)

    titles = ["Local BGP", "Our Scheme", "Full Knowledge"]

    for input_file in input_files:
        with open(input_file[1]) as infile:
            data = json.loads(infile.read())

            # means
            tmp_comm = [0, 0, 0]
            tmp_safe = [0, 0, 0]
            tmp_total = [0, 0, 0]
            for data_point in data.values():
                tmp_comm[0] += data_point["bgp_only"]["num_msgs"]
                tmp_safe[0] += data_point["bgp_only"]["frac2"]
                tmp_total[0] += data_point["bgp_only"]["frac1"]

                tmp_comm[1] += data_point["our_scheme"]["num_msgs"]
                tmp_safe[1] += data_point["our_scheme"]["frac2"]
                tmp_total[1] += data_point["our_scheme"]["frac1"]

                tmp_comm[2] += data_point["full_knowledge"]["num_msgs"]
                tmp_safe[2] += data_point["full_knowledge"]["frac2"]
                tmp_total[2] += data_point["full_knowledge"]["frac1"]

            total[0].append(tmp_total[0]/len(data))
            safe[0].append(tmp_safe[0]/len(data))
            communication[0].append(tmp_comm[0]/len(data))

            total[1].append(tmp_total[1]/len(data))
            safe[1].append(tmp_safe[1]/len(data))
            communication[1].append(tmp_comm[1]/len(data))

            total[2].append(tmp_total[2]/len(data))
            safe[2].append(tmp_safe[2]/len(data))
            communication[2].append(tmp_comm[2]/len(data))

    # safe
    fig, ax = plt.subplots()
    ind = np.arange(4)
    width = 0.25

    rects = list()
    color = ['r', 'gold', 'c', 'b']

    i = 1
    for tmp_means in safe.values():
        rects.append(ax.bar(ind + i*width, tmp_means, width, color=color[i-1]))
        i += 1

    # add some text for labels, title and axes ticks
    ax.set_ylabel('Fraction of Installed Policies')
    ax.set_title('Installed Policies with respect to Safe Policies')
    ax.set_xticks(ind + ((i+1)*width/2))
    ax.set_xticklabels(('500', '1000', '5000', '10000'))

    plt.xlim((0, 4.25))
    plt.ylim((0, 1.1))

    plots = [x[0] for x in rects]
    ax.legend(plots, titles, loc='center left', bbox_to_anchor=(1, 0.5))

    plt.savefig('safe.pdf', bbox_inches='tight')

    # total
    fig, ax = plt.subplots()
    ind = np.arange(4)
    width = 0.25

    rects = list()
    color = ['r', 'gold', 'c', 'b']

    i = 1
    for tmp_means in total.values():
        rects.append(ax.bar(ind + i*width, tmp_means, width, color=color[i-1]))
        i += 1

    # add some text for labels, title and axes ticks
    ax.set_ylabel('Fraction of Installed Policies')
    ax.set_title('Installed Policies with respect to Total Submitted Policies')
    ax.set_xticks(ind + ((i+1)*width/2))
    ax.set_xticklabels(('500', '1000', '5000', '10000'))

    plt.xlim((0, 4.25))
    plt.ylim((0, 1.1))

    plots = [x[0] for x in rects]
    ax.legend(plots, titles, loc='center left', bbox_to_anchor=(1, 0.5))

    plt.savefig('total.pdf', bbox_inches='tight')

    # communication
    fig, ax = plt.subplots()
    ind = np.arange(4)
    width = 0.25

    rects = list()
    color = ['r', 'gold', 'c', 'b']

    i = 1
    for tmp_means in communication.values():
        rects.append(ax.bar(ind + i*width, tmp_means, width, color=color[i-1]))
        i += 1

    # add some text for labels, title and axes ticks
    ax.set_ylabel('Number of Messages Exchanged')
    ax.set_title('Communication Complexity in Terms of Exchanged Messages')
    ax.set_xticks(ind + ((i+1)*width/2))
    ax.set_xticklabels(('500', '1000', '5000', '10000'))

    plt.xlim((0, 4.25))

    plots = [x[0] for x in rects]
    ax.legend(plots, titles, loc='center left', bbox_to_anchor=(1, 0.5))

    plt.savefig('communication.pdf', bbox_inches='tight')

''' main '''
if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('data500', help='path to data file 500')
    parser.add_argument('data1000', help='path to data file 1000')
    parser.add_argument('data5000', help='path to data file 5000')
    parser.add_argument('data10000', help='path to data file 10000')

    args = parser.parse_args()

    main(args)