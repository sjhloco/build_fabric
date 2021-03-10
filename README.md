# Deploy Leaf and Spine

This playbook will deploy a leaf and spine fabric and its related services in a declarative manner. You only have to define a few key values such as *naming convention*, *number of devices* and *addresses ranges*, the playbook will do the rest. It is structured into the following 5 roles giving you the option to deploy part or all of the fabric using playbook tags.

- base: Non-fabric specific core configuration such as hostname, address ranges, users, acls, ntp, etc
- fabric: Fabric specific elements such as fabric size, interfaces (spine-to->leaf/border), OSPF, BGP and MLAG
- services: Services provided by the fabric split into three sub-roles:
  - tenant: VRFs, SVIs, VLANs and VXLANs on the fabric and their associated VNIs
  - interface: Access ports connecting to compute or other non-fabric network devices
  - routing: BGP (address-families), OSPF (additional non-fabric process) and static routes

If you wish to have a more custom build the majority of the settings in the variable files (unless specifically stated) can be changed as none of the scripting or templating logic uses the actual contents (dictionary values) to make decisions.

This deployment will scale up to a maximum of 4 spines, 4 borders and 10 leafs. By default the following ports are used for inter-switch links, these can be changed within *fabric.yml* (*fbc.adv.bse_intf*).

| Connection      | Start Port | End Port |
|-----------------|------------|----------|
| SPINE-to-LEAF   | *Eth1/1*   | *Eth1/10*
| SPINE-to-BORDER | *Eth1/11*  | *Eth1/14*
| LEAF-to-SPINE   | *Eth1/1*   | *Eth1/4*
| BORDER-to-SPINE | *Eth1/1*   | *Eth1/4*
| MLAG Peer-link  | *Eth1/5*   | *Eth1/6*
| MLAG keepalive  | *mgmt*     | *n/a*

