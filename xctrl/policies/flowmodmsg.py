#!/usr/bin/env python
#  Author:
#  Rudiger Birkner (Networked Systems Group ETH Zurich)

import json


class FlowModMsgBuilder(object):
    def __init__(self, participant):
        self.participant = participant
        self.flow_mods = []

    def add_flow_mod(self, mod_type, rule_type, priority, match, action, cookie = None):
        if cookie is None:
            cookie = (len(self.flow_mods)+1, 65535)

        fm = {
               "cookie": cookie,
               "mod_type": mod_type,
               "rule_type": rule_type,
               "priority": priority,
               "match": match,
               "action": action
             }

        self.flow_mods.append(fm)

        return cookie

    def delete_flow_mod(self, mod_type, rule_type, cookie, cookie_mask):
        fm = {
            "cookie": (cookie, cookie_mask),
            "mod_type": mod_type,
            "rule_type": rule_type,
        }

        self.flow_mods.append(fm)

    def get_msg(self):
        msg = {
                "auth_info": {
                               "participant" : self.participant,
                             },
                "flow_mods": self.flow_mods
              }

        return msg
