#  Author:
#  Rudiger Birkner (Networked Systems Group ETH Zurich)

## RouteServer-specific imports
import logging
import json
from netaddr import *
from collections import defaultdict

from route_server.route_server import RouteServerConfig
from vmac_encoder.supersets import SuperSetEncoderConfig
from arp_proxy.arp_proxy import ARPProxyConfig
from loop_detection.loop_detector import LoopDetectorConfig


class Config():
    def __init__(self, identifier, config_file):
        # General Config
        self.id = identifier

        self.sdx = None
        self.sdx_registry = dict()

        self.rs_config = None
        self.arp_proxy = None
        self.vmac_encoder = None
        self.loop_detector = None

        self.participants = {}
        self.port_2_participant = {}

        self.participant_2_port = defaultdict(list)
        self.portip_2_participant = {}
        self.participant_2_portip = defaultdict(list)

        self.portmac_2_participant = {}
        self.participant_2_portmac = defaultdict(list)

        self.asn_2_participant = {}
        self.participant_2_asn = {}

        self.parse_config(config_file)

    def parse_config(self, config_file):
        # loading config file
        config = json.load(open(config_file, 'r'))

        max_random_value = 1000

        if "SDXes" in config:

            asn_2_sdx = defaultdict(set)
            sdx_2_asn = defaultdict(set)

            for sdx_identifier in config["SDXes"]:
                sdx = config["SDXes"][sdx_identifier]

                sdx_id = int(sdx_identifier)

                if "Address" in sdx:
                    address = sdx["Address"]
                if "Port" in sdx:
                    port = sdx["Port"]

                if sdx_id == self.id:
                    if "Refmon URL" in sdx:
                        self.refmon_url = sdx["Refmon URL"]

                    if "VNHs" in sdx:
                        vnhs = IPNetwork(sdx["VNHs"])

                    if "VMAC Computation" in config:
                        if "VMAC Size" in config["VMAC Computation"]:
                            vmac_size = config["VMAC Computation"]["VMAC Size"]
                        if "Superset ID Size" in config["VMAC Computation"]:
                            superset_id_size = config["VMAC Computation"]["Superset ID Size"]
                        if "Max Superset Size" in config["VMAC Computation"]:
                            max_superset_size = config["VMAC Computation"]["Max Superset Size"]
                        if "Best Path Size" in config["VMAC Computation"]:
                            best_path_size = config["VMAC Computation"]["Best Path Size"]
                        if "Superset Threshold" in config["VMAC Computation"]:
                            superset_threshold = config["VMAC Computation"]["Superset Threshold"]

                        self.vmac_encoder = SuperSetEncoderConfig(vmac_size,
                                                                  superset_id_size,
                                                                  max_superset_size,
                                                                  best_path_size,
                                                                  superset_threshold,
                                                                  vnhs)
                    if "Loop Detector" in sdx:
                        if "Max Random Value" in sdx["Loop Detector"]:
                            max_random_value = sdx["Loop Detector"]["Max Random Value"]

                    if "Route Server" in sdx:
                        if "IP" in sdx["Route Server"]:
                            ip = sdx["Route Server"]["IP"]
                        if "Connection Port" in sdx["Route Server"]:
                            connection_port = sdx["Route Server"]["Connection Port"]
                        if "Connection Key" in sdx["Route Server"]:
                            connection_key = sdx["Route Server"]["Connection Key"]
                        if "Interface" in sdx["Route Server"]:
                            interface = sdx["Route Server"]["Interface"]
                        self.route_server = RouteServerConfig(ip, connection_port, connection_key, interface)

                        self.arp_proxy = ARPProxyConfig(interface)

                    if "Participants" in sdx:
                        peers_out = defaultdict(list)
                        for participant_name in sdx["Participants"]:
                            participant = sdx["Participants"][participant_name]

                            for peer in participant["Peers"]:
                                peers_out[peer].append(int(participant_name))

                        for participant_name in sdx["Participants"]:
                            participant_id = int(participant_name)
                            participant = sdx["Participants"][participant_name]

                            # adding asn and mappings
                            asn = participant["ASN"]
                            self.asn_2_participant[participant["ASN"]] = participant_id
                            self.participant_2_asn[participant_id] = participant["ASN"]

                            # adding ports and mappings
                            ports = [Port(participant["Ports"][i]['Id'],
                                          participant["Ports"][i]['MAC'],
                                          participant["Ports"][i]['IP'])
                                     for i in range(0, len(participant["Ports"]))]

                            for i in range(0, len(participant["Ports"])):
                                self.port_2_participant[participant["Ports"][i]['Id']] = participant_id
                                self.portip_2_participant[participant["Ports"][i]['IP']] = participant_id
                                self.portmac_2_participant[participant["Ports"][i]['MAC']] = participant_id
                                self.participant_2_port[participant_id].append(participant["Ports"][i]['Id'])
                                self.participant_2_portip[participant_id].append(participant["Ports"][i]['IP'])
                                self.participant_2_portmac[participant_id].append(participant["Ports"][i]['MAC'])

                            peers_in = participant["Peers"]

                            self.participants[participant_id] = Participant(participant_id,
                                                                            asn,
                                                                            ports,
                                                                            peers_in,
                                                                            peers_out[participant_id])

                else:
                    if "Participants" in sdx:
                        participants = sdx["Participants"].values()
                    self.sdx_registry[sdx_id] = SDX(sdx_id, address, port, participants)

                for participant in sdx["Participants"].values():
                    sdx_2_asn[sdx_id].add(participant["ASN"])
                    asn_2_sdx[participant["ASN"]].add(sdx_id)

            self.loop_detector = LoopDetectorConfig(sdx_2_asn, asn_2_sdx, max_random_value)


class SDX(object):
    def __init__(self, identifier, address, port, refmon_url, participants):
        self.id = identifier
        self.address = address
        self.port = port
        self.refmon_url = refmon_url
        self.participants = participants


class Participant(object):
    def __init__(self, identifier, asn, ports, peers_in, peers_out):
        self.id = identifier
        self.asn = asn
        self.ports = ports
        # all other participants that this participant is advertising the routes to
        self.peers_in = peers_in
        # all participants that advertise routes to this pariticipant
        self.peers_out = peers_out


class Port(object):
    def __init__(self, port_id, mac, ip):
        self.id = port_id
        self.mac = mac
        self.ip = ip


class XCTRLModule(object):
    def __init__(self, config, event_queue, debug):
        self.logger = logging.getLogger(__name__)
        if debug:
            self.logger.setLevel(logging.DEBUG)
        self.logger.info('init')

        self.config = config
        self.event_queue = event_queue


class XCTRLEvent(object):
    def __init__(self, origin, type, data):
        self.origin
        self.type
        self.data