!!!!!!! REDO IMAGE, maybe not use VISIO, NEEDS TO LOOK MORE FRIENDLY !!!!!!!!!
![image](https://user-images.githubusercontent.com/33333983/83332342-9b246500-a292-11ea-9455-7cbe56e0d701.png)

This playbook is based on 1U Nexus devices, therefore using the one linecard module for all the connections. I have not tested how it will work with multiple modules, the role *intf_cleanup* is likely not to work. This role ensures interface configuration is declarative by defaulting non-used interfaces, therefore could be excluded without breaking the playbook.

As Python is a lot more flexible than Ansible the dynamic inventory and custom filter plugins (within the roles) do the manipulating of the data in the variable files to create the data models that are used by the templates. This helps to abstract a lot of the complexity out of the jinja templates making it easier to create new templates for different vendors as you only have to deal with the device configuration rather than data manipulation.

## Fabric Core Variable Elements

These core elements are the minimum requirements to create the declarative fabric. They are used for the dynamic inventory creation as well by the majority of the Jinja2 templates. All variables are proceeded by *ans*, *bse* or *fbc* to make it easier to identify within the playbook, roles and templates which variable file the variable came from.

### ansible.yml (ans)

- ***dir_path:*** Base directory location on the Ansible host that stores all the validation and configuration snippets
- ***device_os:*** Operating system of each device type (spine, leaf and border)
- ***creds_all:*** hostname (got from inventory), username and password

### base.yml (bse)

The settings required to onboard and manage device such as hostname format, IP address ranges, AAA, syslog, etc.

***device_name:*** Naming format that the automatically generated node ID is added to (double decimal format) and group name created from (in lowercase). The name must contain a hyphen (*-*) and the characters after that hyphen must be either letters, digits or underscore as that is what the group name is created from.

- ***device_name:*** Naming format that the automatically generated node ID is added to (double decimal format) and group name created from (in lowercase). The name must contain a hyphen (*-*) and the characters after that hyphen must be either letters, digits or underscore as that is what is used to create the group name from.

| Key      | Value   | Information  |
|----------|---------|--------------|
| spine    | `xx-xx` | *Spine switch naming format. For example with DC1-N9K-SPINE device is DC1-N9K-SPINE01 and group is spine*
| border   | `xx-xx` | *Border switch naming format. For example with DC1-N9K-BORDER device is DC1-N9K-BORDER01 and group is border*
| leaf     | `xx-xx` | *Leaf switch naming format. For example with DC1-N9K-LEAF device is DC1-N9K-LEAF01 and group is leaf*

- ***addr:*** Subnets from which the device specific IP addresses are generated based on the *device type increment* and the *node number*. The majority of subnets need to be at least /27 to cover a maximum network size of 4 spines, 10 leafs and 4 borders (18 addresses)

| Key      | Value | Min size     | Information   |
|----------|-------|--------------|---------------|
| lp_net           | `x.x.x.x/26` | /26 | *Address range routing (OSPF/BGP), VTEP and vPC addresses are from, mask will be /32* |
| mgmt_net         | `x.x.x.x/27` | /27 | *Management network, by default will use .11 to .30* |
| mlag_peer_net    | `x.x.x.x/26` | /26 or /27 | *Split into a per-switch pair /30 for OSPF over peer link. /26 if using same range for keepalive* |
| mlag_kalive_net  | `x.x.x.x/27` | /27 | *Optional keepalive address range. If not set uses the mlag_peer_net range* |
| mgmt_gw          | `x.x.x.x`    | n/a | *Management interface default gateway*

`mlag_kalive_net` is only needed if not using the management interface for the keepalive or you want separate ranges for the peer-link and keepalive interfaces. The keepalive link is created in its own VRF so it can use duplicate IPs or be kept unique by offsetting it with the fabric variable `fbc.adv.addr_incre.mlag_kalive_incre`.

There are a lot of other system wide settings in *base.yml* such as AAA, NTP, DNS, usernames and management ACLs. Anything under bse.services are optional (DNS, logging, NTP, AAA, SNMP, SYSLOG), they will by default use the management interface and VRF as the source unless specifically set.\
These are not included in this section as don't relate to building the fabric, explanations on these can be found in the variable file.
### fabric.yml (fbc)

Variables used to determine how the fabric will be built, the network size, interfaces, routing protocols and address increments. At a bare minimum you only need to declare the size of fabric, total number of switch ports and the routing options.

***network_size:*** How many of each device type make up the fabric. Can range from 1 spine and 2 leafs up to a maximum of 4 spines, 4 borders and 10 leafs. The border and leaf switches are MLAG pairs so must be in increments of 2.

| Key         | Value | Information  |
|-------------|-------|--------------|
| num_spines  | `2`   | *Number of spine switches in increments of 1 up to a maximum of 4* |
| num_borders | `2`   | *Number of border switches in increments of 2 up to a maximum of 4* |
| num_leafs   | `4`   | *Number of leaf switches in increments of 2 up to a maximum of 10* |

***num_intf:*** The total number of interfaces per device type is required to make interface assignment declarative by ensuring that non-defined interfaces are reset to their default settings

| Key    | Value  | Information |
|--------|--------|-------------|
| spine  | `1,64` | *The first and last interface for a spine switch*
| border | `1,64` | *The first and last interface for a border switch*
| leaf   | `1,64` | *The first and last interface for a leaf switch*

***adv.bse_intf:*** Interface naming formats and seed interface numbers used to build the fabric

| Key         | Value          | Information   |
|-------------|----------------|---------------|
| intf_fmt    | `Ethernet1/`   | *Interface naming format*
| intf_short  | `Eth1/`        | *Short interface name used in interface descriptions*
| mlag_fmt    | `port-channel` | *MLAG interface naming format*
| mlag_short  | `Po`           | *Short MLAG interface name used in MLAG interface descriptions*
| lp_fmt      | `loopback`     | *Loopback interface naming format*
| sp_to_lf    | `1`            | *First interface used for SPINE to LEAF links (1 to 10)*
| sp_to_bdr   | `11`           | *First interface used for SPINE to BORDER links (11 to 14)*
| lf_to_sp    | `1`            | *First interface used LEAF to SPINE links (1 to 4)*
| bdr_to_sp   | `1`            | *First interface used BORDER to SPINE links (1 to 4)*
| mlag_peer   | `5-6`          | *Interfaces used for the MLAG peer Link*
| mlag_kalive | `mgmt`         | *Interface for the keepalive. If it is not an integer uses the management interface*

***adv.address_incre:*** Increments added to the node ID and subnet to generate unique device IP addresses. Uniqueness is enforced by using different increments for different device roles and functions.

| Key               | Value | Information   |
|-------------------|-------|---------------|
| spine_ip          | `11`  | *Spine mgmt and routing loopback addresses (default .11 to .14)*
| border_ip         | `16`  | *Border mgmt and routing loopback addresses (default .16 to .19)*
| leaf_ip           | `21`  | *Leaf mgmt and routing loopback addresses (default .21 to .30)*
| border_vtep_lp    | `36`  | *Border VTEP (PIP) loopback addresses (default .36 to .39)*
| leaf_vtep_lp      | `41`  | *Leaf VTEP (PIP) loopback addresses (default .41 to .50)*
| border_mlag_lp    | `56`  | *Shared MLAG anycast (VIP) loopback addresses for each pair of borders (default .56 to .57)*
| leaf_mlag_lp      | `51`  | *Shared MLAG anycast (VIP) loopback addresses for each pair of leafs (default .51 to .55)*
| border_bgw_lp     | `58`  | *Shared BGW MS anycast loopback addresses for each pair of borders (default .58 to .59)*
| mlag_leaf_ip      | `1`   | *Start IP for leaf OSPF peering over peer-link (default LEAF01 is .1, LEAF02 is .2, LEAF03 is .5, etc)*
| mlag_border_ip    | `21`  | *Start IP for border OSPF peering over peer-link (default BORDER01 is .21, BORDER03 is .25, etc)*
| mlag_kalive_incre | `28`  | *Increment added to leaf/border increment (mlag_leaf_ip/mlag_border_ip) for keepalive addresses*

If the management interface is not being used for the keepalive link either specify a separate network range (`bse.addr.mlag_kalive_net`) or use the peer-link range and specify an increment (`mlag_kalive_incre`) that is added to the peer-link increment (`mlag_leaf_ip` or `mlag_border_ip`) to generate unique addresses.

***route:*** Settings related to the fabric routing protocols (OSPF and BGP). BFD is not supported on unnumbered interfaces so the routing protocol timers have been shortened (OSPF 2/8, BGP 3/9), these are set under the advanced settings (`adv.route`)

| Key            | Value                 | Mandatory | Information |
|----------------|-----------------------|-----------|-------------|
| ospf.pro       | `string` or `integer` | Yes | *Can be numbered or named*
| ospf.area      |  x.x.x.x              | Yes | *Area this group of interfaces are in, must be in dotted decimal format*
| bgp.as_num     | `integer`             | Yes | *Local BGP Autonomous System number*
| authentication | `string`              | No  | *Applies to BGP and OSPF. Hash out if don't want to set authentication*

***acast_gw_mac***: The distributed gateway anycast MAC address for all leaf and border switches in the format `xxxx.xxxx.xxxx`

## Dynamic Inventory

The *ansible*, *base* and *fabric* variables are passed through an inventory plugin to create the dynamic inventory and *host_vars* for all the fabric interfaces and IP addresses. By doing this in the inventory the complexity is abstracted from the *base* and *fabric* templates (roles) making it easier to expand the playbook to other vendors in the future.

With the exception of *intf_mlag* and *mlag_peer_ip* (not on spines) the following *host_vars* are created for every host.

- **ansible_host:** *Devices management address*
- **ansible_network_os:** *Got from ansible var_file and used by napalm*
- **intf_fbc:** *Dictionary of fabric interfaces with interface the keys and description the values*
- **intf_lp:** *List of dictionaries with keys of name, ip and description*
- **intf_mlag:** *Dictionary of mlag peer-link interfaces with interface the key and description the value*
- **mlag_peer_ip:** *IP of the VLAN (default VLAN2) used for the OSPF peering over the MLAG peer-link*
- **num_intf:** *Number of the first and last physical interface on the switch*
- **intf_mlag_kalive:** *Dictionary of mlag keepalive link interface with interface the key and description the value (only created if defined)*
- **mlag_kalive_ip:** *IP of the keepalive link (only created if defined)*

The devices (*host-vars*) and groups (*group-vars*) created by the inventory plugin can be checked using the `graph` flag. Note, the inventory config file (*.yml*) not the inventory plugin (*.py*) is referenced when using the dynamic inventory.

The devices (*host-vars*) and groups (*group-vars*) created by the inventory plugin can be checked using the `graph` flag. Note, the inventory config file (*.yml*) not the inventory plugin (*.py*) is referenced when using the dynamic inventory.

```none
ansible-inventory --playbook-dir=$(pwd) -i inv_from_vars_cfg.yml --graph
```

```none
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

```none
ansible-inventory --playbook-dir=$(pwd) -i inv_from_vars_cfg.yml --host DC1-N9K-LEAF01
ansible-inventory --playbook-dir=$(pwd) -i inv_from_vars_cfg.yml --list
```

An example of the *host_vars* created for a leaf switch.

```json
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

To use the inventory plugin in a playbook reference the inventory config file in place of the normal hosts inventory file (-i).

```none
ansible-playbook PB_build_fabric.yml -i inv_from_vars_cfg.yml
```

## Services - Tenant Variables *(svc_tnt)*

Tenants, SVIs, VLANs and VXLANs are created based on the variables stored in the *service_tenant.yml* file (*svc_tnt.tnt*).

***tnt:*** A list of tenants that contains a list of VLANs (L2 or L3)

- Tenants (VRFs) will only be created on a leaf or border if a VLAN within that tenant is to be created on that device
- Even if a tenant is not a L3 tenant a VRF will still be created and the L3VNI/VLAN number reserved
- If the tenant is a L3 tenant the route-map for redistribution is always created and attached to the BGP peer

| Key      | Value | Mandatory | Information |
|----------|-------|-----------|-------------|
 tenant_name | `string` | Yes |  *Name of the VRF* |
| l3_tenant | `True` or `False` | Yes |  *Does it need SVIs or is routing done off the fabric (i.e external router)* |
| bgp_redist_tag | `integer` | No | *Tag used to redistributed SVIs into BGP. By default uses tenant SVI number* |
| vlans |  `list` | Yes | *List of VLANs within this tenant (see the below table)* |

***vlans:*** A List of VLANs within a tenant which at a minimum need the L2 values of *name* and *num*. VLANs and SVIs can only be created on all leafs and/ or all borders, can't selectively say which individual leaf or border switches to create them on

- Unless an IP address is assigned to a VLAN (*ip_addr*) it will only be L2 VLAN
- L3 VLANs are automatically redistributed into BGP. This can be disabled (*ipv4_bgp_redist: False*) on a per-vlan basis
- By default VLANs will only be created on the leaf switches (*create_on_leaf*). This can be changed on a per-vlan basis to create only on borders (*create_on_border*) or on both leafs and borders
- To add a non-anycast SVI create the VLAN as normal but with the extra `VXLAN: False` dict. The SVI is defined under service_interface.yml as `type: svi`
- Optional settings will implicitly use the default value. They only need defining if not using the default value

| Key      | Value | Mandatory | Information |
|----------|-------|-----------|-------------|
| num | `integer` | Yes | *The VLAN number*
| name | `string` | Yes | *The VLAN name*
| ip_addr | x.x.x.x/x | No |  *Adding an IP address automatically makes the VLAN L3 (not set by default)*
| ipv4_bgp_redist |  `True` or `False` | No | *Dictates whether the SVI is redistributed into VRF BGP addr family (default True)*
| create_on_leaf | `True` or `False` | No | *Dictates whether this VLAN is created on the leafs (default True)*
| create_on_border | `True` or `False` | No | *Dictates whether this VLAN is created on the borders (default False)*
| vxlan | `True` or `False` | No | *Dictates whether is VXLAN or normal VLAN. Only need if explicitly done want to be VXLAN (default True)*

The redistribution route-map name can be changed in the advanced (*adv*) section of *services-tenant.yml* or *services-routing.yml*. If defined in both places the setting in *services-routing.yml* takes precedence.

### L2VNI and L3VNI numbers

The L2VNI and L3VNI values are automatically derived and incremented on a per-tenant basis based on the start and increment values defined in the advanced section (*svc_tnt.adv*) of *services_tenant.yml*.

***adv.bse_vni:*** Starting VNI numbers

| Key      | Value | Information |
|----------|-------|-------------|
| tnt_vlan | 3001 | *Starting VLAN number for the transit L3VNI*
| l3vni | 10003001 | *Starting VNI number for the transit L3VNI*
| l2vni | 10000 | *Starting L2VNI number, the VLAN number will be added to this*

***adv.vni_incre:*** Number by which VNIs are incremented for each tenant

| Key      | Value | Information |
|----------|-------|-------------|
| tnt_vlan | 1 | *Value by which the transit L3VNI VLAN number is increased for each tenant*
| l3vni | 1 | *Value by which the transit L3VNI VNI number is increased for each tenant*
| l2vni | 10000 | *Value by which the L2VNI range (range + vlan) is increased for each tenant*

An example of a data model created by the *svc_tnt_dm* method within the *format_dm.py* custom filter plugin. These are created on a device_role basis, so for all leaf switches and for all border switches.

A new data-model is created from the *services_tenant.yml* variables by passing these through the *format_dm.py* filter_plugin method ***create_svc_tnt_dm*** along with the BGP route-map name (if exists) and ASN (from fabric.yml). The result is a per-device role (leaf and border) list of tenants, SVIs and VLANs which are used to render the ***svc_tnt_tmpl.j2*** template and create the config snippet.

Below is an example of the data model format for a tenant and its VLANs.

```json
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

## Services - Interface Variables *(svc_intf)*

The *service_interface.yml* variables can define a single or dual-homed interface (including port-channel number) either statically or dynamically from a range.

- By default all interfaces are dual-homed LACP *'active'*. The VPC number can not be changed, is always the port-channel number
- Interfaces and port-channels can be assigned from a pool defined under advanced or specified manually
- If the tenant (VRF) is not defined for a layer3 or loopback interface it will be created in the global routing table
- If the interface config is the same across multi switches (like an access port) define one interface with a list of switches
- *dual-homed* interfaces only need the odd numbered switch specified, the config for both members for the MLAG pair is automatically generated

There are 6 pre-defined types of interface that can be deployed:

- **access:** *A single VLAN layer2 access port. STP is set to 'edge'*
- **stp_trunk:** *A trunk going to a device that supports Bridge Assurance. STP is set to 'network'*
- **stp_trunk_non_ba:** *Same as stp_trunk except that STP is set to 'normal' to support devices that don't use BA*
- **non_stp_trunk:** *A trunk port going to a device that doesn't support BPDU. STP set to 'edge' and BPDU Guard enabled*
- **layer3:** *A layer3 interface with an IP address. Must be single-homed as MLAG not supported for L3 interfaces*
- **loopback:** *A loopback interface with an IP address (must be single-homed)*
- **svi:** *To define a SVI the VLAN must exist under service_tenant and not be a VXLAN (must be single-homed)*

***intf.single_homed*** *or* ***intf.dual-homed:*** Separate dictionaries that hold lists of all interfaces of that type. If not defining either single or dual-homed omit that dictionary
| Key        | Value   | Mandatory   | Information |
|------------|---------|-------------|-------------|
| descr | `string` | Yes | *Interface or port-channel description*
| type | intf_type | Yes | *Either access, stp_trunk, stp_trunk_non_ba, non_stp_trunk, layer3, loopback or svi*
| ip_vlan | vlan or ip | Yes | *Depends on the type, either ip/prefix, vlan or multiple vlans separated by , and/or -*
| switch  | `list` | Yes | *Switches created on. If dual-homed needs to be the odd switch number from MLAG pair*
| tenant | `string` | No | *Layer3 and loopbacks only. If not defined the default VRF is used (global routing table)*
| po_mbr_descr | `list` | No | *PO member interface description, [odd_switch, even_switch]. If undefined uses PO descr*
| po_mode | `string` | No | *Set the Port-channel mode, 'on', 'passive' or 'active'. Default is 'active'*
| intf_num | `integrar` | No | *Only specify the number, the name and module are got from the fbc.adv.bse_intf.intf_fmt*
| po_num | `integrar` | No | *Only specify the number, the name is got from the fbc.adv.bse_intf.mlag_fmt*

The playbook has the logic to recognize if statically defined interface numbers overlap with the dynamic interface range and exclude them from dynamic interface assignment. For simplicity it is best to use separate ranges for the dynamic and static assignments.

***adv.single_homed:*** Reserved range of interfaces to be used for dynamic single-homed and loopback assignment
| Key        | Value      | Information |
|------------|------------|-------------|
| first_intf | `integrar` | *First single-homed interface to be dynamically assigned*
| last_intf  | `integrar` | *Last single-homed interface to be dynamically assigned*
| first_lp   | `integrar` | *First loopback number to be dynamically used*
| last_lp    | `integrar` | *Last loopback number to be dynamically used*

***adv.dual-homed:*** Reserved range of interfaces to be used for dynamic dual-homed and port-channel assignment
| Key        | Value      | Information  |
|------------|------------|--------------|
| first_intf | `integrar` | *First dual-homed interface to be dynamically assigned*
| last_intf  | `integrar` | *Last dual-homed interface to be dynamically assigned*
| first_po   | `integrar` | *First port-channel number to be dynamically used*
| last_po    | `integrar` | *Last port-channel number to be dynamically used*

The filter_plugin method ***create_svc_intf_dm*** is run for each inventory device to produce a list of all interfaces to be created on that device. In addition to the *services_interface.yml* variables it also passes in the interface naming format (*fbc.adv.bse_intf*) to create the full interface name and *hostname* to find the interfaces relevant to that device.

Below is an example of the data model format for a single-homed and dual-homed interface.

```json
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

In the same manner as tenants *flt_svc_intf* is used to render the template and produce the configuration snippet. The template is quite simple as the same format to create interfaces for all devices.

## Interface Cleanup - Defaulting Interfaces

The interface cleanup role is required to make sure any interfaces not assigned by the fabric or the services (svc_intf) role have a default configuration. Without this if an interface was to be changed (for example a server moved to different interface) the old interface would not have its configuration put back to the default values.

This role goes through the interfaces assigned by the fabric (from the inventory) and service_interface role (from the *svc_intf_dm* method) producing a list of used physical interfaces which are then subtracted from the list of all the switches physical interfaces (*fbc.num_intf*). It has to be run after the fabric or service_interface role as it needs to know what interfaces have been assigned, therefore uses tags to ensure it is run anytime either of these roles are run.

## Services - Routing Variables *(svc_rte)*

BGP peerings, non-backbone OSPF processes, static routes and redistribution (connected, static, bgp, ospf) are configured based on the variables specified in the service_route.yml file. I am undecided about this role as it is difficult to keep it simple due to all the nerd knobs in routing protocols, especially BGP.

Under the advanced section (*adv*) of the variable file the naming policy of the route-maps and prefix-lists used by OSPF and BGP can be changed.
From the values in the *services_routing.yml* file a new per-device data model is created by *svc_rte_dm* method in the *format_dm.py* custom filter plugin.

### Static routes

Routes are added per-tenant with the tenant being the top-level dictionary that routes are created under.

- *tenant*, *switch* and *prefix* are lists to make it easy to apply the same routes across multiple devices and tenants.
- For routes with the same attributes (for example same next-hop gateway) only need the one list with all the routes in that list of the prefix dictionary.
- Optionally set the interface, administrative distance of the route and whether the next hop is in a different VRF (for route leaking)

| parent dict  | Key           | Value      | Mand | Information |
|--------------|---------------|------------|------|-------------|
| static_route | tenant       | `list`     | Yes | *List of tenants to create the routes in. Use 'global' if to go in the global routing table*
| static_route | switch       | `list`     | Yes | *List of switches to create all routes on (alternatively can be set per-route)*
| route        | prefix       | `list`     | Yes | *List of routes that all have same settings (gateway, interface, switch, etc)*
| route        | gateway      | x.x.x.x    | Yes | *Next hop gateway address*
| route        | interface    | `string`   | No  | *Next hop interface, use interface full name (Ethernet) or Vlan*
| route        | ad           | `integrar` | No  | *Set the Administrative Distance for this group of routes (1 - 255)*
| route        | next_hop_vrf | `string`   | No  | *Set the VRF for next-hop if it is in a different VRF (for route leaking)*
| route        | switch       | `list`     | Yes | *List of switches this group of routes are to be created on (overrides static_route)*






### BGP

Uses the concept of groups and peers with inheritance. The majority of settings can either be configured under group or the peer, with those configured under the peer taking precedence.
The *switch* and *tenant* settings must be a list (even if is a single device) to allow for the same group and peers to be created on multiple devices and tenants.
At a bare minimun only the mandatory settings are required to form BGP peerings, all others settings are optional.
To put anything in the global routing table use the tenant name *'global'*

***bgp.group:*** List of groups that hold global settings for all peers within that group. This table shows settings that can ONLY be configured under the group. A group does not need to have a switch defined, it will be automatically created on any switches that peers within it are created on.
| Key      | Value | Mandatory | Information |
|----------|-------|-----------|-------------|
| name | `string` | Yes | *Name of the group. No whitespaces and duplicate group or peer names allowed. Used in group, route-map and prefix-list names*

***grp.group.peer:*** List of peers within the group that will inherit non-configured settings from that group. This table shows settings that can ONLY be configured under the peer.
| Key      | Value | Mandatory | Information |
|----------|-------|-----------|-------------|
| name | `string` |  Yes | *Name of the peer. No whitespaces and duplicate group or peer names allowed. Used in route-map and prefix-list names*
| peer_ip | x.x.x.x |  Yes | *IP address of the peer*
| description| `string` |  Yes | *Description of the peer*

***grp*** or ***peer:*** These settings can be configured under the group, the peer, or both. The native OS handles the duplication of settings (between group and peers) and the hierarchy (peer settings taking precedence). For any of the non-mandatory settings the dictionary only needs to be included if that settings is to be configured.
If the tenant is not specified (dictionary not defined) it the group/peer will be added to the default global routing table

| Key      | Value | Mandatory | Information |
|----------|-------|-----------|-------------|
| switch | `list` |  Yes | *List of switches to create the group and peers on. Has to be list even if is only 1*
| tenant | `list` |  No | *List of tenants to create the peers under. Has to be list even if is only 1*
| remote_as | `integrar` | Yes | *Remote AS of this peer or if set under the group all peers within that group*
| timers | [keepalives, holdtime] | No | *If not defined uses keepalive of 3 and holdtime of 9 seconds. Default timers are set in the group*
| bfd | `True` | No | *Enable BFD for an indivdual peer or all peers in the group. By default is disabled globally*
| password | `string` | No | *Authentication for an indivdual peer or all peers in the group. By default no password set*
| default | `True` | No | *Enable advertisement of the default route to an indivdual peer or all peers in the group. By default not set*
| update_source | `string` | No | *Set the source interface (loopback) for BGP peers. By default it is not set*
| ebgp_multihop | `integrar` | No | *Increase the number of hops for BGP peerings (2 to 255). By default it is set to 1*
| next_hop_self | `True` | No | *Set the next hop to itself for any advertised prefixes. By default it is not set*

***inbound*** or ***outbound:*** These two dictionaires can be set under the group or peers and hold the settings for prefix BGP attribute manipulation and filtering. Dependant on where this is applied the route-maps and prefix-lists incorporate the group or peer name. If everything is defined the order in the route-map is *BGP_ATTR*, *deny_specific*, *allow_specific*, *allow_all*, *deny_all*.
They take either a list of prefixes (can include 'ge' and/or 'le' in the element) or the single special keyword string ('any' or 'default'). This MUST be a single string, NOT within the list of prefixes.

| Key      | Value | Direction |Information |
|----------|-------|-------|-------------|
| weight | `dict` | inbound | *The keys are the weight and the value a list of prefixes or keywords ('any' or 'default')*
| pref | `dict` | inbound | *The keys are the local preference and the value a list of prefixes or keywords ('any' or 'default')*
| med | `dict` | outbound | *The keys are the med value and the values a list of prefixes or keywords ('any' or 'default')*
| as_prepend | `dict` | outbound | *The Keys are the number of times to add the ASN and the values a list of prefixes or keywords ('any' or 'default')*
| allow | `list`, any, default | both | *Can be a list of prefixes or special keywords to advertise 'any' or just the default route*
| deny | `list`, any | both | *Can be a list of prefixes or special 'any' keyword to advertise nothing*

***bgp.tenants:*** List of VRFs to advertise networks, summarization and redistribution. The tenant dictionary is not mandadatory, it is only needed if any of these advertisemnt methods is being used. The *switch* can set globally for all network/summary/redist in a VRF or be overidden on per-prefix basis. As per the inbound/outbound dictionaries 'any' and 'default' keywords can be used rather than the list of prefixes for the *allow* dictionary or the value of the *metric* dictionary.

| Key      | Value | Mandatory | Information |
|----------|-------|-----------|-------------|
| name | `string` | Yes | *Must be a single VRF on which the advertisement (network), summary and redistribution is configured. Use 'default' if needs to go in the global routing table*
| switch | `list` | Yes (in here or nested dict) | *List of a single or multiple switches. Can be set for all (network, summary, redist) or indvidual prefix/redist*

***bgp.tenants.network:*** List of prefixes to be advertised. Only need to have multiple lists of prefixes if the advertisents are different for different switches, otherwise all the prefixes can be in the one list of the prefix dictionary.
| Key      | Value | Mandatory | Information |
|----------|-------|-----------|-------------|
| prefix | `list` | Yes | *List of prefixes to advertised to all switches set under tenant or this list of specific switches*
| switch | `list` | Yes (in here or tenant) | *List of switches to advertise these prefixes to*

***bgp.tenants.summary:*** List of summarizations. If the *switch* and *summary_only* elements are the same for all prefixes only need the one list element and list all the summarizations in the one list of the prefix dictionary.
| Key      | Value | Mandatory | Information |
|----------|-------|-----------|-------------|
| prefix | `list` | Yes | *List sumarizations to apply on all switches set under tenant or this list of specific switches*
| filter | summary-only | No |*Add this dictionary to only advertise the summary and supresses any prefixes below it (disabled by default)*
| switch | `list` | Yes (in here or tenant) | *List of switches to apply sumarization on*

***bgp.tenants.redist:*** Each redistribution list element is the redistribution type, can be *ospf_xx*, *static* or *connected*. Redistributed prefixes can be filtered (*allow*) or weighted (*metric*) with the route-map order being *metric* and then *allow*. If the allow list is not set it will allow any (empty route-map).
| Key      | Value | Mandatory | Information |
|----------|-------|-----------|-------------|
| type | `string` | Yes | *What is to be redistrbuted into BGP. Can be ospf_xxx, static or connected*
| metric | `dict` | No | *The keys are the med value and the values a list of prefixes or keyword ('any' or 'default'). Cant use with metric with connected*
| allow | `list`, any, default | No | *List of prefixes (if connected list of interfaces) or keyword ('any' or 'default') to redistribute*
| switch | `list` | Yes (in here or tenant) | *List of switches to apply redistribution on*

### OSPF

A list of non-backbone OSPF processes which have further nested dictionaries of OSPF interfaces, summarization and redistribution. The list of switches that the OSPF process is configured on can be defined under the main process, any of the nested dictionaires, or both. Nested dictionary configuration takes precedence.
At a bare minimun only the mandatory settings are needed, all others settings are optional.

***ospf:*** List of non-backbone OSPF processes and the global settings for each process.

| Key      | Value | Mandatory | Information |
|----------|-------|-----------|-------------|
| process | `integrar` or `string` | Yes | *Can be a number or word*
| tenant | `string` | No | *VRF to be enabled in this OSPF process. If this dict is not defined uses the default global routing table*
| rid | x.x.x.x | No | *Router-ID for this OSPF process. If not defined will use highest IP of a loopback address*
| bfd | `True` | No | *Enable BFD for all OSPF neighbors. Once enabled can be disabled on a per-interface basis by setting OSPF timers*
| default_orig | `True` or always | No | *By default is disabled, options are enabled (True) or always (send even if no default route in routing table)*
| switch | `list` | Yes (in here or nested dicts) | *List of switches to create OSPF process on, applies to all nested dictionaries unless also defined in those*

***ospf.interface:*** List of OSPF interfaces and the settings. Each list element is a group of interfaces with the same group of settings (same area number, same interface type, etc).
*passive-interface* is enabled globally and automatially disabled on all configured interfaces. This can be enabled on a per-interface basis.
If authentication is enabled for an interface it is enabled globally for that area so the same dictionary setting (*password*) is needed on all interfaces in that area.

| Key      | Value | Mandatory | Information |
|----------|-------|-----------|-------------|
| name | `list` | Yes | List of one or more interfaces which have these same settings. Use interface full name (*Ethernet*) or *Vlan*
| area | x.x.x.x | Yes | *Area this group of interfaces are in, must be in dotted decimal format*
| cost | `integrar` | No | *To statically set the interfaces OSPF cost, can be 1-65535*
| authentication | `string` | No | *Enables authentication for the area and a password (Cisco type 7) for this interface*
| area_type | `string` | No | *Can be stub, nssa, stub/nssa no-summary, nssa default-information-originate or nssa no-redistribution*
| passive | `True` | No | *Make the interface passive so it wont form OSPF peers. By default all interfaces are False (non-passive)*
| timers | [hello, holdtime] | No | *Set the hello and deadtime timers (10/40). If BFD is enabled globally BFD will be disabled for this interface*
| type | point-to-point | No | *By default all interfaces are broadcast, add to change to PtP. All interfaces in the same area must be of the same type*
| switch | `list` | Yes (in here or process) | *What switches to enable these OSPF interfaces on, takes precedence over process switch setting*

***ospf.summary:*** List of summarizations. If the *switch*, *filter* and *area* dictionaries are the same for all prefixes only need the one list with all the summaries in that list of the prefix dictionary.

| Key      | Value | Mandatory | Information |
|----------|-------|-----------|-------------|
| prefix | `list` | Yes | *List of sumarizations to apply on all switches set under the process or this list of specific switches*
| area | x.x.x.x | No | *By default it is a LSA5 summary, by adding an area it makes it a LSA3 summary (summarise from that area)*
| filter | not-advertise | No | *Stops it advertising the summary and subordinate subnets, is basically filtering*
| switch | `list` | Yes (in here or process) | *What switches to enable these sumarizations, takes precedence over process switch setting*

***ospf.redist:***: Each redistribution list element is the redistribution type, can be ospf_xx, bgp_xx, static or connected. Redistributed prefixes can be filtered (allow) or weighted (metric) with the route-map order being metric and then allow. If the allow list is not set it will allow any (empty route-map).

| Key      | Value | Mandatory | Information |
|----------|-------|-----------|-------------|
| type | `string` | Yes | *What is to be redistrbuted into this OSPF process, bgp_xx, ospf_xxx, static or connected*
| metric | `dict` | No | *The keys are the med value and the values a list of prefixes or keyword (‘any’ or ‘default’). Cant use with metric connected*
| allow | `list`, any, default | No | *List of prefixes (if connected list of interfaces) or keyword (‘any’ or ‘default’) to redistribute*
| switch | `list` | Yes (in here or process) | *What switches to redistribute on, takes precedence over process switch setting*



## Passwords

Are 3 main types of passwords used within the playbooks. The way that NAPALM deasl with them when applying is slightly different.
They are all stored within the ansible.yml file using Vault

- BGP/OSPF: In the varible file it is in as plain text but in the device running configuration is encrytped
- Users: Has to be in encrypted format (type-5) in the variable file
- TACACS: Has to be in the encrypted format (type-7) in the variable. Could use type-6 but would also need to generate a master key, may revist

## Input validation

Rather than validating configuration on devices it runs before any device configuration and validate the details entered in the variable files are correct. The idea of this pre-validation is to ensure the values in the variable files are in the correct format, have no typos and conform to the rules of the playbook. Catching these errors early allows the playbook to failfast before device connection and configuration.

The plugin does the actual validation with a result returned to the Ansible Assert module which decides if the playbook fails.
All the error messages returned by pre_val start with the nested location of the variable to make it easier to find. For example *svc_intf.intf.single_homed.ip_vlan* is a singled homed interfaces ip_vlan variable within the *service_interface.yml* variable file.

It is run using the *post_val* tag and will conditionally only check variable files that have been defined under *var_files*. It can be run using the inventory plugin but will fail if any of the values useded to create inventory are wrong so better use a dummy host file.
`ansible-playbook playbook.yml -i hosts --tag post_val`
`ansible-playbook playbook.yml -i inv_from_vars_cfg.yml --tag post_val`

A full list of what variables are checked and the expected input can be found in the header notes of *input_validate.py*.

## Playbook Structure

The playbook is divided into 4 sections with roles used to do all the templating and validation.

- pre_tasks: Creates the file structure and runs the pre validation tasks
- task_roles: Roles are used to to create the templates and in some cases use pluggins to create new data models
  - base: From templates and base.yml creates the base configuration snippets (aaa,  logging, mgmt, ntp, etc)
  - fabric: From templates and fabric.yml creates the fabric configuration snippets (connections, OSPF, BGP)
  - services: Has per-service type tasks and templates for the services to run on top of the fabric
    - svc_tnt: From templates and services_tenant.yml creates the tenant config snippets (VRF, SVI, VXLAN, VLAN)
    - svc_intf: From templates and services_interface.yml creates the interface config snippets (routed, access, trunk)
    - svc_rte: From templates and ervice_routing.yml creates the tenant routing config snippets (BGP, OSPF, static routes, redistribution)
  - intf_cleanup: Based on interfaces used in fabric and svc_intf defaults all other interfaces
- task_config: Assembles the config snippets into the one file and applies as a config_replace
- post_tasks: A validate role creates and compares *desired_state* (built from variables) against *actual_state*
  - validate: custom_validate uses napalm_validate feed with device output to validate things not covered by napalm
    - nap_val: For elements covered by napalm_getters creates desired_state and compares against actual_state
    - cus_val: For elements not covered by napalm_getters creates desired_state and compares against actual_state

## Directory Structure

The following directory structure is created within *~/device_configs* to hold the configuration snippets, validation desired_state files,  and compliance reports. The base location can be changed using *ans.dir_path*.

```bash
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

## Installation and Prerequisites

It using a Python virtual environment change the NAPLAM library and plugin locations in the *ansible.cfg* to match your environment.

```bash
library = /home/ste/virt/ansible_2.8.4/lib/python3.6/site-packages/napalm_ansible/modules
action_plugins = /home/ste/virt/ansible_2.8.4/lib/python3.6/site-packages/napalm_ansible/plugins/action
```

The following base configuration needs to be manually added on all the devices.

- Management IP address and default route
- The features *nxapi* and *scp-server* are required for Naplam *config_replace*
- Image validation can take a while on vNXOS so is best to be done so beforehand

```bash
interface mgmt0
  ip address 10.10.108.11/24
vrf context management
  ip route 0.0.0.0/0 10.10.108.1
feature nxapi
feature scp-server
boot nxos bootflash:/nxos.9.2.5.bin
```

- The custom TCAM allocation (leafs and/or borders) as requires a reboot. This can change dependant on model, for example vNXOS requires TCAM for arp-ether whereas 9300 series don't. Any changes made need correcting in /roles/base/templates/nxos/bse_tmpl.j2 to keep it idempotent.

```bash
hardware access-list tcam region racl 512
hardware access-list tcam region arp-ether 256 double-wide
```

*bse.users.password* holds the password *type5* encrypted, if you don't know this can enter the user on the devices now and get the password from the running config in the correct format. The default username/password in the playbook is *admin/ansible*.

Before the playbook can be run against the switches the SSH keys need adding on the Ansible host (*~/.ssh/known_hosts*). The *ssh_key_playbook.yml* playbook (in *ssh_keys* directory) can be run to add these automatically, just need to add the device`s management IPs to the *ssh_hosts* file.

```bash
sudo apt install ssh-keyscan
ansible-playbook ssh_keys/ssh_key_add.yml -i ssh_keys/ssh_hosts
```

## Physical vs virtual

The OSPF peering over the VPC allows for backup path over VPC if lost spine link.
This SVI VLAN needs to be special infra vlan in order to use an SVI as an underlay interface (one that forwards/originates VXLAN-encapsulated traffic).
This cmd does not work on vNXOS, unhash on physical (/roles/base/templates/nxos/fbc_tmpl.j2)

```bash
system nve infra-vlans {{ fbc.adv.mlag.peer_vlan }}
```

vNXOS requires TCAM for arp-ether whereas 9300 series don't
```
hardware access-list tcam region arp-ether 256 double-wide
```

Has a virtual supervisor so need 'sup-1' at end of cmd

boot nxos bootflash:/nxos.9.3.5.bin sup-1
switch(config)# show module
Mod Ports             Module-Type                      Model           Status
--- ----- ------------------------------------- --------------------- ---------
1    64   Nexus 9000v 64 port Ethernet Module   N9K-X9364v            ok
27   0    Virtual Supervisor Module             N9K-vSUP              active *


## Running playbook

The device configuration is applied using Napalm with the change differences always saved to file (in */device_configs/diff*) and optionally printed to screen. Napalm *commit_changes* is set to true meaning that Ansible *check-mode* is used for dry-runs.

Tags are used to allow for only certain roles or combination of roles to be run.

| tag      | Description |
|----------|-------------|
| pre_val  | Checks var_file contents are valid and conform to script rules (network_size, address format, etc)  |
| bse      | Generates the base configuration snippet |
| fbc      | Generates the fabric and intf_cleanup configuration snippets |
| bse_fbc  | Generates, joins and applies the base, fabric and inft_cleanup configuration snippets |
| rb       | Reverses the changes by applying the rollback configuration |
| diff     | Prints the differences to screen (is still also saved to file) |

- *pre_val* should be run first on its own to find any possible errors before generating or pushing configuration to devices
- *bse* and *fbc* will only generate the config snippet and save it to file. No connections are made to devices or changes applied
- *diff* tag can be used with *bse_fbc* or *rb* to print the configuration changes to screen
- Changes are always saved to file no matter whether *diff* is used or not
- *-C* or *--check-mode* will do everything except actually apply the configuration<p style="margin-top: -20px;"></p>

***pre-validation:*** Validates the contents of variable files defined under *var_files*. Best to use dummy host file instead of dynamic inventory.
{{< cfg_syntax"ansible-playbook PB_build_fabric.yml -i [hosts] --tag post_val">}}

***Generate the base config:*** Creates the base config snippets and saves to file
{{< cfg_syntax"ansible-playbook PB_build_fabric.yml -i inv_from_vars_cfg.yml --tag [bse]">}}

***Generate the complete config:*** Creates the config snippets and compares against what is on the device to see what will be changed
{{< cfg_syntax"ansible-playbook PB_build_fabric.yml -i inv_from_vars_cfg.yml --tag '[bse_fbc, diff]' [-C]">}}

***Apply the config:*** Replaces current config on the device. The output is by default automatically saved */device_configs/diff*
{{< cfg_syntax"ansible-playbook PB_build_fabric.yml -i inv_from_vars_cfg.yml --tag [bse_fbc]">}}                                                        |
## Post Validation checks

The desired state is what you expect the fabric to be in once it has been deployed. The declaration of how the fabric should be built is made in the variables files, therefore it makes sense that these are used to build the desired state validation file. The file a list of dictionaries with the *key* being what *napalm_getter* or command being checked and the *value* the expected result. This is compared against the actual state of the fabric.

*Napalm_validate* can only perform a compliance on anything that has a getter, for anything not covered by this the *custom_validate* filter plugin is used. The plugin uses the same *napalm_validate* framework but the actual state is supplied through a static input file (got using *napalm_cli*) rather than a getter.

The results of the napalm_validate (*nap_val.yml*) and custom_validate (*cus_val.yml*) tasks are joined together to create the one compliance report stored in */device_configs/reports*. Each getter or command has a complies dictionary (True or False) for the state of each task and this feeds into the compliance reports own complies dictionary. It is based on this value that a task in the main playbook will raise an exception.

### napalm_validate

Napalms very nature is to abstract the vendor so along the getter exists the template files are the same for all vendors. The following elements are validated by this module and the roles that use them are in brackets.

- ***hostname*** *(fbc): Automatically created device names are correct*
- ***lldp_neighbors*** *(fbc): Devices physical fabric and MLAG connections are correct*
- ***bgp_neighbors*** *(fbc, tnt): Overlay neighbors are all up (strict). fbc doesn't check for sent/rcv prefixes, tnt expects prefixes*
-
There was originally ICMP validation of all the loopbacks but it took too long to complete. At the end of the day if a loopback was not up you would find out through one of the other tests so I decided not to use it (left the config in but is hashed out).

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

*custom_validate* requires a per-OS type template file and per-OS type method within the *custom_validate.py* filter_plugin. The command output can be collected via Naplam or Ansible Network modules, ideally as JSON or you could use NTC templates or the genieparse collection to do this. Within *custom_validate.py* it matches based on the command and creates a new data model that matches the format of the desired state. Finally the *actual_state* and *desired_state* are fed into napalm_validate using its *compliance_report* method. The following elements are checked, the roles that use these checks are in brackets

- show ip ospf neighbors detail (fbc): *Underlay neighbors are all up*
- show port-channel summary (fbc, intf): *Port-channel state and members (strict) are up*
- show vpc (fbc, tnt, intf): *MLAG peer-link, keep-alive state, vpc status and active VLANs*
- show interfaces trunk	(fbc, tnt, intf): *Allowed vlans and stp forwarding vlans*
- show ip int brief include-secondary vrf all (fbc, tnt, intf): *L3 interfaces in fabric and tenants*
- show nve peers (tnt): *All VTEP tunnels are up*
- show nve vni (tnt): *All VNIs are up, have correct VNI number and VLAN mapping*
- show interface status	(intf): *State and port type*

To aid with creating new validations the custom_val_builder is a stripped down version of custom_validate to use to build new validations. The README has the process but can basically feed in either feed in static dictionary file or device output to aid in the creation of the method code and template snippet before testing and then movign to the main playbook.


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

### Running Post-validation


NEED ADDING ONCE FINISH BLOG

```bash
cat ~/device_configs/reports/DC1-N9K-SPINE01_compliance_report.json | python -m json.tool
```



## Building a new service

Process for building a new service:

1. vars.yml: Build the input variable file. It should be nested dictionary with the root being a short acronym as helps identify which files variables come from
2. format_dm.py: Add a method to this to create the per-device_role DM. Python is more flexibale that jinaj for formatting so helps to keep the template a lot cleaner.
3. tasks.yml: Create a new task that will hold 2 plays, one to generate the new DM and one to render the template
4. tmpl.j2: Create the template that has logic to decide flt_vars based on device_role.
5. tasks_from: Under tasks of the main playbook import the role and the name of this new task.
6. input_validation.py: Add a new method that uses try/except asser statements to validate the input variables.
7. pre_tasks: Add a new Ansible assert module play that references the new input_val method
8. post_checks: use custom_val_builder to build validation tests and then add to 'roles/validate/filter_plugin/custom_validate.py' and 'roles/validate/templates/nxos/val_tmpl.j2'

## Notes and Improvements

Have disabled ping from the napalm validation as took too long, loopbacks with secondary IP address can take 3 mins to come up. If fabric wasnt up BGP and OSPF wouldnt be up, can check other loopbacks as part of services.
Not sure about rollback, all though says all worked odd switch didnt rollback (full config, not sure if would be same with smaller bits of config).

1. Add routing  services

Nice to have

1. Create a seperate playbook to update Netbox with information used to build the fabric
2. Add multi-site
3. Add templates for Arista

## Caveats

-NXOS API: Sometimes stop working if reboot a device or push config. I am not sure if is just happens on virtual devices, suspect so. In NXOS it sasy the API process is up and listening but if you telnet to it port 443 is not listening. To fix disable and renable the feature nxapi
Buggy, some times just stops working for no reason, think is related to 'nxapi use-vrf management'




Features can stop working on reboots, for example nve interface disapperared and couldnt add, had to remove feature nv overlay and add bacl