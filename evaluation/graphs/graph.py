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
    input_files = [(100, argv.data100), (500, argv.data500), (1000, argv.data1000), (5000, argv.data5000)]
    xlabels = ('100', '500', '1000', '5000')

    color = ['r', 'g', 'b', 'c']
    
    #input_files = [(100, argv.data100), (500, argv.data500), (1000, argv.data1000)]
    #xlabels = ('100', '500', '1000')

    num_items = len(input_files)

    total = defaultdict(list)
    total_stats = defaultdict(dict)
    safe = defaultdict(list)
    safe_stats = defaultdict(dict)

    titles = ["Full Privacy", "SIDR", "Full Disclosure"]

    for input_file in input_files:
        with open(input_file[1]) as infile:
            data = json.loads(infile.read())

            # means
            tmp_safe = [[], [], []]
            tmp_total = [[], [], []]

            for data_point in data.values():
                tmp_safe[0].append(data_point["bgp_only"]["frac2"])
                tmp_total[0].append(data_point["bgp_only"]["frac1"])

                tmp_safe[1].append(data_point["our_scheme"]["frac2"])
                tmp_total[1].append(data_point["our_scheme"]["frac1"])

                tmp_safe[2].append(data_point["full_knowledge"]["frac2"])
                tmp_total[2].append(data_point["full_knowledge"]["frac1"])

            for i in range(0, 3):
                tmp_std = np.std(tmp_total[i])
                tmp_mean = np.mean(tmp_total[i])

                total_stats[input_file[0]][i] = {"mean": tmp_mean, "std": tmp_std}
                total[i].append(tmp_mean)

                tmp_std = np.std(tmp_safe[i])
                tmp_mean = np.mean(tmp_safe[i])

                safe_stats[input_file[0]][i] = {"mean": tmp_mean, "std": tmp_std}
                safe[i].append(tmp_mean)

    print str(total_stats)
    print str(safe_stats)

    # safe
    fig, ax = plt.subplots()
    ind = np.arange(num_items)
    width = 0.25

    rects = list()

    i = 1
    for tmp_means in safe.values():
        rects.append(ax.bar(ind + i*width, tmp_means, width, color=color[i-1]))
        i += 1

    # add some text for labels, title and axes ticks
    ax.set_ylabel('Fraction of Safe Policies')
    ax.set_xlabel('Number of Destinations')
    #ax.set_title('Installed Policies with respect to Safe Policies')
    ax.set_xticks(ind + ((i+1)*width/2))
    ax.set_xticklabels(xlabels)

    plt.xlim((0, num_items + width))
    plt.ylim((0, 1.1))

    plots = [x[0] for x in rects]
    ax.legend(plots, titles, loc='center left', bbox_to_anchor=(1, 0.5), frameon=False)

    plt.savefig('safe.pdf', bbox_inches='tight')

    # total
    fig, ax = plt.subplots()
    ind = np.arange(num_items)
    width = 0.25

    rects = list()

    i = 1
    for tmp_means in total.values():
        rects.append(ax.bar(ind + i*width, tmp_means, width, color=color[i-1]))
        i += 1

    # add some text for labels, title and axes ticks
    ax.set_ylabel('Fraction of Submitted Policies')
    ax.set_xlabel('Number of Destinations')
    #ax.set_title('Installed Policies with respect to Total Submitted Policies')
    ax.set_xticks(ind + ((i+1)*width/2))
    ax.set_xticklabels(xlabels)

    plt.xlim((0, num_items + width))
    plt.ylim((0, 1.1))

    plots = [x[0] for x in rects]
    ax.legend(plots, titles, loc='center left', bbox_to_anchor=(1, 0.5), frameon=False)

    plt.savefig('total.pdf', bbox_inches='tight')

    # communication
    #fig, ax = plt.subplots()
    #ind = np.arange(4)
    #width = 0.25

    #rects = list()
    #color = ['r', 'gold', 'c', 'b']

    #i = 1
    #for tmp_means in messages.values():
    #    rects.append(ax.bar(ind + i*width, tmp_means, width, color=color[i]))
    #    i += 1

    # add some text for labels, title and axes ticks
    #ax.set_ylabel('Number of Messages')
    #ax.set_xlabel('Number of Destinations')
    #ax.set_title('Number of Messages Exchanged per Policy Installation')
    #ax.set_xticks(ind + ((i+1)*width/2))
    #ax.set_xticklabels(('500', '1000', '5000', '10000'))

    #plt.xlim((0, 4.25))

    #plots = [x[0] for x in rects]
    #ax.legend(plots, titles[1:], loc='center left', bbox_to_anchor=(1, 0.5))

    #plt.savefig('communication.pdf', bbox_inches='tight')

    # received messages
    #fig, ax = plt.subplots()
    #ind = np.arange(4)
    #width = 0.25

    #rects = list()
    #color = ['r', 'gold', 'c', 'b']

    #i = 1
    #for tmp_means in msgs_per_node.values():
    #    rects.append(ax.bar(ind + i*width, tmp_means, width, color=color[i]))
    #    i += 1

    # add some text for labels, title and axes ticks
    #ax.set_ylabel('Number of Received Messages')
    #ax.set_xlabel('Number of Destinations')
    #ax.set_title('Number of Received Messaages per Node per Policy Installation')
    #ax.set_xticks(ind + ((i+1)*width/2))
    #ax.set_xticklabels(('500', '1000', '5000', '10000'))

    #plt.xlim((0, 4.25))

    #plots = [x[0] for x in rects]
    #ax.legend(plots, titles[1:], loc='center left', bbox_to_anchor=(1, 0.5))

    #plt.savefig('messagespernode.pdf', bbox_inches='tight')

    # length of cycles
    #fig, ax = plt.subplots()
    #ind = np.arange(4)
    #width = 0.25

    #rects = list()
    #color = ['r', 'gold', 'c', 'b']

    #i = 1
    #for tmp_means in cycles.values():
    #    rects.append(ax.bar(ind + i*width, tmp_means, width, color=color[i]))
    #    i += 1

    # add some text for labels, title and axes ticks
    #ax.set_ylabel('Number of SDXes')
    #ax.set_xlabel('Number of Destinations')
    #ax.set_title('Number of SDXes on a Loop')
    #ax.set_xticks(ind + ((i+1)*width/2))
    #ax.set_xticklabels(('500', '1000', '5000', '10000'))

    #plt.xlim((0, 4.25))

    #plots = [x[0] for x in rects]
    #ax.legend(plots, titles[1:], loc='center left', bbox_to_anchor=(1, 0.5))

    #plt.savefig('loops.pdf', bbox_inches='tight')

''' main '''
if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('data100', help='path to data file 100')
    parser.add_argument('data500', help='path to data file 500')
    parser.add_argument('data1000', help='path to data file 1000')
    parser.add_argument('data5000', help='path to data file 5000')

    args = parser.parse_args()

    main(args)
