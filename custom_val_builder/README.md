# Info on how to run Custom Validate Builder

This playbook is designed to help create the structure for the jinja template (desired state) and device output (actual state) data-models that can then be used in the validate role.

The tags allow for it to be run in different ways as you walk through the stages of building the desired and actual state files and eventually create a compliance report

| Title            | Tag        | Information
|------------------|------------|------------------------------------------------------------------------------------------|
| Discovery        | `disc`     | Run the commands from desired_state.yml against a device and print the raw output        |
| Template         | `tmpl`     | Renders the contents of *val_tmpl.j2* to *desired_state.yml* and prints to screen        |
| Data-model       | `dm`       | Run cmds like discovery but feeds output through *device_dm* and prints new DM to screen |
| Report from file | `rpt_file` | Builds compliance report using *desired_state.yml* and static DM in *file_output.json*   |
| Report from cmd  | `report`   | Builds compliance report using *desired_state.yml* and DM created from device cmd output |

The **desired state** (*desired_state.yml*) is rendered from the template *val_tmpl.j2*. It is a list of dictionaries under ta main *cmds* dictionary with the key being the command and value the desired state. The amount of dictionary nesting is determined by the sub-layers of the command output that you are validating.

```yaml
cmds:
  - show ip ospf neighbors detail:
      192.168.100.11:
        state: FULL
      192.168.100.12:
        state: FULL
      192.168.100.22:
        state: FULL
```

The *actual state* (from device or *file_output.json*) is a dictionary in the same format as the desired state value which is created from the returned device output (in JSON format) using a filter plugin.

```json
{"192.168.100.11": {"state": "FULL"}, "192.168.100.12": {"state": "FULL"},"192.168.100.22": {"state": "FULL"}}
```

These two files are fed into the napalm_validate *compare* engine to produce a compliance report. The overall report output is printed to screen along with a link to the report.\
`ansible-playbook PB_val_builder.yml -i hosts --tag report`

```none
Report Complies: True
View the report using cat files/compliance_report.json | python -m json.tool
```

If using *strict_mode* it has to be at the level where you want to enforce it. For example to enforce that only these VNIs are present

```yaml
  - show nve vni:
      _mode: strict
      "20110":
        type: L2 [110]
        state: Up
```

## Developing a new validation test

The method for developing new validations is as follows:

