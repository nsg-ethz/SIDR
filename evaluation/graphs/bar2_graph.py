#!/usr/bin/env python
# a bar plot with errorbars
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rc_file
rc_file('~/GitHub/supercharged_sdx/evaluation/graphs/matplotlibrc')

total = [79599707.0, 79582840.0, 79074302.0, 78212907.0, 79416440.0]
safe = [79585435.0, 79570091.0, 79063536.0, 78201376.0, 79404823.0]
sidr_safe = [72353940.0, 72944777.0, 72429438.0, 71065198.0, 72537527.0]
no_prefixes_safe = [4605657.0, 4160826.0, 4372825.0, 4325574.0, 4314814.0]
bgp_safe = [1506937.0, 1507320.0, 1502735.0, 1499895.0, 1518915.0]


fig, ax = plt.subplots()

index = 1
bar_width = 0.5
distance = 1.0

sidr_efficiency = np.mean(np.array([sidr_safe[i]/total[i] for i in range(0, len(total))]))
full_efficiency = np.mean(np.array([safe[i]/total[i] for i in range(0, len(total))]))
bgp_efficiency = np.mean(np.array([bgp_safe[i]/total[i] for i in range(0, len(total))]))
no_prefixes_efficiency = np.mean(np.array([no_prefixes_safe[i]/total[i] for i in range(0, len(total))]))

rects1 = plt.bar(index - distance - 0.5 * bar_width, bgp_efficiency*100.0, bar_width,
                 color='#467821', label='No')

rects2 = plt.bar(index - 0.5 * bar_width, no_prefixes_efficiency*100.0, bar_width,
                 color='#CF4457', label='No Prefixes')

rects3 = plt.bar(index + distance - 0.5 * bar_width, sidr_efficiency*100.0, bar_width,
                 color='#188487', label='SIDR')

rects3 = plt.bar(index + 2 * distance - 0.5 * bar_width, full_efficiency*100.0, bar_width,
                 color='#E24A33', label='Full')

plt.xticks((index - distance, index, index + distance, index + 2*distance), ('i', 'ii', 'iii', 'iv'))

plt.xlabel('Knowledge of Policies')
plt.ylabel('Safe Policies [\%]')
plt.yticks(np.arange(0, 125, 25))
plt.savefig('as_simulation.pdf', bbox_inches='tight')