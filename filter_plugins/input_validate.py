"""Validates the input variables in the base, fabric and services files are of the correct
format to be able to run the playbook, build a fabric and apply the services.
A pass or fail is returned to the Ansible Assert module, if it fails the full output is also
returned for the failure message. The following methods check:

-base configuration variables using base.yml:
bse.device_name: Ensures that the device names used match the correct format as that is heavily used in inventory script logic
bse.addr: Ensures that the network addresses entered are valid networks (or IP for loopback) with the correct subnet mask
bse.users: Ensures that username and password is present
bse.services: Validates IP addresses defined for any of the services are of a valid IPv4 format
bse.mgmt_acl: Validates ACLs have source prefixes defined and are of a valid IPv4 and subnet mask format
bse.adv.image: Validates image and image_name are defined
bse.adv.exec_timeout: Validates the timeouts are integers

-core fabric configuration variables using fabric.yml
fbc.network_size: Ensures the number of each type of device is within the limits and constraints
fbc.num_intf: Ensures is one number, then a comma and then up to 3
fbc.route.authentication: Ensure that the BGP and OSPF contains no whitespace
fbc.route.ospf: Ensures that the OSPF process is present and area in dotted decimal format
fbc.route.bgp.as_num: Ensures that the AS is present, cant make more specific incase is 2-byte or 4-byte ASNs
fbc.acast_gw_mac: Ensures the anycast virtual MAC is a valid mac address
fbc.adv.nve_hold_time: Ensures that the NVE hold time is an integer
fbc.adv.route.ospf_hello: Ensures that the OSPF hello is an integer
fbc.adv.route.bgp_timers: Make sure is a list, and both keepalive and holdtime are integers
fbc.adv.bse_intf: Ensures that the interface numbers are integers
fbc.adv.lp: Ensures all the loopback names are unique, no duplicates
fbc.adv.mlag: Ensures all of MLAG parameters are integers and VLANs within limit
fbc.adv.addr_incre: Ensures all of the IP address increment values used are integers and are all unique

-tenants (VRFs, VNIs & VLANs) using service_tenant.yml
svc_tnt.tnt.tenant_name/l3_tenant: Ensures all tenants have a name (no restrictions) and marked as L3 or not
svc_tnt.tnt.vlans.num/name: Ensure that the VLAN number and name dictionaries are configured under the tenant
svc_tnt.tnt.tenant_name: Ensures that all tenant names are unique, cant have duplicates
svc_tnt.tnt.l3_tenant: Ensures answer is boolean
svc_tnt.tnt.bgp_redist_tag: Ensures it is an integer
svc_tnt.tnt.vlans: Ensures vlans are defined, must be at least one
svc_tnt.tnt.vlans.num: Ensures all VLANs are numbers and not conflicting
svc_tnt.tnt.vlans.name: Ensures all VLANs have a name, are no restrictions of what it is
svc_tnt.tnt.vlans.create_on_border: Ensures answer is boolean
svc_tnt.tnt.vlans.create_on_leaf: Ensures answer is boolean
svc_tnt.tnt.vlans.ipv4_bgp_redist: Ensures answer is boolean
svc_tnt.tnt.vlans.ip_addr: Ensures that the IP address and subnet mask are of the correct format
svc_tnt.tnt.vlans.num/name: Ensures all VLAN numbers and names are unique, no duplicates accross all tenants
svc_tnt.adv.bse_vni: Ensures all values are integers
svc_tnt.adv.bse_vni.tnt_vlan: Makes sure none of the VLANs are the same VLAN number as the the L3VNI tenant VLAN numbers
svc_tnt.adv.redist.rm_name: Ensures that it contains 'src' and 'dst' within its name

-Interfaces (single_homed, dual_homed & port-channels) using interface_tenant.yml
svc_intf.intf.homed: Ensures that single-homed or dual-homed dictionaries are not empty
svc_intf.intf.homed.descr/type/ip_vlan/switch: Ensures that description, intf_type, ip/vlan and switch mandatory dicts are not empty
svc_intf.intf.homed.intf_num: Ensures that intf_num is integer (also added to a new list to check interface assignment)
svc_intf.intf.homed.type: Ensures that interface is one of the pre-defined types
svc_intf.intf.dual_homed.po_num: Ensures that po_num is integer (also added to a new list to check interface assignment)
svc_intf.intf.dual_homed.po_mode: Ensures that po_mode is on, active or passive
svc_intf.intf.dual_homed.po_mbr_descr: Ensures it is a list of 2 elements
svc_intf.intf.homed.switch: Ensures that it is a list, even if only the one switch
svc_intf.intf.homed.switch: Ensures that it is a valid hostname within the inventory and if dual-homed the hostname is odd numbered
svc_intf.intf.dual_homed.type: Ensures that it is not a Layer3, SVI or loopback, can only have single-homed L3 or loopback ports
svc_intf.intf.single_homed.ip_vlan: Ensures that the Layer3 or SVI IP address is in a valid IPv4 and subnet mask format
svc_intf.intf.single_homed.ip_vlan: Ensures that the Loopback IP address is in a valid IPv4 format and /32
svc_intf.intf.homed.ip_vlan: Ensures all VLANs are integers (numbers)
svc_intf.intf.homed.ip_vlan: Ensures that trunk VLANs have no whitespaces, are integers (number) and no duplicates
svc_intf.intf.single_homed.tenant: Ensures that the VRF exists on the switch that an interface in that VRF is being configured
svc_intf.intf.homed.ip_vlan: Ensures that the VLAN exists on the switch that an SVI or interface using that VLAN is being configured
svc_intf.intf.single_homed.intf_num): Ensures that the SVI does not have duplicate entries on the same switch
svc_intf.adv.homed.first/last: Ensures that the reserved interface, loopback and Port-Channel ranges are integers
svc_intf.intf.loopback: Ensures are enough free loopbacks in the range (range minus conflicting static assignments) for number of loopbacks defined
svc_intf.intf.single_homed: Ensures are enough free ports in the range (range minus conflicting static assignments) for number of interfaces defined
svc_intf.intf.dual_homed: Ensures are enough free ports in the range (range minus conflicting static assignments) for number of interfaces defined
svc_intf.intf.port-channel: Ensures are enough free port-channels in the range (range minus conflicting static assignments) for number of port-channels defined
svc_intf.intf.homed: Make sure that are not more defined interfaces (single and dual_homed) than there are actual interfaces on the switch

-Non-backbone routing (BGP, OSPF and static) using service_route.yml
svc_rte.bgp.group.name: Ensure that the BGP group name is configured
svc_rte.bgp.group.peer.name/desc/peer_ip: Ensure that the dictionary is configured on the peer
svc_rte.bgp.group/peer.switch/remote_as: Ensure that the dict is configured on group, or if not in all peers in that group
svc_rte.bgp.group/peer.switch: Makes sure it is a list and is a valid hostname within the inventory, if not exits script
svc_rte.bgp.group/peer.tenant: Makes sure it is a list, if not exit script as breaks other validation tests
svc_rte.bgp.group/peer.name: Ensure that the group or peer name contains no whitespaces
svc_rte.bgp.group/peer.remote_as: Ensures that the AS is present, cant make more specific incase is 4-byte ASNs
svc_rte.bgp.group/peer.password: Ensure that the group or peer password contains no whitespaces
svc_rte.bgp.group/peer.ebgp_multihop: Must be an integer from 2 to 255
svc_rte.bgp.group/peer.bfd/default/next_hop_self: Only acceptable value is True
svc_rte.bgp.group/peer.timers: Make sure is a list, and both keepalive and holdtime are integers
svc_rte.bgp.group/peer.peer_ip: Ensures that the peer IP address is in a valid IPv4 format
svc_rte.bgp.group/peer.inbound/outbound.deny/allow: Ensures if is either a list of valid prefixes (if le/ge must be 0 to 32) or string (can be 'any' or 'default' (allow only))
svc_rte.bgp.group/peer.inbound.weight/pref: Ensures are only inbound, that the attribute is an integer and is a valid list of prefixes or string (any or default)
svc_rte.bgp.group/peer.outbound.med/as_prepend: Ensures are only outbound, that the attribute is an integer and is a valid list of prefixes or string (any or default)
svc_rte.bgp.peer.tenant: Makes sure the VRF that the BGP peer is in exists on the switch
svc_rte.bgp.group/peer.update_source: Must be a loopback that exists on the switches it is being applied
svc_rte.bgp.group/peer.name: Ensures no duplicate group or peer names

svc_rte.bgp.tnt_advertise.network/summary.prefix: Ensures that exists (mandatory) and that is valid IPv4 prefixes, not duplicated and if le/ge only 0-32
svc_rte.bgp.tnt_advertise.summary.filter: If defined ensures its value is 'summary_only'
svc_rte.bgp.tnt_advertise.redist.type: Ensures the type is bgp xx, ospf xx, static or connected, if not failfast
svc_rte.bgp/ospf.redist.type): Makes sure that the OSPF process being redistributed exists on switch redistribution is being done on.
svc_rte.ospf.redist.type): Makes sure that the BGP ASN being redistributed matches local fabric ASN
svc_rte.bgp.tnt_advertise.redist.type.allow: Ensures either string ('any' or 'default') or list of valid IPv4 prefixes, not duplicated and if le/ge only 0-32
svc_rte.bgp.tnt_advertise.redist.connected.allow: Ensures redist connected interface exist on switch (loopback, vlan, physical) and in correct VRF
svc_rte.bgp.tnt_advertise.redist.type.metric: Ensures that the metric value is a decimal and prefix is either keywords any/default or if list are valid IPv4 prefixes and not duplicated and if le/ge only 0-32
svc_rte.bgp.tnt_advertise.network/summary/redist.switch: Ensure that is a list of switches, name is valid (exists in inventory and tenant is on the switch
svc_rte.bgp.tnt_advertise.name/network/summary/redist.switch: Ensures a switch dictionary is present in the main tenant or any of the advertisement types (network/summary/redist)

svc_rte.ospf.interface: Ensures that the interfaces is not an empty dictionary
svc_rte.ospf.process: Ensure that the OSPF process is configured
svc_rte.ospf.process: Ensure that the OSPF process has a list of switches configured
svc_rte.ospf.interface.name/area: Ensure that the area and name dictionaries are configured under the interface
svc_rte.ospf.rid: Ensures that the RID is a list of valid IPv4 address and equal to the number of switches (in process)
svc_rte.ospf.bfd: Enable BFD for all neighbors. Is disabled by default, only acceptable value is True
svc_rte.ospf.default_orig: Ensures that it is either boolean 'True' or 'always'
svc_rte.ospf.interface.area: Ensures that the area is in dotted decimal format
svc_rte.ospf.interface.cost: Ensures the cost is decimal between 1 and 65535
svc_rte.ospf.interface.authentication: Ensures the password contains no whitespaces
svc_rte.ospf.interface.area_type: Ensures area type is a string starting with stub or nssa
svc_rte.ospf.interface.passive: By default is False, ensures if specified only acceptable value is boolean 'True'
svc_rte.ospf.interface.hello): Ensures that the OSPF hello is an integer
svc_rte.ospf.interface.type: By default all interfaces are broadcast, if defined ensures is 'point-to-point', this is only viable option
svc_rte.ospf.interface.switch: Ensure that it is a list of switches
svc_rte.ospf.interface.switch: Ensure the switch name is valid (exists in inventory)
svc_rte.ospf.process.tenant: Ensure that the tenant exists on the border and leaf switches
svc_rte.ospf.process/interface.tenant: Ensures that the OSPF interface is within the tenant

svc_rte.static_route.tenant: Ensure that the tenant is configured
svc_rte.static_route.prefix/gateway: Ensure that the prefix and either gateway or dictionaries are configured under the route
svc_rte.static_route.tenant/route.switch: Ensure that the switch is configured in tenant or if not in all routes in that tenant
svc_rte.static_route.route.switch: Ensure that it is a list of switches
svc_rte.static_route.route.switch: Ensure the switch name is valid (exists in inventory)
svc_rte.static_route.tenant: Ensure that the tenant exists on the border and leaf switches
svc_rte.static_route.route.interface: Ensures that the next-hop interface (if set) is within the tenant or Null0
svc_rte.static_route.route.next_hop_vrf: Assert that the next hop VRF is a valid VRF on the switch
svc_rte.static_route.route.gateway: Ensures that the next hop address is a valid IP address
svc_rte.static_route.route.prefix: Ensures that prefixes are valid and not duplicates
svc_rte.static_route.route.ad: Ensures that the Administrative Distance is an integer from 2 to 255

fbc.adv.ospf_hello: Ensures that the OSPF hello is an integer
svc_rte.adv.bgp_timers: Make sure is a list, and both keepalive and holdtime are integers
svc_rte.adv.bgp_naming:  MUST contain 'name' as is replaced when creating the RM/PL name
svc_rte.adv.bgp_naming:  MUST contain 'name' and 'val' as is replaced when creating the PL name
svc_rte.adv.dflt_pl:  MUST contain 'name' and 'val' as is replaced when creating the PL name
svc_rte.adv.redist: Ensures that it contain both 'src' and 'dst' as are swapped to the source and destination of the redistribution
svc_rte.adv.bgp.redist: Ensures that it contains 'src', 'dst' and 'val' as swapped to the source, destination and metric value
"""

import re
import ipaddress
from collections import defaultdict
from pprint import pprint

class FilterModule(object):
    def filters(self):
        return {
            'input_bse_validate': self.base,
            'input_fbc_validate': self.fabric,
            'input_svc_tnt_validate': self.svc_tnt,
            'input_svc_intf_validate': self.svc_intf,
            'input_svc_rte_validate': self.svc_rte
        }


