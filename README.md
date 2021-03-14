# Deploy Leaf and Spine

This playbook will deploy a leaf and spine fabric and its related services in a declarative manner. You only have to define a few key values such as *naming convention*, *number of devices* and *addresses ranges*, the playbook is smart enough to do the rest for you.

This came from my project for the [IPSpace Building Network Automation Solutions](https://www.ipspace.net/Building_Network_Automation_Solutions) course and was used in part when we were deploying Cisco 9k leaf and spine fabrics in our Data Centers. The playbook is structured in a way that it should hopefully not be too difficult to add templates to deploy leaf and spine fabrics for other vendors. My plan was to add Arista and Juniper but is unlikely to happen.

I now am done with building DCs (bring on the :cloud:) and with this being on the edge of the limit of my programing knowledge I don't envisage making any future changes. This README is intended to give enough information to understand the playbooks structure and run it. The variable files hold examples of a deployment with more information on what each variable does. For more detailed information about the playbook have a look at the series off posts I did about it on my [blog](https://theworldsgonemad.net/2021/automate-dc-pt1).

<hr>

The playbook deployment is structured into the following 5 roles with the option to deploy part or all of the fabric.

- **base:** Non-fabric specific core configuration such as hostname, address ranges, aaa, users, acls, ntp, syslog, etc
- **fabric:** Fabric specific core elements such as fabric size, interfaces (spine-to->leaf/border), routing protocols (OSPF, BGP) and MLAG
- **services:** Services provided by the fabric (not the fabric core) are split into three sub-roles:
  - ***tenant:*** VRFs, SVIs, VLANs and VXLANs on the fabric and their associated VNIs
  - ***interface:*** Access ports connecting to compute or other non-fabric core network devices
  - ***routing:*** BGP (address-families), OSPF (additional non-fabric process) and static routes

If you wish to have a more custom build the majority of the settings in the variable files (unless specifically stated) can be changed as none of the scripting or templating logic uses the actual contents (dictionary values) to make decisions.

This deployment will scale up to a maximum of 4 spines, 4 borders and 10 leafs, this is how it will be deployed with the default values.
<p align="center">
    <img width="700" src="https://user-images.githubusercontent.com/33333983/111067948-82520c80-84be-11eb-987f-d9c6ced0ef1e.png">
</p>

The default ports used for inter-switch links are in the table below, these can be changed within *fabric.yml* (*fbc.adv.bse_intf*).

| Connection      | Start Port | End Port |
|-----------------|------------|----------|
| SPINE-to-LEAF   | *Eth1/1*   | *Eth1/10*
| SPINE-to-BORDER | *Eth1/11*  | *Eth1/14*
| LEAF-to-SPINE   | *Eth1/1*   | *Eth1/4*
| BORDER-to-SPINE | *Eth1/1*   | *Eth1/4*
| MLAG Peer-link  | *Eth1/5*   | *Eth1/6*
| MLAG keepalive  | *mgmt*     | *n/a*

This playbook is based on 1U Nexus devices, therefore using the one linecard module for all the connections. I have not tested how it will work with multiple modules, the role *intf_cleanup* is likely not to work. This role ensures interface configuration is declarative by defaulting non-used interfaces, therefore could be excluded without breaking the playbook.

As Python is a lot more flexible than Ansible the dynamic *inventory_plugin* and *filter_plugins* (within the roles) do the manipulating of the data in the variable files to create the data models that are used by the templates. This helps to abstract a lot of the complexity out of the jinja templates making it easier to create new templates for different vendors as you only have to deal with the device configuration rather than data manipulation.

## Fabric Core Variable Elements

These core elements are the minimum requirements to create the declarative fabric. They are used for the dynamic inventory creation as well by the majority of the Jinja2 templates. All variables are proceeded by ***ans***, ***bse*** or ***fbc*** to make it easier to identify within the playbook, roles and templates which variable file the variable came from. From the contents of these *var_files* a dynamic inventory is built containing *host_vars* of the fabric interfaces and IP addresses.

### ansible.yml (ans)

- ***dir_path:*** Base directory location on the Ansible host that stores all the validation and configuration snippets
- ***device_os:*** Operating system of each device type (spine, leaf and border)
- ***creds_all:*** hostname (got from the inventory), username and password

### base.yml (bse)

The settings required to onboard and manage device such as hostname format, IP address ranges, aaa, syslog, etc.

***device_name:*** Naming format that the automatically generated node ID (double decimal format) is added to and the group name created from (in lowercase). The name must contain a hyphen (*-*) and the characters after that hyphen must be either letters, digits or underscore as that is what the group name is created from. For example using *DC1-N9K-SPINE* would mean that the device is *DC1-N9K-SPINE01* and the group is *spine*.

| Key      | Value   | Information  |
|----------|---------|--------------|
| `spine`    | xx-xx | *Spine switch device and group naming format*
| `border`   | xx-xx | *Border switch device and group naming format*
| `leaf`     | xx-xx | *Leaf switch device and group naming format*

***addr:*** Subnets from which the device specific IP addresses are generated based on the *device type increment* and the *node number*. The majority of subnets need to be at least /27 to cover a maximum network size of 4 spines, 10 leafs and 4 borders (18 addresses)

| Key      | Value | Min size     | Information   |
|----------|-------|--------------|---------------|
| `lp_net`           | x.x.x.x/26 | /26 | *The range routing (OSPF/BGP), VTEP and vPC loopbacks are from (mask will be /32)*
| `mgmt_net`         | x.x.x.x/27 | /27 | *Management network, by default will use .11 to .30*
| `mlag_peer_net`    | x.x.x.x/26 | /26 or /27 | *Range for OSPF peering between MLAG pairs, is split into /30 per-switch pair. Must be /26 if using same range for keepalive*
| `mlag_kalive_net`  | x.x.x.x/27 | /27 | *Optional keepalive address range (split into /30). If not set uses mlag_peer_net range*
| `mgmt_gw`          | x.x.x.x    | n/a | *Management interface default gateway*

`mlag_kalive_net` is only needed if not using the management interface for the keepalive or you want separate ranges for the peer-link and keepalive interfaces. The keepalive link is created in its own VRF so it can use duplicate IPs or be kept unique by offsetting it with the `fbc.adv.addr_incre.mlag_kalive_incre` fabric variable.

There are a lot of other system wide settings in *base.yml* such as AAA, NTP, DNS, usernames and management ACLs. Anything under `bse.services` are optional (DNS, logging, NTP, AAA, SNMP, SYSLOG) and will use the management interface and VRF as the source unless specifically set. More detailed information can be found in the variable file.
### fabric.yml (fbc)

Variables used to determine how the fabric will be built, the network size, interfaces, routing protocols and address increments. At a bare minimum you only need to declare the size of fabric, total number of switch ports and the routing options.

***network_size:*** How many of each device type make up the fabric. Can range from 1 spine and 2 leafs up to a maximum of 4 spines, 4 borders and 10 leafs. The border and leaf switches are MLAG pairs so must be in increments of 2.

| Key         | Value | Information  |
|-------------|-------|--------------|
| `num_spines`  | 2   | *Number of spine switches in increments of 1 up to a maximum of 4*
| `num_borders` | 2   | *Number of border switches in increments of 2 up to a maximum of 4*
| `num_leafs`   | 4   | *Number of leaf switches in increments of 2 up to a maximum of 10*

***num_intf:*** The total number of interfaces per-device-type is required to make the interface assignment declarative by ensuring that non-defined interfaces are reset to their default settings

| Key    | Value  | Information |
|--------|--------|-------------|
| `spine`  | 1,64 | *The first and last interface for a spine switch*
| `border` | 1,64 | *The first and last interface for a border switch*
| `leaf`   | 1,64 | *The first and last interface for a leaf switch*

***adv.bse_intf:*** Interface naming formats and the *'seed'* interface numbers used to build the fabric

| Key         | Value          | Information   |
|-------------|----------------|---------------|
| `intf_fmt`    | Ethernet1/   | *Interface naming format*
| `intf_short`  | Eth1/        | *Short interface name used in interface descriptions*
| `mlag_fmt`    | port-channel | *MLAG interface naming format*
| `mlag_short`  | Po           | *Short MLAG interface name used in MLAG interface descriptions*
| `lp_fmt`      | loopback     | *Loopback interface naming format*
| `sp_to_lf`    | 1            | *First interface used for SPINE to LEAF links (1 to 10)*
| `sp_to_bdr`   | 11           | *First interface used for SPINE to BORDER links (11 to 14)*
| `lf_to_sp`    | 1            | *First interface used LEAF to SPINE links (1 to 4)*
| `bdr_to_sp`   | 1            | *First interface used BORDER to SPINE links (1 to 4)*
| `mlag_peer`   | 5-6          | *Interfaces used for the MLAG peer Link*
| `mlag_kalive` | mgmt         | *Interface for the keepalive. If it is not an integer uses the management interface*

***adv.address_incre:*** Increments added to the node ID and subnet to generate unique device IP addresses. Uniqueness is enforced by using different increments for different device-types and functions

| Key               | Value | Information   |
|-------------------|-------|---------------|
| `spine_ip`          | 11  | *Spine mgmt and routing loopback addresses (default .11 to .14)*
| `border_ip`         | 16  | *Border mgmt and routing loopback addresses (default .16 to .19)*
| `leaf_ip`           | 21  | *Leaf mgmt and routing loopback addresses (default .21 to .30)*
| `border_vtep_lp`    | 36  | *Border VTEP (PIP) loopback addresses (default .36 to .39)*
| `leaf_vtep_lp`      | 41  | *Leaf VTEP (PIP) loopback addresses (default .41 to .50)*
| `border_mlag_lp`    | 56  | *Shared MLAG anycast (VIP) loopback addresses for each pair of borders (default .56 to .57)*
| `leaf_mlag_lp`      | 51  | *Shared MLAG anycast (VIP) loopback addresses for each pair of leafs (default .51 to .55)*
| `border_bgw_lp`     | 58  | *Shared BGW MS anycast loopback addresses for each pair of borders (default .58 to .59)*
| `mlag_leaf_ip`      | 1   | *Start IP for leaf OSPF peering over peer-link (default LEAF01 is .1, LEAF02 is .2, LEAF03 is .5, etc)*
| `mlag_border_ip`    | 21  | *Start IP for border OSPF peering over peer-link (default BORDER01 is .21, BORDER03 is .25, etc)*
| `mlag_kalive_incre` | 28  | *Increment added to leaf/border increment (mlag_leaf_ip/mlag_border_ip) for keepalive addresses*

If the management interface is not being used for the keepalive link either specify a separate network range (`bse.addr.mlag_kalive_net`) or use the peer-link range and specify an increment (`mlag_kalive_incre`) that is added to the peer-link increment (`mlag_leaf_ip` or `mlag_border_ip`) to generate unique addresses.

***route:*** Settings related to the fabric routing protocols (OSPF and BGP). BFD is not supported on unnumbered interfaces so the routing protocol timers have been shortened (OSPF 2/8, BGP 3/9), these are set under the advanced settings (`adv.route`)

| Key            | Value&nbsp;                 | Mandatory | Information |
|----------------|-----------------------|-----------|-------------|
| `ospf.pro`       | string or integer | Yes | *Can be numbered or named*
| `ospf.area`      |  x.x.x.x              | Yes | *Area this group of interfaces are in, must be in dotted decimal format*
| `bgp.as_num`     | integer             | Yes | *Local BGP Autonomous System number*
| `authentication` | string              | No  | *Applies to both BGP and OSPF. Hash out if don't want to set authentication*

***acast_gw_mac***: The distributed gateway anycast MAC address for all leaf and border switches in the format `xxxx.xxxx.xxxx`

## Dynamic Inventory

The *ansible*, *base* and *fabric* variables are passed through an *inventory_plugin* to create the dynamic inventory and *host_vars* of all the fabric interfaces and IP addresses. By doing this in the inventory the complexity is abstracted from the *base* and *fabric* role templates making it easier to expand the playbook to other vendors in the future.

With the exception of *intf_mlag* and *mlag_peer_ip* (not on the spines) the following *host_vars* are created for every host.

- **ansible_host:** *Devices management address*
- **ansible_network_os:** *Got from ansible var_file and used by napalm device driver*
- **intf_fbc:** *Dictionary of fabric interfaces with interface the keys and description the values*
- **intf_lp:** *List of dictionaries with keys of name, ip and description*
- **intf_mlag:** *Dictionary of mlag peer-link interfaces with interface the key and description the value*
- **mlag_peer_ip:** *IP of the SVI (default VLAN2) used for the OSPF peering over the MLAG peer-link*
- **num_intf:** *Number of the first and last physical interface on the switch*
- **intf_mlag_kalive:** *Dictionary of MLAG keepalive link interface with interface the key and description the value (only created if defined)*
- **mlag_kalive_ip:** *IP of the keepalive link (only created if defined)*

The devices (*host-vars*) and groups (*group-vars*) created by the inventory plugin can be checked using the `graph` flag. It is the inventory config file (*.yml*) not the inventory plugin (*.py*) that is referenced when using the dynamic inventory.

```python
ansible-inventory --playbook-dir=$(pwd) -i inv_from_vars_cfg.yml --graph
```

```yaml
@all:
  |--@border:
  |  |--DC1-N9K-BORDER01
  |  |--DC1-N9K-BORDER02
  |--@leaf:
  |  |--DC1-N9K-LEAF01
  |  |--DC1-N9K-LEAF02
  |  |--DC1-N9K-LEAF03
  |  |--DC1-N9K-LEAF04
  |--@spine:
  |  |--DC1-N9K-SPINE01
  |  |--DC1-N9K-SPINE02
  |--@ungrouped:
```

`host` shows the host-vars for that specific host whereas `list` shows everything, all *host-vars* and *group-vars*.

```python
ansible-inventory --playbook-dir=$(pwd) -i inv_from_vars_cfg.yml --host DC1-N9K-LEAF01
ansible-inventory --playbook-dir=$(pwd) -i inv_from_vars_cfg.yml --list
```

An example of the *host_vars* created for a leaf switch.

```yaml
{
    "ansible_host": "10.10.108.21",
    "ansible_network_os": "nxos",
    "intf_fbc": {
        "Ethernet1/1": "UPLINK > DC1-N9K-SPINE01 - Eth1/1",
        "Ethernet1/2": "UPLINK > DC1-N9K-SPINE02 - Eth1/1"
    },
    "intf_lp": [
        {
            "descr": "LP > Routing protocol RID and peerings",
            "ip": "192.168.101.21/32",
            "name": "loopback1"
        },
        {
            "descr": "LP > VTEP Tunnels (PIP) and MLAG (VIP)",
            "ip": "192.168.101.41/32",
            "mlag_lp_addr": "192.168.101.51/32",
            "name": "loopback2"
        }
    ],
    "intf_mlag_kalive": {
        "Ethernet1/7": "UPLINK > DC1-N9K-LEAF02 - Eth1/7 < MLAG Keepalive"
    },
    "intf_mlag_peer": {
        "Ethernet1/5": "UPLINK > DC1-N9K-LEAF02 - Eth1/5 < Peer-link",
        "Ethernet1/6": "UPLINK > DC1-N9K-LEAF02 - Eth1/6 < Peer-link",
        "port-channel1": "UPLINK > DC1-N9K-LEAF02 - Po1 < MLAG Peer-link"
    },
    "mlag_kalive_ip": "10.10.10.29/30",
    "mlag_peer_ip": "192.168.202.1/30",
    "num_intf": "1,64"
}
```

To use the inventory plugin in a playbook reference the inventory config file in place of the normal hosts inventory file (`-i`).

```python
ansible-playbook PB_build_fabric.yml -i inv_from_vars_cfg.yml
```

## Services - Tenant (svc_tnt)

Tenants, SVIs, VLANs and VXLANs are created based on the variables stored in the *service_tenant.yml* file (***svc_tnt.tnt***).

***tnt:*** A list of tenants that contains a list of VLANs (Layer2 and/ or Layer3)

- Tenants (VRFs) will only be created on a leaf or border if a VLAN within that tenant is to be created on that device
- Even if a tenant is not a layer3 tenant a VRF will still be created and the L3VNI and tenant VLAN number reserved
- If the tenant is a layer3 tenant the route-map for redistribution is always created and attached to the BGP peer

| Key      | Value&nbsp; | Mandatory | Information |
|----------|-------|-----------|-------------|
| `tenant_name` | string | Yes |  *Name of the VRF* |
| `l3_tenant` | True or False | Yes |  *Does it need SVIs or is routing done off the fabric (i.e external router)* |
| `bgp_redist_tag` | integer | No | *Tag used to redistributed SVIs into BGP, by default uses tenant SVI number* |
| `vlans` |  list | Yes | *List of VLANs within this tenant (see the below table)* |

***vlans:*** A List of VLANs within a tenant which at a minimum need the layer2 values of *name* and *num*. VLANs and SVIs can only be created on all leafs and/ or all borders, you can't selectively say which individual leaf or border switches to create them on

- Unless an IP address is assigned to a VLAN (*ip_addr*) it will only be L2 VLAN
- L3 VLANs are automatically redistributed into BGP. This can be disabled (*ipv4_bgp_redist: False*) on a per-vlan basis
- By default VLANs will only be created on the leaf switches (*create_on_leaf*). This can be changed on a per-vlan basis to create only on borders (*create_on_border*) or on both leafs and borders
- To add a non-VXLAN SVI (without anycast address) create the VLAN as normal but with the extra `VXLAN: False` dictionary. The SVI is defined in *service_interface.yml* as `type: svi`
- Optional settings will implicitly use the default value, they only need defining if not using the default value

| Key      | Value &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | Mand | Information |
|----------|-------|-----------|-------------|
| `num` | integer | Yes | *The VLAN number*
| `name` | string | Yes | *The VLAN name*
| `ip_addr` | x.x.x.x/x | No |  *Adding an IP address automatically making the VLAN L3 (not set by default)*
| `ipv4_bgp_redist` | True or False | No | *Dictates whether the SVI is redistributed into VRF BGP addr family (default True)*
| `create_on_leaf` | True or False | No | *Dictates whether this VLAN is created on the leafs (default True)*
| `create_on_border` | True or False | No | *Dictates whether this VLAN is created on the borders (default False)*
| `vxlan` | True or False | No | *Whether VXLAN or normal VLAN. Only need if don't want it to be a VXLAN*

The redistribution route-map name can be changed in the advanced (*adv*) section of *services-tenant.yml* or *services-routing.yml*. If defined in both places the setting in *services-routing.yml* take precedence.

### L2VNI and L3VNI numbers

The L2VNI and L3VNI values are automatically derived and incremented on a per-tenant basis based on the *start* and *increment* seed values defined in the advanced section (*svc_tnt.adv*) of *services_tenant.yml*.

***adv.bse_vni:*** Starting VNI numbers

| Key      | Value | Information |
|----------|-------|-------------|
| `tnt_vlan` | 3001 | *Starting VLAN number for the transit L3VNI*
| `l3vni` | 10003001 | *Starting L3VNI number*
| `l2vni` | 10000 | *Starting L2VNI number, the VLAN number will be added to this*

***adv.vni_incre:*** Number by which VNIs are incremented for each tenant

| Key      | Value | Information |
|----------|-------|-------------|
| `tnt_vlan` | 1 | *Value by which the transit L3VNI VLAN number is increased for each tenant*
| `l3vni` | 1 | *Value by which the transit L3VNI VNI number is increased for each tenant*
| `l2vni` | 10000 | *Value by which the L2VNI range (range + vlan) is increased for each tenant*

For example a two tenant fabric each with a VLAN 20 using the above values would have L3 tenant SVIs of *3001, 3002*, L3VNIs or *10003001, 10003002* and L2VNIs of *10020* and *20020*.

A new data-model is created from the *services_tenant.yml* variables by passing these through the ***format_dm.py*** filter_plugin method ***create_svc_tnt_dm*** along with the BGP route-map name (if exists) and ASN (from fabric.yml). The result is a per-device-type (leaf and border) list of tenants, SVIs and VLANs which are used to render the ***svc_tnt_tmpl.j2*** template and create the config snippet.

Below is an example of the data model format for a tenant and its VLANs.

```yaml
{
    "bgp_redist_tag": 99,
    "l3_tnt": true,
    "l3vni": 100003004,
    "rm_name": "RM_CONN->BGP65001_RED",
    "tnt_name": "RED",
    "tnt_redist": true,
    "tnt_vlan": 3004,
    "vlans": [
        {
            "create_on_border": true,
            "create_on_leaf": false,
            "ip_addr": "10.99.99.1/24",
            "ipv4_bgp_redist": true,
            "name": "red_inet_vl99",
            "num": 99,
            "vni": 40099
        },
        {
            "ip_addr": "l3_vni",
            "ipv4_bgp_redist": false,
            "name": "RED_L3VNI",
            "num": 3004,
            "vni": 100003004
        }
    ]
}
```

## Services - Interface (svc_intf)

The *service_interface.yml* variables define single or dual-homed interfaces (including port-channel) either statically or dynamically.

- By default all interfaces are dual-homed LACP *'active'*. The VPC number can not be changed, is always the port-channel number
- Interfaces and port-channels can be assigned dynamically from a pre-defined pool (under *svc_intf.adv*) or specified manually
- If the tenant (VRF) is not defined for a layer3, SVI or loopback interface it will be created in the global routing table
- If the interface config is the same across multiple switches (like an access port) define one interface with a list of switches
- Only specify the odd numbered switch for *dual-homed* interfaces, the config for MLAG neighbor is automatically generate

There are 7 pre-defined interface types that can be deployed:

- **access:** *A single VLAN layer2 access port with STP is set to 'edge'*
- **stp_trunk:** *A trunk going to a device that supports Bridge Assurance. STP is set to 'network'*
- **stp_trunk_non_ba:** *Same as stp_trunk except that STP is set to 'normal' as it is for devices that don't support BA*
- **non_stp_trunk:** *A trunk port going to a device that doesn't support BPDU. STP is set to 'edge' and BPDU Guard enabled*
- **layer3:** *A layer3 interface with an IP address. Must be single-homed as MLAG not supported for L3 interfaces*
- **loopback:** *A loopback interface with an IP address (must be single-homed)*
- **svi:** *To define a SVI the VLAN must exist in service_tenant.yml and not be a VXLAN (must be single-homed)*

The ***intf.single_homed*** and ***intf.dual-homed*** dictionaries both hold a list of all single-homed or dual-homed interfaces using any of the attributes in the table below. If there are no single-homed or dual-homed interfaces on the fabric hash out the relevant dictionary.

| Key        | Value   | Mand  | Information |
|------------|---------|-------------|-------------|
| `descr` | string | Yes | *Interface or port-channel description*
| `type` | intf_type | Yes | *Either access, stp_trunk, stp_trunk_non_ba, non_stp_trunk, layer3, loopback or svi*
| `ip_vlan` | vlan or ip | Yes | *Depends on the type, either ip/prefix, vlan or multiple vlans separated by , and/or -*
| `switch`  | list | Yes | *List of switches created on. If dual-homed needs to be odd numbered switch from MLAG pair*
| `tenant` | string | No | *Layer3, svi and loopbacks only. If not defined the default VRF is used (global routing table)*
| `po_mbr_descr` | list | No | *PO member interface description, [odd_switch, even_switch]. If undefined uses PO descr*
| `po_mode` | string | No | *Set the Port-channel mode, 'on', 'passive' or 'active' (default is 'active')*
| `intf_num` | integer | No | *Only specify the number, the name and module are got from the fbc.adv.bse_intf.intf_fmt*
| `po_num` | integer | No | *Only specify the number, the name is got from the fbc.adv.bse_intf.mlag_fmt*

The playbook has the logic to recognize if statically defined interface numbers overlap with the dynamic interface range and exclude them from dynamic interface assignment. For simplicity it is probably best to use separate ranges for the dynamic and static assignments.

***adv.single_homed:*** Reserved range of interfaces to be used for dynamic single-homed and loopback assignment

| Key        | Value      | Information |
|------------|------------|-------------|
| `first_intf` | integer | *First single-homed interface to be dynamically assigned*
| `last_intf`  | integer | *Last single-homed interface to be dynamically assigned*
| `first_lp`   | integer | *First loopback number to be dynamically used*
| `last_lp`    | integer | *Last loopback number to be dynamically used*

***adv.dual-homed:*** Reserved range of interfaces to be used for dynamic dual-homed and port-channel assignment

| Key        | Value      | Information  |
|------------|------------|--------------|
| `first_intf` | integer | *First dual-homed interface to be dynamically assigned*
| `last_intf`  | integer | *Last dual-homed interface to be dynamically assigned*
| `first_po`   | integer | *First port-channel number to be dynamically used*
| `last_po`    | integer | *Last port-channel number to be dynamically used*

The ***format_dm.py*** filter_plugin method ***create_svc_intf_dm*** is run for each inventory device to produce a list of all interfaces to be created on that device. In addition to the *services_interface.yml* variables it also passes in the interface naming format (*fbc.adv.bse_intf*) to create the full interface name and *hostname* to find the interfaces relevant to that device. This is saved to the fact *flt_svc_intf* which is used to render the ***svc_intf_tmpl.j2*** template and create the config snippet.

Below is an example of the data model format for a single-homed and dual-homed interface.

```yaml
{
    "descr": "UPLINK > DC1-BIP-LB01 - Eth1.1",
    "dual_homed": false,
    "intf_num": "Ethernet1/9",
    "ip_vlan": 30,
    "stp": "edge",
    "type": "access"
},
{
    "descr": "UPLINK > DC1-SWI-BLU01 - Gi0/0",
    "dual_homed": true,
    "intf_num": "Ethernet1/18",
    "ip_vlan": "10,20,30",
    "po_mode": "on",
    "po_num": 18,
    "stp": "network",
    "type": "stp_trunk"
},
{
    "descr": "UPLINK > DC1-SWI-BLU01 - Po18",
    "intf_num": "port-channel18",
    "ip_vlan": "10,20,30",
    "stp": "network",
    "type": "stp_trunk",
    "vpc_num": 18
}
```

## Interface Cleanup - Defaulting Interfaces

The interface cleanup role is required to make sure any interfaces not assigned by the fabric or the services (svc_intf) role have a default configuration. Without this if an interface was to be changed (for example a server moved to a different interface) the old interface would not have its configuration put back to the default values.

This role goes through the interfaces assigned by the *fabric* (from the inventory) and *service_interface* role (from the *svc_intf_dm* method) producing a list of used physical interfaces which are then subtracted from the list of all the switches physical interfaces (*fbc.num_intf*). It has to be run after the *fabric* or *service_interface* role as it needs to know what interfaces have been assigned, therefore uses tags to ensure it is run anytime either of these roles are run.

## Services - Route (svc_rte)

BGP peerings, non-backbone OSPF processes, static routes and redistribution (connected, static, bgp, ospf) are configured based on the variables specified in the *service_route.yml* file. The naming convention of the route-maps and prefix-lists used by OSPF and BGP can be changed under the advanced section (*adv*) of the variable file.

I am undecided about this role as it goes against the simplistic principles used by the other roles. By its very nature routing is very configurable which leads to complexity due to the number of options and inheritance. In theory all these features should work but due to the number of options and combinations available I have not tested all the possible variations of configuration.

### Static routes (svc_rte.static_route)

Routes are added per-tenant with the tenant being the top-level dictionary that routes are created under.

- *tenant*, *switch* and *prefix* are lists to make it easy to apply the same routes across multiple devices and tenants
- For routes with the same attributes (like next-hop) can group all the routes as a list within the one `prefix` dictionary key
- Can optionally set next-hop interface, administrative distance and the next hop VRF (for route leaking between VRFs)

| Parent dict  | Key           | Value      | Mand | Information |
|--------------|---------------|------------|------|-------------|
| n/a | `tenant`       | list     | Yes | *List of tenants to create the routes in. Use 'global' for the global routing table*
| n/a | `switch`       | list     | Yes | *List of switches to create all routes on (alternatively can be set per-route)*
| route        | `prefix`       | list     | Yes | *List of routes that all have same settings (gateway, interface, switch, etc)*
| route        | `gateway`      | x.x.x.x    | Yes | *Next hop gateway address*
| route        | `interface`    | string   | No  | *Next hop interface, use interface full name (Ethernet), Vlan or Null0*
| route        | `ad`           | integer | No  | *Set the administrative distance for this group of routes (1 - 255)*
| route        | `next_hop_vrf` | string   | No  | *Set the VRF for next-hop if it is in a different VRF (route leaking between VRFs)*
| route        | `switch`       | list     | Yes | *Switches to create this group of routes on (overrides static_route.switch)*

### OSPF (svc_rte.ospf)

An OSPF processes can be configured for any of the tenants or the global routing table.

- Each OSPF process is enabled on a per-interface basis with summarization and redistribution defined on a per-switch basis
- The mandatory `process.switch` list defines the switches the OSPF process is configured on
- Non-mandatory settings only need to be defined if changing the default behavior, otherwise is no need to add the dictionary

| Key      | Value            | Mandatory | Information |
|----------|-----------------|-----------|-------------|
| `process` | integer or string | Yes | *The process can be a number or word*
| `switch` | list | Yes | *List of switches to create the OSPF process on*
| `tenant` | string | No | *The VRF OSPF is enabled in. If not defined uses the global routing table*
| `rid` | list | No | *List of RIDs, must match number of switches (if undefined uses highest loopback)*
| `bfd` | True | No | *Enable BFD globally for all interfaces (disabled by default)*
| `default_orig` | True, always | No | *Conditionally (True) or always advertise a default route (disabled by default)*

*Interface*, *summary* and *redistribution* are child dictionaries of lists under the *ospf* parent dictionary. They inherit `process.switch` unless `switch` is specifically defined under that child dictionary.

***ospf.interface:***  Each list element is a group of interfaces with the same set of attributes (area number, interface type, auth, etc)

| Key      | Value&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | Mandatory | Information |
|----------|-------|-----------|-------------|
| `name` | list | Yes | *List of one or more interfaces. Use interface full name (Ethernet) or Vlan*
| `area` | x.x.x.x | Yes | *Area this group of interfaces are in, must be in dotted decimal format*
| `switch` | list | No | *On which switches to enable OSPF on these interfaces (inherits process.switch if not set)*
| `cost` | integer | No | *Statically set the interfaces OSPF cost, can be 1-65535*
| `authentication` | string | No | *Enable authentication for the area and a password (Cisco type 7) for this interface*
| `area_type` | string | No | *By default is normal. Can be set to stub, nssa, stub/nssa no-summary, nssa default-information-originate or nssa no-redistribution*
| `passive` | True | No | *Make the interface passive. By default all configured interfaces are non-passive*
| `hello` | integer | No | *Interface hello interval (deadtime is x4), automatically disables BFD for this interface*
| `type` | point-to-point | No | *By default all interfaces are broadcast, can be changed to point-to-point*

***ospf.summary:*** All summaries with the same attributes (*switch*, *filter*, *area*) can be grouped in a list within the one `prefix` dictionary key

| Key      | Value | Mandatory | Information |
|----------|-------|-----------|-------------|
| `prefix` | list | Yes | *List of summaries to apply on all the specified switches*
| `switch` | list | No | *What switches to summarize on, inherits process.switch if not set*
| `area` | x.x.x.x | No | *By default it is LSA5. For LSA3 add an area to summarize from that area*
| `filter` | not-advertise | No | *Stops advertisement of the summary and subordinate subnets (is basically filtering)*

***ospf.redist:***: Each list element is the redistribution type (*ospf_xx*, *bgp_xx*, *static* or *connected*). Redistributed prefixes can be filtered (*allow*) or weighted (*metric*) with the route-map order being metric and then allow. If the allow list is not set it will allow any (empty route-map)

| Key      | Value | Mandatory | Information |
|----------|-------|-----------|-------------|
| `type` | string | Yes | *Redistribute either OSPF process, BGP AS (whitespace before process or AS), static or connected*
| `switch` | list | No | *What switches to redistribute on, inherits process.switch if not set*
| `metric` | dict | No | *Add metric to redistributed prefixes. Keys are metric value and values a list of prefixes or keyword ('any' or 'default'). Can't use metric with a type of connected*
| `allow` | list,any,default | No | *List of prefixes (connected is list of interfaces) or keyword ('any' or 'default') to redistribute*

### BGP

Uses the concept of *groups* and *peers* with the majority of the settings configured in either. Peer settings take precedence over group.

- `group` holds the global settings for all peers within it. Are automatically created on any switches that peers within it are created
- `peer` is a list of peers within the group. If the setting is configured in the group and peer the peer setting will take precedence
- The `group.name` and `peer.name` are used in the construction of route-map and prefix-list names (formatting is in advanced)
- If the tenant is not specified (dictionary not defined) the group or peer will be added to the default global routing table
- Non-mandatory settings only need to be defined if changing the default behavior, otherwise is no need to add the dictionary

| Set in  | Key      | Value     | Mandatory | Information |
|-------|----------|------------|-----------|-------------|
| group | `name` | string | Yes | *Name of the group, no whitespaces or duplicate names (group or peer)*
| peer | `name` | string |  Yes | *Name of the peer, no whitespaces or duplicate names (group or peer)*
| peer | `peer_ip` | x.x.x.x |  Yes | *IP address of the peer*
| peer | `descr` | string |  Yes | *Description of the peer*
| both | `switch` | list |  Yes | *List of switches (even if is only 1) to create the group and peers on*
| both | `tenant` | list |  No | *List of tenants (even if is only 1) to create the peers under*
| both | `remote_as` | integer | Yes | *Remote AS of this peer or if group all peers within that group*
| both | `timers` | [klv, htm] | No | *List of [keepalive, holdtime], if  not defined uses [3, 9] seconds*
| both | `bfd` | True | No | *Enable BFD for an individual peer or all peers in group (disabled by default)*
| both | `password` | string | No | *Plain-text password to authenticate a peer or all peers in group (default none)*
| both | `default` | True | No | *Advertise default route to a peer or all peers in the group (default False)*
| both | `update_source` | string | No | *Set the source interface used for peerings (default not set)*
| both | `ebgp_multihop` | integer | No | *Increase the number of hops for eBGP peerings (2 to 255)*
| both | `next_hop_self` | True | No | *Set the next-hop to itself for any advertised prefixes (default not set)*

***inbound*** or ***outbound:*** Can be optionally set under group or peer to filter BGP advertisements and/ or BGP attribute manipulation

- The naming of the route-maps and prefix-lists are dependant on where they are applied (group or peer)
- All attribute settings are dictionaries with the key being the attribute and the value the prefixes it is applied to

| Key      | Value | Direction |Information |
|----------|-------|-------|-------------|
| `weight` | dict | inbound | *Keys are the weight and the value a list of prefixes or keyword ('any' or 'default')*
| `pref` | dict | inbound | *Keys are the local preference and the value a list of prefixes or keyword*
| `med` | dict | outbound | *Keys are the MED value and the values a list of prefixes or keyword*
| `as_prepend` | dict | outbound | *Keys are the number of times to add the ASN and values a list of prefixes or keyword*
| `allow` | list, any, default | both | *Can be a list of prefixes or a keyword to advertise just the default route or anything*
| `deny` | list, any, default | both | *Can be a list of prefixes or a keyword to not advertise the default route or anything*

***bgp.tnt_advertise:*** Optionally advertise prefixes on a per-tenant basis (list of VRFs) using network, summary and redistribution. The `switch` can be set globally for all network/summary/redist in a VRF and be overridden on an individual per-prefix basis

- ***network:*** List of prefixes to be advertised on a per-switch basis (*network* cmd). If a device is covered by 2 different *network.prefix* statements it will get a combination of them both (merged), so *network* statements for all prefixes
- ***summary:*** Group summaries (*aggregate-address*) with the same attributes (*switch* and *summary_only*) within the same list element
- ***redist:*** Each list element is the redistribution type (*ospf process*, *static* or *connected*) with the redistributed prefixes weighted (*metric*) and/or filtered (*allow*). If the allow list is not set it is allow any (empty route-map). Can only have one each of *connected* and *static* per-switch, first occurrence is used. The switch set under the redistribution type is preferred over that set in *process.switch*, is no merging

| Set in          | Key    | Value    | Mand | Information |
|-----------------|--------|----------|-----------|-------------|
| tnt_advertise   | `name`   | string | Yes  | *A single VRF that is being advertising into (use 'global' for global routing table)*
| all             | `switch` | list   | Yes  | *What switches to redistribute on, inherits process.switch if not set*
| network/summary | `prefix` | list   | Yes  | *List of prefixes to advertise*
| summary         | `filter` | summary-only | No | *Only advertise the summary, suppress all prefixes within it (disabled by default)*
| redist          | `type`   | string | Yes | *Redistribute ospf_process (whitespace before process), static or connected*
| redist          | `metric` | dict | No | *Add metric to redistributed prefixes. Keys are the MED value and values a list of prefixes or keyword ('any' or 'default'). Cant use metric with connected*
| redist          | `allow`  | list, any, default | No | *List of prefixes (can use 'ge' and/or 'le'), interfaces (for connected) or keyword ('any' or 'default') to redistribute. Placed after the metric in the RM sequence*

Advanced settings (*svc_rte.adv*) allow the changing of the default routing protocol timers and naming convention of the route-maps and prefix-lists used for advertisement and redistribution.

The filter_plugin method ***create_svc_rte_dm*** is run for each inventory device to produce a data model of the routing configuration for that device. The outcome is a list of seven per-device data models that are used by the *svc_rte_tmpl.j2* template.

- **all_pfx_lst**: *List of all prefix-lists with each element in the format [name, seq, permission, prefix]*
- **all_rm**: *List of all route-maps with each element in the format [name, seq, permission, prefix, [attribute, value]]. If no BGP attributes are set in the RM the last entry in the list will be [null, null]*
- **stc_rte:** *Per-VRF dictionaries (VRF is the key) of lists of static routes with interface and/or gateway, optional AD and destination VRF*
- **group:** *Dictionaries of BGP groups (group is the key) that have peers on this device. The value is dictionaries of any group settings*
- **peer:** *Dictionaries of tenants (VRFs) containing the following nested dictionaries:*
  - ***peers:*** *Dictionary of peers (key is the peer) with the value being dictionaries of the peers settings*
  - ***network:*** *List of networks to be advertised by BGP*
  - ***summary:*** *Dictionary of summaries with the key being the prefix and value either null (doesn't suppress) or summary-only*
  - ***redist:*** *Two dictionaries of the route-map name (rm_name) and redistribution type (connected, static, etc)*
- **ospf_proc:** *Dictionary of VRFs (key) and the OSPF process settings for each VRF (settings configured under the process)*
- **ospf_intf:** *Dictionary of interfaces (key) that have OSPF enabled, the values are the interface specific OSPF settings*

## Passwords

There are four main types of passwords used within the playbooks.

- BGP/OSPF: In the variable file it is in as plain text but in the device running configuration is encrypted
- Users: Has to be in encrypted format (type-5) in the variable file
- TACACS: Has to be in the encrypted format (type-7) in the variable. Could use type-6 but would also need to generate a master key
- device: The password used by Napalm to log into devices defined under `ans.creds_all`. Can be plain-text or use vault

## Input validation

Pre-task input validation checks are run on the variable files with the goal being to highlight any problems with variable before any of the fabric build tasks are started. *Fail fast based on logic rather failing halfway through a build*. Pre-validation checks for things such as missing mandatory variables, variables are of the correct type (str, int, list, dict), IP addresses are valid, duplicate entires, dependencies (VLANs assigned but not created), etc. It wont catch everything but will eliminate a lot of the needless errors that would break a fabric build.

A combination of *Python assert* within a filter plugin (to identify any issues) and *Ansible assert* within the playbook (to return user-friendly information) is used to achieve the validation. All the error messages returned by input validation start with the nested location of the variable to make it easier to find.

It is run using the `pre_val' tag and will conditionally only check variable files that have been defined under *var_files*. It can be run using the inventory plugin but will fail if any of the values used to create inventory are wrong so better use a dummy host file.

```none
ansible-playbook playbook.yml -i hosts --tag pre_val
ansible-playbook playbook.yml -i inv_from_vars_cfg.yml --tag pre_val
```

A full list of what variables are checked and the expected input can be found in the header notes of the filter plugin ***input_validate.py***.

## Playbook Structure

The main playbook (***PB_build_fabric.yml***) is divided into 3 sections with roles used to do the data manipulation and templating

- **pre_tasks:** Pre-validation checks and deletion/creation of file structure (at each playbook run) to store config snippets
- **tasks:** Imports tasks from roles which in turn use variables (*.yml*) and templates (*.j2*) to create the config snippets
  - ***base:*** From *base.yml* and *bse_tmpl.j2* creates the base configuration snippet (aaa, logging, mgmt, ntp, etc)
  - ***fabric:*** From *fabric.yml* and *fbc_tmpl.j2* creates the fabric configuration snippet (interfaces, OSPF, BGP)
  - ***services:*** Per-service-type *tasks*, templates and plugins (create data models) to create the config for services that run on the fabric
    - ***svc_tnt:*** From *services_tenant.yml* and *svc_tnt_tmpl.j2* creates the tenant config snippet (VRF, SVI, VXLAN, VLAN)
    - ***svc_intf:*** From *services_interface.yml* and *svc_intf_tmpl.j2* creates interface config snippet (routed, access, trunk, loop)
    - ***svc_rte:*** From *service_route.yml* and *svc_rte_tmpl.j2* creates the tenant routing config snippet (BGP, OSPF, routes, redist)
  - ***intf_cleanup:*** Based on the interfaces used in the fabric creates config snippet to default all the other interfaces
- **task_config:** Assembles the config snippets into the one file and applies using Napalm replace_config

The post-validation playbook (***PB_post_validate.yml****) uses the validation role to do the majority of the work

- **pre_tasks:** Creates the file structure to store validation files (*desired_state*) and the compliance report
- **roles:** Imports the *services* role so that the filter plugins within it can be used to create the service data models for validation
- **tasks:** Imports tasks from roles and checks the compliance report result
  - ***validation:*** Per-validation engine *tasks* to create *desired_state*, gather the *actual_state* and produce a compliance report
    - ***nap_val***: For elements covered by *napalm_getters* creates *desired_state* and compares against *actual_state*
    - ***cus_val***: For elements not covered by *napalm_getters* creates *desired_state* and compares against *actual_state*
  - ***compliance_report:*** Loads validation report (created by *nap_val* and *cus_val*) and checks whether it complies (passed)

## Directory Structure

The directory structure is created within *~/device_configs* to hold the configuration snippets, output (diff) from applied changes, validation *desired_state* files and compliance reports. The parent directory is deleted and re-added at each playbook run.\
The base location for this directory can be changed using the `ans.dir_path` variable.

```none
~/device_configs/
├── DC1-N9K-BORDER01
│   ├── config
│   │   ├── base.conf
│   │   ├── config.cfg
│   │   ├── dflt_intf.conf
│   │   ├── fabric.conf
│   │   ├── svc_intf.conf
│   │   ├── svc_rte.conf
│   │   └── svc_tnt.conf
│   └── validate
│       ├── napalm_desired_state.yml
│       └── nxos_desired_state.yml
├── diff
│   ├── DC1-N9K-BORDER01.txt
└── reports
    ├── DC1-N9K-BORDER01_compliance_report.json
```

## Prerequisites

The deployment has been tested on `NXOS 9.3(5)` using `ansible 2.10.6` and `Python 3.6.9`. To set up the environment follow the below steps, once all packages are installed run `napalm-ansible` to get the location of the *napalm-ansible* paths and add these to *ansible.cfg* under *[defaults]*.

```bash
git clone https://github.com/sjhloco/build_fabric.git
mkdir ~/venv/venv_ansible2.10
python3 -m venv ~/venv/venv_ansible2.10
source ~/venv/venv_ansible2.10/bin/activate
pip install -r build_fabric/requirements.txt
```

Before any configuration can be deployed using Ansible a few things need to be manually configured on all devices:

- Management IP address and default route
- The features *nxapi* and *scp-server* are required for Naplam *replace_config*
- Image validation can take a while on NXOS so is best to be done so beforehand

```none
interface mgmt0
  ip address 10.10.108.11/24
vrf context management
  ip route 0.0.0.0/0 10.10.108.1
feature nxapi
feature scp-server
boot nxos bootflash:/nxos.9.3.5.bin sup-1
```

- Leaf and border switches also need the TCAM allocation changed to allow for *arp-suppression*. This can differ dependant on device model, any changes made need correcting in `/roles/base/templates/nxos/bse_tmpl.j2` to keep it idempotent.

```none
hardware access-list tcam region racl 512
hardware access-list tcam region arp-ether 256 double-wide
copy run start
reload
```

The default username/password for all devices is *admin/ansible* and is stored in the variable `bse.users.password`. Swap this out for the encrypted as *type5* password from the running config. The username and password used by Napalm to connect to devices is stored in `ans.creds_all` and will also need changing (plain-text so use vault).

Before the playbook can be run the devices SSH keys need adding on the Ansible host. *ssh_key_playbook.yml* (in *ssh_keys* directory) can be run to add these automatically, you just need to populate the device`s management IPs in the *ssh_hosts* file.

```bash
sudo apt install ssh-keyscan
ansible-playbook ssh_keys/ssh_key_add.yml -i ssh_keys/ssh_hosts
```

## Running playbook

The device configuration is applied using Napalm with the differences always saved to file (*/device_configs/diff*) and optionally printed to screen. Napalm *commit_changes* is set to *True* meaning that Ansible *check-mode* is used for *dry-runs*. It can take 3 to 4 minutes to deploy the full configuration when including the service roles so the Napalm default timeout has been increased to 240 seconds.

Due to the declarative nature of the playbook and inheritance between roles there are only a certain number of combinations that the roles can be deployed in.

| Ansible tag    | Playbook action |
|----------------|-------------|
| `pre_val`      | Checks that the var_file contents are of a valid format
| `bse_fbc`      | Generates, joins and applies the *base*, *fabric* and *inft_cleanup* config snippets
| `bse_fbc_tnt`  | Generates, joins and applies the *base*, *fabric*, *inft_cleanup* and *tenant* config snippets
| `bse_fbc_intf` | Generates, joins and applies the *base*, *fabric*, *tenant*, *interface* and *inft_cleanup* config snippets
| `full`         | Generates, joins and applies the *base*, *fabric*, *tenant*, *interface*, *inft_cleanup* and *route* config snippets
| `rb`           | Reverses the last applied changes by deploying the rollback configuration (*rollback_config.txt*)
| `diff`         | Prints the differences to screen (is also saved to file)

- ***diff*** tag can be used with *bse_fbc_tnt*, *bse_fbc_intf*, *full* or *rb* to print the configuration changes to screen
- Changes are always saved to file no matter whether *diff* is used or not
- ***-C*** or ***--check-mode*** will do everything except actually apply the configuration

***pre-validation:*** Validates the contents of variable files defined under *var_files*. Best to use dummy host file instead of dynamic inventory\
`ansible-playbook PB_build_fabric.yml -i hosts --tag post_val`

***Generate the complete config:*** Creates the config snippets and compares against what is on the device to see what will be changed\
`ansible-playbook PB_build_fabric.yml -i inv_from_vars_cfg.yml --tag 'full, diff' -C`

***Apply the config:*** Replaces current config on the device, the output is by default automatically saved to */device_configs/diff*\
`ansible-playbook PB_build_fabric.yml -i inv_from_vars_cfg.yml --tag full`

All roles can be deployed individually to just to create the config snippet files, so no connections are made to devices or changes applied./
The `merge` tag can be used with any of to deploy the config snippet to merge rather than replace the configuration non-declaratively. As the L3VNIs and interfaces are generated automatically the variable files still need at a bare minimum current tenants and interfaces as well as the advanced variable sections.

| Ansible tag | Playbook action |
|-------------|-------------|
| `bse`       | Generates the base configuration snippet saved to *device_name/config/base.conf*
| `fbc`       | Generates the fabric and intf_cleanup configuration snippets saved to *fabric.conf* and *dflt_intf.conf*
| `tnt`       | Generates the tenant configuration snippet saved to *device_name/config/svc_tnt.conf*
| `intf`      | Generates the interface configuration snippet saved to *device_name/config/svc_intf.conf*
| `rte`       | Generates the route configuration snippet saved to *device_name/config/svc_rte.conf*
| `merge`     | Non-declaratively merges the new and current config, can be run with any combination of role tags

***Generate the fabric config:*** Creates the fabric and interface cleanup config snippets and saves them to *fabric.conf* and *dflt_intf.conf*\
`ansible-playbook PB_build_fabric.yml -i inv_from_vars_cfg.yml --tag fbc`

***Apply tenants and interfaces non-declaratively:*** Adds additional tenant and routing objects by merging with the current config. The diffs for merges are simply the lines in the merge candidate config, therefore these wont be as true as the diffs from declerative deployments\
`ansible-playbook PB_build_fabric.yml -i inv_from_vars_cfg.yml --tag tnt,rte,merge,diff`

## Post Validation checks

A declaration of how the fabric should be built (desired_state) is created from the values of the variables files and validated against the actual_state. *napalm_validate* can only perform a compliance check against anything it has a getter for, for anything not covered by this the *custom_validate* filter plugin is used. This plugin uses the same *napalm_validate* framework but the actual state is supplied through a static input file (got using *napalm_cli*) rather than a getter.

The results of the napalm_validate (*nap_val.yml*) and custom_validate (*cus_val.yml*) tasks are joined together to create the one combined compliance report. Each getter or command has a *complies* dictionary (True or False) to report its state which feeds into the compliance reports overall *complies* dictionary. It is based on this value that a task in the post-validation playbook will raise an exception.

### napalm_validate

As Napalm is vendor agnostic the jinja template file used to create the validation file is the same for all vendors. The following elements are validated by *napalm_validate* with the roles being validated in brackets.

- ***hostname*** *(fbc): Automatically created device names are correct*
- ***lldp_neighbors*** *(fbc): Devices physical fabric and MLAG connections are correct*
- ***bgp_neighbors*** *(fbc, tnt): Overlay neighbors are all up (strict). fbc doesn't check for sent/rcv prefixes, this is done by tnt*

An example of the desired and actual state file formats.

```yaml
- get_bgp_neighbors:
    global:
      router_id: 192.168.101.16
      peers:
        _mode: strict
        192.168.101.11:
          is_enabled: true
          is_up: true
```

### custom_validate

*custom_validate* requires a per-OS type template file and per-OS type method within the ***custom_validate.py*** filter_plugin. The command output is collected in JSON format using *naplam_cli*, passed through the ***nxos_dm*** method to create a new *actual_state* data model and along with the *desired_state* is fed into napalm_validate using the *compliance_report* method.

The following elements are validated by *napalm_validate* with the roles being validated in brackets.

- ***show ip ospf neighbors detail*** *(fbc): Underlay neighbors are all up (strict)*
- ***show port-channel summary*** *(fbc, intf): Port-channel state and members (strict) are up*
- ***show vpc*** *(fbc, tnt, intf): MLAG peer-link, keep-alive state, vpc status and active VLANs*
- ***show interfaces trunk*** *(fbc, tnt, intf): Allowed vlans and STP forwarding vlans*
- ***show ip int brief include-secondary vrf all*** *(fbc, tnt, intf): Layer3 interfaces in fabric and tenants*
- ***show nve peers*** *(tnt): All VTEP tunnels are up*
- ***show nve vni*** *(tnt): All VNIs are up, have correct VNI number and VLAN mapping*
- ***show interface status*** *(intf): State and port type*
- ***show ip ospf interface brief vrf all*** *(rte):* *Tenant OSPF interfaces are in correct process, area and are up*
- ***show bgp vrf all ipv4 unicast*** *(rte):* *Prefixes advertised by network and summary are in the BGP table*
- ***show ip route vrf all*** *(rte):* *Static routes are in the routing table with correct gateway and AD*

An example of the desired and actual state file formats

```yaml
cmds:
  - show ip ospf neighbors detail:
      192.168.101.11:
        state: FULL
      192.168.101.12:
        state: FULL
      192.168.101.22:
        state: FULL
```

To aid with creating new validations the ***custom_val_builder*** directory is a stripped down version of custom_validate to use when building new validations. The README has more detail on how to run it, the idea being to walk through each stage of creating the desired and actual state ready to add to the validate roles.

### Running Post-validation

Post-validation is hierarchial as the addition of elements in the later roles effects the validation outputs in the earlier roles. For example, extra VLANs added in tenant_service will effect the bse_fbc post-validate output of *show vpc* (peer-link_vlans). For this reason post-validation must be run for the current role and all applied roles before it. This is done automatically by Jinja template inheritance as calling a template with the *extends* statement will also render the inheriting templates.

| Ansible tag | Playbook action |
|-------------|-------------|
| `fbc_bse`   | Validates the configuration applied by the *base* and *fabric* roles
| `tnt`       | Validates the configuration applied by the *base*, *fabric* and *tenant* roles
| `intf`      | Validates the configuration applied by the *base*, *fabric*, *tenant* and *interfaces* roles
| `full`      | Validates the configuration applied by the *base*, *fabric*, *tenant*, *interfaces* and *route* roles

***Run fabric validation:*** Runs validation against the *desired state* got from all the variable files. There is no differentiation between *naplam_validate* and *custom_validate*, both are run as part of the validation tasks\
`ansible-playbook PB_post_validate.yml -i inv_from_vars_cfg.yml --tag full`

***Viewing compliance report:*** Viewing the whole validation report\
`cat ~/device_configs/reports/DC1-N9K-SPINE01_compliance_report.json | python -m json.tool`

## Caveats

When staring this project I used N9Kvs on EVE-NG and later on then moved onto physical devices when we were deploying the data centers. vPC fabric peering does not work on the virtual devices so this was never added as an option in the playbook.

As deployments are declarative and there are differences with physical devices you will need a few minor tweaks to the *bse_tmpl.j2* template as different hardware can have slightly different base commands. The `system nve infra-vlans` command is required for infrastructure VLANs (OSPF over vPC peer link VLAN) and to run VLXAN over a VLAN but is not supported on N9Kv. For physical devices this line needs unhashing at the starte of *bse_tmpl.j2*.

```jinja
{# system nve infra-vlans {{ fbc.adv.mlag.peer_vlan }} #}
```

EVE-NG is not perfect for running N9Ks. I originally started on `9.2.4` and although it is fairly stable in terms of features and uptime, the API can be very slow at times and take upto 10 minuets ot deploy. Sometimes after a deployment the API would stop responding (couldn`t telnet on 443) but NXOS said it was listening. To fix this you had disable and re-enable the feature nxapi. Removing the command 'nxapi use-vrf management' helps to make this more stable.

I next moved to NXOS `9.3.5` and although the API is consitantly more stable and faster, it has a strange issue around the interface module. When the N9Kv went to 9.3 the interfaces where moved to a separate module, module 1.

```none
Mod Ports             Module-Type                      Model           Status
--- ----- ------------------------------------- --------------------- ---------
1    64   Nexus 9000v 64 port Ethernet Module   N9K-X9364v            ok
27   0    Virtual Supervisor Module             N9K-vSUP              active *
```

Once I get past five NXOS devices the interfaces module becomes unstable on the new devices, either randomly working or not workign at all. It will kick up an error on the CLI and go into a *pwr-cycld* state.

```none
Mod Ports             Module-Type                      Model           Status
--- ----- ------------------------------------- --------------------- ---------
1    64   Nexus 9000v 64 port Ethernet Module                         pwr-cycld
27   0    Virtual Supervisor Module             N9K-vSUP              active *

Mod  Power-Status  Reason
---  ------------  ---------------------------
1    pwr-cycld      Unknown. Issue show system reset mod ...
```

Was not able to find a reason for it, it doesnt seem to be related to resources for either the virtual device or the EVE-NG box.
