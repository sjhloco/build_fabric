""" Used to test creating compliance reports to be used with the custom_validate in playbook
Uses napalm_validate with an input file of the actual state rather than naplam_validate state

Can take an input of a static file (files/file_input.json) of the expected output (DM) or the actual device output
The desired state is rendered from template (val_tmpl.j2) amd saved to files/desired_sate.yml
The generated report is saved to files/compliance_report.json

'disc' (discovery) prints raw device output, 'tmpl' (template) generates desired state and prints to screen and dm (data-model) generates DM from rawoutput and prints

ansible-playbook PB_val_builder.yml -i hosts --tag disc
ansible-playbook PB_val_builder.yml -i hosts --tag tmpl
ansible-playbook PB_val_builder.yml -i hosts --tag dm

Report creates a compliance report using rendered template to generate desired state and device output to create DM for the actual state
rpt_file (Report from file) again uses rendered desired state, however for actual state uses a static file of the device output DM

ansible-playbook PB_val_builder.yml -i hosts --tag rpt_file
ansible-playbook PB_val_builder.yml -i hosts --tag report
"""

from napalm.base import validate
from napalm.base.exceptions import ValidationException
import json
from collections import defaultdict
import os
import re
from pprint import pprint

class FilterModule(object):
    def filters(self):
        return {
            'val_builder': self.val_builder,
        }

############################################ Method to run napalm_validate ############################################
# REPORT: Uses naplam_validate on custom data fed into it (still supports '_mode: strict') to validate and create reports

    def compliance_report(self, desired_state, actual_state):
        report = {}
        # Feeds files into napalm_validate and produces a report
        for each_dict in desired_state:
            for cmd, desired_results in each_dict.items():
                try:
                    report[cmd] = validate.compare(desired_results, actual_state[cmd])
                # If validation couldn't be run on a command adds skipped key to the cmd dictionary
                except NotImplementedError:
                    report[cmd] = {"skipped": True, "reason": "NotImplemented"}

        # Results of compliance report (complies = validation result, skipped = alidation didn't run)
        existing_report = {}
        existing_report['complies'] = all([each_cmpl.get("complies", True) for each_cmpl in report.values()])
        existing_report['skipped']= [cmd for cmd, output in report.items() if output.get("skipped", False)]

        # Updates report and writes it to file
        existing_report.update(report)
        with open('files/compliance_report.json', 'w') as file_content:
            json.dump(existing_report, file_content)

        print("Report Complies: {}".format(existing_report['complies']))
        print("View the report using 'cat files/compliance_report.json | python -m json.tool'")


############################################ Engine for custom_validate ############################################
# ENGINE: Runs method to get data model, puts it through napalm_validate and then responds to Ansible

    def val_builder(self, desired_state, output, tag):
        cmd_output, actual_state= ({} for i in range(2))

        ############ Tasks run based on the flag that the playbook is run with ############

        ## DISCOVERY (disc) - Prints devices raw cmd output
        if 'disc' in tag:
            tmp_dict = {}
            # Strips out cli_results from output and convert Ansible serialized json (long sting) into normal dictionaries
            for each_cmd in output:
                cmd_output.update(each_cmd['cli_results'])
            for cmd, output in cmd_output.items():
                json_output = json.loads(output)
                tmp_dict[cmd] = json_output
            return tmp_dict

        ## DATA-MODEL from CMD (dm) and/or REPORT (report) - Builds the data model from the raw cmd output
        elif 'dm' in tag or 'report' in tag:
            # Strips out cli_results from output before running 'device_dm' method to create new data-model
            for each_cmd in output:
                cmd_output.update(each_cmd['cli_results'])
            actual_state = self.device_dm(cmd_output, actual_state)
            # PRINT_DM (dm): Returns the newly created DM to be printed by Ansible
            if 'dm' in tag:
                return actual_state
            # REPORT (report): Passes the newly created DM through 'compliance_report' method to generate a report
            elif 'report' in tag:
                self.compliance_report(desired_state, actual_state)

        # REPORT from FILE (rpt_file): Creates a compliance report by passing static file of the output DM
        elif 'rpt_file' in tag:
            actual_state = json.loads(output)
            self.compliance_report(desired_state, actual_state)


############################################ Device data-model generators ############################################
# Creates the data model from the output returned by the device
    def device_dm(self, cmd_output, actual_state):
       # Fixes issues due to shit NXOS JSON making dict rather than list if only item
        def shit_nxos(main_dict, parent_dict, child_dict):
            if isinstance(main_dict[parent_dict][child_dict], dict):
                main_dict[parent_dict][child_dict] = [main_dict[parent_dict][child_dict]]

        # For each cmd serializes json (long sting) into normal dictionaries and runs pre-cmd data-model manipulation
        for cmd, output in cmd_output.items():
            tmp_dict = defaultdict(dict)
            json_output = json.loads(output)

            # INT_STATUS: Is a 1 deep nested dict {intf_name: {attribute: value}}}
            if "show interface status" in cmd:
                # Loops through interfaces in creates temp dict of each interface in format {intf_name: {attribute: value}}
                for intf in json_output['TABLE_interface']['ROW_interface']:
                    tmp_dict[intf['interface']]['state'] = intf['state']
                    tmp_dict[intf['interface']]['vlan'] = intf['vlan']
                    intf.setdefault('name', None)
                    tmp_dict[intf['interface']]['name'] = intf['name']
                # Adds the output gathered to the actual state dictionary
                actual_state["show interface status"] = dict(tmp_dict)

            # OSPF_INT_BRIEF: Is a 1 deep nested dict {interfaces: {attribute: value}}
            if "show ip ospf interface brief" in cmd:
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


            # show ip route: Is a 1 deep nested dict {route: {attribute: value}} with multiple attributes per-route
            if "show ip route" in cmd:
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


            # BGP_TABLE: Is a 1 deep nested dict {prefix: {attribute: value}} with multiple attributes per prefix
            if "show bgp vrf all ipv4 unicast" in cmd:
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

        return actual_state