######################## Generic assert functions used by all classes to make it DRY ########################
    # REGEX search matches the specified pattern anywhere within the string
    def assert_regex_search(self, errors, regex, input_string, error_message):
        try:
            assert re.search(regex, input_string), error_message
        except AssertionError as e:
            errors.append(str(e))
    # REGEX match matches the specified pattern at the beginning of the string
    def assert_regex_match(self, errors, regex, input_string, error_message):
        try:
            assert re.match(regex, input_string), error_message
        except AssertionError as e:
            errors.append(str(e))

    # == asserts that the variable does match the specified value
    def assert_equal(self, errors, variable, input_value, error_message):
        try:
            assert variable == input_value, error_message
        except AssertionError as e:
            errors.append(str(e))
    # <= asserts that the variable is equal to or less than the specified value
    def assert_equal_less(self, errors, variable, input_value, error_message):
        try:
            assert variable <= input_value, error_message
        except AssertionError as e:
            errors.append(str(e))
    # <= asserts that the variable is equal to or more than the specified value
    def assert_equal_more(self, errors, variable, input_value, error_message):
        try:
            assert variable >= input_value, error_message
        except AssertionError as e:
            errors.append(str(e))
    # =! asserts that the variable does not match the specified value
    def assert_not_equal(self, errors, variable, input_value, error_message):
        try:
            assert variable != input_value, error_message
        except AssertionError as e:
            errors.append(str(e))

    # IN asserts that the variable is within the specified value
    def assert_in(self, errors, variable, input_value, error_message):
        try:
            assert variable in input_value, error_message
        except AssertionError as e:
            errors.append(str(e))
    # NOT IN asserts that the variable is NOT within the specified value
    def assert_not_in(self, errors, variable, input_value, error_message):
        try:
            assert variable not in input_value, error_message
        except AssertionError as e:
            errors.append(str(e))

    # INTEGER: Asserts that the variable is an integer (number)
    def assert_integer(self, errors, variable, error_message):
        try:
            assert isinstance(variable, int), error_message
        except AssertionError as e:
            errors.append(str(e))
    # INTEGER: Asserts that the variable is a string
    def assert_string(self, errors, variable, error_message):
        try:
            assert isinstance(variable, str), error_message
        except AssertionError as e:
            errors.append(str(e))
    # LIST_LEN: Asserts that the variable is a list with x elements
    def assert_list(self, errors, variable, error_message):
        try:
            assert isinstance(variable, list), error_message
        except AssertionError as e:
            errors.append(str(e))
    # LIST_LEN: Asserts that the variable is a list with x elements
    def assert_list_len(self, errors, variable, list_len, error_message):
        try:
            assert isinstance(variable, list), error_message
            assert len(variable) == list_len, error_message
        except AssertionError as e:
            errors.append(str(e))
    # BOOLEAN: Asserts that the variable is True or False
    def assert_boolean(self, errors, variable, error_message):
        try:
            assert isinstance(variable, bool), error_message
        except AssertionError as e:
            errors.append(str(e))
    # IPv4: Asserts that it is a valid IP address or network address (correct mask and within it)
    def assert_ipv4(self, errors, variable, error_message):
        try:
            ipaddress.IPv4Interface(variable)
        except ipaddress.AddressValueError:
            errors.append(error_message)
        except ipaddress.NetmaskValueError:
            errors.append(error_message)

    # IPv4: Asserts that it is a valid IP address and that a mask exists (for interfaces and prefix-lists)
    def assert_ipv4_and_mask(self, errors, variable, error_message):
            try:
                ipaddress.IPv4Interface(variable)
                variable.split('/')[1]
            except ipaddress.AddressValueError:
                errors.append(error_message)
            except ipaddress.NetmaskValueError:
                errors.append(error_message)
            except IndexError:
                errors.append(error_message)

    # EXIST: Asserts that the dictionary exists
    def assert_exist(self, errors, my_list, dict_key, error_message):
        try:
            assert my_list.get(dict_key) != None, error_message
        except AssertionError as e:
            errors.append(str(e))
    # DUPLICATE: Asserts there are no duplicate elements in a list, if so returns the duplicates in the error message
    def duplicate_in_list(self, errors, input_list, error_message, args):       # Args is a list of 0 to 4 args to use in error message before dup error
        dup = [i for i in set(input_list) if input_list.count(i) > 1]
        self.assert_equal(errors, len(dup), 0, error_message.format(*args, dup))

    # INTF: Asserts whether there are enough free interfaces to accommodate all the defined interfaces
    def check_used_intfs(self, errors, intf_type, per_dev_used_intf, intf_range):
        for switch, intf in per_dev_used_intf.items():
            used_intf = len(intf)
            aval_intf = []
            for x in intf:                      # Gets only the statically defined interface numbers
                if x != 'dummy':
                    aval_intf.append(x)
            aval_intf.extend(intf_range)           # Adds range of intfs to static intfs
            total_intf = len(set(aval_intf))    # Removes duplicate intfs to find how many available interfaces from range
            self.assert_equal_less(errors, used_intf, total_intf, "-svc_intf.intf.{} Are more defined interfaces ({}) than free interfaces ({})" \
                                   " in the {} reserved range on {}".format(intf_type, used_intf, total_intf, intf_type, switch))

    # FABRIC_INTF: Asserts whether interfaces or loopbacks are duplicated/ overlap (same interface used for both fabric and service interfaces)
    def check_used_fbc_intfs(self, errors, intf_type, intf_fmt, per_dev_used_intf, intf_range, fbc_intf):
        for switch, intf in per_dev_used_intf.items():
            svc_intf = []
            # Gets the statically defined interface numbers and adds to the range of interfaces
            for x in intf:
                if x != 'dummy':
                    svc_intf.append(x)
            svc_intf.extend(intf_range)
            # Finds duplicate interfaces from those used/reserved in fabric and service_interface var files
            dup_intf = set(fbc_intf) & set(svc_intf)
            self.assert_equal(errors, len(dup_intf), 0, "-svc_intf.intf.{} {}{} is/are duplicated, they are used/reserved for both " \
                                                        "fabric and service interfaces on {}".format(intf_type, intf_fmt, list(dup_intf), switch))

    # PFX_LIST: Asserts that the prefix-list is in the entry correct format (le/ge 0-32), prefix is a valid IP address and not duplicated
    def asset_pfx_lst(self, errors, pfx_lst, args):           # args is a list of upt o 4 things used in error message
        for each_pfx in pfx_lst:
            # If white space in the prefix entry must have le or ge
            if ' ' in each_pfx:
                # Gets everything after prefix and asserts it has le/ge 0-32 once or twice
                ge_le = ' '.join(each_pfx.split(' ')[1:])
                self.assert_regex_match(errors, '^([g|l]e ([0-9]|[1-2]\d|3[0-2])\s?){1,2}$', ge_le, "-svc_rte.{}.{}.{} in '{}' is invalid ({}), it "
                                        "only takes le/ge 0-32 once or twice".format(*args, each_pfx))
                each_pfx = each_pfx.split(' ')[0]
            self.assert_ipv4_and_mask(errors, each_pfx, "-svc_rte.{}.{}.{} in '{}' has non-valid IPv4 Address/Netmask '{}'".format(*args, each_pfx))
        # self.duplicate_in_list(pfx_lst, errors, "-svc_rte.bgp.{}.{}.{} in '{}' has duplicated prefix {}, all prefixes should be unique", args)
        self.duplicate_in_list(errors, pfx_lst, "-svc_rte.{}.{}.{} in '{}' has duplicated prefix {}, all prefixes should be unique", args)


######################## Validate formatting of variables within the base.yml file ########################
    def base(self, device_name, base, services, mgmt_acl):
        addr = base['addr']
        users = base['users']
        adv = base['adv']
        base_errors = ['Check the contents of base.yml for the following issues:']

        # DEVICE_NAME (bse.device_name): Ensures that the device names used match the correct format as is used to create group names
        for dvc, name in device_name.items():
            self.assert_regex_search(base_errors, '-[a-zA-Z0-9_]+$', name, "-bse.device_name.{} '{}' is not in the correct format. Anything after " \
                           "the last '-' is used for the group name so must be letters, digits or underscore".format(dvc, name))

        # ADDR (bse.addr): Ensures that the network addresses entered are valid networks (or IP for loopback) with the correct subnet mask
        for name, address in addr.items():
            try:
                num_addr = ipaddress.IPv4Network(address).num_addresses
                # Loopback address must be /26 to cover 18 Loop1 (all), 21 Loop2 (leaf and border) and 2 Lp3 (border)
                if name == 'lp_net':
                    self.assert_equal_more(base_errors, num_addr, 64, "-bse.addr.{} '{}' is not a valid subnet mask, must be at least '/26'".format(name, address))
                # If keepalive has own network management, peer-link and keepalive networks must be at least /27 (32 addresses or more)
                elif addr.get('mlag_kalive_net') != None:
                     if name != 'mgmt_gw':
                        self.assert_equal_more(base_errors, num_addr, 32, "-bse.addr.{} '{}' is not a valid subnet mask, must be at least '/27'".format(name, address))
                # If no dedicated keepalive network peer-link must be a /26 to cover both peer-link and keepalive addresses (64 addresses or more)
                else:
                    if name == 'mlag_peer_net':
                        self.assert_equal_more(base_errors, num_addr, 64, "-bse.addr.{} '{}' is not a valid subnet mask, must be at least '/26'".format(name, address))
                    # Management networks must be at least /27 (32 addresses or more)
                    elif name == 'mgmt_net':
                        self.assert_equal_more(base_errors, num_addr, 32, "-bse.addr.{} '{}' is not a valid subnet mask, must be at least '/27'".format(name, address))
            except ipaddress.AddressValueError:
                base_errors.append("-bse.addr.{} '{}' 1 is not a valid IPv4 network address".format(name, address))
            except ipaddress.NetmaskValueError:
                base_errors.append("-bse.addr.{} '{}' 2 is not a valid IPv4 network address".format(name, address))
            except ValueError:
                base_errors.append("-bse.addr.{} '{}' 3 is not a valid IPv4 network address".format(name, address))

        # USERS (bse.users): Ensures that username and password is present
        for user in users:
            self.assert_not_equal(base_errors, user['username'], None, "-bse.users.username one of the usernames does not have a value")
            self.assert_not_equal(base_errors, user['password'], None, "-bse.users.password username '{}' does not have a password".format(user.setdefault('username')))

        # SERVICES (bse.services): Validates IP addresses defined for any of the services are of a valid format
        for each_obj in [('dns', 'prim'), ('dns', 'sec'), ('snmp', 'host')]:
            if services.get(each_obj[0], {}).get(each_obj[1]) != None:
                ip = services[each_obj[0]][each_obj[1]]
                self.assert_ipv4(base_errors, ip, "-bse.services.{}.{} '{}' is not a valid IPv4 Address".format(each_obj[0], each_obj[1], ip))
        for svc in ['ntp', 'log', 'tacacs']:
            if services.get(svc, {}).get('server') != None:
                for ip in services[svc]['server']:
                    self.assert_ipv4(base_errors, ip, "-bse.services.{}.server '{}' is not a valid IPv4 Address".format(svc, ip))

        # MGMT_ACL (bse.mgmt_acl): Validates ACLs have source prefixes defined and are of a valid format
        self.assert_not_equal(base_errors, 0, len(mgmt_acl), "-bse.mgmt_acl is empty or does not exist")
        for each_acl in mgmt_acl:
            try:
                for ip in each_acl['source']:
                    if ip == 'any':
                        pass
                    else:
                        self.assert_ipv4_and_mask(base_errors, ip, "-bse.mgmt_acl '{} in an ACL is not a valid IPv4 Address/Netmask".format(ip))
            except:
                base_errors.append("-bse.mgmt_acl One of the management ACLs does not have a valid list of source prefixes")

        # IMAGE (bse.adv.image): Validates image and image_name are defined
        self.assert_exist(base_errors, adv, 'image', "-bse.adv.image NXOS image is not defined, this is mandatory")
        self.assert_exist(base_errors, adv, 'image_version', "-bse.adv.image_version is not defined, Napalm config_replace will fail without this")

        # TIMEOUT *bse.adv.exec_timeout): Validates the timeouts are integers
        self.assert_integer(base_errors, adv.get('exec_timeout', {}).get('console') , "-bse.adv.exec_timeout.console does not exist or is not an integer")
        self.assert_integer(base_errors, adv.get('exec_timeout', {}).get('vty') , "-bse.adv.exec_timeout.vty does not exist or is not an integer")

        if len(base_errors) == 1:
            return "'base.yml unittest pass'"             # For some reason ansible assert needs the inside quotes
        else:
            return base_errors


######################## Validate formatting of variables within the fabric.yml file ########################
    def fabric(self, network_size, num_intf, route, acast_gw_mac, nve_hold_time, adv_route, bse_intf, lp, mlag, addr_incre):
        fabric_errors = ['Check the contents of fabric.yml for the following issues:']

        # NETWORK_SIZE (fbc.network_size): Ensures they are integers and the number of each type of device is within the limits and constraints
        for dev_type, net_size in network_size.items():
            self.assert_integer(fabric_errors, net_size, "-fbc.network_size.{} '{}' should be an integer (number)".format(dev_type, net_size))
        self.assert_regex_match(fabric_errors, '[1-4]', str(network_size['num_spine']),
                                "-fbc.network_size.num_spine is '{}', valid values are 1 to 4".format(network_size['num_spine']))
        self.assert_regex_match(fabric_errors, '^([2468]|10)$', str(network_size['num_leaf']),
                                "-fbc.network_size.num_leaf is '{}', valid values are 2, 4, 6, 8 and 10".format(network_size['num_leaf']))
        self.assert_regex_match(fabric_errors, '^[024]$', str(network_size['num_border']),
                                "-fbc.network_size.num_border is '{}', valid values are 0, 2 and 4".format(network_size['num_border']))

        # NUMBER_INTERFACES (fbc.num_intf): Ensures is one number, then a comma and then up to 3 numbers
        for dev_type, intf in num_intf.items():
            self.assert_regex_match(fabric_errors, r'^\d,\d{1,3}$', str(intf),
                                    "-fbc.num_intf.{} '{}' is not a valid, must be a digit, comma and 1 to 3 digits".format(dev_type, intf))

        # PWORD (fbc.route.authentication): Ensure that the BGP and OSPF contains no whitespaces
        self.assert_regex_search(fabric_errors, '^\S+$', route.get('authentication', 'dummy'), "-fbc.route.authentication contains whitespaces")
        # OSPF (fbc.route.ospf): Ensures that the OSPF process is present and area in dotted decimal format
        self.assert_not_equal(fabric_errors, route['ospf']['pro'], None, "-fbc.route.ospf.pro does not have a value, this needs to be a string or integer")
        self.assert_ipv4(fabric_errors, route['ospf']['area'],
                         "-fbc.route.ospf.area '{}' is not a valid dotted decimal area, valid values are 0.0.0.0 to 255.255.255.255".format(route['ospf']['area']))
        # BGP (fbc.route.bgp.as_num): Ensures that the AS is present, cant make more specific incase is 2-byte or 4-byte ASNs
        self.assert_not_equal(fabric_errors, route['bgp']['as_num'], None, "-fbc.route.bgp.as_num does not have a value")

        # ACAST_GW_MAC (fbc.acast_gw_mac): Ensures the anycast virtual MAC is a valid mac address
        self.assert_regex_match(fabric_errors, r'([0-9A-Fa-f]{4}\.){2}[0-9A-Fa-f]{4}', acast_gw_mac,
                                "-fbc.acast_gw_mac '{}' is not valid, can be [0-9], [a-f] or [A-F] in the format xxxx.xxxx.xxxx".format(acast_gw_mac))

        # NVE_TIMER (fbc.adv.nve_hold_time): Ensures that the NVE hold time is an integer
        self.assert_integer(fabric_errors, nve_hold_time, "-fbc.adv.nve_hold_time '{}' should be an integer (number)".format(nve_hold_time))
        # OSPF_HELLO (fbc.adv.route.ospf_hello): Ensures that the OSPF hello is an integer
        self.assert_integer(fabric_errors, adv_route['ospf_hello'], "-fbc.adv.route.ospf_hello '{}' should be an integer (number)".format(adv_route['ospf_hello']))
        # BGP_TIMERS (fbc.adv.route.bgp_timers): Make sure is a list, and both keepalive and holdtime are integers
        try:
            assert isinstance(adv_route['bgp_timers'], list), "-fbc.adv.route.bgp_timers '{}' default values must be a list of [keepalive, holdtime]".format(adv_route['bgp_timers'])
            assert isinstance(adv_route['bgp_timers'][0], int), "-fbc.adv.route.bgp_timers keepalive ({}) default value must be an integer".format(adv_route['bgp_timers'][0])
            assert isinstance(adv_route['bgp_timers'][1], int), "-fbc.adv.route.bgp_timers holdtime ({}) default value must be an integer".format(adv_route['bgp_timers'][1])
        except AssertionError as e:
            fabric_errors.append(str(e))

        # BSE_INTF (fbc.adv.bse_intf): Ensures that the interface numbers are integers
        for name, intf in bse_intf.items():
            if '_to_' in name:
                self.assert_integer(fabric_errors, intf, "-fbc.adv.bse_intf.{} '{}' should be an integer (number)".format(name, intf))
            elif 'mlag_peer' == name:
                self.assert_regex_match(fabric_errors, '^[0-9]{1,3}-[0-9]{1,3}$', str(intf),
                                        "-fbc.adv.bse_intf.{} '{}' should be numerical values in the format xxx-xxx".format(name, intf))

        # LP (fbc.adv.lp): Ensures all the loopback names are unique, no duplicates
        list_lp = []
        for lp_type in lp.values():
            list_lp.append(lp_type['num'])
        self.duplicate_in_list(fabric_errors, list_lp, "-fbc.adv.lp number {} is/are duplicated, all loopbacks should be unique", [])

        # MLAG (fbc.adv.mlag): Ensures all of MLAG paraemters are integers and VLANs within limit
        for mlag_attr, value in mlag.items():
            if mlag_attr == 'kalive_vrf':       # Is a string so no need to check
                pass
            else:
                self.assert_integer(fabric_errors, value, "-fbc.adv.mlag.{} '{}' should be an integer (number)".format(mlag_attr, value))
        self.assert_regex_match(fabric_errors, r'^(?:(?:[1-9]\d{0,2}|[1-3]\d{3}|40[0-8]\d|409[0-6]),)*?(?:(?:[1-9]\d{0,2}|[1-3]\d{3}|40[0-8]\d|409[0-6]))$',
                                  str(mlag['peer_vlan']), "-fbc.adv.mlag.peer_vlan '{}' is not a valid VLAN number, valid values are 0 to 4096".format(mlag['peer_vlan']))

        # ADDR_INCRE (fbc.adv.addr_incre): Ensures all of the IP address increment values used are integers and are all unique
        for incr_type, incr in addr_incre.items():
            self.assert_integer(fabric_errors, incr, "-fbc.adv.addr_incre.{} '{}' should be an integer (number)".format(incr_type, incr))
        list_incr, list_mlag_incr = ([] for i in range(2))
        for incr_type, incr in addr_incre.items():
            if incr_type == 'mlag_leaf_ip' or incr_type == 'mlag_border_ip':
                list_mlag_incr.append(incr)
            elif not incr_type.startswith('mlag'):
                list_incr.append(incr)
        self.duplicate_in_list(fabric_errors, list_incr, "-fbc.adv.addr_incre (non-mlag) {} is/are duplicated, all address increments should be unique", [])
        self.duplicate_in_list(fabric_errors, list_mlag_incr, "-fbc.adv.addr_incre (mlag) {} is/are duplicated, all address increments should be unique", [])

        # The value returned to Ansible Assert module to determine whether failed or not
        if len(fabric_errors) == 1:
            return "'fabric.yml unittest pass'"             # For some reason ansible assert needs the inside quotes
        else:
            return fabric_errors


