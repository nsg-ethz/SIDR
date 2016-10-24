import argparse
import json
import random
import numpy as np
import time

def main(argv):
    notification_file = argv.out_path + "notifications.log"

    notifications = list()

    start_time = int(argv.start_time)

    sender_sdxes = argv.sender_sdxes.split(",")

    ingress_participant = int(argv.ingress_participant)

    probability = float(argv.probability)

    num_prefixes = int(argv.num_prefixes)

    with open(argv.prefix_file, "r") as infile:
        i = 0

        for line in infile:
            i += 1

            if i > num_prefixes:
                break

            choice = np.random.choice([True, False], p=[probability, 1.0 - probability])

            if choice:
                prefix = line.strip()

                sender_sdx = random.choice(sender_sdxes)
                s_time = start_time
                tmp_notification = {
                    "time": s_time,
                    "type": "announce",
                    "prefix": prefix,
                    "sender_sdx": sender_sdx,
                    "sdx_set": sender_sdx,
                    "ingress_participant": ingress_participant,
                    "timestamp": time.time(),
                    "random_value": random.randint(0, 10000)
                }
                notifications.append(tmp_notification)

    with open(notification_file, 'w') as outfile:
        json.dump(notifications, outfile)


''' main '''
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('sender_sdxes', help='comma separated list of senders sdxes')
    parser.add_argument('ingress_participant', help='ingress participants')
    parser.add_argument('prefix_file', help='prefix')
    parser.add_argument('num_prefixes', help='number of prefixes to read from file')
    parser.add_argument('probability', help='probability that this prefix has an installed policy (0.75)')
    parser.add_argument('start_time', help='start time')
    parser.add_argument('out_path', help='path of output file')
    args = parser.parse_args()

    main(args)