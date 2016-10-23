import argparse
import random


def main(argv):
    announcements_file = argv.out_path + "announcements.log"

    interval = argv.interval
    start_time =  argv.start_time
    curr_announcement = 0

    remote_address = '172.1.0.1'
    local_address = '172.1.255.254'
    local_asn = '65000'

    prefix = argv.prefix

    if not ':' in argv.from_participants:
        from_participants = [int(argv.from_participants)]
    else:
        tmp_from, tmp_to = argv.from_participants.split(':')
        from_participants = range(int(tmp_from), int(tmp_to) + 1)

    prev_announce = False
    types = ['announce', 'withdraw']
    as_paths = argv.as_paths.split(';')

    with open(announcements_file, 'w') as outfile:

        for from_participant in from_participants:
            time = start_time + curr_announcement * interval
            curr_announcement += 1

            if prev_announce:
                msg_type = random.choice(types)
                if msg_type == 'withdraw':
                    prev_announce = False

            else:
                msg_type = 'announce'
                prev_announce = True

            if msg_type == 'announce':
                as_path = random.choice(as_paths)
            else:
                as_path = ''

            announcement = str(time) + '|' + str(msg_type) + '|' + str(remote_address) + '|' + str(from_participant) \
                           + '|' + str(local_address) + '|' + str(local_asn) + '|' + str(as_path) + '|' + str(prefix)

            outfile.write(announcement + '\n')


''' main '''
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('from_participants', help='asn format 1:100')
    parser.add_argument('prefix', help='prefix')
    parser.add_argument('as_paths', help='as paths separated by semi-colon, and ases within as path separated by comma: 100,200;300,400')
    parser.add_argument('start_time', help='start time')
    parser.add_argument('interval', help='interval')
    parser.add_argument('out_path', help='path to output file')
    args = parser.parse_args()

    main(args)