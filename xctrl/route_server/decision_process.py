#!/usr/bin/env python
#  Author:
#  Muhammad Shahbaz (muhammad.shahbaz@gatech.edu)
#  Sean Donovan

import socket
import struct


def decision_process(rib, affected_participants, participants_structure, route):
    best_routes = []

    # Need to loop through all participants
    if 'announce' in route:
        announce_route = route['announce']
        
        for participant in affected_participants:
            routes = []
            # Need to loop through participants to build up routes, don't include current participant

            advertising_participants = participants_structure[participant].peers_out

            routes = rib.get_routes('input', None, advertising_participants, announce_route['prefix'], None, True)

            if routes:
                best_route = best_path_selection(routes)
                best_routes.append({'announce': best_route})
            
                # TODO: can be optimized? check to see if current route == best_route?
                rib.delete_route('local', participant, announce_route['prefix'])
                rib.add_route('local', participant, best_route['prefix'], best_route)

    elif'withdraw' in route:
        deleted_route = route['withdraw']
        
        if deleted_route is not None:
            for participant in affected_participants:
                
                # delete route if being used
                if rib.get_routes('local', ['prefix'], participant, deleted_route['prefix'], None, True):
                    rib.delete_route('local', participant, deleted_route['prefix'])

                    advertising_participants = participants_structure[participant].peers_out

                    routes = rib.get_routes('input', None, advertising_participants, deleted_route['prefix'], None, True)
                    
                    if routes:
                        best_route = best_path_selection(routes)
                        best_routes.append({'withdraw': best_route})
                    
                        rib.add_route('local', participant, best_route['prefix'], best_route)
    
    return best_routes


def best_path_selection(routes):

    # Priority of rules to make decision:
    # ---- 0. [Vendor Specific - Cisco has a "Weight"]
    # ---- 1. Highest Local Preference
    # 2. Lowest AS Path Length
    # ---- 3. Lowest Origin type - Internal preferred over external
    # 4. Lowest  MED
    # ---- 5. eBGP learned over iBGP learned - so if the above's equal, and you're at a border router,
    #         send it out to the next AS rather than transiting
    # ---- 6. Lowest IGP cost to border routes
    # 7. Lowest Router ID (tie breaker!)
    #
    # I believe that steps 0, 1, 3, 5, and 6 are out

    # 1. Lowest AS Path Length
    
    best_routes = []
    min_route_length = 9999

    for route in routes:
            
        # find ones with smallest AS Path Length
        if not best_routes:
            # prime the pump
            min_route_length = aspath_length(route['as_path'])
            best_routes.append(route)
        elif min_route_length == aspath_length(route['as_path']):
            best_routes.append(route)
        elif min_route_length > aspath_length(route['as_path']):
            best_routes = []
            min_route_length = aspath_length(route['as_path'])
            best_routes.append(route)

    # If there's only 1, it's the best route    
    
    if len(best_routes) == 1:
        return best_routes.pop()

    # 2. Lowest MED

    # Compare the MED only among routes that have been advertised by the same AS. 
    # Put it differently, you should skip this step if two routes are advertised by two different ASes. 
    
    # get the list of origin ASes
    as_list = []
    post_med_best_routes = []
    for route in best_routes:
        as_list.append(get_advertised_as(route['as_path']))

    # sort the advertiser's list and 
    # look at ones who's count != 1
    as_list.sort()

    i = 0
    while i < len(as_list):
        
        if as_list.count(as_list[i]) > 1:
            
            # get all that match the particular AS
            from_as_list = [x for x in best_routes if get_advertised_as(x['as_path']) == as_list[i]]

            # MED comparison here
            j = 0
            lowest_med = from_as_list[j]['med']
            
            j += 1
            while j < len(from_as_list):
                if lowest_med > from_as_list[j]['med']:
                    lowest_med = from_as_list[j]['med']
                j += 1
            
            # add to post-MED list - this could be more than one if MEDs match
            temp_routes = [x for x in from_as_list if x['med'] == lowest_med]
            for el in temp_routes:
                post_med_best_routes.append(el)
            
            i += as_list.count(as_list[i])
        
        else:
            temp_routes = [x for x in best_routes if get_advertised_as(x['as_path']) == as_list[i]]
            for el in temp_routes:
                post_med_best_routes.append(el)
            i += 1
    
    # If there's only 1, it's the best route
    if len(post_med_best_routes) == 1:
        return post_med_best_routes.pop()

    # 3. Lowest Router ID

    # Lowest Router ID - Origin IP of the routers left.
    i = 0
    lowest_ip_as_long = ip_to_long(post_med_best_routes[i]['next_hop'])
    
    i += 1
    while i < len(post_med_best_routes):
        if lowest_ip_as_long > ip_to_long(post_med_best_routes[i]['next_hop']):
            lowest_ip_as_long = ip_to_long(post_med_best_routes[i]['next_hop'])
        i += 1
    
    return post_med_best_routes[get_index(post_med_best_routes, 'next_hop', long_to_ip(lowest_ip_as_long))]


def aspath_length(as_path_set):
    temp = as_path_set.split('(')
    as_path = temp[0].split()
    as_set = temp[1].replace(')', '').split() if len(temp) > 1 else []

    length = len(as_path)+1 if len(as_set) > 0 else len(as_path)
    return length


def get_advertised_as(as_path_set):
    temp = as_path_set.split('(')
    as_path = temp[0].split()
    as_set = temp[1].replace(')', '').split() if len(temp) > 1 else []

    return as_path[0]


def ip_to_long(ip):
    return struct.unpack('!L', socket.inet_aton(ip))[0]


def long_to_ip(ip):
    return socket.inet_ntoa(struct.pack('!L', ip))


def get_index(seq, attr, value):
    return next(index for (index, d) in enumerate(seq) if d[attr] == value)
