""" Generates compliance reports using napalm_validate with an input file of the actual state
rather than naplam_validate state to allow the validation of features that don't have naplam_getters.
As cant use variables for Ansible filter plugin names has device specific methods that are called
by the main method (engine).

Methods:
-compliance_report: Replaces the Napalm compliance_report method doing a similar job of running
 validate.compare but with static desired state and actual state yaml files.
-xxx_dm: Formats the command output received from the device into the same format as the desired_state
 yaml file ready for comparison. Will have a different method for each different OS type.
-custom_validate: The engine that runs the OS specific methods (xxx_dm) and passes the returned DM through
 compliance_report (and napalm_validate) to create a compliance report and inform Ansible of the outcome.
-fix_home_path: Converts ~/ to full path for naplam_validate and compliance_report as don't recognize

A pass or fail is returned to the Ansible Assert module, as well as the compliance report joined to
the napalm_validate compliance report
"""

from napalm.base import validate
from napalm.base.exceptions import ValidationException
import json
from collections import defaultdict
import os
import re

class FilterModule(object):
    def filters(self):
        return {
            'fix_home_path': self.fix_home_path,
            'custom_validate': self.custom_validate,
        }

    # FIX: napalm_validate doesn't recognize ~/ for home drive, also used in report method
    def fix_home_path(self, input_path):
        if re.match('^~/', input_path):
            return os.path.expanduser(input_path)
        else:
            return input_path

############################################ Method to run napalm_validate ############################################
# REPORT: Uses naplam_validate on custom data fed into it (still supports '_mode: strict') to validate and create reports

    def compliance_report(self, desired_state, actual_state, directory, hostname):
        report = {}

        # Feeds files into napalm_validate and produces a report
        for cmd, desired_results in desired_state.items():
            try:
                report[cmd] = validate.compare(desired_results, actual_state[cmd])
            # If validation couldn't be run on a command adds skipped key to the cmd dictionary
            except NotImplementedError:
                report[cmd] = {"skipped": True, "reason": "NotImplemented"}

        # Results of compliance report (complies = validation result, skipped = alidation didn't run)
        complies = all([each_cmpl.get("complies", True) for each_cmpl in report.values()])
        skipped = [cmd for cmd, output in report.items() if output.get("skipped", False)]

        filename = os.path.join(self.fix_home_path(directory), 'reports/', hostname + '_compliance_report.json')
        # If a compliance report exists conditionally updates 'skipped' and 'complies' before adding new report to it
        if os.path.exists(filename):
            with open(filename, 'r') as file_content:
                existing_report = json.load(file_content)
            if list(report.values())[0].get('skipped'):
                existing_report['skipped'].extend(skipped)
            if existing_report.get('complies'):         # No need to add if already failing compliance
                existing_report['complies'] = complies
        # If creating a new report adds 'complies' and 'skipped' keys to the dict (validation result or validation didn't run)
        else:
            existing_report = {}
            existing_report['complies'] = complies
            existing_report['skipped'] = skipped

        # Updates report and writes to file
        existing_report.update(report)
        with open(filename, 'w') as file_content:
            json.dump(existing_report, file_content)

        # Returns compliance result of this command
        return complies

############################################ Engine for custom_validate ############################################
# ENGINE: Runs OS specific method to get data model, puts it through napalm_validate and then responds to Ansible

    def custom_validate(self, tmp_desired_state, output, directory, hostname, os):
        cmd_output, actual_state, desired_state = ({} for i in range(3))
        # Creates nested dict of the cmd output dictionaries {cmd: output}}
        for each_cmd in output:
            cmd_output.update(each_cmd['cli_results'])
        # Changes desired state from list of dicts to nested dict {cmd: output}}
        for each_cmd in tmp_desired_state:
            desired_state.update(each_cmd)

        # Runs the OS specific method
        if os == 'nxos':
            actual_state = self.nxos_dm(cmd_output, actual_state)

        # Feeds the validation file and new data model through the reporting function
        self.compliance_report(desired_state, actual_state, directory, hostname)