######################## Validate formatting of variables within the service_tenant.yml file ########################
    def svc_tnt(self, svc_tnt, adv, fbc_mlag):
        # Used by duplicate VLAN check
        all_vl_num, all_vl_name, num_bdr_tnt, num_lf_tnt, all_bdr_vl, tnt_bdr_vl, all_lf_vl, tnt_lf_vl, all_tnt = ([] for i in range(9))
        svc_tnt_errors = ['Check the contents of service_tenant.yml for the following issues:']

        # MAND: Makes sure that mandatory dicts exist, if not exits the scripts
        mand_tnt_err = []
        for tnt in svc_tnt:
            try:
                # VLANS (svc_tnt.tnt.vlans): Ensures that the vlans is not an empty dictionary
                assert tnt['vlans'] != None, "-svc_tnt.tnt.vlans in tenant '{}' should not be an empty dictionary, if not used hash it out".format(tnt.get('tenant_name', 'Unknown'))
                all_tnt.append(tnt['tenant_name'])
                # TNT_NME/L3_TNT: (svc_tnt.tnt.tenant_name/l3_tenant): Ensures all tenants have a name (no restrictions) and marked as L3 or not
                self.assert_exist(mand_tnt_err, tnt, 'tenant_name', "-svc_tnt.tnt.tenant_name a tenant does not have a name, this is a mandatory dictionary")
                self.assert_exist(mand_tnt_err, tnt, 'l3_tenant', "-svc_tnt.tnt.l3_tenant is not defined in tenant '{}', this is a mandatory " \
                                                                  "dictionary".format(tnt.get('tenant_name', 'Unknown')))
                for vl in tnt['vlans']:
                    # VL_NUM/VL_NME (svc_tnt.tnt.vlans.num/name): Ensure that the VLAN number and name dictionaries are configured under the tenant
                    self.assert_exist(mand_tnt_err, vl, 'num', "-svc_tnt.vlans.num vlan '{}' in tenant '{}' has no number, this is a mandatory " \
                                                                "dictionary".format(vl.get('name', 'Unknown'), tnt.get('tenant_name', 'Unknown')))
                    self.assert_exist(mand_tnt_err, vl, 'name', "-svc_tnt.vlans.name vlan '{}' in tenant '{}' has no name, this is a mandatory " \
                                                                 "dictionary".format(vl.get('num', 'Unknown'), tnt.get('tenant_name', 'Unknown')))
            except AssertionError as e:
                mand_tnt_err.append(str(e))
        # FAILFAST: Exit script if don't exist as cant do further tests without these dict
        if len(mand_tnt_err) != 0:
            svc_tnt_errors.extend(mand_tnt_err)           # adds to main error list so all errors displayed before exiting
            return svc_tnt_errors

        # DUP_TNT (svc_tnt.tnt.tenant_name): Ensures that all tenant names are unique, cant have duplicates
        self.duplicate_in_list(svc_tnt_errors, all_tnt, "-svc_tnt.tnt.tenant_name {} is duplicated, all tenant names should be unique", [])

        for tnt in svc_tnt:
            # L3_TENANT (svc_tnt.tnt.l3_tenant): Ensures answer is boolean
            self.assert_boolean(svc_tnt_errors, tnt['l3_tenant'],
                                "-svc_tnt.tnt.l3_tenant '{}' is not a boolean ({}), must be True or False".format(tnt['tenant_name'], tnt['l3_tenant']))
            # BGP_REDIST_TAG (svc_tnt.tnt.bgp_redist_tag): Ensures it is an integer
            self.assert_integer(svc_tnt_errors, tnt.get('bgp_redist_tag', 0), "-svc_tnt.tnt.bgp_redist_tag '{}' of tenant '{}' should be an integer " \
                                                                              "(number)".format(tnt.get('bgp_redist_tag'), tnt['tenant_name']))

            # VLAN (svc_tnt.tnt.vlans): Ensures vlans are defined, must be at least one
            try:
                assert tnt['vlans'] != None, "-svc_tnt.tnt.vlans '{}' tenant has no VLANs, must be at least 1 VLAN to create the tenant".format(tnt['tenant_name'])
            except AssertionError as e:
                svc_tnt_errors.append(str(e))
                return svc_tnt_errors       # Has to exit if this errors as other tests wont run due to it being unable to loop through the vlans

            for vl in tnt['vlans']:
                all_vl_num.append(vl['num'])
                all_vl_name.append(vl['name'])
                # VLAN_NUMBER (svc_tnt.tnt.vlans.num): Ensures all VLANs are numbers
                self.assert_integer(svc_tnt_errors, vl['num'], "-svc_tnt.tnt.vlans.num '{}' should be an integer (number)".format(vl['num']))

                # Create dummy default values if these settings aren't set in the variable file
                vl.setdefault('create_on_border', False)
                vl.setdefault('create_on_leaf', True)
                vl.setdefault('ipv4_bgp_redist', True)
                vl.setdefault('ip_addr', '169.254.255.254/16')

                # CREATE_ON_BDR, CREATE_ON_LEAF, REDIST (svc_tnt.tnt.vlans): Ensures answer is boolean
                for opt in ['create_on_border', 'create_on_leaf', 'ipv4_bgp_redist']:
                    self.assert_boolean(svc_tnt_errors, vl[opt], "-svc_tnt.tnt.vlans.{} in VLAN {} is not a boolean ({}), must be True or False".format(opt, vl['num'], vl[opt]))

                # IP_ADDR (svc_tnt.tnt.vlans.ip_addr): Ensures that the IP address is of the correct format
                self.assert_ipv4_and_mask(svc_tnt_errors, vl['ip_addr'], "-svc_tnt.tnt.vlans.ip_addr '{}' is not a valid IPv4 Address/Netmask".format(vl['ip_addr']))

        # DUPLICATE VLAN NUM/NAME (svc_tnt.tnt.vlans.num/name): Ensures all VLAN numbers and names are unique, no duplicates accross all tenants
        self.duplicate_in_list(svc_tnt_errors, all_vl_num, "-svc_tnt.tnt.vlans.num {} are duplicated, all VLAN numbers should be unique", [])
        self.duplicate_in_list(svc_tnt_errors, all_vl_name, "-svc_tnt.tnt.vlans.name {} are duplicated, all VLAN names should be unique", [])

        # FBC VLAN (svc_tnt.tnt.vlans.num): Check that the fabric MLAG peer vlan (fbc.mlag.peer_vlan) is not in the list of VLANs
        self.assert_not_in(svc_tnt_errors, fbc_mlag['peer_vlan'], all_vl_num, "-svc_tnt.tnt.vlans.num VLAN{} is used for both the MLAG peer vlan (fbc.mlag.peer_vlan)" \
                                                                              " and the user VLANs, these must be unique".format(fbc_mlag['peer_vlan']))
        # BASE_VNI (svc_tnt.adv.bse_vni): Ensures all values are integers
        for opt in ['l3vni', 'l2vni']:
            self.assert_integer(svc_tnt_errors, adv['bse_vni'][opt], "-adv.bse_vni.{} '{}' should be an integer (number)".format(opt, adv['bse_vni'][opt]))
        try:
            assert isinstance(adv['bse_vni']['tnt_vlan'], int), "-adv.bse_vni.tnt_vlan '{}' should be an integer (number)".format(adv['bse_vni']['tnt_vlan'])
        except AssertionError as e:
            svc_tnt_errors.append(str(e))
            return svc_tnt_errors               # Breaks the script as if not an integer breaks the next L3VNI VLAN pre_val check

        # Finds out the number of tenants on border and leaf switches as well as the new user vlans to be created on them
        for tnt in svc_tnt:
            for vl in tnt['vlans']:
                if vl.get('create_on_border', False) == True:
                    all_bdr_vl.append(vl['num'])
                    num_bdr_tnt.append(tnt['tenant_name'])
                if vl.setdefault('create_on_leaf', True) == True:
                    all_lf_vl.append(vl['num'])
                    num_lf_tnt.append(tnt['tenant_name'])
        # Creates a list tenant of vlans (used by L3VNI) using starting tnt_vlan number and the number of tenants:
        for vl in range(adv['bse_vni']['tnt_vlan'], adv['bse_vni']['tnt_vlan'] + len(set(num_bdr_tnt))):
            tnt_bdr_vl.append(vl)
        for vl in range(adv['bse_vni']['tnt_vlan'], adv['bse_vni']['tnt_vlan'] + len(set(num_lf_tnt))):
            tnt_lf_vl.append(vl)

        # L3VNI VLAN (svc_tnt.adv.bse_vni.tnt_vlan): Makes sure none of the VLANs are the same VLAN number as the the L3VNI tenant VLAN numbers
        bdr_dup_intf = set(tnt_bdr_vl) & set(all_bdr_vl)
        self.assert_equal(svc_tnt_errors, len(bdr_dup_intf), 0, "-svc_tnt.adv.bse_vni.tnt_vlan VLAN{} is used for both the L3VNI tenant VLANs and user the VLANs " \
                                                        "on border switches, these must be unique".format(list(bdr_dup_intf)))
        lf_dup_intf = set(tnt_lf_vl) & set(all_lf_vl)
        self.assert_equal(svc_tnt_errors, len(lf_dup_intf), 0, "-svc_tnt.adv.bse_vni.tnt_vlan VLAN{} is used for both the L3VNI tenant VLANs and user the VLANs " \
                                                        "on leaf switches, these must be unique".format(list(lf_dup_intf)))

        # RM_NAME (svc_tnt.adv.redist.rm_name): Ensures that it contains 'src' and 'dst' within its name
        self.assert_regex_search(svc_tnt_errors, r'src\S*dst|dst\S*src', adv['redist']['rm_name'],
                                 "-adv.redist.rm_name format '{}' is not correct. It must contain 'src' and 'dst' within its name".format(adv['redist']['rm_name']))

        # The value returned to Ansible Assert module to determine whether failed or not
        if len(svc_tnt_errors) == 1:
            return "'service_tenant.yml unittest pass'"             # For some reason ansible assert needs the inside quotes
        else:
            return svc_tnt_errors


