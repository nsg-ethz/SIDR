import argparse
import json
import random
import time


def main(argv):
    notification_file = argv.out_path + "notifications.log"

    notifications = list()

    interval = int(argv.interval)
    start_time = int(argv.start_time)
    curr_notification = 0

    num_notifications = int(argv.num_notifications)
    prefix = argv.prefix

    types = ['announce', 'withdraw']
    sender_sdxes = argv.sender_sdxes.split(",")

    if not ':' in argv.ingress_participants:
        ingress_participants = [int(argv.ingress_participants)]
    else:
        tmp_from, tmp_to = argv.ingress_participants.split(':')
        ingress_participants = range(int(tmp_from), int(tmp_to) + 1)

    for ingress_participant in ingress_participants:
        prev_announce = False
        for i in range(0, num_notifications):
            s_time = start_time + curr_notification * interval
            curr_notification += 1

            sender_sdx = random.choice(sender_sdxes)

            if prev_announce:
                msg_type = random.choice(types)
                if msg_type == 'withdraw':
                    prev_announce = False
            else:
                msg_type = 'announce'
                prev_announce = True

            tmp_notification = {
                "time": s_time,
                "type": msg_type,
                "prefix": prefix,
                "sender_sdx": sender_sdx,
                "sdx_set": sender_sdx,
                "ingress_participant": ingress_participant + 100,
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
    parser.add_argument('ingress_participants', help='participant id - range of ingress participants 1:100')
    parser.add_argument('prefix', help='prefix')
    parser.add_argument('num_notifications', help='number of notifications per participant')
    parser.add_argument('start_time', help='start time')
    parser.add_argument('interval', help='interval')
    parser.add_argument('out_path', help='path of output file')
    args = parser.parse_args()

    main(args)