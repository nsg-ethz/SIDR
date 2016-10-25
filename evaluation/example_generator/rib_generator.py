import argparse
import random
from netaddr import IPNetwork, IPAddress


def main(argv):
    announcements_file = argv.out_path + "1.log"

    interval = int(argv.interval)
    start_time = int(argv.start_time)
    curr_announcement = 0

    local_sdx_network = "172.0.0.0/16"
    ip_generator = IPAddressGenerator(local_sdx_network)

    local_address = '172.1.255.254'
    local_asn = '65000'

    num_announcements = int(argv.num_announcements)

    prefix = argv.prefix

    if not ':' in argv.from_participants:
        from_participants = [int(argv.from_participants)]
    else:
        tmp_from, tmp_to = argv.from_participants.split(':')
        from_participants = range(int(tmp_from), int(tmp_to) + 1)

    types = ['announce', 'withdraw']
    as_paths = argv.as_paths.split(';')

    with open(announcements_file, 'w') as outfile:

        for from_participant in from_participants:
            prev_announce = False

            for i in range(0, num_announcements):

                if i == 0 and start_time > 10:
                    time = 2
                else:
                    time = start_time + curr_announcement * interval
                curr_announcement += 1

                if prev_announce:
                    msg_type = random.choice(types)
                    if msg_type == 'withdraw':
                        prev_announce = False

                else:
                    msg_type = 'announce'
                    prev_announce = True
                
                if i == 0:
                    as_path = '7000,7100'
                elif msg_type == 'announce':
                    as_path = random.choice(as_paths)
                else:
                    as_path = ''

                announcement = str(time) + '|' + str(msg_type) + '|' + str(ip_generator.get_address(from_participant)) + '|' + str(from_participant + 100) \
                               + '|' + str(local_address) + '|' + str(local_asn) + '|' + str(as_path) + '|' + str(prefix)

                outfile.write(announcement + '\n')


class IPAddressGenerator(object):
    def __init__(self, network):
        self.network = IPNetwork(network)
        self.start = self.network.value

    def get_address(self, i):
        return str(IPAddress(self.start + i))


''' main '''
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('from_participants', help='participant id - format 1:100')
    parser.add_argument('num_announcements', help='number of announcements')
    parser.add_argument('prefix', help='prefix')
    parser.add_argument('as_paths', help='as paths separated by semi-colon, and ases within as path separated by comma: 100,200;300,400')
    parser.add_argument('start_time', help='start time')
    parser.add_argument('interval', help='interval')
    parser.add_argument('out_path', help='path to output file')
    args = parser.parse_args()

    main(args)