######################## Validate formatting of variables within the service_interface.yml file ########################
    def svc_intf(self, svc_intf, adv, network_size, tenants, dev_name, fbc):
        sh_per_dev_intf, dh_per_dev_intf, per_dev_po, per_dev_intf, lp_per_dev_intf = (defaultdict(list) for i in range(5))
        svcintf_vrf_on_lf, svcintf_vl_on_lf, svcintf_vrf_on_bdr, svcintf_vl_on_bdr, svctnt_vl_on_lf, svctnt_vl_on_bdr = ([] for i in range(6))
        svctnt_vrf_on_lf, svctnt_vrf_on_bdr = (['global'] for i in range(2))
        sh_intf, dh_intf, po_intf, all_devices, lp_intf, fbc_lp, lf_fbc_intf, bdr_fbc_intf = ([] for i in range(8))
        svc_intf_errors = ['Check the contents of service_interface.yml for the following issues:']

        # MAND: Makes sure that mandatory dicts exist, if not exits the scripts
        mand_intf_err = []
        for homed, interfaces in svc_intf.items():
            # HOMED (svc_intf.intf.homed): Ensures that single-homed or dual-homed dictionaries are not empty
            try:
                assert interfaces != None, "-svc_intf.intf.{0} should not be an empty dictionary, if not used hash it out".format(homed)
                for intf in interfaces:
                    # DSC/TYPE/IP_VLAN/SWITCH: (svc_intf.intf.homed.descr/type/ip_vlan/switch): Ensures that description, intf_type, ip/vlan and switch mandatory dicts are not empty
                    self.assert_exist(mand_intf_err, intf, 'descr', "-svc_intf.intf.homed.descr a tenant does not have a 'description', this is a mandatory dictionary")
                    self.assert_exist(mand_intf_err, intf, 'type', "-svc_intf.intf.homed.type interface '{}' does not have a 'type', this is a " \
                                                                    "mandatory dictionary".format(intf.get('descr', 'Unknown')))
                    self.assert_exist(mand_intf_err, intf, 'ip_vlan', "-svc_intf.intf.homed.ip_vlan '{}' does not have an 'ip/vlan', this is a " \
                                                                      "mandatory dictionary".format(intf.get('descr', 'Unknown')))
                    self.assert_exist(mand_intf_err, intf, 'switch', "-svc_intf.intf.homed.switch '{}' does not have a 'switch', this is a mandatory "\
                                                                     "dictionary".format(intf.get('descr', 'Unknown')))
            except AssertionError as e:
                mand_intf_err.append(str(e))
        # # FAILFAST: Exit script if don't exist as cant do further tests without these dict
        if len(mand_intf_err) != 0:
            svc_intf_errors.extend(mand_intf_err)           # adds to main error list so all errors displayed before exiting
            return svc_intf_errors

        # Creates a list of all possible devices based on fabric size
        for dev_type in ['spine', 'leaf', 'border']:
            for dev_id in range(1, network_size['num_' + dev_type ] + 1):
                all_devices.append(dev_name[dev_type] + str("%02d" % dev_id))

        # Creates lists what VRFs and VLANs are on leafs and borders switches (got from service.tenant.yml)
        for tnt in tenants:
            for vl in tnt['vlans']:
                if vl.get('create_on_leaf') != False:
                    svctnt_vrf_on_lf.extend([tnt['tenant_name']])
                    svctnt_vl_on_lf.extend([vl['num']])
                if vl.get('create_on_border') == True:
                    svctnt_vrf_on_bdr.extend([tnt['tenant_name']])
                    svctnt_vl_on_bdr.extend([vl['num']])
        # FUNCTION: Create lists of what VRFs and VLANs are to be created on leafs and borders switches (got from service_interface.yml
        def svcinft_vrf(switch, info):
            if info != None:        # No need if the VRF is global
                for sw in switch:
                    if dev_name['leaf'] in sw:
                        svcintf_vrf_on_lf.append(info)
                    elif dev_name['border'] in sw:
                        svcintf_vrf_on_bdr.append(info)

        def svcinft_vlan(switch, info):
            for sw in switch:
                if dev_name['leaf'] in sw:
                    svcintf_vl_on_lf.append(info)
                elif dev_name['border'] in sw:
                    svcintf_vl_on_bdr.append(info)

        svi_vlan = defaultdict(list)
        for homed, interfaces in svc_intf.items():
            for intf in interfaces:

                # TYPE (svc_intf.intf.homed.type): Ensures that interface is one of the pre-defined types
                self.assert_in(svc_intf_errors, intf['type'], ['access', 'stp_trunk', 'stp_trunk_non_ba', 'non_stp_trunk', 'layer3', 'loopback', 'svi'], "-svc_intf.intf.homed.type "\
                                                                                                                "'{}' is not a predefined interface type".format(intf['type']))
                # INTF_NUM (svc_intf.intf.homed.intf_num): Ensures that intf_num is integer (also added to a new list to check interface assignment)
                if intf.get('intf_num') != None:
                    self.assert_integer(svc_intf_errors, intf['intf_num'], "-svc_intf.intf.{}.intf_num '{}' should be an integer (number)".format(homed, intf['intf_num']))
                # PO_NUM (svc_intf.intf.dual_homed.po_num): Ensures that po_num is integer (also added to a new list to check interface assignment)
                if intf.get('po_num') != None:
                    self.assert_integer(svc_intf_errors, intf['po_num'], "-svc_intf.intf.dual_homed.po_num '{}' should be an integer (number)".format(intf['po_num']))

                # PO_MODE (svc_intf.intf.dual_homed.po_mode): Ensures that po_mode is on, active or passive
                if intf.get('po_mode') != None:
                    if intf.get('po_mode') == True:     # Needed as 'on' in yaml is converted to True
                        intf['po_mode'] = 'on'
                    self.assert_regex_match(svc_intf_errors, '^(active|passive|on)$', intf['po_mode'],
                                            "-svc_intf.intf.dual_homed.po_mode '{}' not a valid Port-Channel mode, options are active, passive or on".format(intf['po_mode']))

                # PO_MBR_DESCR (svc_intf.intf.dual_homed.po_mbr_descr): Ensures it is a list of 2 elements
                if intf.get('po_mbr_descr') != None:
                    self.assert_list_len(svc_intf_errors, intf['po_mbr_descr'], 2, "-svc_intf.intf.dual_homed.po_mbr_descr '{}' must be a list of "\
                                                                                   "2 elements".format(intf['po_mbr_descr']))

                # SWITCH (svc_intf.intf.homed.switch): Ensures that it is a list, even if only the one switch
                try:
                    assert isinstance(intf['switch'], list), "-svc_intf.intf.{}.switch '{}' must be a list of switches, even if is only 1".format(homed, intf['switch'])
                except AssertionError as e:
                    svc_intf_errors.append(str(e))
                    return svc_intf_errors               # Has to exit script here as if is not a list breaks rest of tests as it cant loop it

                #  SWITCH_NAME (svc_intf.intf.homed.switch): Ensures that it is a valid hostname within the inventory and if dual-homed the hostname is odd numbered
                for sw in intf['switch']:
                    self.assert_in(svc_intf_errors, sw, all_devices, "-svc_intf.intf.{}.switch '{}' is not a valid hostname within the inventory".format(homed, sw))
                    if homed == 'dual_homed':
                        self.assert_not_equal(svc_intf_errors, int(sw[-2:]) % 2, 0, "-svc_intf.intf.dual_homed.switch '{}' should be an odd numbered MLAG switch".format(sw))
                # HOMED_TYPE (svc_intf.intf.dual_homed.type): Ensures that it is not a Layer3, loopback or SVI can only have single-homed loopback or L3 ports
                if homed == 'dual_homed':
                    self.assert_not_equal(svc_intf_errors, intf['type'], 'layer3',
                                            "-svc_intf.intf.dual_homed.type '{}' is a Layer3 dual-homed port, it must be single-homed".format(intf['descr']))
                    self.assert_not_equal(svc_intf_errors, intf['type'], 'loopback',
                                            "-svc_intf.intf.dual_homed.type '{}' is a Loopback dual-homed port, it must be single-homed".format(intf['descr']))
                    self.assert_not_equal(svc_intf_errors, intf['type'], 'svi',
                                            "-svc_intf.intf.dual_homed.type '{}' is a SVI dual-homed port, it must be single-homed".format(intf['descr']))

                # IP (svc_intf.intf.single_homed.ip_vlan): Ensures that the IP address is in a valid IPv4 format
                if intf['type'] == 'layer3':
                    self.assert_ipv4_and_mask(svc_intf_errors, intf['ip_vlan'], "-svc_intf.intf.single_homed.ip_vlan {} is not a valid IPv4 Address/Netmask".format(intf['ip_vlan']))
                    svcinft_vrf(intf['switch'], intf.get('tenant', 'global'))
               # LP (svc_intf.intf.single_homed.ip_vlan): Ensures that the Loopback IP address is in a valid IPv4 format and /32
                elif intf['type'] == 'loopback':
                    self.assert_ipv4_and_mask(svc_intf_errors, intf['ip_vlan'], "-svc_intf.intf.single_homed.ip_vlan {} is not a valid IPv4 Address/Netmask".format(intf['ip_vlan']))
                    self.assert_equal(svc_intf_errors, intf['ip_vlan'].split('/')[1], '32', "-svc_intf.intf.single_homed.ip_vlan {} is not a valid "\
                                                                                            "Loopback, should be /32".format(intf['ip_vlan']))
                    svcinft_vrf(intf['switch'], intf.get('tenant', 'global'))
                # SVI_VLAN (svc_intf.intf.homed.ip_vlan): Ensures that the IP address is in a valid IPv4 form and all VLANs are integers (numbers)
                elif intf['type'] == 'svi':
                    self.assert_ipv4_and_mask(svc_intf_errors, intf['ip_vlan'], "-svc_intf.intf.single_homed.ip_vlan {} is not a valid IPv4 Address/Netmask".format(intf['ip_vlan']))
                    self.assert_integer(svc_intf_errors, intf['intf_num'], "-svc_intf.intf.{}.ip_vlan SVI '{}' should be one VLAN (integer)".format(homed, intf['intf_num']))
                    svcinft_vrf(intf['switch'], intf.get('tenant', 'global'))
                    svcinft_vlan(intf['switch'], intf['intf_num'])
                    svi_vlan[intf['intf_num']].extend(intf['switch'])

                # ACCESS_VLAN (svc_intf.intf.homed.ip_vlan): Ensures all VLANs are integers (numbers)
                elif intf['type'] == 'access':
                    self.assert_integer(svc_intf_errors, intf['ip_vlan'], "-svc_intf.intf.{}.ip_vlan access port '{}' should be one VLAN (integer)".format(homed, intf['ip_vlan']))
                    svcinft_vlan(intf['switch'], intf.get('ip_vlan'))

                # TRUNK_VLAN (svc_intf.intf.homed.ip_vlan): Ensures that there are no whitespaces
                else:
                    self.assert_equal(svc_intf_errors, re.search(r'\s', str(intf['ip_vlan'])), None, "-svc_intf.intf.{}.ip_vlan '{}' should not have "\
                                                                                                "any whitespaces in it".format(homed, intf['ip_vlan']))

                    if ',' in str(intf['ip_vlan']):
                        list_intf_vlans = []
                        for vlan in str(intf['ip_vlan']).split(','):
                            # Ensures that each single VLAN (not ranges) is an integer before getting list of all vlans to check for duplicates
                            if '-' not in vlan:
                                try:
                                    int(vlan)
                                    svcinft_vlan(intf['switch'], int(vlan))
                                    list_intf_vlans.append(int(vlan))
                                except:
                                    svc_intf_errors.append("-svc_intf.intf.{}.ip_vlan VLAN '{}' should be an integer (number)".format(homed, vlan))
                            # Check first and last VLAN in range are integers before getting list of all vlans to check for duplicates
                            if '-' in vlan:
                                try:
                                    int(vlan.split('-')[0])
                                    int(vlan.split('-')[1])
                                    for vl in range(int(vlan.split('-')[0]), int(vlan.split('-')[1]) +1):
                                        svcinft_vlan(intf['switch'], int(vl))
                                        list_intf_vlans.append(vl)
                                except:
                                    svc_intf_errors.append("-svc_intf.intf.{}.ip_vlan VLAN '{}' should be an integer (number)".format(homed, vlan))
                        # DUPLICATE VLANS: Ensures that are no duplicate VLANs in the allowed trunk vlan list
                        self.assert_equal(svc_intf_errors, len(set(list_intf_vlans)), len(list_intf_vlans), "-svc_intf.intf.{}.ip_vlan trunk contains "\
                                                                                                    "duplicate VLANs {}".format(homed, list_intf_vlans))
                    # If it is just a range ('-') ensures both start and end VLAN number are integers
                    elif '-' in str(intf['ip_vlan']):
                        try:
                            int(intf['ip_vlan'].split('-')[0])
                            int(intf['ip_vlan'].split('-')[1])
                        except:
                            svc_intf_errors.append("-svc_intf.intf.{}.ip_vlan VLAN '{}' should be an integer (number)".format(homed, intf['ip_vlan']))
                    # Ensures single VLANs are integers
                    else:
                        self.assert_integer(svc_intf_errors, intf['ip_vlan'], "-svc_intf.intf.{}.ip_vlan VLAN1 '{}' should be an integer (number)".format(homed, intf['ip_vlan']))
                        svcinft_vlan(intf['switch'], intf.get('ip_vlan'))

                # Gets number of Interfaces per device and any static interface/PO given
                for sw in intf['switch']:
                    if homed == 'single_homed' and intf['type'] == 'loopback':
                        lp_per_dev_intf[sw].append(intf.get('intf_num', 'dummy'))
                    elif homed == 'single_homed':
                        sh_per_dev_intf[sw].append(intf.get('intf_num', 'dummy'))
                    elif homed == 'dual_homed':
                        switch_pair = sw[:-2]+ "{:02d}".format(int(sw[-2:]) +1)
                        dh_per_dev_intf[sw].append(intf.get('intf_num', 'dummy'))
                        dh_per_dev_intf[switch_pair].append(intf.get('intf_num', 'dummy'))
                        per_dev_po[sw].append(intf.get('po_num', 'dummy'))
                        per_dev_po[switch_pair].append(intf.get('po_num', 'dummy'))

        # VRF/VLAN: Ensures that the VRF or VLAN of the interfaces being configured on are on the switches they are being configured on
        miss_vrf_on_lf = set(svcintf_vrf_on_lf) - set(svctnt_vrf_on_lf)
        miss_vrf_on_bdr = set(svcintf_vrf_on_bdr) - set(svctnt_vrf_on_bdr)
        miss_vl_on_lf = set(svcintf_vl_on_lf) - set(svctnt_vl_on_lf)
        miss_vl_on_bdr = set(svcintf_vl_on_bdr) - set(svctnt_vl_on_bdr)

        # VRF_ON_SWITCH (svc_intf.intf.single_homed.tenant): Ensures that the VRF exists on the switch that an interface in that VRF is being configured
        self.assert_equal(svc_intf_errors, len(miss_vrf_on_lf), 0,
                        "-svc_intf.intf.single_homed.tenant VRF {} is not on leaf switches but is in leaf interface configurations".format(list(miss_vrf_on_lf)))
        self.assert_equal(svc_intf_errors, len(miss_vrf_on_bdr), 0,
                        "-svc_intf.intf.single_homed.tenant VRF {} is not on border switches but is in border interface configurations".format(list(miss_vrf_on_bdr)))
        # VRF_ON_SWITCH (svc_intf.intf.homed.ip_vlan): Ensures that the VLAN exists on the switch that an interface using that VLAN is being configured
        self.assert_equal(svc_intf_errors, len(miss_vl_on_lf), 0,
                        "-svc_intf.intf.homed.ip_vlan VLAN {} is not on leaf switches but is in leaf interface configurations".format(list(miss_vl_on_lf)))
        self.assert_equal(svc_intf_errors, len(miss_vl_on_bdr), 0,
                        "-svc_intf.intf.homed.ip_vlan VLAN {} is not on border switches but is in border interface configurations".format(list(miss_vl_on_bdr)))

        # SVI_DUP: (svc_intf.intf.single_homed.intf_num): Ensures that the SVI does not have duplicate entries on the same switch
        for each_vl, list_sw in svi_vlan.items():
            self.assert_equal(svc_intf_errors, len(list_sw), len(set(list_sw)), "-svc_intf.intf.single_homed.intf_num VLAN {} has duplicate entries on {}".format(each_vl, set(list_sw)))

        for homed, intf in adv.items():
            # INTF_RANGE (svc_intf.adv.homed.first/last): Ensures that the reserved interface, loopback and Port-Channel ranges are integers
            for intf_pos, num in intf.items():
                try:
                    assert isinstance(num, int), "-svc_intf.adv.{}.{} '{}' should be an integer (number)".format(homed, intf_pos, num)
                except AssertionError as e:
                    svc_intf_errors.append(str(e))
                    return svc_intf_errors          # Has to exit if this errors as other tests wont run due to it being unable to loop through the interfaces

            # Create list of all interfaces in the reserved ranges
            if homed == 'single_homed':
                for intf_num in range(intf['first_lp'], intf['last_lp'] + 1):
                     lp_intf.append(intf_num)
                for intf_num in range(intf['first_intf'], intf['last_intf'] + 1):
                     sh_intf.append(intf_num)
            if homed == 'dual_homed':
                for intf_num in range(intf['first_intf'], intf['last_intf'] + 1):
                     dh_intf.append(intf_num)
                for po_num in range(intf['first_po'], intf['last_po'] + 1):
                     po_intf.append(po_num)

        # LP_INTF_RANGE (svc_intf.intf.loopback): Ensures are enough free loopbacks in the range (minus conflicting static) for number of loopbacks defined
        self.check_used_intfs(svc_intf_errors, 'loopback', lp_per_dev_intf, lp_intf)
        # SH_INTF_RANGE (svc_intf.intf.single_homed): Ensures are enough free ports in the range (minus conflicting static) for number of interfaces defined
        self.check_used_intfs(svc_intf_errors, 'single_homed', sh_per_dev_intf, sh_intf)
        # DH_INTF_RANGE (svc_intf.intf.dual_homed): Ensures are enough free ports in the range (minus conflicting static) for number of interfaces defined
        self.check_used_intfs(svc_intf_errors, 'dual_homed', dh_per_dev_intf, dh_intf)
        # PO_INTF_RANGE (svc_intf.intf.dual_homed): Ensures are enough free port-channels in the range (minus conflicting static) for number of POs defined
        self.check_used_intfs(svc_intf_errors, 'port_channel', per_dev_po, po_intf)

        # Combines the SH and DH per device interface dictionaries
        for d in (sh_per_dev_intf, dh_per_dev_intf):
            for key, value in d.items():
                per_dev_intf[key].extend(value)

        # TOTAL_INTF (svc_intf.intf.homed): Make sure that are not more defined interfaces (single and dual_homed) than there are actual interfaces on the switch
        for switch, intf in per_dev_intf.items():
            if dev_name['leaf'] in switch:
                max_intf = int(fbc['num_intf']['leaf'].split(',')[1])
            elif dev_name['border'] in switch:
                max_intf = int(fbc['num_intf']['border'].split(',')[1])
            self.assert_equal_less(svc_intf_errors, len(intf), max_intf, "-svc_intf.intf.homed Are more defined interfaces ({}) than the maximum "\
                                                                         "number of interfaces ({}) on {}".format(len(intf), max_intf, switch))

        # Get list of all the Port-channels, loopbacks, lf/bdr -to-> spine and MLAG links in the fabric
        fbc_po = fbc['adv']['mlag']['peer_po']
        for lp_type in fbc['adv']['lp'].values():
            fbc_lp.append(lp_type['num'])
        for intf_num in range(fbc['adv']['bse_intf']['lf_to_sp'], fbc['network_size']['num_leaf'] +1):
            lf_fbc_intf.append(intf_num)
        for intf_num in range(fbc['adv']['bse_intf']['bdr_to_sp'], fbc['network_size']['num_border'] +1):
            bdr_fbc_intf.append(intf_num)
        mlag_intf = [int(fbc['adv']['bse_intf']['mlag_peer'].split('-')[0]), int(fbc['adv']['bse_intf']['mlag_peer'].split('-')[1])]
        lf_fbc_intf.extend(mlag_intf)
        bdr_fbc_intf.extend(mlag_intf)

        # FBC_INTF (svc_intf.intf.homed): Make sure no duplicate interfaces/loopbacks in those reserved for fabric and those reserved & specified in svc_intf
        self.check_used_fbc_intfs(svc_intf_errors, 'loopback', fbc['adv']['bse_intf']['lp_fmt'], lp_per_dev_intf, lp_intf, fbc_lp)
        self.check_used_fbc_intfs(svc_intf_errors, 'port-channel', fbc['adv']['bse_intf']['mlag_short'], per_dev_po, po_intf, [fbc_po])
        for swi, intf in per_dev_intf.items():
            if dev_name['leaf'] in swi:
                self.check_used_fbc_intfs(svc_intf_errors, 'homed', fbc['adv']['bse_intf']['intf_short'], {swi: intf}, sh_intf + dh_intf, lf_fbc_intf)
            elif dev_name['border'] in swi:
                self.check_used_fbc_intfs(svc_intf_errors, 'homed', fbc['adv']['bse_intf']['intf_short'], {swi: intf}, sh_intf + dh_intf, bdr_fbc_intf)

        if len(svc_intf_errors) == 1:
            return "'service_interface.yml unittest pass'"             # For some reason ansible assert needs the inside quotes
        else:
            return svc_intf_errors


