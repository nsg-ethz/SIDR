#!/usr/bin/env python
#  Author:
#  Muhammad Shahbaz (muhammad.shahbaz@gatech.edu)
#  Rudiger Birkner (Networked Systems Group ETH Zurich)

from rib_backend import SQLRIB

LOG = False


class RIB(object):
    def __init__(self, config):
        self.down = True
        self.config = config
        sdx_id = self.config.id
        self.rib = SQLRIB(sdx_id, ["input", "local", "output"])

    def update(self, participant, route):
        origin = None
        as_path = None
        med = None
        atomic_aggregate = None
        communities = ''

        route_list = []

        if 'state' in route['neighbor']:
            if route['neighbor']['state'] == 'down':
                if LOG:
                    print "PEER DOWN - PARTICIPANT " + str(participant)

                routes = self.get_routes('input', participant, None, None, all)

                for route_item in routes:
                    route_list.append({'withdraw': route_item})

                self.delete_all_routes(participant, 'output')

                self.delete_all_routes(participant, 'input')

            elif route['neighbor']['state'] == 'up':
                # announce all existing prefixes from local rib
                if LOG:
                    print "PEER UP - PARTICIPANT " + str(participant)

                routes = self.get_routes('local', participant, None, None, all)

                for route_item in routes:
                    route_list.append({'re-announce': route_item})

        if 'message' in route['neighbor']:
            if 'update' in route['neighbor']['message']:
                if 'attribute' in route['neighbor']['message']['update']:
                    attribute = route['neighbor']['message']['update']['attribute']

                    origin = attribute['origin'] if 'origin' in attribute else ''

                    temp_as_path = attribute['as-path'] if 'as-path' in attribute else []

                    temp_as_set = attribute['as-set'] if 'as-set' in attribute else []

                    as_path = ' '.join(map(str, temp_as_path)).replace('[', '').replace(']', '').replace(',', '')
                    if len(temp_as_set) > 0:
                        as_path += ' ( ' + ' '.join(map(str, sorted(list(temp_as_set), key=int))).replace('[',
                                                                                                          '').replace(
                            ']', '').replace(',', '') + ' )'

                    if LOG:
                        print "AS PATH: " + str(attribute['as-path'] if 'as-path' in attribute else "empty")
                        print "AS SET: " + str(attribute['as-set'] if 'as-set' in attribute else "empty")
                        print "COMBINATION: " + str(as_path)

                    med = attribute['med'] if 'med' in attribute else ''

                    community = attribute['community'] if 'community' in attribute else ''
                    communities = ''
                    for c in community:
                        communities += ':'.join(map(str, c)) + " "

                    atomic_aggregate = attribute['atomic-aggregate'] if 'atomic-aggregate' in attribute else ''

                if 'announce' in route['neighbor']['message']['update']:
                    announce = route['neighbor']['message']['update']['announce']
                    if 'ipv4 unicast' in announce:
                        for next_hop in announce['ipv4 unicast'].keys():
                            for prefix in announce['ipv4 unicast'][next_hop].keys():
                                self.add_route("input",
                                               participant,
                                               prefix,
                                               (
                                                   next_hop,
                                                   origin,
                                                   as_path,
                                                   communities,
                                                   med,
                                                   atomic_aggregate
                                               )
                                               )
                                self.rib.commit()
                                announce_route = self.get_routes("input", participant, prefix, None, False)

                                route_list.append({'announce': announce_route})

                elif 'withdraw' in route['neighbor']['message']['update']:
                    withdraw = route['neighbor']['message']['update']['withdraw']
                    if 'ipv4 unicast' in withdraw:
                        for prefix in withdraw['ipv4 unicast'].keys():
                            deleted_route = self.get_routes("input", participant, prefix, None, False)
                            self.delete_route("input", participant, prefix)

                            route_list.append({'withdraw': deleted_route})
        return route_list

    def process_notification(self, participant, route):
        if 'shutdown' == route['notification']:
            self.delete_all_routes("input", participant)
            self.delete_all_routes("local", participant)
            self.delete_all_routes("output", participant)

            # TODO: send shutdown notification to participants

    # Helper Methods
    def add_route(self, rib_name, participant, prefix, attributes):
        self.rib.add(rib_name, int(participant), prefix, attributes)
        self.rib.commit()

    def get_routes(self, rib_name, columns, participants, prefix, next_hop, all_entries):
        key_items = dict()
        key_sets = None

        if prefix:
            key_items['prefix'] = prefix
        if next_hop:
            key_items['next_hop'] = next_hop
        if participants:
            if isinstance(participants, list):
                key_sets = ('participant', [int(participant) for participant in participants])
            else:
                key_items['participant'] = int(participants)

        return self.rib.get(rib_name, columns, key_sets, key_items, all_entries)

    def delete_route(self, rib_name, participant, prefix):
        key_items = {
            "participant": int(participant),
            "prefix": prefix
        }
        self.rib.delete(rib_name, key_items)
        self.rib.commit()

    def delete_all_routes(self, rib_name, participant):
        key_items = {
            "participant": int(participant)
        }
        self.rib.delete(rib_name, key_items)
        self.rib.commit()

    def get_all_prefixes_advertised(self, from_participant, to_participant=None):
        """
        all prefixes that from_participant advertised to to_participant
        :param from_participant:
        :param to_participant:
        :return: set of prefix strings
        """
        prefixes = set()
        columns = ['prefix']

        if to_participant and to_participant not in self.config.participants[from_participant].peers_in:
            return None

        routes = self.get_routes('input', columns, from_participant, None, None, True)

        for route in routes:
            prefixes.add(route['prefix'])

        return prefixes

    def get_all_participants_advertising(self, prefix, to_participant=None):
        """
        all participants that advertise prefix
        :param prefix:
        :param to_participant:
        :return: set of participant ids
        """
        participants = set()
        columns = ['participant']

        routes = self.get_routes('input', columns, None, prefix, None, True)

        participants = set([route['participant'] for route in routes])
        if to_participant:
            participants = participants.intersection(self.config.participants[to_participant].peers_out)

        return participants

    def get_all_receiver_participants(self, prefix, from_participant=None):
        """
        all participants that got an advertisement for prefix
        :param prefix:
        :param from_participant: optional
        :return: set of participants
        """
        participants = set()
        columns = ['participant']

        if from_participant:
            route = self.get_routes('input', columns, from_participant, prefix, None, False)
            if route:
                participants = set(self.config.participants[from_participant].peers_in)
        else:
            routes = self.get_routes('local', columns, None, prefix, None, True)
            participants = set([route['participant'] for route in routes])
        return participants

    def get_best_path_participants(self, ingress_participant):
        """
        all participants that ingress_participant uses for a best path
        :param ingress_participant:
        :return: set of participants
        """
        participants = set()
        columns = ['next_hop']

        routes = self.get_routes('local', columns, ingress_participant, None, None, True)
        participants = set([self.config.portip_2_participant[route['next_hop']] for route in routes])
        return participants

    def get_all_participants_using_best_path(self, prefix=None, egress_participant=None):
        """
        all participants that use egress_participant for a best path
        :param prefix:
        :param egress_participant:
        :return: set of participants
        """
        participants = set()
        columns = ['participant']

        next_hops = self.config.participant_2_portip[egress_participant]

        for next_hop in next_hops:
            routes = self.get_routes('local', columns, None, prefix, next_hop, True)
            participants.update(set([route['participant'] for route in routes]))

        return participants

    def get_route(self, prefix, from_participant, to_participant=None):
        """
        get route for prefix that from_participant advertised to to_participant
        :param prefix:
        :param from_participant:
        :param to_participant:
        :return:route dict
        """
        route = self.get_routes('input', None, from_participant, prefix, None, False)
        if not (to_participant and to_participant not in self.config.participants[from_participant].peers_in):
            return route
        return None

    def get_all_participant_sets(self, prefix_2_vnh):
        participant_sets = []

        for prefix in prefix_2_vnh:
            participant_sets.append(self.get_all_participants_advertising(prefix))

        return participant_sets
