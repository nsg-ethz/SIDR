#  Author:
#  Rudiger Birkner (Networked Systems Group ETH Zurich)

import httplib

import json
from webob import Response

from ryu.app.wsgi import ControllerBase, route


# REST API for aSDX configuration
#
# change supersets
# POST /asdx/supersets
#
#  request body format:
#    {"type": "update/new",
#     "changes": [
#            {"participant": 81, "superset_id": 1, "index": 2},
#            {"participant": 34, "superset_id": 3, "index": 13},
#            ...]
#    }
#


superset_url = '/asdx/supersets'
correctness_url = '/asdx/correctness'

class aSDXController(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(aSDXController, self).__init__(req, link, data, **config)
        self.asdx = data
        self.superset_url = self.asdx.config.superset_url
        self.correctness_url = self.asdx.config.correctness_url
        
    @route('asdx', superset_url, methods=['POST'])
    def supersets_changed(self, req, **kwargs):
        try:
            update = json.loads(req.body)
        except SyntaxError:
            return Response(status=400)

        msgs = self.asdx.supersets_changed(update)

        body = json.dumps(msgs)
        return Response(content_type='application/json', body=body)

    @route('asdx', correctness_url, methods=['POST'])
    def forwards_update(self, req, **kwargs):
        try:
            update = json.loads(req.body)
        except SyntaxError:
            return Response(status=400)

        msgs = self.asdx.correctness_module.update_forwards(update)

        body = json.dumps(msgs)

        return Response(content_type='application/json', body=body)
