import argparse
import json
import random


def main(argv):
    notification_file = argv.out_path + "notifications.log"

    notifications = list()

    interval = argv.interval
    start_time =  argv.start_time
    curr_notification = 0

    num_notifications = argv.num_notifications
    prefix = argv.prefix

    sender_sdxes = argv.sender_sdxes.split(",")


    if not ':' in argv.ingress_participants:
        ingress_participants = [int(argv.ingress_participants)]
    else:
        tmp_from, tmp_to = argv.ingress_participants.split(':')
        ingress_participants = range(int(tmp_from), int(tmp_to) + 1)

    for ingress_participant in ingress_participants:
        for i in range(0, num_notifications):
            time = start_time + curr_notification * interval
            curr_notification += 1

            sender_sdx = random.choice(sender_sdxes)

            tmp_notification = {
                "time": time,
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
    parser.add_argument('ingress_participants', help='range of ingress participants 1:100')
    parser.add_argument('prefix', help='prefix')
    parser.add_argument('num_notifications', help='number of notifications per participant')
    parser.add_argument('start_time', help='start time')
    parser.add_argument('interval', help='interval')
    parser.add_argument('out_path', help='path of output file')
    args = parser.parse_args()

    main(args)