from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

# ============================== Documentation ============================
# options match get_options (in section that parses) and are actually the configuration (i.e. type, required, default)
DOCUMENTATION = '''
    name: inv_from_vars
    plugin_type: inventory
    version_added: "2.8"
    short_description: Creates inventory from desired state
    description:
        - Dynamically creates inventory from specified number of Leaf & Spine devices
    extends_documentation_fragment:
        - constructed
        - inventory_cache
    options:
        plugin:
            description: Token that ensures this is a source file for the 'inv_from_vars' plugin.
            required: True
            choices: ['inv_from_vars']
        var_files:
            description: Var files in Ansible vars directory where dictionaries will be imported from
            required: True
            type: list
        var_dicts:
            description: Dictionaries that wil be imported from the var files
            required: True
            type: dictionary
'''
# What users see as a way of instructions on how to run the plugin
EXAMPLES = '''
# inv_from_vars_cfg.yml file in YAML format
# Example command line: ANSIBLE_INVENTORY_PLUGINS=$(pwd) ansible-inventory -v --list -i inv_from_vars_cfg.yml
plugin: inv_from_vars

# Data-model in Ansible vars directory where dictionaries will imported from
var_files:
  - ansible.yml
  - base.yml
  - fabric.yml

# Dictionaries that wil be imported from the data-model
var_dicts:
  ansible:
    - device_os                       # Device type (os) for each switch type (group)
  base:
    - device_name                       # Naming format for each host
    - addr                              # Address ranges the devices IPs are created from. Loopback must be /32
  fabric:
    - network_size                      # Dictates number of inventory objects created for each device role
    - num_intf                          # Number of the first and last interface on the switch
    - bse_intf                          # Naming and increments for the fabric interfaces
    - lp                                # Loopback interface naming and descriptions
    - mlag                              # Holds the peer link Port-Channel number
    - addr_incre                        # Network address increment used for each device role (group)
'''

# ==================================== Plugin ==================================
# Modules used to format data ready for creating the inventory
import os
import yaml
from ipaddress import ip_network
from collections import defaultdict
# Ansible modules required for the features of the inventory plugin
from ansible.errors import AnsibleParserError
from ansible.module_utils._text import to_native, to_text
from ansible.plugins.inventory import BaseInventoryPlugin, Constructable, Cacheable

# Ansible Inventory plugin class that holds pre-built methods that run automatically (verify_file, parse) without needing to be called
class InventoryModule(BaseInventoryPlugin, Constructable, Cacheable):
    NAME = 'inv_from_vars'                  # Should match name of the plugin

# ==================================== 1. Verify config file ==================================
# 1. Makes a quick determination whether the inventory source config file is usable by the plugin
    def verify_file(self, path):
        valid = False
        if super(InventoryModule, self).verify_file(path):
            if path.endswith(('inv_from_vars_cfg.yaml', 'inv_from_vars_cfg.yml')):
                valid = True
        return valid

