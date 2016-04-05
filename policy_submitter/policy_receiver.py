#  Author:
#  Arpit Gupta (Princeton)

import json
from multiprocessing.connection import Listener

POLICY_SOCKET = ("localhost", 5551)
LOG = True


def policy_listener():
        '''Socket listener for policy events '''
        if LOG: print "Policy Event Handler started."
        listener_eh = Listener(POLICY_SOCKET, authkey=None)
        while True:
            if LOG: print "waiting for connection..."
            conn_eh = listener_eh.accept()

            tmp = conn_eh.recv()

            if tmp != "terminate":
                if LOG: print "established connection..."

                data = json.loads(tmp)

                if LOG: print "# of policy items received", len(data.values())

                # Send a message back to the sender.
                reply = "Policy items received"
                conn_eh.send(reply)
            conn_eh.close()



''' main '''
if __name__ == '__main__':
    policy_listener()
