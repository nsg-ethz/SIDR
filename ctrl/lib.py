#  Author:
#  Rudiger Birkner (Networked Systems Group ETH Zurich)


# VMAC BUILDER


def vmac_participant_match(superset_id, participant_index, sdx):
    
    # add superset identifier
    vmac_bitstring = '{num:0{width}b}'.format(num=int(superset_id), width=sdx.superset_id_size)
        
    # set bit of participant
    vmac_bitstring += '{num:0{width}b}'.format(num=1, width=(participant_index+1))
    vmac_bitstring += '{num:0{width}b}'.format(num=0, width=(sdx.VMAC_size-len(vmac_bitstring)))

    # convert bitstring to hexstring and then to a mac address
    vmac_addr = '{num:0{width}x}'.format(num=int(vmac_bitstring, 2), width=sdx.VMAC_size/4)
    vmac_addr = ':'.join([vmac_addr[i]+vmac_addr[i+1] for i in range(0, sdx.VMAC_size/4, 2)])
        
    return vmac_addr


def vmac_best_path_match(participant_name, sdx):
        
    # add participant identifier
    vmac_bitstring = '{num:0{width}b}'.format(num=participant_name, width=sdx.VMAC_size)

    # convert bitstring to hexstring and then to a mac address
    vmac_addr = '{num:0{width}x}'.format(num=int(vmac_bitstring, 2), width=sdx.VMAC_size/4)
    vmac_addr = ':'.join([vmac_addr[i]+vmac_addr[i+1] for i in range(0, sdx.VMAC_size/4, 2)])
            
    return vmac_addr

def create_cookie(participant_id, type, id):
    return int('{0:012b}'.format(participant_id)+'{0:04b}'.format(type)+'{0:016b}'.format(id),2)


def create_cookie_mask(participant_id, type, id):
    mask = ""
    mask += '{0:012b}'.format(2**12-1) if participant_id else '{0:012b}'.format(0)
    mask += '{0:04b}'.format(2**4-1) if type else '{0:04b}'.format(0)
    mask += '{0:016b}'.format(2**16-1) if id else '{0:012b}'.format(0)

    return int(mask,2)