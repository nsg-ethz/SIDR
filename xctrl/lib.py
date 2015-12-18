#  Author:
#  Rudiger Birkner (Networked Systems Group ETH Zurich)

## RouteServer-specific imports
import logging


class XCTRLModule(object):
    def __init__(self, config, event_queue, debug):
        self.logger = logging.getLogger(self.__class__.__name__)
        if debug:
            self.logger.setLevel(logging.DEBUG)
        self.logger.info('init')

        self.config = config
        self.event_queue = event_queue


class XCTRLEvent(object):
    def __init__(self, origin, type, data):
        self.origin = origin
        self.type = type
        self.data = data
