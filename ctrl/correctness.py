#  Author:
#  Rudiger Birkner (Networked Systems Group ETH Zurich)

import requests
import json

from collections import defaultdict


class ForwardCorrectness(object):
    def __init__(self, asdx):
        self.nh_sdx_2_fwds = defaultdict(set)
        self.asdx = asdx

    def check_policy(self, **kwargs):
        if "nh_sdx" in kwargs:
            fwds = list()
            for nh_sdx in kwargs["nh_sdx"]:
                fwds.extend(list(self.nh_sdx_2_fwds[nh_sdx]))
            fwds.extend(kwargs["nh_sdx"])
            fwds = set(fwds)

            if self.asdx.config.id in fwds:
                return False
            else:
                for sdx_id, sdx_attributes in self.asdx.config.nh_sdxes.iteritems():
                    if sdx_id != self.asdx.config.id:
                        self.send_forwards_update(sdx_id, "announce", fwds)
                return True

    def update_forwards(self, fwds_update):
        sender_id = fwds_update["id"]
        update_type = fwds_update["type"]
        forwards = set(fwds_update["forwards"]) if "forwards" in fwds_update else None

        current_fwds = self.nh_sdx_2_fwds[sender_id]

        if update_type == "announce":
            if forwards:
                self.nh_sdx_2_fwds[sender_id] = current_fwds.union(forwards)
            if self.asdx.config.id in current_fwds:
                self.asdx.check_policies(sender_id)
        elif update_type == "withdraw" and forwards:
            if self.asdx.id in forwards:
                self.nh_sdx_2_fwds[sender_id] = current_fwds.difference(forwards)
                self.asdx.check_policies(sender_id)
        else:
            # ERROR
            pass

        # Update all neighbors
        for sdx_id in self.asdx.config.nh_sdxes.keys():
            if sdx_id != sender_id and sdx_id != self.asdx.config.id:
                if self.asdx.config.id in forwards:
                    forwards.remove(self.asdx.config.id)
                self.send_forwards_update(sdx_id, update_type, forwards)

    def send_forwards_update(self, receiver_id, update_type, forwards):
        payload = {"id": self.asdx.config.id, "type": update_type}
        if forwards:
            payload["forwards"] = list(forwards)

        nh_sdx = self.asdx.config.nh_sdxes[receiver_id]
        url = str(nh_sdx.ip) + ":" + str(nh_sdx.port) + "" + str(self.asdx.config.correctness_url)
        r = requests.post(url, data=json.dumps(payload))

        if r.status_code == requests.codes.ok:
            self.asdx.logger.debug("Update Succeeded - "+str(r.status_code))
        else:
            self.asdx.logger.debug("Update Failed - "+str(r.status_code))
