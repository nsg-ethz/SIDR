import argparse
import random
from netaddr import IPNetwork, IPAddress


def main(argv):
    announcements_file = argv.out_path + "1.log"

    start_time = int(argv.start_time)

    local_sdx_network = "172.0.0.0/16"
    ip_generator = IPAddressGenerator(local_sdx_network)

    local_address = '172.1.255.254'
    local_asn = '65000'

    prefix_file = argv.prefix_file
    num_prefixes = int(argv.num_prefixes)

    from_id = int(argv.from_participant)
    from_asn = from_id + 100

    as_paths = argv.as_paths.split(';')

    with open(announcements_file, 'w') as outfile:
        with open(prefix_file, "r") as infile:

            i = 0

            for line in infile:
                i += 1

                if i > num_prefixes:
                    break

                prefix = line.strip()

                time = start_time

                msg_type = 'announce'

                as_path = random.choice(as_paths)

                announcement = str(time) + '|' + str(msg_type) + '|' + str(ip_generator.get_address(from_id)) + '|' + str(from_asn) \
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
    parser.add_argument('from_participant', help='participant id of remote as advertising the routes')
    parser.add_argument('prefix_file', help='prefix file')
    parser.add_argument('num_prefixes', help='number of prefixes to read from file')
    parser.add_argument('as_paths', help='as paths separated by semi-colon, and ases within as path separated by comma: 100,200;300,400')
    parser.add_argument('start_time', help='start time')
    parser.add_argument('out_path', help='path to output file')
    args = parser.parse_args()

    main(args)