######################## Validate formatting of variables within the service_route.yml file ########################
    def svc_rte(self, bgp_grp, bgp_tnt_adv, ospf, route, adv, fbc, svc_intf, dev_name, tenants):
        fbc_tnt_lp, lf_intf, bdr_intf, all_devices  = ([] for i in range(4))
        svctnt_vrf_on_bdr, svctnt_vrf_on_lf = (['global'] for i in range(2))
        l3vl_on_bdr, l3vl_on_lf, per_dev_intf = (defaultdict(list) for i in range(3))
        temp_per_dev_tnt_intf, per_dev_tnt_intf = (defaultdict(lambda: defaultdict(list)) for i in range(2))
        svc_rte_errors = ['Check the contents of service_router.yml for the following issues:']

################ Generic functions or data gathering  ################
        # FBC_LP: Creates a list of all the loopback interfaces from fabric
        for lp_type in fbc['adv']['lp'].values():
            fbc_tnt_lp.append((fbc['adv']['bse_intf']['lp_fmt'] + str(lp_type['num']), 'global'))

        # SW_INTF_TNT: Creates a dict switches with a list (of tuples) of interface on that switch and tenant the interface is in {sw: [(intf, tnt), (intf, tnt)]}
        def sw_intf_tnt(intf_type, intf_short):
            per_dev_intf_tnt = defaultdict(list)
            # LP: Get interfaces which are on the devices.
            for intf in svc_intf['intf']['single_homed']:
                if intf['type'] == intf_type:
                    for sw in intf['switch']:
                        # 1. Create a dict of devices with a list of tuples {sw: [(intf, tnt), (intf, tnt)]}
                        per_dev_intf_tnt[sw].append((intf.get('intf_num', 'dummy'), intf.get('tenant', 'global')))
            # 2. Loop through all interfaces on each switch
            for sw, intf_tnt in per_dev_intf_tnt.items():
                intf_range, all_intf_tnt = ([] for i in range(2))
                # 3. Expands the range of reserved interfaces into a list
                for intf_num in range(svc_intf['adv']['single_homed']['first_' + intf_short], svc_intf['adv']['single_homed']['last_' + intf_short] + 1):
                    intf_range.append(intf_num)
                # 4. Get non-conflicting static interfaces that can be assigned
                intf_range_tmp = set(intf_range) - set([intf[0] for intf in intf_tnt])
                intf_range = list(intf_range_tmp)
                intf_range.sort()
                # 5. Loop through each interface_tenant tuple
                for each_intf_tnt in intf_tnt:
                    # 6. Add static assigned interfaces to the list of tuples (interfaces, tenant)
                    if each_intf_tnt[0] != 'dummy':
                        all_intf_tnt.append((fbc['adv']['bse_intf'][intf_short + '_fmt'] + str(each_intf_tnt[0]), each_intf_tnt[1]))
                    # 7. Assigns an interface number form the reserved range for non-static assigned interfaces
                    else:
                        asgn_intf = intf_range.pop(0)
                        all_intf_tnt.append((fbc['adv']['bse_intf'][intf_short + '_fmt'] + str(asgn_intf), each_intf_tnt[1]))
                # 8. Creates dict of per switch (intf, tnt) tuples. If Loopback adds fabric loopbacks to the list of tuples
                if intf_type == 'loopback':
                    all_intf_tnt.extend(fbc_tnt_lp)
                per_dev_intf_tnt[sw] = all_intf_tnt
            return per_dev_intf_tnt
        lp_per_dev_intf = sw_intf_tnt('loopback', 'lp')
        sw_per_dev_intf = sw_intf_tnt('layer3', 'intf')

        # DVC: Creates a list of all possible devices based on the fabric size
        for dev_type in ['spine', 'leaf', 'border']:
            for dev_id in range(1, fbc['network_size']['num_' + dev_type ] + 1):
                all_devices.append(dev_name[dev_type] + str("%02d" % dev_id))

        # TNT/VLAN: Creates lists of what VRFs and a list of VLANs that are on leafs and borders switches (got from service.tenant.yml)
        for tnt in tenants:
            for vl in tnt['vlans']:
                if vl.get('create_on_border') == True:
                    svctnt_vrf_on_bdr.extend([tnt['tenant_name']])
                    l3vl_on_bdr[tnt['tenant_name']].append('Vlan' + str(vl['num']))
                if vl.get('create_on_leaf') != False:
                    svctnt_vrf_on_lf.extend([tnt['tenant_name']])
                    l3vl_on_lf[tnt['tenant_name']].append('Vlan' + str(vl['num']))

        # INTF: Creates a list of all interfaces on the leafs and borders to be used for redist connected statement
        for intf_num in range(int(fbc['num_intf']['border'].split(',')[0]), int(fbc['num_intf']['border'].split(',')[1]) + 1):
            bdr_intf.append(fbc['adv']['bse_intf']['intf_fmt'] + str(intf_num))
        for intf_num in range(int(fbc['num_intf']['leaf'].split(',')[0]), int(fbc['num_intf']['leaf'].split(',')[1]) + 1):
            lf_intf.append(fbc['adv']['bse_intf']['intf_fmt'] + str(intf_num))

        # ALL_SW_INTF_TNT: Creates nested dict of all interfaces in each tenant on each switch {sw: tnt: [intf, intf]}
        # 1. Joins the loopback and layer3 interface dict (of tuples) into the one dictionary
        for d in (sw_per_dev_intf, lp_per_dev_intf):
            for key, value in d.items():
                per_dev_intf[key].extend(value)
        # 2. Splits the tuple and adds another layer of nested dict, so switch >> tenant >> list_of_interfaces
        for dvc, intf_tnt in per_dev_intf.items():
            for intf in intf_tnt:
                temp_per_dev_tnt_intf[dvc][intf[1]].append(intf[0])
        # 3. Join all L3VLANs from border or leaf to a switch of that type
        for sw, tnt in temp_per_dev_tnt_intf.items():
            if dev_name['border'] in sw:
                for d in (tnt, l3vl_on_bdr):
                    for key, value in d.items():
                        per_dev_tnt_intf[sw][key].extend(value)
            if dev_name['leaf'] in sw:
                for d in (tnt, l3vl_on_lf):
                    for key, value in d.items():
                        per_dev_tnt_intf[sw][key].extend(value)