# ============================ 3. Generate all the device specific IP interface addresses  ==========================
# #3. Generates the hostname and IP addresses to be used to create the inventory using data model from config file
    def create_ip(self):
        self.all_lp, self.all_mgmt, self.mlag_peer, self.mlag_kalive = ({} for i in range(4))
        self.spine, self.border, self.leaf = ([] for i in range(3))

        # Create new network size variabels as will be decreasing the value
        num_sp = self.network_size['num_spine']
        num_lf = self.network_size['num_leaf']
        num_bdr = self.network_size['num_border']

        # 3a. SPINE: Generates name, management and Loopback IP (rtr) and adds to self.all_x dictionaries (spine_name is the key)
        incr_num = 0
        while num_sp != 0:
            incr_num += 1                    # Increments by 1 for each device
            # Creates the spine name using the incremented (double-decimal format)
            self.spine.append(self.device_name['spine'] + str("%02d" % incr_num))
            # Creates the mgmt IP by adding the num_incr and device_ip_incr to the the network address ({sp_name: mgmt_ip})
            self.all_mgmt[self.spine[incr_num -1]] = str(ip_network(self.addr['mgmt_net'], strict=False)[self.addr_incre['spine_ip'] + incr_num -1])
            # Creates the RTR loopback by adding the num_incr and device_ip_incr to the the network address and then adding subnet and adds to dict
            rtr_ip = str(ip_network(self.addr['lp_net'])[0] + self.addr_incre['spine_ip'] + incr_num -1) + '/32'
            # Creates dict in format sp_name: [{name:lp, ip:lp_ip, descr:lp_descr}) used in next method to create the inventory
            self.all_lp[self.spine[incr_num -1]] = [{'name': self.bse_intf['lp_fmt'] + str(self.lp['rtr']['num']), 'ip': rtr_ip, 'descr': self.lp['rtr']['descr']}]
            num_sp -= 1        # Reduces number of spines each iteration

        # 3b. LEAF: Generates name, management, Loopback IPs (rtr, vtep, mlag), mlag peer IP and adds to self.all_x dictionaries (leaf_name is the key)
        incr_num, odd_incr_num = (0 for i in range(2))
        while num_lf != 0:
            incr_num += 1
            self.leaf.append(self.device_name['leaf'] + str("%02d" % incr_num))
            # If device_name ends in an odd number makes one MLAG (loopback secondary) IP as is shared between a VPC pair
            if int(self.leaf[incr_num -1][-2:]) % 2 != 0:
                odd_incr_num += 1
                mlag_ip = str(ip_network(self.addr['lp_net'])[0] + self.addr_incre['leaf_mlag_lp'] + odd_incr_num -1) + '/32'
            self.all_mgmt[self.leaf[incr_num -1]] = str(ip_network(self.addr['mgmt_net'], strict=False)[self.addr_incre['leaf_ip'] + incr_num -1])
            rtr_ip = str(ip_network(self.addr['lp_net'])[0] + self.addr_incre['leaf_ip'] + incr_num - 1) + '/32'
            vtep_ip = str(ip_network(self.addr['lp_net'])[0] + self.addr_incre['leaf_vtep_lp'] + incr_num -1) + '/32'
            self.all_lp[self.leaf[incr_num -1]] = [{'name': self.bse_intf['lp_fmt'] + str(self.lp['rtr']['num']), 'ip': rtr_ip, 'descr': self.lp['rtr']['descr']},
                                                   {'name': self.bse_intf['lp_fmt'] + str(self.lp['vtep']['num']), 'ip': vtep_ip, 'descr': self.lp['vtep']['descr'],
                                                   'mlag_lp_addr': mlag_ip}]
            # Increases the increment for each switchpair to be next /30 out of MLAG peer link and keepalive address range
            if incr_num == 1 or incr_num == 2:
                mlag_incr = self.addr_incre['mlag_leaf_ip'] + incr_num - 1
            elif incr_num == 3 or incr_num == 4:
                mlag_incr = self.addr_incre['mlag_leaf_ip'] + incr_num + 1
            elif incr_num == 5 or incr_num == 6:
                mlag_incr = self.addr_incre['mlag_leaf_ip'] + incr_num + 3
            elif incr_num == 7 or incr_num == 8:
                mlag_incr = self.addr_incre['mlag_leaf_ip'] + incr_num + 5
            elif incr_num == 9 or incr_num == 10:
                mlag_incr = self.addr_incre['mlag_leaf_ip'] + incr_num + 7
            # Generates MLAG peer IP and adds to dictionary
            self.mlag_peer[self.leaf[incr_num -1]] = str(ip_network(self.addr['mlag_peer_net'], strict=False)[mlag_incr]) + '/30'
            # If MLAG keepalive interface uses mgmt (not a integer) use the mgmt IP
            if isinstance(self.bse_intf['mlag_kalive'], int) == False:
                self.mlag_kalive[self.leaf[incr_num -1]] = self.all_mgmt[self.leaf[incr_num -1]]
             # If MLAG keepalive interface uses an interface (is an integer) generated from keepalive range if defined, if not from peer range
            elif isinstance(self.bse_intf['mlag_kalive'], int) == True:
                self.mlag_kalive[self.leaf[incr_num -1]] = str(ip_network(self.addr.get('mlag_kalive_net', self.addr['mlag_peer_net']),
                                                               strict=False)[mlag_incr + self.addr_incre['mlag_kalive_incre']]) + '/30'
            num_lf -= 1

       # 3c. BORDER: Generates name, management and Loopback IPs (rtr, vtep, mlag, bgw) and adds to self.all_x dictionaries (border_name is the key)
        incr_num, odd_incr_num = (0 for i in range(2))
        while num_bdr != 0:
            incr_num += 1
            self.border.append(self.device_name['border'] + str("%02d" % incr_num))
            if int(self.border[incr_num -1][-2:]) % 2 != 0:
                odd_incr_num += 1
                mlag_ip = str(ip_network(self.addr['lp_net'])[0] + self.addr_incre['border_mlag_lp'] + odd_incr_num -1) + '/32'
                bgw_ip = str(ip_network(self.addr['lp_net'])[0] + self.addr_incre['border_bgw_lp'] + odd_incr_num -1) + '/32'
            self.all_mgmt[self.border[incr_num -1]] = str(ip_network(self.addr['mgmt_net'], strict=False)[self.addr_incre['border_ip'] + incr_num -1])
            rtr_ip = str(ip_network(self.addr['lp_net'])[0] + self.addr_incre['border_ip'] + incr_num - 1) + '/32'
            vtep_ip = str(ip_network(self.addr['lp_net'])[0] + self.addr_incre['border_vtep_lp'] + incr_num - 1) + '/32'
            self.all_lp[self.border[incr_num -1]] = [{'name': self.bse_intf['lp_fmt'] + str(self.lp['rtr']['num']), 'ip': rtr_ip, 'descr': self.lp['rtr']['descr']},
                                                {'name': self.bse_intf['lp_fmt'] + str(self.lp['vtep']['num']), 'ip': vtep_ip, 'descr': self.lp['vtep']['descr'],
                                                'mlag_lp_addr': mlag_ip},
                                                {'name': self.bse_intf['lp_fmt'] + str(self.lp['bgw']['num']), 'ip': bgw_ip, 'descr': self.lp['bgw']['descr']}]
            # Increases the increment for each switchpair to be next /30 out of MLAG peer address range
            if incr_num == 1 or incr_num == 2:
                mlag_incr = self.addr_incre['mlag_border_ip'] + incr_num - 1
            elif incr_num == 3 or incr_num == 4:
                mlag_incr = self.addr_incre['mlag_border_ip'] + incr_num + 1
            # Generates MLAG peer IP and adds to dictionary
            self.mlag_peer[self.border[incr_num -1]] = str(ip_network(self.addr['mlag_peer_net'], strict=False)[mlag_incr]) + '/30'
            # If MLAG keepalive interface uses mgmt (not a integer) use the mgmt IP
            if isinstance(self.bse_intf['mlag_kalive'], int) == False:
                self.mlag_kalive[self.border[incr_num -1]] = self.all_mgmt[self.leaf[incr_num -1]]
             # If MLAG keepalive interface uses an interface (is an integer) generated from keepalive range if defined, if not from peer range
            elif isinstance(self.bse_intf['mlag_kalive'], int) == True:
                self.mlag_kalive[self.border[incr_num -1]] = str(ip_network(self.addr.get('mlag_kalive_net', self.addr['mlag_peer_net']),
                                                               strict=False)[mlag_incr + self.addr_incre['mlag_kalive_incre']]) + '/30'
            num_bdr -= 1

