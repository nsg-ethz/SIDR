import argparse
from netaddr import IPNetwork, IPAddress
from scapy.all import RandMAC
import json


def main(argv):
    config = {"SDXes": dict()}

    current_sdx = 1

    # local SDX default settings
    local_sdx_network = "172.0.0.0/16"
    ip_generator = IPAddressGenerator(local_sdx_network)
    asn_generator = ASNGenerator()

    num_participants = int(argv.num_participants)

    config_file = argv.out_path + "global.cfg"

    # local SDX config
    tmp_sdx = {"Address": "localhost",
               "VNHs": "172.1.1.1/24",
               "VMAC Computation": {
                   "VMAC Size": 48,
                   "Superset ID Size": 6,
                   "Max Superset Size": 30,
                   "Best Path Size": 12,
                   "Superset Threshold": 10
               },
               "Loop Detector": {
                   "Port": 2201,
                   "Max Random Value": 10000
               },
               "Policy Handler": {
                   "Address": "localhost",
                   "Port": 2301
               },
               "Route Server": {
                    "IP": "172.1.255.254",
                    "MAC": "08:00:27:89:33:dd",
                    "Connection Port": 2301,
                    "Connection Key": "xrs",
                    "Interface": "rs1-eth0",
                    "Fabric Port": 4
               },
               "Participants": {}
               }

    for i in range(1, num_participants + 1):
        tmp_sdx["Participants"][str(i)] = {
            "Ports": [{
                "Id": i,
                "MAC": str(RandMAC()),
                "IP": ip_generator.get_address()
            }],
            "ASN": asn_generator.get_asn()
        }

        if i == 1:
            tmp_sdx["Participants"][str(i)]["Peers"] = range(2, num_participants + 1)
        else:
            tmp_sdx["Participants"][str(i)]["Peers"] = [1]

    config["SDXes"]["1"] = tmp_sdx

    # remote SDXes
    config["SDXes"]["2"] = {
        "Address": "localhost",
        "Loop Detector": {
            "Port": 9999
        },
        "Participants": {
            "1": {
                "ASN": 5000
            },
            "2": {
                "ASN": 5100
            }
        }
    }

    config["SDXes"]["3"] = {
        "Address": "localhost",
        "Loop Detector": {
            "Port": 9999
        },
        "Participants": {
            "1": {
                "ASN": 6000
            },
            "2": {
                "ASN": 6100
            }
        }
    }

    with open(config_file, 'w') as outfile:
        json.dump(config, outfile)

class IPAddressGenerator(object):
    def __init__(self, network):
        self.network = IPNetwork(network)
        self.start = self.network.value
        self.current = 0

    def get_address(self):
        self.current += 1
        return str(IPAddress(self.start + self.current))


class ASNGenerator(object):
    def __init__(self):
        self.start = 100
        self.current = 0

    def get_asn(self):
        self.current += 1
        return self.start + self.current

''' main '''
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('num_participants', help='number of participants at local sdx - participant one is connected to all others - so 1 vs num-1')
    parser.add_argument('out_path', help='path to output file')
    args = parser.parse_args()

    main(args)