################ BGP variables ################
        # MAND_ONLY: Makes sure that mandatory dicts are only in group or only in peer, if not exits the scripts
        mand_bgp_err = []
        for grp in bgp_grp:
            try:
                assert grp['peer'] != None, "-svc_rte.bgp.group.peer in group '{}' should not be an empty dictionary, if not used hash it out".format(grp.get('name', 'Unknown'))
                # GRP_NAME (svc_rte.bgp.group.name): Ensure that the BGP group name is configured
                self.assert_exist(mand_bgp_err, grp, 'name', "-svc_rte.bgp.group.name a group does not have a name, this is a mandatory dictionary key")
                for pr in grp['peer']:
                    # PR_NAME/DESCR/IP (svc_rte.bgp.group.peer.name/desc/peer_ip): Ensure that the dictionary is configured on the peer
                    self.assert_exist(mand_bgp_err, pr, 'name', "-svc_rte.bgp.peer.name peer '{}' has no name, this is a mandatory dictionary".format(pr.get('peer_ip','Unknown')))
                    self.assert_exist(mand_bgp_err, pr, 'descr', "-svc_rte.bgp.peer.desc peer '{}' has no description, this is a mandatory dictionary".format(pr.get('peer_ip','Unknown')))
                    self.assert_exist(mand_bgp_err, pr, 'peer_ip', "-svc_rte.bgp.peer.peer_ip peer '{}' has no IP, this is a mandatory dictionary".format(pr.get('name','Unknown')))
            except AssertionError as e:
                    mand_bgp_err.append(str(e))
        # FAILFAST: Exit script if don't exist as cant do further tests without these dict
        if len(mand_bgp_err) != 0:
            svc_rte_errors.extend(mand_bgp_err)           # adds to main error list so all errors displayed before exiting
            return svc_rte_errors

        # MAND_OR: Make sure mandatory dicts are in group or peer. The names definitely exist (per last test) so can use in the error messages
        for grp in bgp_grp:
            # SWI/TNT/AS (svc_rte.bgp.group/peer.switch/tenant/remote_as): Ensure that the dict is configured on group, or if not in all peers in that group
            for opt in ['switch', 'remote_as']:
                pr_errors = []
                try:
                    assert grp.get(opt) != None
                except:                             # If the group['xxxx'] dict doesn't exist checks to make sure that peer['xxxx'] dict exists for all peers
                    for pr in grp['peer']:          # Assert returns a list of peer names missing xxxx dict
                        self.assert_exist(pr_errors, pr, opt, pr['name'])
                if len(pr_errors) != 0:             # If any of the peers are missing the xxxx dict (list not empty) adds an error with group and peer names
                    mand_bgp_err.append("-svc_rte.bgp.group/peer.{} group '{}' and peers {} do not have '{}' set. It is a mandatory dictionary, " \
                                          "one of them must have it".format(opt, grp['name'], pr_errors, opt))
        # FAILFAST: Exit script if dont exist as cant do further tests without these dict
        if len(mand_bgp_err) != 0:
            svc_rte_errors.extend(mand_bgp_err)           # adds to main error list so all errors displayed before exiting
            return svc_rte_errors

        # FUNCTION_GRP_PR: Function used by both group and peers to validate any of the options that could be in either
        def assert_bgp_grp_pr(obj, obj_type, tnt_sw_err):        # obj_type is string 'group' or 'peer' used in error messages
            # SWI (svc_rte.bgp.group/peer.switch): Makes sure it is a list and is a valid hostname within the inventory
            try:
                # All get statements have a default value of what is expected so that the assert doesn't fail if dict is not present in group or peer
                assert isinstance(obj.get('switch', all_devices), list), "-svc_rte.bgp.{}.switch '{}' in group '{}' must be a list of switches, " \
                                  "even if is only 1".format(obj_type, obj.get('switch'), obj['name'])
                for sw in obj.get('switch', all_devices):
                    self.assert_in(tnt_sw_err, sw, all_devices, "-svc_rte.bgp.{}.switch '{}' in group '{}' is not a valid hostname within the inventory".format(obj_type, sw, obj['name']))
                # TNT (svc_rte.bgp.group/peer.tenant): Makes sure it is a list, if not exit script as breaks other validation tests
                assert isinstance(obj.get('tenant', all_devices), list), "-svc_rte.bgp.{}.tenant '{}' in group '{}' must be a list of tenants, "\
                                  "even if is only 1".format(obj_type, obj.get('tenant'), obj['name'])
            except AssertionError as e:
                tnt_sw_err.append(str(e))

            # NAME (svc_rte.bgp.group/peer.name): Ensure that the group or peer name contains no whitespaces
            self.assert_regex_search(svc_rte_errors, '^\S+$', obj['name'], "-svc_rte.bgp.{}.name '{}' contains whitespaces".format(obj_type, obj['name']))
            # REM_AS (svc_rte.bgp.group/peer.remote_as): Ensures that the AS is present, cant make more specific incase is 4-byte ASNs
            self.assert_not_equal(svc_rte_errors, obj.get('remote_as', 'dummy'), None, "-svc_rte.bgp.{}.remote_as in '{}' does not have a value".format(obj_type, obj['name']))
            # PWORD (svc_rte.bgp.group/peer.password): Ensure that the group or peer password contains no whitespaces
            self.assert_regex_search(svc_rte_errors, '^\S+$', obj.get('password', 'dummy'), "-svc_rte.bgp.{}.password in '{}' contains whitespaces".format(obj_type, obj['name']))
            # MHOP (svc_rte.bgp.group/peer.ebgp_multihop): Must be an itegrar from 2 to 255
            self.assert_regex_match(svc_rte_errors, '^([2-9]|[1-9]\d|1\d\d|2[0-4]\d|25[0-5])$', str(obj.get('ebgp_multihop', 2)),
                                    "-svc_rte.bgp.{}.ebgp_multihop '{}' in '{}' must be an integer from 2 to 255".format(obj_type, obj.get('ebgp_multihop'), obj['name']))
            # BFD/DFLT/NH_SLF (svc_rte.bgp.group/peer.bfd/default/next_hop_self): Only acceptable value is True
            for obj_type1 in ['bfd', 'default', 'next_hop_self']:
                self.assert_equal(svc_rte_errors, obj.get(obj_type1, True), True, "-svc_rte.bgp.{}.{} in '{}' has a value of '{}', it only accepts the boolean " \
                                  "'True'".format(obj_type, obj_type1, obj['name'], obj.get(obj_type1)))

            # TIMERS (svc_rte.bgp.group/peer.timers): Make sure is a list, and both keepalive and holdtime are integers
            try:
                assert isinstance(obj.setdefault('timers', [3,9]), list), "-svc_rte.bgp.{}.timers '{}' in '{}' must be a list of [keepalive, holdtime]".format(obj_type, obj.get('timers'), obj['name'])
                assert isinstance(obj['timers'][0], int), "-svc_rte.bgp.{}.timers keepalive ({}) in '{}' must be an integer. It is recommended the holdtime " \
                                  "be 3 times the keepalive".format(obj_type, obj.get('timers')[0], obj['name'])
                assert isinstance(obj['timers'][1], int), "-svc_rte.bgp.{}.timers holdtime ({}) in '{}' must be an integer. It is recommended the holdtime " \
                                  "be 3 times the keepalive".format(obj_type, obj.get('timers')[1], obj['name'])
            except AssertionError as e:
                svc_rte_errors.append(str(e))

        # RUN_FUNCTION_GRP_PR: Runs the grp_pr function against groups and peers to make sure defined values comply. Also creates a list of grp/pr names for duplicate checks
        grp_name, pr_name, tnt_sw_err = ([] for i in range(3))     # tnt_sw_err uses own dict to be able to stop script if error found as tnt/swi must be lists for later tests
        for grp in bgp_grp:
            grp_name.append(grp['name'])
            assert_bgp_grp_pr(grp, 'group', tnt_sw_err)
            for pr in grp['peer']:
                pr_name.append(pr['name'])
                assert_bgp_grp_pr(pr, 'peer', tnt_sw_err)
                # PR_IP (svc_rte.bgp.group/peer.peer_ip): Ensures that the peer IP address is in a valid IPv4 format
                self.assert_ipv4(svc_rte_errors, pr['peer_ip'], "-svc_rte.bgp.peer.peer_ip {} is not a valid IPv4 Address".format(pr['peer_ip']))

        # FAILFAST: If Switch and tenant are not lists breaks other validation tests so needs to stop the script
        if len(tnt_sw_err) != 0:
            svc_rte_errors.extend(tnt_sw_err)           # adds to main error list so all errors displayed before exiting
            return svc_rte_errors

        # FUNCTION_FILTER: Function used by both group and peers to validate inbound/outbound prefix advertisement filters (allow, deny & manipulation with BGP attributes)
        def assert_bgp_flt(obj, obj_type, flt_dir):             # flt_dir is string 'inbound' or 'outbound'
            for flt_name, flt_value in obj[flt_dir].items():    # flt_name is allow/deny/weight/pref/med/as_prepend and flt_value that dictionary value (list, string or dict)
                if flt_name == 'allow' or flt_name == 'deny':

                    # ALLOW_KEYWORD (svc_rte.bgp.group/peer.inbound/outbound.allow): Ensures if is a string the value is 'any' or 'default'
                    if isinstance(flt_value, str) == True:
                        self.assert_regex_match(svc_rte_errors, '^any$|^default$', flt_value, "-svc_rte.bgp.{}.{}.{} ('{}') in '{}' must be a list of " \
                                            "prefixes or a string of 'any' or 'default'".format(obj_type, flt_dir, flt_name, flt_value, obj['name']))
                    # ALLOW/DENY PFX (svc_rte.bgp.group/peer.inbound/outbound.deny/allow): If is a list ensures are valid IPv4 prefixes, not duplicated and if le/ge only 0-32
                    elif isinstance(flt_value, list) == True:
                        self.asset_pfx_lst(svc_rte_errors, flt_value, ['bgp.' + obj_type, flt_dir, flt_name, obj['name']])
                    # CATCHALL: If not a list or string
                    else:
                        svc_rte_errors.append("-svc_rte.bgp.{}.{}.{} '{}' in '{}' is not valid, can only be a list or string (any or default)".format(obj_type,
                                              flt_dir, flt_name, flt_value, obj['name']))
                else:
                    if isinstance(flt_value, dict) == True:
                        # BGP_ATTR_DIR (svc_rte.bgp.group/peer.inbound/outbound.weight/pref/med/as_prepend): Ensures correct BGP attribute type for direction
                        if flt_dir == 'inbound':
                            self.assert_regex_match(svc_rte_errors, '^weight$|^pref$', flt_name, "-svc_rte.bgp.{}.{} in '{}' cant be '{}', only acceptable " \
                                                    "inbound BGP attributes are Local pref or weight".format(obj_type, flt_dir, obj['name'], flt_name))
                        elif flt_dir == 'outbound':
                            self.assert_regex_match(svc_rte_errors, '^med$|^as_prepend$', flt_name, "-svc_rte.bgp.{}.{} in '{}' cant be '{}', only acceptable " \
                                                    "outbound BGP attributes are med or as_prepend".format(obj_type, flt_dir, obj['name'], flt_name))
                        # BGP_ATTR (svc_rte.bgp.group/peer.inbound/outbound.weight/pref/med/as_prepend): Ensures that BGP attribute is an integer
                        for bgp_attr, pfx in flt_value.items():
                            self.assert_integer(svc_rte_errors, bgp_attr, "-svc_rte.bgp.{}.{}.{} the BGP attribute ('{}') in '{}' must be an numerical value".format(
                                                 obj_type, flt_dir, flt_name, bgp_attr, obj['name']))
                            # BGP_PFX: (svc_rte.bgp.group/peer.inbound/outbound.weight/pref/med/as_prepend): Ensures only keywords any/default or if list are valid IPv4 prefixes and not duplicated
                            if isinstance(pfx, str) == True:
                                self.assert_regex_match(svc_rte_errors, '^any$|^default$', pfx, "-svc_rte.bgp.{}.{}.{} ('{}') in '{}' must be a list of " \
                                            "prefixes or a string of 'any' or 'default'".format(obj_type, flt_dir, flt_name, pfx, obj['name']))
                            elif isinstance(pfx, list) == True:
                                self.asset_pfx_lst(svc_rte_errors, pfx, ['bgp.' + obj_type, flt_dir, flt_name, obj['name']])
                    # CATCHALL: If not a dictionary
                    else:
                        svc_rte_errors.append("-svc_rte.bgp.{}.{}.{} '{}' in '{}' is not valid, can only be a dictionary of attribute and prefixes".format(
                                              obj_type, flt_dir, flt_name, flt_value, obj['name']))

        # RUN_FUNCTION_FILTER: Runs the bgp_flt function against groups and peers for inbound and outbound filters
        for grp in bgp_grp:
            if grp.get('inbound') != None:
                assert_bgp_flt(grp, 'group', 'inbound')
            if grp.get('outbound') != None:
                assert_bgp_flt(grp, 'group', 'outbound')
            for pr in grp['peer']:
                if pr.get('inbound') != None:
                    assert_bgp_flt(pr, 'peer', 'inbound')
                if pr.get('outbound') != None:
                    assert_bgp_flt(pr, 'peer', 'outbound')

            # TNT (svc_rte.bgp.peer.tenant: Makes sure the VRF that the BGP peer is in exists on the switch
            for each_peer in grp['peer']:
                # DFLT_VAL: If switch or tenant is not specified in the peer adds the group values (which are blank lists [] if not defined)
                for sw in each_peer.get('switch', grp.get('switch', [])):
                    if dev_name['leaf'] in sw:
                        # LF_VRF: Checks if the VRF which the BGP peer is in exist on the switch by comparing against list of VRFs on leaf switches
                        result = set(each_peer.get('tenant', grp.get('tenant', []))) - set(svctnt_vrf_on_lf)
                        self.assert_equal(svc_rte_errors, len(result), 0, "-svc_rte.bgp.peer.tenant '{}' needs to exist on '{}' to create peer '{}' on that switch".format(
                                          list(result), sw, each_peer['name']))
                    if dev_name['border'] in sw:
                        # BDR_VRF: Checks if the VRF which the BGP peer is in exist on the switch by comparing against list of VRFs on border switches
                        result = set(each_peer.get('tenant', grp.get('tenant', []))) - set(svctnt_vrf_on_bdr)
                        self.assert_equal(svc_rte_errors, len(result), 0, "-svc_rte.bgp.peer.tenant '{}' needs to exist on '{}' to create peer '{}' on that switch".format(
                                          list(result), sw, each_peer['name']))

            # UPDT_SRC (svc_rte.bgp.group/peer.update_source): Must be a loopback that exists on that switch
            for each_peer in grp['peer']:
                # DFLT_VAL: If is set in the group is passed down to the peer
                if each_peer.setdefault('update_source', grp.get('update_source', None)) != None:
                    # LP: Loops through dict of all {switch: [loopbacks] and asserts whether update_source loopback exists on this switch
                    for sw, lp in lp_per_dev_intf.items():
                        lp = [intf[0] for intf in lp]       # Gets just the intf from the (intf, tnt) tuple
                        if sw in each_peer.get('switch', grp.get('switch', [])):
                            self.assert_in(svc_rte_errors, each_peer['update_source'], lp, "-svc_rte.bgp.group/peer.update_source '{}' in group/peer '{}/{}' does not " \
                                          "exist on '{}'".format(each_peer['update_source'], grp['name'], each_peer['name'], sw))

        # GRP/PR_NAME (svc_rte.bgp.group/peer.name): Ensures no duplicate group or peer names
        self.duplicate_in_list(svc_rte_errors, grp_name, "-svc_rte.bgp.group.name '{}' is/are duplicated accross multiple groups, all names must be unique", [])
        self.duplicate_in_list(svc_rte_errors, pr_name, "-svc_rte.bgp.peer.name '{}' is/are duplicated accross multiple peers, all names must be unique", [])
        grp_name = set(grp_name)
        pr_name = set(pr_name)
        grp_pr_name = list(grp_name)
        grp_pr_name.extend(list(pr_name))
        self.duplicate_in_list(svc_rte_errors, grp_pr_name, "-svc_rte.bgp.group/peer.name '{}' is/are duplicated accross groups and peers, all names must be unique", [])

################ OSPF variables ################
        # MAND_ONLY: Makes sure that mandatory dicts are only in process or only in interface, if not exits the scripts
        mand_ospf_err = []
        self.ospf_proc_swi = defaultdict(list)
        for proc in ospf:

            try:
                # INTF (svc_rte.ospf.interface): Ensures that the interfaces is not an empty dictionary
                assert proc.get('interface') != None, "-svc_rte.ospf.interface in tenant '{}' process '{}' should not be an empty dictionary, if not used "\
                                                      "hash it out".format(proc.get('tenant','global'), proc.get('process','Unknown'))
                # PROC (svc_rte.ospf.process): Ensure that the OSPF process is configured
                self.assert_exist(mand_ospf_err, proc, 'process', "-svc_rte.ospf.process a process in tenant '{}' does not have a value, this is a mandatory dictionary "\
                                                                  "key".format(proc.get('tenant','global')))
                # PROC (svc_rte.ospf.switch): Ensure that the OSPF process switch is configured and is a list
                self.assert_list(mand_ospf_err, proc.get('switch'), "-svc_rte.ospf.switch process '{}' does not have the mandatory switch dictionary or it is not a " \
                                                                          "list".format(proc.get('tenant','global'), proc.get('process','Unknown')))
                for intf in proc['interface']:
                    # INTF_NAME/AREA (svc_rte.ospf.interface.name/area): Ensure that the area and name dictionaries are configured under the interface
                    self.assert_exist(mand_ospf_err, intf, 'name', "-svc_rte.ospf.interface.name an interface in process '{}' has no name, this is a mandatory "\
                                    "dictionary".format(proc.get('name','Unknown')))
                    self.assert_exist(mand_ospf_err, intf, 'area', "-svc_rte.ospf.interface.area interface {} has no area, this is a mandatory dictionary".format(intf.get('name','Unknown')))
            except AssertionError as e:
                mand_ospf_err.append(str(e))
        # FAILFAST: Exit script if dont exist as cant do further tests without these dict
        if len(mand_ospf_err) != 0:
            svc_rte_errors.extend(mand_ospf_err)           # adds to main error list so all errors displayed before exiting
            return svc_rte_errors

        for proc in ospf:
            # Creates a dict of {ospf_pro: [list_swi]} for validating they exist when doing redistribution validation
            self.ospf_proc_swi[proc['process']].extend(proc['switch'])

            # OSPF (svc_rte.ospf.rid): Ensures that the RID is a list of valid IPv4 address and equal to the number of switches (in process)
            if proc.get('rid') != None:
                try:
                    assert isinstance(proc.get('rid'), list), "-svc_rte.ospf.rid '{}' in process '{}' must be a list of RIDs, even if is only 1".format(proc.get('rid'), proc['process'])
                    for each_rid in proc['rid']:
                        self.assert_ipv4(svc_rte_errors, each_rid, "-svc_rte.ospf.rid '{}' in process '{}' is not a valid IPv4 Address".format(each_rid, proc['process']))
                    self.assert_equal(svc_rte_errors, len(proc['rid']) ,len(proc['switch']), "-svc_rte.ospf.rid process '{}' has '{}' RIDs and '{}' switches, these must be "\
                                                                                            "the same and number".format(proc['process'], len(proc['rid']) ,len(proc['switch'])))
                except AssertionError as e:
                    svc_rte_errors.append(str(e))
            # BFD (svc_rte.ospf.bfd): Enable BFD for all neighbors. Is disabled by default, only acceptable value is True
            self.assert_equal(svc_rte_errors, proc.get('bfd', True), True, "-svc_rte.ospf.bfd '{}' in process '{}' not valid. BFD is disabled by default, only acceptable "\
                              "option is boolean 'True'".format(proc.get('bfd'), proc['process']))
            # DFLT_ORIG (svc_rte.ospf.default_orig): Ensures that it is either boolean 'True' or 'always'
            self.assert_regex_match(svc_rte_errors, '^True$|^always$', str(proc.get('default_orig', 'always')), "-svc_rte.ospf '{}' in process '{}' not valid, only options are "\
                                   "boolean 'True' or 'always'".format(proc.get('default_orig'), proc['process']))

            for intf in proc['interface']:
                # AREA (svc_rte.ospf.interface.area): Ensures that the area is in dotted decimal format
                self.assert_ipv4(svc_rte_errors, intf['area'], "-svc_rte.ospf.interface.area '{}' for {} in process '{}' is not a valid dotted decimal area, "\
                                 "valid values are 0.0.0.0 to 255.255.255.255".format(intf['area'], intf['name'], proc['process']))
                # COST (svc_rte.ospf.interface.cost): Ensures the cost is decimal between 1 and 65535
                self.assert_in(svc_rte_errors, intf.get('cost', 1), range(1, 65535), "-svc_rte.ospf.interface.cost '{}' for {} in process '{}' must be a integer between "\
                              "1 and 65535".format(intf.get('cost'), intf['name'], proc['process']))
                # AUTH (svc_rte.ospf.interface.authentication): Ensures the password contains no whitespaces
                self.assert_regex_search(svc_rte_errors, '^\S+$', intf.get('authentication', 'dummy'), "-svc_rte.ospf.interface.authentication for {} in process '{}' "\
                                         "contains whitespaces".format(intf['name'], proc['process']))
                # AREA_TYPE (svc_rte.ospf.interface.area_type): Ensures area type is a string starting with stub or nssa
                self.assert_regex_match(svc_rte_errors, '^stub|nssa', intf.get('area_type', 'stub'), "-svc_rte.ospf.interface.area_type '{}' for {} in process '{}' is "\
                                        "not valid, it must start with 'stub' or 'nssa'".format(intf.get('area_type'), intf['name'], proc['process']))
                # PASSIVE (svc_rte.ospf.interface.passive): By default is False, ensures if specficied only acceptable value is boolean 'True'
                self.assert_equal(svc_rte_errors, intf.get('passive', True), True, "-svc_rte.ospf.interface.passive '{}' for {} in process '{}' not valid. It is disabled "\
                                 "by default, the only acceptable option is boolean 'True'".format(intf.get('passive'), intf['name'], proc['process']))
                # HELLO (svc_rte.ospf.interface.hello): Ensures that the OSPF hello is an integer
                self.assert_integer(svc_rte_errors, intf.get('hello', 0), "-svc_rte.ospf.interface.hello '{}' should be an integer (number)".format(intf.get('hello')))
                # INTF_TYPE (svc_rte.ospf.interface.type): By default all interfaces are broadcast, if defiend ensures is 'point-to-point', this is only viable option
                self.assert_equal(svc_rte_errors, 'point-to-point', intf.get('type', 'point-to-point'), "-svc_rte.ospf.interface.type '{}' for {} in process '{}' is not "\
                                 "valid. Only option is 'point-to-point'".format(intf.get('type'), intf['name'], proc['process']))

                # If switch not configured under interface uses process switch value
                intf.setdefault('switch', proc.get('switch', None))
                temp_bdr, temp_lf = ([] for i in range(2))
                try:
                    # SW_LIST (svc_rte.ospf.interface.switch): Ensure that it is a list of switches
                    assert isinstance(intf['switch'], list), "-svc_rte.ospf.interface.switch '{}' for '{}' in process '{}' must be a list of switches, even if is "\
                                      "only 1".format(intf['switch'], intf['name'], proc['process'])
                    # SW_NAME (svc_rte.ospf.interface.switch): Ensure the switch name is valid (exists in inventory)
                    for sw in intf['switch']:
                        self.assert_in(svc_rte_errors, sw, all_devices, "-svc_rte.ospf.interface.switch {} for {} in process '{}' is not a valid hostname within the "\
                                       "inventory".format(intf['switch'], intf['name'], proc['process']))
                        # Variables to be used for the next test
                        if dev_name['leaf'] in sw:
                            temp_lf.append(sw)
                        elif dev_name['border'] in sw:
                            temp_bdr.append(sw)
                except AssertionError as e:
                    svc_rte_errors.append(str(e))

                try:
                    # TNT (svc_rte.ospf.process.tenant): Ensure that the tenant exists on the border and leaf switches (must exist to do next tests)
                    if len(temp_bdr) != 0:
                        assert proc.get('tenant', 'global') in set(svctnt_vrf_on_bdr), "-svc_rte.ospf.process.tenant '{}' in process '{}' is not on switch '{}'".format(proc.get('tenant', 'global'), proc['process'], temp_bdr)
                    if len(temp_lf) != 0:
                        assert proc.get('tenant', 'global') in set(svctnt_vrf_on_lf), "-svc_rte.ospf.process.tenant '{}' in process '{}' is not on switch '{}'".format(proc.get('tenant', 'global'), proc['process'], temp_lf)
                    for each_sw in intf['switch']:
                        # Loops through all switches and tenant/interface to compare and make sure specified interface is in the tenant
                        for sw, tnt_intf in per_dev_tnt_intf.items():
                            if each_sw == sw:
                                # print(tnt_intf)
                                for each_intf in intf['name']:          # OSPF interface name is a list so loops through each
                                    # INTF_TNT (svc_rte.ospf.process/interface.tenant): Ensures that the OSPF interface is within the tenant
                                    self.assert_in(svc_rte_errors, each_intf, str(tnt_intf[proc.get('tenant', 'global')]), "-svc_rte.ospf.interface '{}' in process '{}' is not in tenant '{}' on '{}. "
                                                                                "Remember interface name has to be full format'".format(each_intf, proc['process'], proc.get('tenant', 'global'), sw))
                except AssertionError as e:
                    svc_rte_errors.append(str(e))


