#!/usr/bin/env python
#  Author:
#  Rudiger Birkner (Networked Systems Group ETH Zurich)

LOG = False


def get_all_participants_advertising(prefix, participants):
    participant_set = set()
   
    for participant_name in participants:
        route = participants[participant_name].get_route('input', prefix)
        if route:
            participant_set.add(participant_name)
            
    return participant_set


def get_all_as_paths(prefix, participants):
    as_sets = {}
   
    for participant_name in participants:
        route = participants[participant_name].get_routes('input', prefix)
        if route:
            as_sets[participant_name] = route['as_path']
            
    return as_sets


def get_all_participant_sets(config):
    participant_sets = []
     
    for prefix in config.vmac_encoder.prefix_2_vnh:
        participant_sets.append(get_all_participants_advertising(prefix, config.participants))
            
    return participant_sets    


def bgp_update_peers(updates, config, route_server):
    changes = []

    for update in updates:
        if 'announce' in update or 're-announce' in update:
            as_sets = {}
            if 'announce' in update:
                prefix = update['announce']['prefix']
            else:
                prefix = update['re-announce']['prefix']
                    
            # send custom route advertisements based on peerings
            for participant_name in config.participants:
                route = bgp_make_route_advertisement(route_server, participant_name, prefix)
        
                # only announce route if at least one of the peers advertises it to that participant
                if route:     
                    # check if we have already announced that route
                    prev_route = route_server.rib[participant_name].get_route("output", prefix)
                    
                    if not bgp_routes_are_equal(route, prev_route):
                        # store announcement in output rib
                        route_server.rib[participant_name].delete_route("output", prefix)
                        route_server.rib[participant_name].add_route("output", prefix, route)

                        # we only care for changes in existing routes, as only in this case a gratuituous ARP has to
                        # be sent
                        if prev_route:
                            changes.append({"participant": participant_name,
                                            "prefix": prefix})
                        
                        # announce the route to each router of the participant
                        for neighbor in config.participant_2_portip[participant_name]:
                            announcement = announce_route(neighbor, prefix, route["next_hop"], route["as_path"])
                            if LOG:
                                print announcement
                            route_server.server.sender_queue.put(announcement)
        
        elif 'withdraw' in update:
            as_sets = {}
            prefix = update['withdraw']['prefix']
            
            # send custom route advertisements based on peerings
            for participant_name in config.participants:
                # only modify route advertisement if this route has been advertised to the participant
                prev_route = route_server.rib[participant_name].get_route("output", prefix)
                if prev_route: 
                    route = bgp_make_route_advertisement(route_server, participant_name, prefix)
                    # withdraw if no one advertises that route, else update reachability
                    if route:
                        # check if we have already announced that route
                        if not bgp_routes_are_equal(route, prev_route):
                            # store announcement in output rib
                            route_server.rib[participant_name].delete_route("output",prefix)
                            route_server.rib[participant_name].add_route("output",prefix,route)
                            
                            changes.append({"participant": participant_name,
                                            "prefix": prefix})
                            
                            # announce the route to each router of the participant
                            for neighbor in config.participant_2_portip[participant_name]:
                                announcement = announce_route(neighbor, prefix, route["next_hop"], route["as_path"])
                                if LOG:
                                    print announcement
                                route_server.server.sender_queue.put(announcement)
                    else:
                        route_server.rib[participant_name].delete_route("output", prefix)
                        for neighbor in config.participant_2_portip[participant_name]:
                            next_hop = config.vmac_encoder.prefix_2_vnh[prefix]
                            announcement = withdraw_route(neighbor, prefix, next_hop)
                            if LOG:
                                print announcement
                            route_server.server.sender_queue.put(announcement)
    return changes


def bgp_routes_are_equal(route1, route2):
    if route1 is None:
        return False
    if route2 is None:
        return False
    if route1['next_hop'] != route2['next_hop']:
        return False
    if route1['as_path'] != route2['as_path']:
        return False
    return True


