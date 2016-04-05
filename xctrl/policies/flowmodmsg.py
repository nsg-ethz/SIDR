#!/usr/bin/env python
#  Author:
#  Rudiger Birkner (Networked Systems Group ETH Zurich)

import json


class FlowModMsgBuilder(object):
    def __init__(self):
        self.flow_mods = list()
        self.flow_mod_count = 0

    def add_flow_mod(self, mod_type, rule_type, priority, match, action, cookie = None):
        if cookie is None:
            self.flow_mod_count += 1
            cookie = (self.flow_mod_count, 2**32 - 1)

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

    def delete_flow_mod(self, mod_type, rule_type, cookie, cookie_mask=2**32 - 1):
        fm = {
            "cookie": (cookie, cookie_mask),
            "mod_type": mod_type,
            "rule_type": rule_type,
        }

        self.flow_mods.append(fm)

    def get_msg(self):
        msg = {
                "flow_mods": list(self.flow_mods)
              }

        self.flow_mods = list()

        return msg