1\. **SETUP_ENV:** Add an entry for the host to be tested in the *hosts file* and playbook *hosts*. The *include_vars* are got from the files in the main playbook (*../vars/*).

2\. **CMD_DISCOVERY:** Run the command (or commands) against the device to see what raw JSON structured data looks like. Add the command with a dummy dictionary to *desired_state.yml*, don't forget to have ':' after the command.

```yaml
cmds:
  - show ip ospf interface brief vrf all:
      dummy: dummy
```

Run the playbook in discovery mode to get back the output.\
`ansible-playbook PB_val_builder.yml  -i hosts --tag disc`

```json
ok: [DC1-N9K-BORDER02] => {
    "validate_result": {
        "show ip ospf interface brief vrf all | json": {
            "TABLE_ctx": {
                "ROW_ctx": [
                    {
                        "TABLE_intf": {
                            "ROW_intf": [
                                {
                                    "admin_status": "up",
                                    "area": "0.0.0.0",
                                    "cost": "100",
                                    "ifname": "Vlan2",
                                    "index": "3",
                                    "nbr_total": "1",
                                    "state_str": "P2P"
                                },
```

3\. **INPUT_DM:** Now that we know what we will get back from the device this can be manipulated into a data model for the attributes we want to validate. For example, if you want to ensure that the interfaces have the correct OSPF process, area and are up you would want an actual state dictionary for each interface in the following format:

```json
{
  "Eth1/1": {
      "area": "0.0.0.0",
      "nbr_count": "1",
      "proc": "DC_UNDERLAY",
      "status": "up"
  },
```

The data model to produce this is quite simple as the dictionary is only 1 nested dictionary deep. This is done under the method *device_dm* within filter plugin *val_builder.yml*.

```python
tmp_dict = defaultdict(dict)
if "show ip ospf interface brief" in cmd:
    for each_proc in json_output['TABLE_ctx']['ROW_ctx']:
        # Loops through interfaces in OSPF process and creates temp dict of each interface in format {intf_name: {attribute: value}}
        for each_intf in each_proc['TABLE_intf']['ROW_intf']:
            tmp_dict[each_intf['ifname']]['proc'] = each_proc['ptag']
            tmp_dict[each_intf['ifname']]['area'] = each_intf['area']
            tmp_dict[each_intf['ifname']]['status'] = each_intf['admin_status']
            tmp_dict[each_intf['ifname']]['nbr_count'] = each_intf['nbr_total']
```

As the data model is created in python it is easier than Ansible to troubleshoot, you can print this out using the 'dm' tag.\
`ansible-playbook PB_val_builder.yml  -i hosts --tag dm`

```json
ok: [DC1-N9K-BORDER02] => {
    "validate_result": {
        "show ip ospf interface brief vrf all": {
            "Eth1/1": {
                "area": "0.0.0.0",
                "nbr_count": "1",
                "proc": "DC_UNDERLAY",
                "status": "up"
            },
            "Eth1/11": {
                "area": "0.0.0.99",
                "nbr_count": "1",
                "proc": "99",
                "status": "up"
            }
        }
    }
}

```

4\. **DESIRED_DM:** Now we know what our actual state looks like we need to create the desired state DM and test. *desired_state.yml* is rendered from the template (*var_tmpl.j2*) so the configuration should be in *var_tmpl.j2*
The desired DM is the actual state JSON (from the value of *"validate_result"*) converted into YAML, are many sites such as https://www.json2yaml.com that can do it (make sure any ' are replaced for " or wont work).

```yaml
cmds:
  - show ip ospf interface brief vrf all:
      Eth1/1:
        area: 0.0.0.0
        nbr_count: '1'
        proc: DC_UNDERLAY
        status: up
      Eth1/11:
        area: 0.0.0.99
        nbr_count: '1'
        proc: '99'
        status: up
```

Run the report `ansible-playbook PB_val_builder.yml  -i hosts --tag report`, this will prove that the desired state data model is correct.

```none
Report Complies: True
View the report using cat files/compliance_report.json | python -m json.tool`
```

**REPORT_FROM_FILE:** Rather than having to connect to the device each time to generate the input DM this can be fed in from a static file (*file_input.json*). The file contents are the exact DM that was produced by *device_dm*.\
`ansible-playbook PB_val_builder.yml  -i hosts --tag rpt_file`

```json
{
      "show ip ospf interface brief vrf all": {
          "Eth1/1": {
              "area": "0.0.0.0",
              "nbr_count": "1",
              "proc": "DC_UNDERLAY",
              "status": "up"
          },
          "Eth1/11": {
              "area": "0.0.0.99",
              "nbr_count": "1",
              "proc": "99",
              "status": "up"
          }
      }
  }
```



5\. **DESIRED_DM_TMPL:** The last thing to do is to build this desired state dynamically from the the input variables using jinja2 templating. The contents of the template (*var_tmpl.j2*) are:

```jinja
cmds:
  - show ip ospf interface brief vrf all:
{% for each_proc in svc_rte.ospf %}
{% if each_proc.interface is defined %}
{% for each_intf in each_proc.interface %}
{% if inventory_hostname in each_intf.switch |default(each_proc.switch) %}
{% for each_name in each_intf.name %}
      {{ each_name | replace(fbc.adv.bse_intf.intf_fmt, fbc.adv.bse_intf.intf_short) }}:
        proc: '{{ each_proc.process }}'
        area: {{ each_intf.area }}
        status: up
        nbr_count: '>=1'
{% endfor %}{% endif %}{% endfor %}{% endif %}{% endfor %}
```

Using `ansible-playbook PB_val_builder.yml  -i hosts --tag tmpl` the rendered output (desired state) will be printed to screen as well as saved to *desired_state.yml*.

```yaml
cmds:
  - show ip ospf interface brief vrf all:
      Vlan99:
        proc: '99'
        area: 0.0.0.0
        status: up
        nbr_count: '>=1'
      Eth1/11:
        proc: '99'
        area: 0.0.0.99
        status: up
        nbr_count: '>=1'
```

Finally the report can be run using dynamically created desired state (from template) and comparing it against dynamically created device out DM (gor from device with napalm_cli).\
`ansible-playbook PB_val_builder.yml  -i hosts --tag report`

This is now ready to be added to the validate role, actual state in *nxos_dm* method of *custom_valdiate.py* and the desired state template in the template file for the role the validation is to be run under (*bse_fbc_val_tmpl.j2, svc_tnt_val_tmpl.j2, svc_intf_val_tmpl.j2, svc_rte_val_tmpl.j2)*.

## Errors

The actual_state must always be a dict, if it is a list you will get the following error in ansible:\
`The error was: AttributeError: 'bool' object has no attribute 'get'`

A compliance report *'missing'* error means that it is in the desired_state but not in the actual state. For example the below error means that *'10010'* is not in actual state. Be careful with string and integers, this was caused because needed to be a string in desired state

```json
{
    "show nve vni": {
        "complies": false,
        "present": {},
        "missing": [
            10010
        ],
        "extra": []
    },
    "skipped": [],
    "complies": false
}
```

This Ansible message means that ':' is probably missing somewhere, so is not a dictionary.

```json
fatal: [DC1-N9K-LEAF01]: FAILED! => {"ansible_facts": {}, "ansible_included_var_files": [], "changed": false, "message": "Syntax Error while loading YAML.\n  mapping values are not allowed here\n\nThe error appears to be in '/home/ste/mac_hd/Ansible/playbooks_and_cmds/ip_auto_lab/build_fabric/custom_val_builder/files/desired_state.yml': line 7, column 13, but may\nbe elsewhere in the file depending on the exact syntax problem.\n\nThe offending line appears to be:\n\n      10010\n        type: L2 [10]\n            ^ here\n"}
```

```yaml
  - show nve vni:
      10010                     <<<<<< needs :
        type: L2 [10]
        vni-state: Up
```

If using ***strict*** it has to be added at the level where you want to enforce it. If an extra element is is in the output you will get an *'extra'* error in the compliance report
```json
ok: [DC1-N9K-BORDER01] => {
    "result": {
        "complies": false,
        "show nve vni": {
            "complies": false,
            "extra": [
                "90999"                             <<< VNI on the device but not in desired_state
```

## Example - *show ip ospf neighbors detail*

**desired_state in val_tmpl.j2**

```yaml
  - show ip ospf neighbors detail:
      192.168.100.11:
        state: FULL
      192.168.100.12:
        state: FULL
      192.168.100.22:
        state: FULL
```

**actual_state in file_input.json**

```json
{"192.168.100.11": {"state": "FULL"}, "192.168.100.12": {"state": "FULL"},"192.168.100.22": {"state": "FULL"}}
```

or

```json
{
        "192.168.100.11": {
            "state": "FULL"
        },
        "192.168.100.12": {
            "state": "FULL"
        },
        "192.168.100.22": {
            "state": "FULL"
        }
}
```

**desired_state in val_tmpl.j2**

```yaml
  - show ip int brief vrf all:
      BLU:
        Vlan10:
          proto-state: up
          link-state: up
          admin-state: up
          prefix: 10.10.10.1

      RED:
        Vlan20:
          proto-state: up
          link-state: up
          admin-state: up
          prefix: 10.10.20.1
```

**actual_state in file_input.json**

```json
{"BLU": {"Vlan10": {"proto-state": "up", "link-state": "up", "admin-state": "up", "prefix": "10.10.10.1"}}, "RED": {"Vlan20": {"proto-state": "up", "link-state": "up", "admin-state": "up", "prefix": "10.10.20.1"}}}
```

or

```json
{
        "BLU": {
            "Vlan10": {
                "admin-state": "up",
                "link-state": "up",
                "prefix": "10.10.10.1",
                "proto-state": "up"
            }
        },
        "RED": {
            "Vlan20": {
                "admin-state": "up",
                "link-state": "up",
                "prefix": "10.10.20.1",
                "proto-state": "up"
            }
        }
}
```
