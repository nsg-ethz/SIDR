import argparse
import json


def main(argv):
    policy_file = argv.out_path + "all_policies.plc"

    policies = list()

    interval = int(argv.interval)
    start_time = int(argv.start_time)
    curr_policy = 0

    num_policies = int(argv.num_policies)

    if not (':' in argv.from_participants):
        from_participants = [int(argv.from_participants)]
    else:
        tmp_from, tmp_to = argv.from_participants.split(':')
        from_participants = range(int(tmp_from), int(tmp_to) + 1)

    if not (':' in argv.to_participants):
        to_participants = [int(argv.to_participants)]
    else:
        tmp_from, tmp_to = argv.to_participants.split(':')
        to_participants = range(int(tmp_from), int(tmp_to) + 1)

    for from_participant in from_participants:
        for to_participant in to_participants:
            for i in range(0, num_policies):
                time = start_time + curr_policy * interval
                curr_policy += 1

                tmp_policy = {
                    "time": time,
                    "type": "outbound",
                    "participant": from_participant,
                    "match": {
                        "tcp_dst": 80
                    },
                    "action": {
                        "fwd": to_participant
                    }
                }

                policies.append(tmp_policy)

    with open(policy_file, 'w') as outfile:
        json.dump(policies, outfile)


''' main '''
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('from_participants', help='policy ingress format 1:100')
    parser.add_argument('to_participants', help='policy egress - format 1:100')
    parser.add_argument('num_policies', help='number policies')
    parser.add_argument('start_time', help='time of first policy installation')
    parser.add_argument('interval', help='interval')
    parser.add_argument('out_path', help='path to output file')
    args = parser.parse_args()

    main(args)