# ============================ 4. Generate all the fabric interfaces  ==========================
# 4. For the uplinks (doesn't include iPs) creates nested dicts with key the device_name and value a dict {sp_name: {intf_num: descr}, {intf_num: descr}}
    def create_intf(self):
        self.all_intf, self.mlag_peer_intf, self.mlag_kalive_intf, mlag_ports  = (defaultdict(dict) for i in range(4))

        # 4a. SPINE: Create nested dictionary of the devices fabric interfaces based on number of leaf and border switches
        for sp in self.spine:
            for lf_num in range(self.network_size['num_leaf']):
                # Loops through the number of leafs using the increment to create the remote device name
                dev_name = 'UPLINK > ' + self.device_name['leaf'] + "{:02d} ".format(lf_num +1) + "- "
                # Creates remote device port using spine number and the leaf_to_spine interface increment
                dev_int = self.bse_intf['intf_short'] + "{:01d}".format(int(sp[-2:]) + self.bse_intf['lf_to_sp'] -1)
                # Interface number got from the starting interface increment (sp_to_lf) and the loop interation (lf_num)
                self.all_intf[sp][self.bse_intf['intf_fmt'] + (str(self.bse_intf['sp_to_lf'] + lf_num))] = dev_name + dev_int
            for bdr_num in range(self.network_size['num_border']):
                dev_name = 'UPLINK > ' + self.device_name['border'] + "{:02d} ".format(bdr_num +1) + "- "
                dev_int = self.bse_intf['intf_short'] + "{:01d}".format(int(sp[-2:]) + self.bse_intf['bdr_to_sp'] -1)
                self.all_intf[sp][self.bse_intf['intf_fmt'] + (str(self.bse_intf['sp_to_bdr'] + bdr_num))] = dev_name + dev_int

        # 4b. LEAF: Create nested dictionary of the devices fabric interfaces based on the number of spine switches
        for lf in self.leaf:
            for sp_num in range(self.network_size['num_spine']):
                dev_name = 'UPLINK > ' + self.device_name['spine'] + "{:02d} ".format(sp_num +1) + "- "
                dev_int = self.bse_intf['intf_short'] + "{:01d}".format(int(lf[-2:]) + self.bse_intf['sp_to_lf'] -1)
                self.all_intf[lf][self.bse_intf['intf_fmt'] + (str(self.bse_intf['lf_to_sp'] + sp_num))] = dev_name + dev_int

        # 4c. BORDER: Create nested dictionary of the devices fabric interfaces based on the number of spine switches
        for bdr in self.border:
            for sp_num in range(self.network_size['num_spine']):
                dev_name = 'UPLINK > ' + self.device_name['spine'] + "{:02d} ".format(sp_num +1) + "- "
                dev_int = self.bse_intf['intf_short'] + "{:01d}".format(int(bdr[-2:]) + self.bse_intf['sp_to_bdr'] -1)
                self.all_intf[bdr][self.bse_intf['intf_fmt'] + (str(self.bse_intf['bdr_to_sp'] + sp_num))] = dev_name + dev_int

        # 4d. BORDER, LEAF: Create nested dictionary for border and leaf MLAG interfaces
        # Create a list of dicts of MLAG ports and their description [{int_name: short_int_name < function}]
        mlag_ports[self.bse_intf['mlag_fmt'] + str(self.mlag['peer_po'])] = self.bse_intf['mlag_short'] + str(self.mlag['peer_po']) + ' < MLAG Peer-link'
        for intf_num in self.bse_intf['mlag_peer'].split('-'):
            mlag_ports[self.bse_intf['intf_fmt'] + intf_num] = self.bse_intf['intf_short'] + intf_num + ' < Peer-link'
            if isinstance(self.bse_intf['mlag_kalive'], int) == True:
                mlag_ports[self.bse_intf['intf_fmt'] + str(self.bse_intf['mlag_kalive'])] = self.bse_intf['intf_short'] \
                                                                                            + str(self.bse_intf['mlag_kalive']) + ' < MLAG Keepalive'
        # Add full description to each port
        for dev in self.leaf + self.border:
            for intf, intf_short in mlag_ports.items():
                # If is keepalive link and device_name ends in an odd number increment the device_name by 1
                if intf == self.bse_intf['intf_fmt'] + str(self.bse_intf['mlag_kalive']) and int(dev[-2:]) % 2 != 0:
                    self.mlag_kalive_intf[dev][intf] = 'UPLINK > ' + dev[:-2] + "{:02d} - ".format(int(dev[-2:]) +1) + intf_short
                # If device_name ends in an odd number increment the device_name by 1
                elif int(dev[-2:]) % 2 != 0:
                    self.mlag_peer_intf[dev][intf] = 'UPLINK > ' + dev[:-2] + "{:02d} - ".format(int(dev[-2:]) +1) + intf_short
                # If device_name ends in an even number decreases the device_name by 1
                elif intf == self.bse_intf['intf_fmt'] + str(self.bse_intf['mlag_kalive']):
                    self.mlag_kalive_intf[dev][intf] = 'UPLINK > ' + dev[:-2] + "{:02d} - ".format(int(dev[-2:]) -1) + intf_short
                else:                           # If device_name ends in an even number
                    self.mlag_peer_intf[dev][intf] = 'UPLINK > ' + dev[:-2] + "{:02d} - ".format(int(dev[-2:]) -1) + intf_short


