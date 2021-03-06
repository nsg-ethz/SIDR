#  Author:
#  Rudiger Birkner (Networked Systems Group ETH Zurich)

import json
import logging

from Queue import Queue
# PRIORITIES
FLOW_MISS_PRIORITY = 0

# COOKIES
NO_COOKIE = 0

class Config(object):
    def __init__(self, config_file, instance):
        self.server = None

        self.ofv = None
        self.tables = None
        self.datapath_ports = None

        self.datapaths = {}
        self.parser = None
        self.ofproto = None

        # loading config file
        tmp_config = json.load(open(config_file, 'r'))
        config = tmp_config["SDXes"][str(instance)]

        if "RefMon Settings" in config:
            if "fabric options" in config["RefMon Settings"]:
                if "tables" in config["RefMon Settings"]["fabric options"]:
                    self.tables = config["RefMon Settings"]["fabric options"]["tables"]
                if "OF version" in config["RefMon Settings"]["fabric options"]:
                    self.ofv = config["RefMon Settings"]["fabric options"]["OF version"]

            if "fabric connections" in config["RefMon Settings"]:
                self.datapath_ports = config["RefMon Settings"]["fabric connections"]

            if "long URL" in config["RefMon Settings"]:
                self.long_url = config["RefMon Settings"]["long URL"]
            if "short URL" in config["RefMon Settings"]:
                self.short_url = config["RefMon Settings"]["short URL"]
        else:
            raise InvalidConfigError(config)

        # check if valid config
        if not (self.ofv == "1.3" and self.tables and self.datapath_ports):
            raise InvalidConfigError(config)

class InvalidConfigError(Exception):
    def __init__(self, flow_mod):
        self.flow_mod = flow_mod
    def __str__(self):
        return repr(self.flow_mod)


class MultiTableController():
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger('MultiTableController')
        self.logger.info('mt_ctrlr: creating an instance of MultiTableController')

        self.fm_queue = Queue()

    def init_fabric(self):    
        # install table-miss flow entry
        self.logger.info("mt_ctrlr: init fabric")
        match = self.config.parser.OFPMatch()
        actions = [self.config.parser.OFPActionOutput(self.config.ofproto.OFPP_CONTROLLER, self.config.ofproto.OFPCML_NO_BUFFER)]
        instructions = [self.config.parser.OFPInstructionActions(self.config.ofproto.OFPIT_APPLY_ACTIONS, actions)]

        for table in self.config.tables.values():
            mod = self.config.parser.OFPFlowMod(datapath=self.config.datapaths["main"], 
                                                cookie=NO_COOKIE, cookie_mask=1, 
                                                table_id=table, 
                                                command=self.config.ofproto.OFPFC_ADD, 
                                                priority=FLOW_MISS_PRIORITY, 
                                                match=match, instructions=instructions)
            self.config.datapaths["main"].send_msg(mod)

    def switch_connect(self, dp):
        self.config.datapaths["main"] = dp
        self.config.ofproto = dp.ofproto
        self.config.parser = dp.ofproto_parser
        self.logger.info("mt_ctrlr: main switch connected")
        self.init_fabric()

        if self.is_ready():
            while not self.fm_queue.empty():
                self.process_flow_mod(self.fm_queue.get())

    def switch_disconnect(self, dp):
        if "main" in self.config.datapaths and self.config.datapaths["main"] == dp:
            self.logger.info("mt_ctrlr: main switch disconnected")
            del self.config.datapaths["main"]

    def process_flow_mod(self, fm):
        if not self.is_ready():
            self.fm_queue.put(fm)
        else:
            mod = fm.get_flow_mod(self.config)
            self.config.datapaths["main"].send_msg(mod)
           
    def packet_in(self, ev):
        self.logger.info("mt_ctrlr: packet in")

    def is_ready(self):
        if "main" in self.config.datapaths:
            return True
        return False