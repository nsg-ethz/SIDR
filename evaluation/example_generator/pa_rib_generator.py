import argparse
import random


def main(argv):
    announcements_file = argv.out_path + "announcements.log"

    start_time =  argv.start_time
    curr_announcement = 0

    remote_address = '172.1.0.1'
    local_address = '172.1.255.254'
    local_asn = '65000'

    prefix_file = argv.prefix_file
    num_prefixes = argv.num_prefixes

    from_participant = int(argv.from_participants)

    as_paths = argv.as_paths.split(';')

    with open(announcements_file, 'w') as outfile:
        with open(prefix_file, "r") as infile:

            i = 0

            for line in prefix_file:
                i += 1

                if i > num_prefixes:
                    break

                prefix = line.strip()

                time = start_time + curr_announcement
                curr_announcement += 1

                msg_type = 'announce'

                as_path = random.choice(as_paths)

                announcement = str(time) + '|' + str(msg_type) + '|' + str(remote_address) + '|' + str(from_participant) \
                               + '|' + str(local_address) + '|' + str(local_asn) + '|' + str(as_path) + '|' + str(prefix)

                outfile.write(announcement + '\n')


''' main '''
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('from_participant', help='asn of remote as advertising the routes')
    parser.add_argument('prefix_file', help='prefix file')
    parser.add_argument('num_prefixes', help='number of prefixes to read from file')
    parser.add_argument('as_paths', help='as paths separated by semi-colon, and ases within as path separated by comma: 100,200;300,400')
    parser.add_argument('start_time', help='start time')
    parser.add_argument('out_path', help='path to output file')
    args = parser.parse_args()

    main(args)