# ============================ 5. Create the inventory ==========================
# 5. Adds groups, hosts and host_vars to create the inventory file
    def create_inventory(self):
        # Creates list of groups created from the device names
        groups = [self.device_name['spine'].split('-')[-1].lower(), self.device_name['border'].split('-')[-1].lower(),
                  self.device_name['leaf'].split('-')[-1].lower()]

        #5a. Creates all the group, they are automatically added to the 'all' group
        for gr in groups:
            self.inventory.add_group(gr)
            # Creates the host entries, os and mlag_lp_addr host_var (although assigned to group in the cmd)
            if gr in self.device_name['spine'].lower():
                for sp in self.spine:
                    self.inventory.add_host(sp, gr)
                    self.inventory.set_variable(gr, 'ansible_network_os', self.device_os['spine_os'])
                    self.inventory.set_variable(gr, 'num_intf', self.num_intf['spine'])
            if gr in self.device_name['border'].lower():
                for br in self.border:
                    self.inventory.add_host(br, gr)
                    self.inventory.set_variable(gr, 'ansible_network_os', self.device_os['border_os'])
                    self.inventory.set_variable(gr, 'num_intf', self.num_intf['border'])
            if gr in self.device_name['leaf'].lower():
                for lf in self.leaf:
                    self.inventory.add_host(lf, gr)
                    self.inventory.set_variable(gr, 'ansible_network_os', self.device_os['leaf_os'])
                    self.inventory.set_variable(gr, 'num_intf', self.num_intf['leaf'])

        #5b. Adds host_vars for all the IP dictionaries created in 'create_ip' method
        for host, mgmt_ip in self.all_mgmt.items():
            self.inventory.set_variable(host, 'ansible_host', mgmt_ip)
        for host, lp in self.all_lp.items():
            self.inventory.set_variable(host, 'intf_lp', lp)
        for host, mlag_peer in self.mlag_peer.items():
            self.inventory.set_variable(host, 'mlag_peer_ip', mlag_peer)
        for host, mlag_kalive in self.mlag_kalive.items():
            self.inventory.set_variable(host, 'mlag_kalive_ip', mlag_kalive)

        #5c. Adds host_vars for all the Interface dictionaries created in 'create_intf' method
        for host, int_details in self.all_intf.items():
            self.inventory.set_variable(host, 'intf_fbc', int_details)
        for host, int_details in self.mlag_peer_intf.items():
            self.inventory.set_variable(host, 'intf_mlag_peer', int_details)
        for host, int_details in self.mlag_kalive_intf.items():
            self.inventory.set_variable(host, 'intf_mlag_kalive', int_details)


