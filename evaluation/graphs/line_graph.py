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
from collections import defaultdict


def main(argv):
    in_path = argv.inpath
    experiments = argv.experiments.split(',')

    examples = [argv.example + '_' + x for x in experiments]

    x_values = [int(x) for x in experiments]
    x_labels = argv.xlabels.split(',')

    x_label = argv.xlabel

    color = ['r', 'g', 'b', 'c']

    y_values = {
        '5th': list(),
        'median': list(),
        '95th': list()
    }
    for example in examples:
        input_file = in_path + example + '.log'

        tmp_times = list()

        with open(input_file) as infile:
            for line in infile:
                time = float(line.strip())
                tmp_times.append(time)

        tmp_array = np.array(tmp_times)
        y_values['5th'].append(np.percentile(tmp_array, 5))
        y_values['median'].append(np.percentile(tmp_array, 50))
        y_values['95th'].append(np.percentile(tmp_array, 95))

    # plot it
    p1 = plt.plot(x_values, y_values['5th'], '-o')
    p2 = plt.plot(x_values, y_values['median'], '-s')
    p3 = plt.plot(x_values, y_values['95th'], '-v')

    # add some text for labels, title and axes ticks
    plt.ylabel('Time [s]')
    plt.xlabel('Number of ' + x_label)
    plt.legend((p1[0], p2[0], p3[0]), ('5th Percentile', 'Median', '95th Percentile'), loc='upper left', ncol=1)

    plt.savefig(example + '.pdf', bbox_inches='tight')

''' main '''
if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('inpath', help='path to example folder')
    parser.add_argument('example', help='name of example folder')
    parser.add_argument('experiments', help='experiments - comma separated list')
    parser.add_argument('xlabels', help='xlabels - comma separated list')
    parser.add_argument('xlabel', help='xlabel')

    args = parser.parse_args()

    main(args)