############################################ OS data-model generators ############################################
# NXOS: Formats the actual_state into data models to return to the engine that then passes it through the reporting method
    def nxos_dm(self, cmd_output, actual_state):
        # Fixes issues due to shit NXOS JSON making dict rather than list if only item
        def shit_nxos(main_dict, parent_dict, child_dict):
            if isinstance(main_dict[parent_dict][child_dict], dict):
                main_dict[parent_dict][child_dict] = [main_dict[parent_dict][child_dict]]

        for cmd, output in cmd_output.items():
            tmp_dict = defaultdict(dict)
            # Ansible output is in serialized json (long sting), needs making into json so can be used like a normal dictionary
            if output != None:
                json_output = json.loads(output)

            # EMPTY: If output is empty just adds an empty dictionary
            if output == None:
                actual_state[cmd.replace(" | json", '')] = tmp_dict

            # OSPF: Creates a dictionary from the device output to match the format of the validation file
            elif "show ip ospf neighbors detail" in cmd:
                shit_nxos(json_output, 'TABLE_ctx', 'ROW_ctx')
                for each_proc in json_output['TABLE_ctx']['ROW_ctx']:
                    shit_nxos(each_proc, 'TABLE_nbr', 'ROW_nbr')
                    for each_nhbr in each_proc['TABLE_nbr']['ROW_nbr']:
                        tmp_dict[each_nhbr['rid']] = {'state': each_nhbr['state']}
                actual_state["show ip ospf neighbors detail"] = tmp_dict

            # PO: Creates a dictionary from the device output to match the format of the validation file
            elif "show port-channel summary" in cmd:
                shit_nxos(json_output, 'TABLE_channel', 'ROW_channel')
                for po in json_output['TABLE_channel']['ROW_channel']:
                    tmp_dict[po['port-channel']]['oper_status'] = po['status']
                    tmp_dict[po['port-channel']]['protocol'] = po['prtcl']
                    po_mbrs = {}
                    if len(po) == 7:
                        shit_nxos(po, 'TABLE_member', 'ROW_member')
                        # if isinstance(po['']['ROW_member'], dict):
                        #     po['TABLE_member']['ROW_member'] = [po['TABLE_member']['ROW_member']]
                        for mbr in po['TABLE_member']['ROW_member']:
                            # Creates dict of members to add to as value in the PO dictionary
                            po_mbrs[mbr['port']] = {'mbr_status': mbr['port-status']}
                    tmp_dict[po['port-channel']]['members'] = po_mbrs
                actual_state["show port-channel summary"] = tmp_dict

            # # vPC: Creates a dictionary from the device output to match the format of the validation file
            elif "show vpc" in cmd:
                tmp_dict['peer-link_po'] = json_output['TABLE_peerlink']['ROW_peerlink']['peerlink-ifindex']
                tmp_dict['peer-link_vlans'] = json_output['TABLE_peerlink']['ROW_peerlink']['peer-up-vlan-bitset']
                tmp_dict['vpc_peer_keepalive_status'] = json_output['vpc-peer-keepalive-status']
                tmp_dict['vpc_peer_status'] = json_output['vpc-peer-status']
                # TABLE_vpc is only present if are vPCs configured
                if json_output.get('TABLE_vpc') != None:
                    shit_nxos(json_output, 'TABLE_vpc', 'ROW_vpc')
                    for vpc in json_output['TABLE_vpc']['ROW_vpc']:
                        tmp_dict[vpc['vpc-ifindex']]['consistency_status'] = vpc['vpc-consistency-status']
                        tmp_dict[vpc['vpc-ifindex']]['port_status'] = vpc['vpc-port-state']
                        tmp_dict[vpc['vpc-ifindex']]['vpc_num'] = vpc['vpc-id']
                        tmp_dict[vpc['vpc-ifindex']]['active_vlans'] = vpc['up-vlan-bitset']
                actual_state["show vpc"] = tmp_dict

            elif "show ip int brief include-secondary vrf all" in cmd:
                shit_nxos(json_output, 'TABLE_intf', 'ROW_intf')
                for intf in json_output['TABLE_intf']['ROW_intf']:
                    tmp_dict[intf['intf-name']]['proto-state'] = intf['proto-state']
                    tmp_dict[intf['intf-name']]['link-state'] = intf['link-state']
                    tmp_dict[intf['intf-name']]['admin-state'] = intf['admin-state']
                    tmp_dict[intf['intf-name']]['tenant'] = intf['vrf-name-out']
                    intf.setdefault('prefix', None)
                    tmp_dict[intf['intf-name']]['prefix'] = intf['prefix']
                actual_state["show ip int brief include-secondary vrf all"] = tmp_dict

            elif "show nve peers" in cmd:
                shit_nxos(json_output, 'TABLE_nve_peers', 'ROW_nve_peers')
                for peer in json_output['TABLE_nve_peers']['ROW_nve_peers']:
                    tmp_dict[peer['peer-ip']] = {'peer-state': peer['peer-state']}
                actual_state["show nve peers"] = tmp_dict

            elif "show nve vni" in cmd:
                shit_nxos(json_output, 'TABLE_nve_vni', 'ROW_nve_vni')
                for vni in json_output['TABLE_nve_vni']['ROW_nve_vni']:
                    tmp_dict[vni['vni']] = {'type': vni['type'], 'state': vni['vni-state']}
                actual_state["show nve vni"] = tmp_dict

            elif "show interface status" in cmd:
                shit_nxos(json_output, 'TABLE_interface', 'ROW_interface')
                for intf in json_output['TABLE_interface']['ROW_interface']:
                    tmp_dict[intf['interface']]['state'] = intf['state']
                    tmp_dict[intf['interface']]['vlan'] = intf['vlan']
                    intf.setdefault('name', None)
                    tmp_dict[intf['interface']]['name'] = intf['name']
                actual_state["show interface status"] = tmp_dict

            elif "show interface trunk" in cmd:
                shit_nxos(json_output, 'TABLE_allowed_vlans', 'ROW_allowed_vlans')
                shit_nxos(json_output, 'TABLE_stp_forward', 'ROW_stp_forward')
                for allow_vlan, stp_vlan in zip(json_output['TABLE_allowed_vlans']['ROW_allowed_vlans'], json_output['TABLE_stp_forward']['ROW_stp_forward']):
                    tmp_dict[allow_vlan['interface']]['allowed_vlans'] = allow_vlan['allowedvlans']
                    tmp_dict[stp_vlan['interface']]['stpfwd_vlans'] = stp_vlan['stpfwd_vlans']
                actual_state["show interface trunk"] = tmp_dict

            # OSPF_INT_BRIEF: Is a 1 deep nested dict {interfaces: {attribute: value}}
            elif "show ip ospf interface brief" in cmd:
                # Apply NXOS 'dict to list' fix incase only one interface
                shit_nxos(json_output, 'TABLE_ctx', 'ROW_ctx')
                for each_proc in json_output['TABLE_ctx']['ROW_ctx']:
                    shit_nxos(each_proc, 'TABLE_intf', 'ROW_intf')

                    # Loops through interfaces in OSPF process and creates temp dict of each interface in format {intf_name: {attribute: value}}
                    for each_intf in each_proc['TABLE_intf']['ROW_intf']:
                        tmp_dict[each_intf['ifname']]['proc'] = each_proc['ptag']
                        tmp_dict[each_intf['ifname']]['area'] = each_intf['area']
                        tmp_dict[each_intf['ifname']]['status'] = each_intf['admin_status']
                        tmp_dict[each_intf['ifname']]['nbr_count'] = each_intf['nbr_total']
                # Adds the output gathered to the actual state dictionary
                actual_state["show ip ospf interface brief vrf all"] = dict(tmp_dict)

           # BGP_TABLE: Is a 1 deep nested dict {prefix: {attribute: value}} with multiple attributes per prefix
            elif "show bgp vrf all ipv4 unicast" in cmd:
                # Apply NXOS 'dict to list' fix incase only one element
                shit_nxos(json_output, 'TABLE_vrf', 'ROW_vrf')
                for each_vrf in json_output['TABLE_vrf']['ROW_vrf']:
                    # Anything after 'ROW_safi' only exists if BGP table is configured and populated
                    try:
                        # Loops each prefix (ipprefix) and paths (ROW_path) for that prefix, paths hold the prefix attributes
                        for each_net in each_vrf['TABLE_afi']['ROW_afi']['TABLE_safi']['ROW_safi']['TABLE_rd']['ROW_rd']['TABLE_prefix']['ROW_prefix']:
                            shit_nxos(each_net, 'TABLE_path', 'ROW_path')
                            # Loops through the each path (can be multiple) for each prefix, only adds entry if a local are summary prefix
                            for each_path in each_net['TABLE_path']['ROW_path']:
                                if each_path['type'] == 'local' or each_path['type'] == 'aggregate':
                                    # Temp dict in the format {prefix: {attribute: value}}
                                    tmp_dict[each_net['ipprefix']]['vrf'] = each_vrf['vrf-name-out'].replace('default', 'global')
                                    tmp_dict[each_net['ipprefix']]['type'] = each_path['type']
                                    tmp_dict[each_net['ipprefix']]['status'] = each_path['status']
                                    tmp_dict[each_net['ipprefix']]['best'] = each_path['best']
                    except:
                        pass
                # Adds the output gathered to the actual state dictionary
                actual_state["show bgp vrf all ipv4 unicast"] = dict(tmp_dict)

            # show ip route: Is a 1 deep nested dict {route: {attribute: value}} with multiple attributes per-route
            elif "show ip route" in cmd:
                shit_nxos(json_output, 'TABLE_vrf', 'ROW_vrf')
                for each_vrf in json_output['TABLE_vrf']['ROW_vrf']:
                    # These dictionaries only exist if there are routes in the routing table (for example if L3 interface in the VRF)
                    try:
                        # Loops each prefix (ipprefix) and attributes (TABLE_path.ROW_path) of that prefix
                        for each_rte in each_vrf['TABLE_addrf']['ROW_addrf']['TABLE_prefix']['ROW_prefix']:
                            # Will have multiple paths if a route has multiple ECMP in the routing table
                            shit_nxos(each_rte, 'TABLE_path', 'ROW_path')
                            for each_path in each_rte['TABLE_path']['ROW_path']:
                                # If is a static route (clientname) adds to temp dict in format {route: {attribute: value}}.
                                if each_path['clientname'] == 'static':
                                    tmp_dict[each_rte['ipprefix']]['vrf'] = each_vrf['vrf-name-out'].replace('default', 'global')
                                    tmp_dict[each_rte['ipprefix']]['next-hop'] = each_path.get('ipnexthop', each_path.get('ifname'))
                                    tmp_dict[each_rte['ipprefix']]['ad'] = each_path['pref']
                                # Need 'discard' to catch any aggregate routes that are suppressed, also sets AD to 254 (for some reason is 220).
                                elif each_path.get('type') == 'discard':
                                    tmp_dict[each_rte['ipprefix']]['vrf'] = each_vrf['vrf-name-out'].replace('default', 'global')
                                    tmp_dict[each_rte['ipprefix']]['next-hop'] = each_path.get('ipnexthop', each_path.get('ifname'))
                                    tmp_dict[each_rte['ipprefix']]['ad'] = '254'
                    except:
                        pass
                # Adds the output gathered to the actual state dictionary
                actual_state["show ip route vrf all"] = dict(tmp_dict)

        return actual_state

