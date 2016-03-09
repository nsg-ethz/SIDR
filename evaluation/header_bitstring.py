#!/usr/bin/env python
#  Author:
#  Rudiger Birkner (ETH Zurich)

#        {'ipv4_src': '10.0.0.0/16', 'eth_type': 0x0800},
#        {'ipv4_dst': '10.0.0.0/16', 'eth_type': 0x0800},
#        {'tcp_src': 5555, 'eth_type': 0x0800, 'ip_proto': 6},
#        {'tcp_dst': 80, 'eth_type': 0x0800, 'ip_proto': 6},
#        {'udp_src': 7777, 'eth_type': 0x0800, 'ip_proto': 17},
#        {'udp_dst': 53, 'eth_type': 0x0800, 'ip_proto': 17},


class HeaderBitString(object):
    def __init__(self, match=None, header=None):
        """
        bitstring format
            ip_proto       src_port       dst_port
        +--------------+--------------+---------------+
        |0     ...    7|8     ...   23|24    ...    39|
        +--------------+--------------+---------------+
        each bit in the header is represented by two bits to account for don't care and impossible bit
        0 -> 01, 1 -> 10, wildcard -> 11, impossible bit -> 00
        """
        self.header_length = 80
        self.header = 2**self.header_length-1

        if match:
            self.header = self.create_from_match(match)

        if header:
            self.header = header

    @staticmethod
    def combine(hbs1, hbs2):
        """
        This method merges the two header bit strings.
        :param hbs1: header bit string
        :param hbs2: header bit string
        :return:new combined HeaderBitString
        """

        combined_header = hbs1.header & hbs2.header
        if HeaderBitString.contains_impossible_bit(combined_header):
            return None
        else:
            return HeaderBitString(header=combined_header)

    @staticmethod
    def contains_impossible_bit(header):
        """
        This method checks if the bit string contains at least one impossible bit
        :return: return True if it contains at least one, False otherwise
        """

        bitstring = '{0:080b}'.format(header)
        bits = [bitstring[i:i+2] for i in range(0, 80, 2)]
        for bit in bits:
            if bit == '00':
                return True
        return False

    def create_from_match(self, match):
        """
        This method creates a bitstring from a high-level match dictionary.
        :param match: high-level match dictionary (e.g. {'tcp_dst': 179})
        :return: corresponding bit string
        """

        if ('tcp_src' in match or 'tcp_dst' in match) and ('udp_src' in match or 'udp_dst' in match):
            return None

        ip_proto = '{0:016b}'.format(2**16-1)
        proto_src = '{0:032b}'.format(2**32-1)
        proto_dst = '{0:032b}'.format(2**32-1)


        if 'tcp_src' in match or 'tcp_dst' in match:
            ip_proto = self.transform_bitstring('{0:08b}'.format(6))
            if 'tcp_src' in match:
                proto_src = self.transform_bitstring('{0:016b}'.format(match['tcp_src']))
            if 'tcp_dst' in match:
                proto_dst = self.transform_bitstring('{0:016b}'.format(match['tcp_dst']))
        if 'udp_src' in match or 'udp_dst' in match:
            ip_proto = self.transform_bitstring('{0:08b}'.format(17))
            if 'udp_src' in match:
                proto_src = self.transform_bitstring('{0:016b}'.format(match['udp_src']))
            if 'udp_dst' in match:
                proto_dst = self.transform_bitstring('{0:016b}'.format(match['udp_dst']))

        # combine all fields
        return int(''.join([ip_proto, proto_src, proto_dst]), 2)

    @staticmethod
    def transform_bitstring(bitstring):
        """
        Transforms an ordinary bitstring to a bitstring, where each 0 is replaced by 01, and each 1 by 10
        :param bitstring: bitstring of any length to be converted
        :return: converted string
        """

        result = ''

        for bit in bitstring:
            if bit == '0':
                result += '01'
            else:
                result += '10'

        return result

    @staticmethod
    def reduce_bitstring(bitstring):
        """
        Transforms a bitstring to an ordinary bitstring, where each 01 is replaced by 0, and each 10 by 1
        :param bitstring: bitstring of any length to be converted
        :return: converted string
        """
        result = ''

        bits = [bitstring[i:i+2] for i in range(0, 80, 2)]
        for bit in bits:
            if bit == '01':
                result += '0'
            elif bit == '10':
                result += '1'
        return result

    def get_match(self):
        """
        Converts the header from the bitstring back into a human readable format.
        :return: match dictionary
        """
        match = {}

        bitstring = '{0:080b}'.format(self.header)

        ip_proto = bitstring[0:16]
        if int(ip_proto, 2) != 2**16-1:
            ip_proto = int(self.reduce_bitstring(ip_proto), 2)
            proto_string = 'tcp' if ip_proto == 6 else 'udp'

            proto_src = bitstring[16:48]
            if int(proto_src, 2) != 2**32-1:
                match[proto_string + '_src'] = int(self.reduce_bitstring(proto_src), 2)
            proto_dst = bitstring[48:80]
            if int(proto_dst, 2) != 2**32-1:
                match[proto_string + '_dst'] = int(self.reduce_bitstring(proto_dst), 2)

        return match

    def get_match_set(self):
        """
        Create a set corresponding to the match header. Both the bit (0, 1, *, x) and the position is encoded
        into an int and then added to the set. When computing the cardinality intersection, it can easily be
        determined if there is a overlap of two matches
        :return:set that contains items according to the bits in the match header
        """

        match_set = set()

        bitstring = '{0:080b}'.format(self.header)
        bits = [bitstring[i:i+2] for i in range(0, 80, 2)]

        i = 0
        for bit in bits:
            i += 1
            if bit == '11':
                match_set.add(10*i+0)
                match_set.add(10*i+1)
            elif bit == '01':
                match_set.add(10*i+0)
            elif bit == '10':
                match_set.add(10*i+1)

        return match_set

    def get_match_int(self):
        return self.header