def bgp_make_route_advertisement(route_server, participant_name, prefix):
    as_path_attribute = get_best_path(route_server, participant_name, prefix)

    next_hop = route_server.config.vmac_encoder.prefix_2_vnh[prefix]

    if as_path_attribute:
        route = {"next_hop": str(next_hop),
                 "origin": "",
                 "as_path": as_path_attribute,
                 "communities": "",
                 "med": "",
                 "atomic_aggregate": ""}
        return route
    return None


def get_best_path(route_server, participant_name, prefix):
    route = route_server.rib[participant_name].get_route('local', prefix)
    return route['as_path'] if route else ""


def get_as_set(config, participant_name, peers, prefix):
    as_path = []
    as_set = set()
    as_path_attribute = ""
    num_routes = 0

    for peer in peers:
        route = config.participants[peer].get_route('input', prefix)
        if route:
            as_set.update(set(route['as_path'].replace('(','').replace(')','').split()))
            num_routes += 1
            peer_as_path = route['as_path']

    if num_routes == 1:
        if LOG:
            print str(peer_as_path)
        path_set = peer_as_path.split('(')
        as_path = path_set[0].split()
        as_set = set(path_set[1].replace(')','').split()) if len(path_set) > 1 else set()

    if as_path:
        as_path_attribute += ' '.join(map(str,as_path))
    if as_set:
        as_path_attribute += ' ( ' + ' '.join(map(str,sorted(list(as_set), key=int))) + ' )'

    return as_path_attribute


def get_policy_as_set(config, participant_name, prefix):
    peers = []
    peers.extend(config.participants[participant_name].fwd_peers)

    route = config.participants[participant_name].get_route('local', prefix)
    if route:
        best_path_participant = config.portip_2_participant[route['next_hop']]
        if best_path_participant not in peers:
            peers.append(best_path_participant)

    as_path_attribute = get_as_set(config, participant_name, peers, prefix)
    return as_path_attribute


def get_blocking_policy_as_set(config, participant_name, prefix):
    peers = []
    peers.extend(config.participants[participant_name].fwd_peers)

    if LOG:
        print "PEERS: "+str(peers)

    route = config.participants[participant_name].get_route('local', prefix)
    if route:
        best_path_participant = config.portip_2_participant[route['next_hop']]
        if best_path_participant not in peers:
            peers.append(best_path_participant)

    if LOG:
        print "PEERS BEFORE: "+str(peers)

    for peer in config.participants[participant_name].fwd_peers:
        route = config.participants[peer].get_route('input', prefix)
        if route:
            ases = route["as_path"].replace('(','').replace(')','').split()
            if LOG:
                print "ASES: "+str(ases)
                print str(config.participant_2_asn[participant_name])
            if str(config.participant_2_asn[participant_name]) in ases:
                if LOG:
                    print "REMOVE: "+str(peer)
                peers.remove(peer)
                if route["prefix"] not in config.participants[participant_name].no_fwd_peers:
                    config.participants[participant_name].no_fwd_peers[route["prefix"]] = []
                config.participants[participant_name].no_fwd_peers[route["prefix"]].append(peer)
            else:
                if route["prefix"] in config.participants[participant_name].no_fwd_peers:
                    if peer in config.participants[participant_name].no_fwd_peers[route["prefix"]]:
                        config.participants[participant_name].no_fwd_peers[route["prefix"]].remove(peer)

    if LOG:
        print "PEERS AFTER: "+str(peers)

    as_path_attribute = get_as_set(config, participant_name, peers, prefix)
    return as_path_attribute


def announce_route(neighbor, prefix, next_hop, as_path):
           
    msg = "neighbor " + neighbor + " announce route " + prefix + " next-hop " + str(next_hop)
    msg += " as-path [ " + as_path + " ]"

    return msg


def withdraw_route(neighbor, prefix, next_hop):

    msg = "neighbor " + neighbor + " withdraw route " + prefix + " next-hop " + str(next_hop)

    return msg