################ Advertisement (network/summary/redist) variables ################
        # FUNCTION_SWI_TNT: Function validates that list of switches exists, switches within the inventory and the tenant is on the switch
        def assert_sw_tnt(tnt, adv_type, adv_value, error):
            for each_entry in tnt[adv_type]:
                # If switch not configured under group uses peer switch value
                each_entry.setdefault('switch', tnt.get('switch', None))
                temp_bdr, temp_lf = ([] for i in range(2))
                try:
                    #1. LIST (svc_rte.bgp.tnt_advertise.network/summary/redist.switch): Ensure that is a list of switches
                    assert isinstance(each_entry['switch'], list), "-svc_rte.bgp.tnt_advertise.{}.switch '{}' for prefix '{}' in tenant '{}' must be a list of switches, even if "\
                                                                    "is only 1".format(adv_type, each_entry['switch'], each_entry.get(adv_value, 'Unknown'), tnt['name'])
                    # 2. NAME (svc_rte.bgp.tnt_advertise.network/summary/redist.switch): Ensure the switch name is valid (exists in inventory)
                    for sw in each_entry['switch']:
                        self.assert_in(svc_rte_errors, sw, all_devices, "-svc_rte.bgp.tnt_advertise.{}.switch '{}' in tenant '{}' is not a valid hostname within the inventory".format(
                                        adv_type, sw, tnt['name']))
                        if dev_name['leaf'] in sw:
                            temp_lf.append(sw)
                        elif dev_name['border'] in sw:
                            temp_bdr.append(sw)
                    # 3a. LF_TNT (svc_rte.bgp.tnt_advertise.network/summary/redist.switch): Ensure that the tenant is on the leaf switches
                    if dev_name['leaf'] in str(temp_lf):
                        self.assert_in(svc_rte_errors, tnt['name'], set(svctnt_vrf_on_lf), "-svc_rte.bgp.tnt_advertise.{}.switch {} for {} {} doesn't have tenant '{}'".format(
                                        adv_type, temp_lf, adv_value, each_entry.get(adv_value, 'Unknown'), tnt['name']))
                    # 3b. BDR_TNT (svc_rte.bgp.tnt_advertise.network/summary/redist.switch): Ensure that the tenant is on the border switches
                    if dev_name['border'] in str(temp_bdr):
                        self.assert_in(svc_rte_errors, tnt['name'], set(svctnt_vrf_on_bdr), "-svc_rte.bgp.tnt_advertise.{}.switch {} for {} {} doesn't have tenant '{}'".format(
                                        adv_type, temp_bdr, adv_value, each_entry.get(adv_value, 'Unknown'), tnt['name']))
                except AssertionError as e:
                    error.append(str(e))

      # FUNCTION_ADV_PFX: Function validates all elements of the various methods used to advertise prefixes into the routing protocol (network (bgp only), summary and redistribution)
        def adv_pfx_checks(opt, adv_type, adv_value, tnt_name, summary, error, err_msg):
            # 1. LP: Within each advertisment type (network, summary, redist), loop through each indivdual advertisment
            for each_type in opt[adv_type]:
                try:
                    # 2. ALL_MAND_EXIST (svc_rte.ospf/bgp.tenant.network/summary/redist.prefix/type): If prefix/type doesnt exists must failfast for that type (uses separate error_var) as other checks rely on it
                    assert each_type.get(adv_value) != None, "-svc_rte.{0}.{1}.{2} '{1}' in tenant '{3}' is missing a mandatory '{2}' dictionary for one of " \
                                                            "its list elements".format(err_msg, adv_type, adv_value, opt.get(tnt_name, 'global'))
                    # 3. NET/SUM: Checks to be performed on network or summary adv_types
                    if adv_type != 'redist':
                        # 3a. MAND_LIST (svc_rte.ospf/bgp.tenant.network/summary.prefix): If is not a list failfast as other checks rely on it being a list
                        assert isinstance(each_type[adv_value], list) == True, "-svc_rte.{}.{}.{} '{}' in tenant '{}' must be a list of prefixes".format(err_msg, adv_type,
                                                                                adv_value, each_type[adv_value], opt.get(tnt_name, 'global'))
                        # 3b. PFX (svc_rte.ospf/bgp.tenant.network/summary.prefix): Ensures that prefixes are valid and not duplicates. Errors added to the main 'svc_rte_errors' list of errors
                        self.asset_pfx_lst(svc_rte_errors, each_type[adv_value], [err_msg, adv_type, adv_value, 'tenant ' + opt.get(tnt_name, 'global')])
                        # 3c. SUM (svc_rte.ospf/bgp.tenant.summary.filter): If using summary fitering ensures value is summary-only (bgp) or not-advertise (ospf).
                        self.assert_equal(svc_rte_errors, each_type.get('filter', summary), summary, "-svc_rte.{}.{}.filter '{}' for {} in tenant '{}' is invalid, only "\
                                         "possible option is '{}'".format(err_msg, adv_type, each_type.get('filter'), each_type[adv_value], opt.get(tnt_name, 'global'), summary))
                      # 3d. AREA (svc_rte.OSPF.summary.filter): OSPF only ensures area is in dotted decimal format. Adding area makes it a makes it a LSA3 summary.
                        self.assert_ipv4(svc_rte_errors, each_type.get('area', '0.0.0.0'), "-svc_rte.{}.{}.area '{}' for {} in process '{}' is not a valid dotted decimal area, "\
                                 "valid values are 0.0.0.0 to 255.255.255.255".format(err_msg, adv_type, each_type.get('area'), each_type[adv_value], opt.get(tnt_name, 'global')))
                    # 4. REDIST: Checks to be performed on redist adv_type
                    elif adv_type == 'redist':
                        # 4a. MATCH_STR (svc_rte.ospf/bgp.tenant.redist.type): Ensures the type is bgp xx, ospf xx, static or connected, if not failfast for that
                        assert re.match('^bgp\s\S+$|^ospf\s\S+|^static$|^connected$', each_type[adv_value]), "-svc_rte.{}.{}.{} '{}' in tenant '{}' is invalid, only possible "\
                                        "options are 'bgp xx', 'ospf xx', 'static' or 'connected'".format(err_msg, adv_type, adv_value, each_type[adv_value], opt.get(tnt_name, 'global'))

                        #4b. REDIST_OSPF (svc_rte.bgp/ospf.redist.type): Makes sure that the OSPF process being redistributed exists on the switch it is being redistributed on
                        if 'ospf ' in each_type[adv_value]:
                            redist_proc = str(each_type[adv_value].split('ospf ')[1])       # Gets the OSPF process
                            all_proc = [fbc['route']['ospf']['pro']]                        # Create list with underlay OSPF process to hold all OSPF processes
                            for each_proc, list_sw in self.ospf_proc_swi.items():
                                all_proc.append(str(each_proc))                             # Adds each process to all proccess list
                                if redist_proc == str(each_proc):
                                    on_sw_result = set(each_type.get('switch', opt['switch'])) - set(list_sw)
                                    self.assert_equal(svc_rte_errors, len(on_sw_result), 0, "-svc_rte.bgp/ospf.redist.type '{}' in tenant '{}' cant be redistributed as not "\
                                                                                      "configured on {}".format(each_type[adv_value], opt.get(tnt_name, 'global'), on_sw_result))
                            # REDIST_OSPF (svc_rte.bgp/ospf.redist.type): Makes sure that the OSPF process being redistributed exists (as is missed bt previous check if)
                            self.assert_in(svc_rte_errors, redist_proc, set(all_proc), "-svc_rte.ospf.redist.type '{}' in tenant '{}' can't be redistributed, as the OSPF "\
                                                                                       "process doesn't exist".format(each_type[adv_value], opt.get(tnt_name, 'global')))

                        #4c. REDIST_BGP (svc_rte.ospf.redist.type): Makes sure that the BGP ASN being redistributed matches local fabric ASN
                        if 'bgp ' in each_type[adv_value]:
                            self.assert_equal(svc_rte_errors, each_type[adv_value].split('bgp ')[1], str(fbc['route']['bgp']['as_num']), "-svc_rte.ospf.redist.type '{}' in tenant "\
                                "'{}' can't be redistrubuted, should be local BGP AS ({})".format(each_type[adv_value], opt.get(tnt_name, 'global'), fbc['route']['bgp']['as_num']))

                        if each_type.get('allow') != None:
                            # 5a. ALLOW_KEYWORD (svc_rte.ospf/bgp.tenant.redist.type.allow): Ensures if is a string the value is 'any' or 'default'
                            if isinstance(each_type['allow'], str) == True:
                                self.assert_regex_match(svc_rte_errors, '^any$|^default$', each_type['allow'], "-svc_rte.{}.{}.{}.allow '{}' in '{}' must be a list of " \
                                           "prefixes (interfaces if connected), or a string ('any' or 'default')".format(err_msg, adv_type, each_type[adv_value], each_type['allow'], opt.get(tnt_name, 'global')))
                            elif isinstance(each_type['allow'], list) == True:
                                # 5b. ALLOW_CONN (svc_rte.ospf/bgp.tenant.redist.connected.allow): Ensures redist connected interface exist on switch (loopback, vlan, physical) and in correct VRF
                                if each_type['type'] == 'connected':
                                    # Opens up dictionary of tenant (list of interfaces in it) per-switch
                                    for each_sw, each_tnt in per_dev_tnt_intf.items():
                                        # If the switch is one of the ones redistributing interfaces and the tenant is on that switch with an interface
                                        if each_sw in each_type.get('switch', opt.get('switch')):
                                            if each_tnt.get(opt[tnt_name]) != None:
                                                # Creates a list of any interfaces named in redistribution but not on switch and in the VRF. Assers that list should be empty
                                                miss_intf = set(each_type['allow']) - set(each_tnt.get(opt[tnt_name]))
                                                self.assert_equal(svc_rte_errors, len(miss_intf), 0, "-svc_rte.{}.{}.{}.allow interface '{}' in tenant '{}' is not an interface on '{}' or in "\
                                                                                "correct VRF.".format(err_msg, adv_type, each_type[adv_value], miss_intf, opt.get(tnt_name, 'global'), each_sw))
                                else:
                                     # 5c. ALLOW_PFX (svc_rte.ospf/bgp.tenant.redist.type.allow): Ensures list of prefixes are valid IPv4 prefixes, not duplicated and if le/ge only 0-32
                                    self.asset_pfx_lst(svc_rte_errors, each_type['allow'], [err_msg, adv_type, each_type[adv_value] + '.allow', 'tenant ' + opt.get(tnt_name, 'global')])
                            # 5e. ALLOW_CATCH_ALL: If is not a list or string
                            else:
                                svc_rte_errors.append("-svc_rte.{}.{}.{}.allow '{}' in tenant '{}' must be a string (any or default) or a list of prefixes (interfaces if "\
                                                     "connected)".format(err_msg, adv_type, each_type[adv_value], each_type['allow'], opt.get(tnt_name, 'global')))
                        # 6. METRIC (svc_rte.ospf/bgp.tenant.redist.type.metric): Ensures prefixes and metric/med used in redistribution are valid
                        if each_type.get('metric') != None:
                            if isinstance(each_type['metric'], dict) == True:
                                for attr, pfx in each_type['metric'].items():
                                    # 6a. METRIC_VAL: Ensures that the metric value is a decimal
                                    self.assert_integer(svc_rte_errors, attr, "-svc_rte.{}.{}.{}.metric '{}' in tenant {} must be an numerical value".format(err_msg,
                                                         adv_type, each_type[adv_value], attr, opt.get(tnt_name, 'global')))
                                    # 6b. METRIC_PFX: Ensures only keywords any/default or if list are valid IPv4 prefixes and not duplicated and if le/ge only 0-32
                                    if isinstance(pfx, str) == True:
                                        self.assert_regex_match(svc_rte_errors, '^any$|^default$', pfx, "-svc_rte.{}.{}.{}.metric '{}' in '{}' must be a list of prefixes "\
                                                                "or a string of 'any' or 'default'".format(err_msg, adv_type, each_type[adv_value], pfx, opt.get(tnt_name, 'global')))
                                    elif isinstance(pfx, list) == True:
                                        self.asset_pfx_lst(svc_rte_errors, pfx, [err_msg, adv_type, each_type[adv_value] + '.metric', 'tenant ' + opt.get(tnt_name, 'global')])
                                    # 6c. CATCH_ALL: If dictionary value is not a list or string
                                    else:
                                        svc_rte_errors.append("-svc_rte.{}.{}.{}.metric dictionary value '{}' in tenant '{}' must be keywords 'any' or 'default', "\
                                                              "or a list of prefixes".format(err_msg, adv_type, each_type[adv_value], pfx, opt.get(tnt_name, 'global')))
                            # 6d. CATCH_ALL: If is not a dict
                            else:
                                svc_rte_errors.append("-svc_rte.{}.{}.{}.metric '{}' in tenant '{}' must be a dictionary".format(err_msg, adv_type, each_type[adv_value],
                                                      each_type['metric'], opt.get(tnt_name, 'global')))
                except AssertionError as e:
                    error.append(str(e))

        # FUNCTION_ADV_PFX and SWI_TNT: Runs the functions against the possible advertisement types in BGP and OSPF
        mand_adv_type_err = []
        for tnt in bgp_tnt_adv:
            if tnt.get('network') != None:
                adv_pfx_checks(tnt, 'network', 'prefix', 'name', 'summary-only', mand_adv_type_err, 'bgp.tnt_advertise')
                assert_sw_tnt(tnt, 'network', 'prefix', svc_rte_errors)
            if tnt.get('summary') != None:
                adv_pfx_checks(tnt, 'summary', 'prefix', 'name', 'summary-only', mand_adv_type_err, 'bgp.tnt_advertise')
                assert_sw_tnt(tnt, 'summary', 'prefix', svc_rte_errors)
            if tnt.get('redist') != None:
                adv_pfx_checks(tnt, 'redist', 'type', 'name', 'summary-only', mand_adv_type_err, 'bgp.tnt_advertise')
                assert_sw_tnt(tnt, 'redist', 'type', svc_rte_errors)
        for proc in ospf:
            if proc.get('summary') != None:
                adv_pfx_checks(proc, 'summary', 'prefix', 'tenant', 'not-advertise', mand_adv_type_err, 'ospf')
            if proc.get('redist') != None:
                adv_pfx_checks(proc, 'redist', 'type', 'tenant', 'not-advertise', mand_adv_type_err, 'ospf')

        # FAILFAST: Exit script if dont exist as cant do further tests without this dict
        if len(mand_adv_type_err) != 0:
            svc_rte_errors.extend(mand_adv_type_err)           # adds to main error list so all errors displeyd before exiting
            return svc_rte_errors


