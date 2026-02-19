#
# (c) 2017 Red Hat Inc.
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.
#
from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = """
author: Ansible Networking Team (@ansible-network)
name: junos
short_description: Use junos cliconf to run command on Juniper Junos OS platform
description:
- This junos plugin provides low level abstraction apis for sending and receiving
  CLI commands from Juniper Junos OS network devices.
version_added: 1.0.0
deprecated:
  removed_from_collection: junipernetworks.junos
  removed_at_date: '2028-04-01'
  why: The junipernetworks.junos collection is deprecated. Redirects will be removed after 2028-04-01.
  alternative: Use the juniper.device collection instead.
options:
  config_commands:
    description:
    - Specifies a list of commands that can make configuration changes to the target device.
    - When C(ansible_network_single_user_mode) is enabled, if a command sent to the device is present in this list, the existing cache is invalidated.
    type: list
    elements: str
    default: []
    vars:
    - name: ansible_junos_config_commands
    version_added: 2.0.0
"""

from ansible_collections.juniper.device.plugins.cliconf.junos import Cliconf


class Cliconf(Cliconf):
    pass
