#  Author:
#  Rudiger Birkner (Networked Systems Group ETH Zurich)

## RouteServer-specific imports
import logging
import json
from netaddr import IPNetwork
from collections import defaultdict

from route_server.route_server import RouteServerConfig
from vmac_encoder.supersets import SuperSetEncoderConfig
from arp_proxy.arp_proxy import ARPProxyConfig
from loop_detection.loop_detector import LoopDetectorConfig
from policies.policies import PolicyHandlerConfig


class Config(object):
    def __init__(self, identifier, base_path, config_file):
        # General Config
        self.base_path = base_path
        self.id = identifier

        self.sdx = None
        self.sdx_registry = dict()

        self.route_server = None
        self.arp_proxy = None
        self.vmac_encoder = None
        self.loop_detector = None
        self.policy_handler = None

        self.participants = dict()
        self.port_2_participant = dict()

        self.participant_2_port = defaultdict(list)
        self.portip_2_participant = dict()
        self.participant_2_portip = defaultdict(list)

        self.portmac_2_participant = dict()
        self.participant_2_portmac = defaultdict(list)

        self.asn_2_participant = dict()
        self.participant_2_asn = dict()

        self.refmon_url = ""

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
                if "Loop Detector" in sdx and "Port" in sdx["Loop Detector"]:
                    port = sdx["Loop Detector"]["Port"]

                if sdx_id == self.id:
                    if "RefMon Settings" in sdx and "long URL" in sdx["RefMon Settings"]:
                        self.refmon_url = sdx["RefMon Settings"]["long URL"]

                    if "VNHs" in sdx:
                        vnhs = IPNetwork(sdx["VNHs"])

                    if "VMAC Computation" in sdx:
                        if "VMAC Size" in sdx["VMAC Computation"]:
                            vmac_size = sdx["VMAC Computation"]["VMAC Size"]
                        if "Superset ID Size" in sdx["VMAC Computation"]:
                            superset_id_size = sdx["VMAC Computation"]["Superset ID Size"]
                        if "Max Superset Size" in sdx["VMAC Computation"]:
                            max_superset_size = sdx["VMAC Computation"]["Max Superset Size"]
                        if "Best Path Size" in sdx["VMAC Computation"]:
                            best_path_size = sdx["VMAC Computation"]["Best Path Size"]
                        if "Superset Threshold" in sdx["VMAC Computation"]:
                            superset_threshold = sdx["VMAC Computation"]["Superset Threshold"]

                        self.vmac_encoder = SuperSetEncoderConfig(vmac_size,
                                                                  superset_id_size,
                                                                  max_superset_size,
                                                                  best_path_size,
                                                                  superset_threshold,
                                                                  vnhs)

                    if "Loop Detector" in sdx:
                        if "Max Random Value" in sdx["Loop Detector"]:
                            max_random_value = sdx["Loop Detector"]["Max Random Value"]
                        if "Port" in sdx["Loop Detector"]:
                            loop_handler_port = sdx["Loop Detector"]["Port"]

                    if "Policy Handler" in sdx:
                        if "Address" in sdx["Policy Handler"]:
                            tmp_address = sdx["Policy Handler"]["Address"]
                        if "Port" in sdx["Policy Handler"]:
                            tmp_port = sdx["Policy Handler"]["Port"]
                        self.policy_handler = PolicyHandlerConfig(tmp_address, tmp_port)

                    if "Route Server" in sdx:
                        if "IP" in sdx["Route Server"]:
                            ip = sdx["Route Server"]["IP"]
                        if "Connection Port" in sdx["Route Server"]:
                            connection_port = sdx["Route Server"]["Connection Port"]
                        if "Connection Key" in sdx["Route Server"]:
                            connection_key = sdx["Route Server"]["Connection Key"]
                        if "Interface" in sdx["Route Server"]:
                            interface = sdx["Route Server"]["Interface"]
                        if "Fabric Port" in sdx["Route Server"]:
                            fabric_port = sdx["Route Server"]["Fabric Port"]
                        if "MAC" in sdx["Route Server"]:
                            mac = sdx["Route Server"]["MAC"]

                        rs_port = Port(fabric_port, mac, ip)

                        self.route_server = RouteServerConfig(ip, connection_port, connection_key, rs_port, interface)

                        self.arp_proxy = ARPProxyConfig(interface, rs_port)

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

                    self.sdx = SDX(sdx_id, address, port, self.refmon_url, self.participants)

                else:
                    if "Participants" in sdx:
                        participants = sdx["Participants"].values()
                    self.sdx_registry[sdx_id] = SDX(sdx_id, address, port, None, participants)

                for participant in sdx["Participants"].values():
                    sdx_2_asn[sdx_id].add(participant["ASN"])
                    asn_2_sdx[participant["ASN"]].add(sdx_id)

            self.loop_detector = LoopDetectorConfig(sdx_2_asn, asn_2_sdx, max_random_value, loop_handler_port)


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