################ static-route variables ################
        # MAND_ONLY: Makes sure that mandatory dicts are only in tenant or route, if not exits the scripts
        mand_rte_err = []
        for tnt in route:
            # TNT (svc_rte.static_route.tenant): Ensure that the tenant is configured
            self.assert_exist(mand_rte_err, tnt, 'tenant', "-svc_rte.static_route.tenant a static the tenant is missing, this is a mandatory dictionary key")
            for rte in tnt['route']:
                # PFX/GWAY (svc_rte.static_route.prefix/gateway): Ensure that the prefix and gateway dictionaries are configured under the route
                self.assert_exist(mand_rte_err, rte, 'prefix', "-svc_rte.static_route.prefix a route in tenant '{}' has no prefix, this is a mandatory dictionary".format(
                                    tnt.get('tenant', 'Unknown')))
                if bool(rte.get('gateway')) + bool(rte.get('interface')) == False:
                    mand_rte_err.append("-svc_rte.static_route.gateway/network route {} in tenant '{}' has no gateway and interface, it must have at least one of "\
                                        "them".format(rte.get('prefix', 'Unknown'), tnt.get('tenant', 'Unknown')))

        # FAILFAST: Exit script if dont exist as cant do further tests without these dict
        if len(mand_rte_err) != 0:
            svc_rte_errors.extend(mand_rte_err)           # adds to main error list so all errors displayed before exiting
            return svc_rte_errors

        # MAND_SW: (svc_rte.static_route.tenant/route.switch): Ensure that the switch is configured in tenant or if not in all routes in that tenant
        for tnt in route:
            sw_errors = []
            try:
                assert tnt.get('switch') != None
            except:                             # If the tnt['switch'] dict doesnt exist checks to make sure that route['switch'] dict exists for all routes
                for rte in tnt['route']:
                    self.assert_exist(sw_errors, rte, 'switch', rte['prefix'])          # Assert returns a list of all routes missing switch dict
            if len(sw_errors) != 0:             # If any of the routes are missing the switch dict (list not empty) adds an error with tenant anme and prefixes
                mand_rte_err.append("-svc_rte.static_route.tenant/route.switch tenant '{}' and prefix {} do not have a switch set. It is a mandatory dictionary, " \
                                        "one of them must have it".format(tnt['tenant'], sw_errors[0]))
        # FAILFAST: Exit script if dont exist as cant do further tests without these dict
        if len(mand_rte_err) != 0:
            svc_rte_errors.extend(mand_rte_err)           # adds to main error list so all errors displayed before exiting
            return svc_rte_errors

        # SWI/TNT:
        for tnt in route:
            try:
                # TNT_LIST (svc_rte.static_route.tenant): Ensure that it is a list of tenants, if not fails as cant run further tests
                assert isinstance(tnt['tenant'], list), "-svc_rte.static_route.tenant '{}' must be a list of tenants, even if is only 1".format(tnt['tenant'])
                for rte in tnt['route']:
                    # If switch not configured under the tenant uses the routes switch value
                    rte.setdefault('switch', tnt.get('switch', None))
                    temp_bdr, temp_lf = ([] for i in range(2))
                    # SW_LIST (svc_rte.static_route.route.switch): Ensure that it is a list of switches, if not fails as cant run further tests
                    assert isinstance(rte['switch'], list), "-svc_rte.static_route.route.switch '{}' for route '{}' in tenant '{}' must be a list of switches, even if is "\
                                        "only 1".format(rte['switch'], rte['prefix'], tnt['tenant'])
                    # SW_NAME (svc_rte.static_route.route.switch): Ensure the switch name is valid (exists in inventory)
                    for sw in rte['switch']:
                        self.assert_in(svc_rte_errors, sw, all_devices, "-svc_rte.static_route.route.switch {} for {} in tenant '{}' is not a valid hostname within the "\
                                       "inventory".format(rte['switch'], rte['prefix'], tnt['tenant']))
                        # Variables to be used for the next test
                        if dev_name['leaf'] in sw:
                            temp_lf.append(sw)
                        elif dev_name['border'] in sw:
                            temp_bdr.append(sw)

                    for each_tnt in tnt['tenant']:
                        # TNT (svc_rte.static_route.tenant): Ensure that the tenant exists on the border and leaf switches (tenant must exist as referenced in next tests)
                        # NXT_HOP_VRF (svc_rte.static_route.route.next_hop_vrf): Assert that the next hop VRF is a valid VRF on the switch
                        if len(temp_bdr) != 0:
                            assert each_tnt in set(svctnt_vrf_on_bdr), "-svc_rte.static_route.tenant '{}' for route '{}' is not on switch '{}'".format(each_tnt, rte['prefix'], temp_bdr)
                            self.assert_in(svc_rte_errors, rte.get('next_hop_vrf', 'global'), set(svctnt_vrf_on_bdr), "-svc_rte.static_route.next_hop_vrf '{}' for route "\
                                           "'{}' is not on switch '{}'".format(rte.get('next_hop_vrf'), rte['prefix'], temp_bdr))
                        if len(temp_lf) != 0:
                            assert each_tnt in set(svctnt_vrf_on_lf), "-svc_rte.static_route.tenant'{}' for route '{}' is not on switch '{}'".format(each_tnt, rte['prefix'], temp_lf)
                            self.assert_in(svc_rte_errors, rte.get('next_hop_vrf', 'global'), set(svctnt_vrf_on_lf), "-svc_rte.static_route.next_hop_vrf '{}' for route "\
                                           "'{}' is not on switch '{}'".format(rte.get('next_hop_vrf'), rte['prefix'], temp_lf))

                        # If next-hop interface is set make sure it is in the VRF
                        if rte.get('interface') != None:
                            if rte['interface'] == 'null0':
                                svc_rte_errors.append("-svc_rte.static_route.route.interface '{}' in route '{}' must be 'Null0".format(rte['interface'], rte['prefix']))
                            elif rte['interface'] != 'Null0':
                                for each_sw in rte['switch']:
                                    # Loops through all switches and tenant/interface to compare and make sure specified interface is in the tenant
                                    for sw, tnt_intf in per_dev_tnt_intf.items():
                                        if each_sw == sw:
                                            # NXT_HP_INTF (svc_rte.static_route.route.interface): Ensures that the next-hop interface (if set) is within the tenant or matches the next-hop VRF
                                            if rte.get('next_hop_vrf') != None:
                                                self.assert_in(svc_rte_errors, rte['interface'], str(tnt_intf[rte['next_hop_vrf']]), "-svc_rte.static_route.route.interface '{}' in "\
                                                                                        "route '{}' is not in tenant '{}' on '{}'".format(rte['interface'], rte['prefix'], each_tnt, sw))
                                            else:
                                                self.assert_in(svc_rte_errors, rte['interface'], str(tnt_intf[each_tnt]), "-svc_rte.static_route.route.interface '{}' in route '{}' is "\
                                                                                                    "not in tenant '{}' on '{}'".format(rte['interface'], rte['prefix'], each_tnt, sw))

                    # GWAY (svc_rte.static_route.route.gateway): Ensures that the next hop address is a valid IP address
                    if rte.get('gateway') != None:
                        self.assert_ipv4(svc_rte_errors, rte['gateway'], "-svc_rte.static_route.route.gateway '{}' for route {} in tenant '{}' is not a valid IPv4 Address".format(
                                                                                                                                    rte['gateway'], rte['prefix'], tnt['tenant']))
                    # PFX (svc_rte.static_route.route.prefix): Ensures that prefixes are valid and not duplicates
                    self.asset_pfx_lst(svc_rte_errors, rte['prefix'], ['static_route', 'route', 'prefix', 'tenant ' + str(tnt['tenant'])])
                    # AD (svc_rte.static_route.route.ad): Ensures that the Administrative Distance is an itegrar from 2 to 255
                    self.assert_regex_match(svc_rte_errors, '^([1-9]|[1-9]\d|1\d\d|2[0-4]\d|25[0-5])$', str(rte.get('ad', 1)), "-svc_rte.static_route.route.ad '{}' for {} in tenant {} must be an integer from 1 to 255".format(rte.get('ad'),  rte['prefix'], tnt['tenant']))

            except AssertionError as e:
                svc_rte_errors.append(str(e))


################ Advanced variables ################
        # OSPF_HELLO (fbc.adv.ospf_hello): Ensures that the OSPF hello is an integer
        self.assert_integer(svc_rte_errors, adv['ospf_hello'], "-fbc.adv.ospf_hello '{}' should be an integer (number)".format(adv['ospf_hello']))
        # BGP_TIMERS (svc_rte.adv.bgp_timers: Make sure is a list, and both keepalive and holdtime are integers
        try:
            assert isinstance(adv['bgp_timers'], list), "-svc_rte.adv.bgp_timers '{}' default values must be a list of [keepalive, holdtime]".format(adv['bgp_timers'])
            assert isinstance(adv['bgp_timers'][0], int), "-svc_rte.adv.bgp_timers keepalive ({}) default value must be an integer".format(adv['bgp_timers'][0])
            assert isinstance(adv['bgp_timers'][1], int), "-svc_rte.adv.bgp_timers holdtime ({}) default value must be an integer".format(adv['bgp_timers'][1])
        except AssertionError as e:
            svc_rte_errors.append(str(e))

        for key, rm_pl in adv['bgp_naming'].items():
            # Matches names with only one '_' in the key
            if re.match(r'^[a-z]+_[a-z]+$', key):
                # RM_PL_NME (svc_rte.adv.bgp.naming):  MUST contain 'name' as is replaced when creating the RM/PL name
                self.assert_regex_search(svc_rte_errors, r'name', rm_pl, "-svc_rte.adv.bgp.naming.{} '{}' is not correct, it must contain 'name' within it".format(key, rm_pl))
            # Matches all other names (with more than one '_' in the key)
            else:
                # BGP_ATTR_PL_NME (svc_rte.adv.bgp.naming):  MUST contain 'name' and 'val' as is replaced when creating the PL name
                self.assert_regex_search(svc_rte_errors, r'name\S*val|val\S*name', rm_pl, "-svc_rte.adv.bgp.naming.{} '{}' is not correct, it must contain 'name' and 'val' within it".format(key, rm_pl))

        for key, pl in adv['dflt_pl'].items():
            # DFLT_PL (svc_rte.adv.dflt_pl):  MUST contain 'name' and 'val' as is replaced when creating the PL name
            self.assert_string(svc_rte_errors, pl, "-svc_rte.adv.dflt_pl.{} '{}' is not correct, it must be a string".format(key, pl))

        for key, rm_pl in adv['redist'].items():
            # Matches names with only one '_' in the key
            if re.match(r'^[a-z]+_[a-z]+$', key):
                # RM/PL_NME (svc_rte.adv.redist): Ensures that it contain both 'src' and 'dst' as are swapped to the source and destination of the redistribution
                self.assert_regex_search(svc_rte_errors, r'src\S*dst|dst\S*src', rm_pl, "-svc_rte.adv.redist.{} '{}' is not correct, it must contain 'src' and 'dst' within its name".format(key, rm_pl))
            # Matches all other names (with more than one '_' in the key)
            else:
                # PL_MET_NME (svc_rte.adv.bgp.redist): Ensures that it contains 'src', 'dst' and 'val' as swapped to the source, destination and metric value
                self.assert_regex_search(svc_rte_errors, r'val\S*src\S*dst|src\S*val\S*dst|src\S*dst\S*val|val\S*dst\S*src |dst\S*val\S*src|dst\S*src\S*val', rm_pl,
                                         "-svc_rte.adv.redist.{} '{}' is not correct, it must contain 'src', 'dst' and 'val' within its name".format(key, rm_pl))

        # The value returned to Ansible Assert module to determine whether failed or not
        if len(svc_rte_errors) == 1:
            return "'service_route.yml unittest pass'"             # For some reason ansible assert needs the inside quotes
        else:
            return svc_rte_errors