# ============================ 2. Parse data from config file ==========================
# !!!! The parse method is always auto-run, so is what starts the plugin and runs any custom methods !!!!

# 2. This Ansible pre-defined method pulls the data from the config file and creates variables for it.
    def parse(self, inventory, loader, path, cache=False):
        # Inherited methods: inventory creates inv, loader loads vars from cfg file and path is path to cfg file
        super(InventoryModule, self).parse(inventory, loader, path)

        # 2a. Read the data from the config file and create variables. !!! The options MUST be defined in DOCUMENTATION options section !!!
        self._read_config_data(path)
        var_files = self.get_option('var_files')           # List of the Ansible variable files (in vars)
        var_dicts = self.get_option('var_dicts')           # Dictionary of {var_filename, list_of_dictionary_names_within_that_var_file}

        # 2b. Loads the var files and makes a new dictionary of dictionaries holding contents of each var file in format {file_name:file_contents}
        all_vars = {}
        mydir = os.getcwd()                 # Gets current directory
        for dict_name, file_name in zip(var_dicts.keys(), var_files):
            with open(os.path.join(mydir, 'vars/') + file_name, 'r') as file_content:
                all_vars[dict_name] = yaml.load(file_content, Loader=yaml.FullLoader)

        # 2c. Create new variables of only those needed from the dict created in the last step (all_vars)
        # As it loops through list in cfg file is easy to add more variables in the future
        for file_name, var_names in var_dicts.items():
            for each_var in var_names:
                if each_var == 'device_os':
                    self.device_os = all_vars[file_name]['ans'][each_var]
                elif each_var == 'device_name':
                    self.device_name = all_vars[file_name]['bse'][each_var]
                elif each_var == 'addr':
                    self.addr = all_vars[file_name]['bse'][each_var]
                elif each_var == 'network_size':
                    self.network_size = all_vars[file_name]['fbc'][each_var]
                elif each_var == 'num_intf':
                    self.num_intf = all_vars[file_name]['fbc'][each_var]
                elif each_var == 'bse_intf':
                    self.bse_intf = all_vars[file_name]['fbc']['adv'][each_var]
                elif each_var == 'lp':
                    self.lp = all_vars[file_name]['fbc']['adv'][each_var]
                elif each_var == 'mlag':
                    self.mlag = all_vars[file_name]['fbc']['adv'][each_var]
                elif each_var == 'addr_incre':
                    self.addr_incre = all_vars[file_name]['fbc']['adv'][each_var]

        # 3. Creates a data model of the hostnames and device specific IP interface addresses
        self.create_ip()
        # 4. Creates a data model of all the fabric interfaces
        self.create_intf()
        # 5. Uses  the data models to create the inventory containing groups, hosts and host_vars
        self.create_inventory()


   # Example ways to test variable format is correct before running other methods
        # test = self.addr['lp_net']
        # test = config.get('device_name')[0]['spine']
        # self.inventory.add_host(test)

    # To use error handling within the plugin use this format
        # try:
        #     cause_an_exception()
        # except Exception as e:
        #     raise AnsibleError('Something happened, this was original exception: %s' % to_native(e))

        # self.inventory.add_host(a)