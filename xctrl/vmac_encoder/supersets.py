#!/usr/bin/env python
#  Author:
#  Rudiger Birkner (Networked Systems Group ETH Zurich)

import logging
from collections import defaultdict
from lib import XCTRLModule


from netaddr import IPNetwork


class SuperSetEncoder(XCTRLModule):
    def __init__(self, config, event_queue, debug, rib, loop_detection, test):
        super(SuperSetEncoder, self).__init__(config, event_queue, debug)
        self.rib = rib
        self.loop_detection = loop_detection

        self.supersets = list()

    def update_supersets(self, updates):
        sdx_msgs = {"type": "update",
                    "changes": []}

        for update in updates:
            if 'announce' in update:
                prefix = update['announce']['prefix']

                # get set of all participants advertising that prefix
                basic_set = self.rib.get_all_participants_advertising(prefix, self.config.participants)

                # check if this set is a subset of one of the existing supersets
                if not SuperSetEncoder.is_subset_of_superset(basic_set, self.supersets):
                    # since it is not a subset, we have to either extend an existing superset (if possible)
                    # or add a new subset

                    diffs = [len(basic_set.difference(set(superset))) for superset in self.supersets]
                    unions  = [len(basic_set.union(set(superset))) for superset in self.supersets]
                    sorted_diff = sorted(diffs)

                    new_members = None
                    superset_index = None
                    add_superset = True

                    # check to which superset the minimal number of participants has to be added while
                    # staying within the maximum size
                    for i in range(0, len(sorted_diff)):
                        index = diffs.index(sorted_diff[i])
                        if unions[index] <= self.config.vmac_encoder.max_superset_size:
                            new_members = list(basic_set.difference(set(self.supersets[i])))
                            self.supersets[i].extend(new_members)
                            add_superset = False
                            superset_index = index
                            break

                    # if it is not possible to extend a superset, a new superset has to be created
                    if add_superset:
                        self.supersets.append(list(basic_set))
                        superset_index = len(self.supersets) - 1
                        for participant in self.supersets[-1]:
                            # changes in the superset are prepared to be sent to the controller
                            sdx_msgs["changes"].append({"participant_id": participant,
                                                       "superset": superset_index,
                                                       "position": self.supersets[superset_index].index(participant)})
                    else:
                        for participant in new_members:
                            # changes in the superset are prepared to be sent to the controller
                            sdx_msgs["changes"].append({"participant_id": participant,
                                                       "superset": superset_index,
                                                       "position": self.supersets[superset_index].index(participant)})

                    # if preconfigured threshold is exceeded, then start completely from scratch
                    if len(self.supersets) > self.config.vmac_encoder.superset_threshold:
                        self.recompute_all_supersets()

                        sdx_msgs = {"type": "new",
                                    "changes": []}

                        for superset in self.supersets:
                            for participant in superset:
                                sdx_msgs["changes"].append({"participant_id": participant,
                                                           "superset": superset_index,
                                                           "position": self.supersets[superset_index].index(participant)})

            elif 'withdraw' in update:
                continue

        self.logger.debug('update_supersets(): ' + str(self.supersets))

        # check which participants joined a new superset
        return sdx_msgs

    def recompute_all_supersets(self):
        # get all sets of participants advertising the same prefix
        peer_sets = self.rib.get_all_participant_sets(self.config.vmac_encoder.prefix_2_vnh)

        # remove all subsets
        peer_sets.sort(key=len, reverse=True)
        for i in range(0, len(peer_sets)):
            for j in reversed(range(i+1, len(peer_sets))):
                if peer_sets[i].issuperset(peer_sets[j]):
                    peer_sets.remove(peer_sets[j])

        # start combining sets to supersets
        supersets = []

        # start building the supersets by combining the sets with the largest intersections
        for tmp_set in peer_sets:
            peer_sets.remove(tmp_set)
            superset = tmp_set

            intersects = [len(superset.intersection(s)) for s in peer_sets]

            for i in range(0, len(intersects)):
                index = intersects.index(max(intersects))
                if (len(superset) == self.config.max_size) or (intersects[index] == -1):
                    break
                if len(superset.union(peer_sets[index])) <= self.config.max_size:
                    superset = superset.union(peer_sets[index])
                    intersects[index] = -1
            for i in reversed(range(0, len(intersects))):
                if intersects[i] == -1:
                    peer_sets.remove(peer_sets[i])
            supersets.append(list(superset))
        # check if threshold is still exceeded and if so adjust it
        if len(superset) > self.xrs.superset_threshold:
            self.config.vmac_encoder.superset_threshold *= 2

        self.supersets = supersets

    @staticmethod
    def is_subset_of_superset(subset, supersets):
        for superset in supersets:
            if (set(superset)).issuperset(subset):
                return True
        return False

    def vnh_assignment(self, updates):
        for update in updates:
            if 'announce' in update:
                prefix = update['announce']['prefix']

                if prefix not in self.config.vmac_encoder.prefix_2_vnh:
                    # get next VNH and assign it the prefix
                    self.config.vmac_encoder.num_vnhs_in_use += 1
                    vnh = str(self.config.vmac_encoder.vnhs[self.config.vmac_encoder.num_vnhs_in_use])

                    self.config.vmac_encoder.prefix_2_vnh[prefix] = vnh
                    self.config.vmac_encoder.vnh_2_prefix[vnh] = prefix

    def prefix_to_vnh(self, prefix):
        return self.config.vmac_encoder.prefix_2_vnh[prefix]

    def vnh_to_prefix(self, vnh):
        return self.config.vmac_encoder.vnh_2_prefix[vnh]

    def vmac(self, vnh, participant):
        vmac_bitstring = ""
        vmac_addr = ""

        if vnh in self.config.vmac_encoder.vnh_2_prefix:
            # get corresponding prefix
            prefix = self.config.vmac_encoder.vnh_2_prefix[vnh]
            # get set of participants advertising prefix
            basic_set = self.rib.get_all_participants_advertising(prefix, self.config.participants)



            # get corresponding superset identifier
            superset_identifier = 0
            for i in range(0, len(self.supersets)):
                if (set(self.supersets[i])).issuperset(basic_set):
                    superset_identifier = i
                    break

            vmac_bitstring = '{num:0{width}b}'.format(num=superset_identifier,
                                                      width=(self.config.vmac_encoder.vmac_size -
                                                             self.config.vmac_encoder.max_superset_size -
                                                             self.config.vmac_encoder.best_path_size)
                                                      )

            # add one bit for each participant that is a member of the basic set and has a "link" to it
            set_bitstring = ""

            self.logger.debug('Basic Set: ' + str(basic_set) +
                              ', Peers Out: ' + str(self.config.participants[participant].peers_out) +
                              'Loop Detection: ' + str(self.loop_detection[participant][prefix]))

            for temp_participant in self.supersets[superset_identifier]:
                if temp_participant in basic_set and temp_participant in self.config.participants[participant].peers_out and \
                                temp_participant not in self.loop_detection[participant][prefix]:
                    set_bitstring += "1"
                else:
                    set_bitstring += "0"
            if len(set_bitstring) < self.config.vmac_encoder.max_superset_size:
                set_bitstring += '{num:0{width}b}'.format(num=0, width=(self.config.vmac_encoder.max_superset_size -
                                                                        len(set_bitstring)))

            vmac_bitstring += set_bitstring

            # add identifier of best path
            route = self.rib.get_route_from_rib(participant, 'local', prefix)
            if route:
                best_participant = self.config.portip_2_participant[route['next_hop']]

                vmac_bitstring += '{num:0{width}b}'.format(num=best_participant,
                                                           width=self.config.vmac_encoder.best_path_size)

                # convert bitstring to hexstring and then to a mac address
                vmac_addr = self.bitstring_to_mac_address(vmac_bitstring)

                self.logger.debug('VMAC-Mapping \nParticipant: ' + str(participant) + ', Prefix: ' + str(prefix) +
                                  'Best Path: ' + str(best_participant) + '\nSuperset ' + str(superset_identifier) +
                                  ': ' + str(self.supersets[superset_identifier]) + '\nVMAC: ' +
                                  str(vmac_addr) + ', Bitstring: ' + str(vmac_bitstring))

        return vmac_addr

    def best_path_match(self, participant_id):
        # add participant identifier
        vmac_bitstring = '{num:0{width}b}'.format(num=participant_id,
                                                  width=self.config.vmac_encoder.vmac_size)

        # convert bitstring to hexstring and then to a mac address
        return self.bitstring_to_mac_address(vmac_bitstring)

    def best_path_mask(self):
        # add participant identifier
        vmac_bitstring = '{num:0{width}b}'.format(num=2**self.config.vmac_encoder.best_path_size - 1,
                                                  width=self.config.vmac_encoder.vmac_size)

        # convert bitstring to hexstring and then to a mac address
        return self.bitstring_to_mac_address(vmac_bitstring)

    def participant_bit_match(self, participant):
        for i in range(0, len(self.supersets)):
            if participant in self.supersets[i]:
                participant_position = self.supersets[i].index(participant) + 1
                superset_identifier = i

                # add participant identifier
                vmac_bitstring = '{num:0{width}b}'.format(num=superset_identifier,
                                                              width=self.config.vmac_encoder.superset_id_size)

                vmac_bitstring += '{num:0{width}b}'.format(num=1, width=participant_position)
                vmac_bitstring += '{num:0{width}b}'.format(num=0,
                                                           width=self.config.vmac_encoder.vmac_size-len(vmac_bitstring))

                # convert bitstring to hexstring and then to a mac address
                return self.bitstring_to_mac_address(vmac_bitstring)

    def participant_bit_mask(self, participant):
        for i in range(0, len(self.supersets)):
            if participant in self.supersets[i]:
                participant_position = self.supersets[i].index(participant) + 1

                # add participant identifier
                vmac_bitstring = '{num:0{width}b}'.format(num=2**self.config.vmac_encoder.superset_id_size-1,
                                                          width=self.config.vmac_encoder.superset_id_size)

                vmac_bitstring += '{num:0{width}b}'.format(num=1, width=participant_position)
                vmac_bitstring += '{num:0{width}b}'.format(num=0,
                                                           width=self.config.vmac_encoder.vmac_size-len(vmac_bitstring))

                # convert bitstring to hexstring and then to a mac address
                return self.bitstring_to_mac_address(vmac_bitstring)

    def participant_port_match(self, participant, port):
        # port match
        port_match_length = self.config.vmac_encoder.superset_id_size + self.config.vmac_encoder.max_superset_size
        vmac_bitstring = '{num:0{width}b}'.format(num=port,
                                                  width=port_match_length)
        vmac_bitstring += '{num:0{width}b}'.format(num=participant,
                                                  width=self.config.vmac_encoder.best_path_size)

        # convert bitstring to hexstring and then to a mac address
        return self.bitstring_to_mac_address(vmac_bitstring)

    def participant_port_mask(self):
        vmac_bitstring = '{num:0{width}b}'.format(num=2**self.config.vmac_encoder.vmac_size-1,
                                                  width=self.config.vmac_encoder.vmac_size)

        # convert bitstring to hexstring and then to a mac address
        return self.bitstring_to_mac_address(vmac_bitstring)

    def bitstring_to_mac_address(self, bit_string):
        vmac_addr = '{num:0{width}x}'.format(num=int(bit_string,2), width=self.config.vmac_encoder.vmac_size/4)
        vmac_addr = ':'.join([vmac_addr[i]+vmac_addr[i+1] for i in range(0,self.config.vmac_encoder.vmac_size/4,2)])

        return vmac_addr


class SuperSetEncoderConfig(object):
    def __init__(self, vmac_size, superset_id_size, max_superset_size, best_path_size, superset_threshold, vnhs):
        self.vmac_size = vmac_size
        self.superset_id_size = superset_id_size
        self.max_superset_size = max_superset_size
        self.best_path_size = best_path_size
        self.superset_threshold = superset_threshold

        self.vnhs = IPNetwork(vnhs)
        self.num_vnhs_in_use = 0
        self.vnh_2_prefix = {}
        self.prefix_2_vnh = {}
