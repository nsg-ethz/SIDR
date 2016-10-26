import json
import time
import argparse

from multiprocessing.connection import Client

LOG = False


class Notifier(object):
    def __init__(self, config_file, notifications_file):
        self.address, self.port = self.parse_config(config_file)

        self.time_to_notifications = self.parse_notifications(notifications_file)

        self.send_notification(self.time_to_notifications, self.address, self.port)

    def parse_config(self, config_file):
        config = json.load(open(config_file, 'r'))

        address = config["SDXes"]["1"]["Address"]
        port = config["SDXes"]["1"]["Loop Detector"]["Port"]

        return address, port

    def parse_notifications(self, notifications_file):
        out = {}
        with open(notifications_file, 'r') as f:
            notifications = json.load(f)
            for notification in notifications:
                k = notification['time']
                notification.pop('time', None)
                if k not in out:
                    out[k] = []
                out[k].append(notification)
        return out

    @staticmethod
    def send_notification(time_to_notifications, address, port):
        if time_to_notifications:
            max_time = max(time_to_notifications.keys())
            if LOG:
                print "This script will run for ", max_time, " seconds"
            for ind in range(1, max_time + 1):
                if ind in time_to_notifications:
                    if LOG:
                        print "Sending notifications at time ", ind
                    socket = Client((address, port))
                    data = time_to_notifications[ind]
                    socket.send(json.dumps(data))
                    socket.close()
                time.sleep(1)

''' main '''
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('config_file', help='path to config file')
    parser.add_argument('notifications_file', help='path to notifications file')
    args = parser.parse_args()

    Notifier(args.config_file, args.notifications_file)
