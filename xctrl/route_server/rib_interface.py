#!/usr/bin/env python
#  Author:
#  Rudiger Birkner (Networked Systems Group ETH Zurich)


class RIBInterface(object):
    def __init__(self, config, rib):
        self.rib = rib
        self.config = config

    def get_all_prefixes_advertised(self, from_participant, to_participant=None):
        """
        all prefixes that from_participant advertised to to_participant
        :param from_participant:
        :param to_participant:
        :return: set of prefix strings
        """
        prefixes = set()
        if to_participant and to_participant not in self.config.participants[from_participant].peers_in:
            return None

        routes = self.rib[from_participant].get_all_routes("input")

        for route in routes:
            prefixes.add(route["prefix"])

        return prefixes

    def get_all_participants_advertising(self, prefix, to_participant=None):
        """
        all participants that advertise prefix
        :param prefix:
        :param to_participant:
        :return: set of participant ids
        """
        participants = set()

        for participant in self.config.participants:
            route = self.rib[participant].get_route("input", prefix)
            if route:
                if not (to_participant and to_participant in self.config.participants[participant].peers_in):
                    participants.add(participant)

        return participants

    def get_all_receiver_participants(self, prefix, from_participant=None):
        """
        all participants that got an advertisement for prefix
        :param prefix:
        :param from_participant: optional
        :return: set of participants
        """
        participants = set()

        if from_participant:
            route = self.rib[from_participant].get_route("input", prefix)
            if route:
                participants = set(self.config.participants[from_participant].peers_in)
        else:
            for participant in self.config.participants:
                route = self.rib[participant].get_route("local", prefix)
                if route:
                    participants.add(participant)
        return participants

    def get_best_path_participants(self, ingress_participant):
        """
        all participants that ingress_participant uses for a best path
        :param ingress_participant:
        :return: set of participants
        """
        participants = set()
        routes = self.rib[ingress_participant].get_all_routes("local")
        for route in routes:
            participants.add(self.config.portip_2_participant[route["next_hop"]])
        return participants

    def get_all_participants_using_best_path(self, prefix, egress_participant):
        """
        all participants that use egress_participant uses for a best path
        :param ingress_participant:
        :return: set of participants
        """
        participants = set()
        for participant in self.config.participants:
            route = self.rib[participant].get_route("local", prefix)
            if route and egress_participant == self.config.portip_2_participant[route["next_hop"]]:
                participants.add(participant)
        return participants

    def get_route(self, prefix, from_participant, to_participant=None):
        """
        get route for prefix that from_participant advertised to to_participant
        :param prefix:
        :param from_participant:
        :param to_participant:
        :return:route dict
        """
        route = self.rib[from_participant].get_route("input", prefix)
        if not (to_participant and to_participant not in self.config.participants[from_participant].peers_in):
            return route
        return None

    def get_all_participant_sets(self, prefix_2_vnh):
        participant_sets = []

        for prefix in prefix_2_vnh:
            participant_sets.append(self.get_all_participants_advertising(prefix))

        return participant_sets