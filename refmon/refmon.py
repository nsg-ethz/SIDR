#  Author:
#  Rudiger Birkner (Networked Systems Group ETH Zurich)

import os
import logging
import json

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER 
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_0, ofproto_v1_3
from ryu.app.wsgi import WSGIApplication
from ryu import cfg

from lib import MultiSwitchController, MultiTableController, Config, InvalidConfigError
from ofp13 import FlowMod as OFP13FlowMod

from rest import FlowModReceiver

from time import time

LOG = False

class RefMon(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION, ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = { 'wsgi': WSGIApplication }

    def __init__(self, *args, **kwargs):
        super(RefMon, self).__init__(*args, **kwargs)

        # Used for REST API
        wsgi = kwargs['wsgi']
        wsgi.register(FlowModReceiver, self)

        self.logger = logging.getLogger('ReferenceMonitor')
        self.logger.info('refmon: start')

        # retrieve command line arguments
        CONF = cfg.CONF
        config_file_path = CONF['refmon']['config']

        config_file = os.path.abspath(config_file_path)

        # configure flow mod logging
        if CONF['refmon']['flowmodlog']:
            log_file = os.path.abspath(CONF['refmon']['flowmodlog'])
            self.flow_mod_log = open(log_file, "w")
            self.log = True
        else:
            self.log = False

        # load config from file
        self.logger.info('refmon: load config')
        try:
            self.config = Config(config_file)
        except InvalidConfigError as e:
            self.logger.info('refmon: invalid config '+str(e))

        # start controller
        self.controller = MultiTableController(self.config)

    def close(self):
        self.logger.info('refmon: stop')

        if self.log:
            self.flow_mod_log.close()

    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def dp_state_change_handler(self, ev):
        datapath = ev.datapath

        if ev.state == MAIN_DISPATCHER:
            self.controller.switch_connect(datapath)
        elif ev.state == DEAD_DISPATCHER:
            self.controller.switch_disconnect(datapath)
        
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        self.controller.packet_in(ev)

    def process_flow_mods(self, msg):
        self.logger.info('refmon: received flowmod request')

        # authorization
        if "auth_info" in msg:
            auth_info = msg["auth_info"]

            origin = auth_info["participant"]

            if "flow_mods" in msg:

                # flow mod logging
                if self.log:
                    self.flow_mod_log.write('BURST: ' + str(time()) + '\n')
                    self.flow_mod_log.write('PARTICIPANT: ' + str(msg['auth_info']['participant']) + '\n')
                    for flow_mod in msg["flow_mods"]:
                        self.flow_mod_log.write(json.dumps(flow_mod) + '\n')
                    self.flow_mod_log.write('\n')

                # push flow mods to the data plane
                self.logger.info('refmon: process ' + str(len(msg["flow_mods"])) + ' flowmods from ' + str(origin))
                for flow_mod in msg["flow_mods"]:
                    fm = OFP13FlowMod(self.config, origin, flow_mod)

                    self.controller.process_flow_mod(fm)