def test():
    test_cases = [
        {
            'name': 'Simple Exact Test',
            'match1': {'tcp_src': 80, 'tcp_dst': 179},
            'result': 403344208105042280290906,
        },
        {
            'name': 'Simple Exact Test',
            'match1': {'tcp_src': 80},
            'result': 403344208105045143584767,
        },
        {
            'name': 'Impossible Match Test',
            'match1': {'udp_src': 80, 'tcp_dst': 179},
            'result': None
        },
        {
            'name': 'Combination with Feasible Match Test 1',
            'match1': {'tcp_src': 80},
            'match2': {'tcp_dst': 179},
            'result': 403344208105042280290906
        },
        {
            'name': 'Combination with Unfeasible Match Test 3',
            'match1': {'tcp_src': 80},
            'match2': {'tcp_src': 179},
            'result': None
        },
        {
            'name': 'Combination with Unfeasible Match Test 4',
            'match1': {'tcp_src': 80},
            'match2': {'udp_src': 179},
            'result': None
        },
    ]

    for test_case in test_cases:
        print "Running " + str(test_case['name'])
        error = False

        if 'match2' not in test_case:
            tmp1 = HeaderBitString(test_case['match1'])
            if tmp1.header != test_case['result']:
                error = True

            if tmp1.header and not tmp1.get_match() == test_case['match1']:
                print "--> Failed to correctly convert bitstring to human readable match structure"
                print "--> match is " + str(tmp1.get_match()) + " should be " + str(test_case['match1'])
                error = True

        else:
            tmp1 = HeaderBitString(test_case['match1'])
            tmp2 = HeaderBitString(test_case['match2'])

            combined = HeaderBitString.combine(tmp1, tmp2)

            if combined and combined.header != test_case['result']:
                print "--> Failed to combine. Result is " + str(combined.header) + " should be " + str(test_case['result'])
                error = True
            elif not combined and test_case['result']:
                print "--> Failed to combine. Result is " + str(combined) + " should be " + str(test_case['result'])
                error = True

        if error:
            print "-> Test failed\n"
        else:
            print "-> Test passed\n"


''' main '''
if __name__ == '__main__':
    test()
