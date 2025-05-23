# -*- coding: utf-8 -*-

#
# Copyright (c) 2017-2020, Juniper Networks Inc. All rights reserved.
#
# License: Apache 2.0
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright
#   notice, this list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# * Neither the name of the Juniper Networks nor the
#   names of its contributors may be used to endorse or promote products
#   derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY Juniper Networks, Inc. ''AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL Juniper Networks, Inc. BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

from __future__ import absolute_import, division, print_function


__metaclass__ = type

import hashlib
import json
import logging
import os

# Standard library imports
from argparse import ArgumentParser


try:
    import jnpr

    HAS_PYEZ_JNPR = True
except ImportError:
    HAS_PYEZ_JNPR = False
try:
    import xmltodict

    HAS_XMLTODICT = True
except ImportError:
    HAS_XMLTODICT = False
from ansible.module_utils._text import to_bytes
from ansible.module_utils.basic import AnsibleModule, boolean
from ansible.module_utils.common.validation import check_type_dict

# Ansible imports
from ansible.module_utils.connection import Connection
from ansible.module_utils.six import string_types


try:
    from jnpr.junos.utils.sw import SW

    HAS_PYEZ_SW = True
except ImportError:
    HAS_PYEZ_SW = False
try:
    from jnpr.junos.utils.ftp import FTP

    HAS_PYEZ_FTP = True
except ImportError:
    HAS_PYEZ_FTP = False
try:
    from jnpr.junos.utils.scp import SCP

    HAS_PYEZ_SW = True
except ImportError:
    HAS_PYEZ_SW = False
try:
    from jnpr.junos import exception as pyez_exception

    HAS_PYEZ_EXCEPTION = True
except ImportError:
    HAS_PYEZ_EXCEPTION = False
try:
    from ncclient.operations.errors import TimeoutExpiredError

    HAS_NCCLIENT = True
except ImportError:
    HAS_NCCLIENT = False
try:
    import ncclient.operations.errors as ncclient_exception

    HAS_NCCLIENT_EXCEPTIONS = True
except ImportError:
    HAS_NCCLIENT_EXCEPTIONS = False

from ansible_collections.juniper.device.plugins.module_utils import configuration as cfg


class ModuleDocFragment(object):
    """Documentation fragment for connection-related parameters.

    All modules share a common set of connection parameters
    which are documented in this class.

    Attributes:
        CONNECTION_DOCUMENTATION: The documentation string defining the
                                  connection-related parameters for the
                                  modules.
        LOGGING_DOCUMENTATION: The documentation string defining the
                               logging-related parameters for the
                               modules.
    """

    # The connection-specific options. Defined here so it can be re-used as
    # suboptions in provider.
    _CONNECT_DOCUMENTATION = """
      attempts:
        description:
          - The number of times to try connecting and logging in to the Junos
            device. This option is only applicable when using C(mode = 'telnet')
            or C(mode = 'serial'). Mutually exclusive with the I(console)
            option.
        required: false
        default: 10
        type: int
      baud:
        description:
          - The serial baud rate, in bits per second, used to connect to the
            Junos device. This option is only applicable when using
            C(mode = 'serial'). Mutually exclusive with the I(console) option.
        required: false
        default: 9600
        type: int
      console:
        description:
          - An alternate method of specifying a NETCONF over serial console
            connection to the Junos device using Telnet to a console server.
            The value of this option must be a string in the format
            C(--telnet <console_hostname>,<console_port_number>).
            This option is deprecated. It is present only for backwards
            compatibility. The string value of this option is exactly equivalent
            to specifying I(host) with a value of C(<console_hostname>),
            I(mode) with a value of C(telnet), and I(port) with a value of
            C(<console_port_number>). Mutually exclusive with the I(mode),
            I(port), I(baud), and I(attempts) options.
        required: false
        default: none
        type: str
      host:
        description:
          - The hostname or IP address of the Junos device to which the
            connection should be established. This is normally the Junos device
            itself, but is the hostname or IP address of a console server when
            connecting to the console of the device by setting the I(mode)
            option to the value C(telnet). This option is required, but does not
            have to be specified explicitly by the user because it defaults to
            C({{ inventory_hostname }}).
        required: true
        default: C({{ inventory_hostname }})
        type: str
        aliases:
          - hostname
          - ip
      mode:
        description:
          - The PyEZ mode used to establish a NETCONF connection to the Junos
            device. A value of C(none) uses the default NETCONF over SSH mode.
            Depending on the values of the I(host) and I(port) options, a value
            of C(telnet) results in either a direct NETCONF over Telnet
            connection to the Junos device, or a NETCONF over serial console
            connection to the Junos device using Telnet to a console server.
            A value of C(serial) results in a NETCONF over serial console
            connection to the Junos device. Mutually exclusive with the
            I(console) option.
        required: false
        default: none
        type: str
        choices:
          - none
          - telnet
          - serial
      passwd:
        description:
          - The password, or ssh key's passphrase, used to authenticate with the
            Junos device. If this option is not specified, authentication is
            attempted using an empty password, or ssh key passphrase.
        required: false
        default: The first defined value from the following list
                 1) The C(ANSIBLE_NET_PASSWORD) environment variable.
                    (used by Ansible Tower)
                 2) The value specified using the C(-k) or C(--ask-pass)
                    command line arguments to the C(ansible) or
                    C(ansible-playbook) command.
                 3) none (An empty password/passphrase)
        type: str
        aliases:
          - password
      port:
        description:
          - The TCP port number or serial device port used to establish the
            connection. Mutually exclusive with the I(console) option.
        required: false
        default: C(830) if C(mode = none), C(23) if C(mode = 'telnet'),
                 C('/dev/ttyUSB0') if (mode = 'serial')
        type: int or str
      ssh_private_key_file:
        description:
          - The path to the SSH private key file used to authenticate with the
            Junos device. If this option is not specified, and no default value
            is found using the algorithm below, then the SSH private key file
            specified in the user's SSH configuration, or the
            operating-system-specific default is used.
          - This must be in the RSA PEM format, and not the newer OPENSSH
            format. To check if the private key is in the correct format, issue
            the command `head -n1 ~/.ssh/some_private_key` and ensure that
            it's RSA and not OPENSSH. To create a key in the RSA PEM format,
            issue the command `ssh-keygen -m PEM -t rsa -b 4096`. To convert
            an OPENSSH key to an RSA key, issue the command `ssh-keygen -p -m
            PEM -f ~/.ssh/some_private_key`
        required: false
        default: The first defined value from the following list
                 1) The C(ANSIBLE_NET_SSH_KEYFILE) environment variable.
                    (used by Ansible Tower)
                 2) The value specified using the C(--private-key) or
                    C(--key-file) command line arguments to the C(ansible) or
                    C(ansible-playbook) command.
                 3) none (the file specified in the user's SSH configuration,
                          or the operating-system-specific default)
        type: path
        aliases:
          - ssh_keyfile
      ssh_config:
        description:
          - The path to the SSH client configuration file. If this option is not
            specified, then the PyEZ Device instance by default queries file
            ~/.ssh/config.
        required: false
        type: path
      timeout:
        description:
          - The maximum number of seconds to wait for RPC responses from the
            Junos device. This option does NOT control the initial connection
            timeout value.
        required: false
        default: 30
        type: int
      user:
        description:
          - The username used to authenticate with the Junos device. This option
            is required, but does not have to be specified explicitly by the
            user due to the algorithm for determining the default value.
        required: true
        default: The first defined value from the following list
                 1) The C(ANSIBLE_NET_USERNAME) environment variable.
                    (used by Ansible Tower)
                 2) The C(remote_user) as defined by Ansible. Ansible sets this
                    value via several methods including
                    a) C(-u) or C(--user) command line arguments to the
                       C(ansible) or C(ansible-playbook) command.
                    b) C(ANSIBLE_REMOTE_USER) environment variable.
                    c) C(remote_user) configuration setting.
                    See the Ansible documentation for the precedence used to set
                    the C(remote_user) value.
                3) The C(USER) environment variable.
        type: str
        aliases:
          - username
      cs_user:
        description:
          - The username used to authenticate with the console server over SSH.
            This option is only required if you want to connect to a device over console
             using SSH as transport. Mutually exclusive with the I(console) option.
        required: false
        type: str
        aliases:
          - console_username
      cs_passwd:
        description:
          - The password used to authenticate with the console server over SSH.
            This option is only required if you want to connect to a device over console
             using SSH as transport. Mutually exclusive with the I(console) option.
        required: false
        type: str
        aliases:
          - console_password
      huge_tree:
        description:
          - Parse XML with very deep trees and long text content.
        required: false
        type: bool
        default: false
"""

    LOGGING_DOCUMENTATION = """
    logging_options:
      logdir:
        description:
          - The path to a directory, on the Ansible control machine, where
            debugging information for the particular task is logged.
          - If this option is specified, debugging information is logged to a
            file named C({{ inventory_hostname }}.log) in the directory
            specified by the I(logdir) option.
          - The log file must be writeable. If the file already exists, it is
            appended. It is the users responsibility to delete/rotate log files.
          - The level of information logged in this file is controlled by
            Ansible's verbosity, debug options and level option in task
          - 1) By default, messages at level C(WARNING) or higher are logged.
          - 2) If the C(-v) or C(--verbose) command-line options to the
               C(ansible-playbook) command are specified, messages at level
               C(INFO) or higher are logged.
          - 3) If the C(-vv) (or more verbose) command-line option to the
               C(ansible-playbook) command is specified, or the C(ANSIBLE_DEBUG)
               environment variable is set, then messages at level C(DEBUG) or
               higher are logged.
          - 4) If C(level) is mentioned then messages at level C(level) or more are
               logged.
          - The I(logfile) and I(logdir) options are mutually exclusive. The
            I(logdir) option is recommended for all new playbooks.
        required: false
        default: none
        type: path
        aliases:
          - log_dir
      logfile:
        description:
          - The path to a file, on the Ansible control machine, where debugging
            information for the particular task is logged.
          - The log file must be writeable. If the file already exists, it is
            appended. It is the users responsibility to delete/rotate log files.
          - The level of information logged in this file is controlled by
            Ansible's verbosity, debug options and level option in task
          - 1) By default, messages at level C(WARNING) or higher are logged.
          - 2) If the C(-v) or C(--verbose) command-line options to the
               C(ansible-playbook) command are specified, messages at level
               C(INFO) or higher are logged.
          - 3) If the C(-vv) (or more verbose) command-line option to the
               C(ansible-playbook) command is specified, or the C(ANSIBLE_DEBUG)
               environment variable is set, then messages at level C(DEBUG) or
               higher are logged.
          - 4) If C(level) is mentioned then messages at level C(level) or more are
               logged.
          - When tasks are executed against more than one target host,
            one process is forked for each target host. (Up to the maximum
            specified by the forks configuration. See
            U(forks|http://docs.ansible.com/ansible/latest/intro_configuration.html#forks)
            for details.) This means that the value of this option must be
            unique per target host. This is usually accomplished by including
            C({{ inventory_hostname }}) in the I(logfile) value. It is the
            user's responsibility to ensure this value is unique per target
            host.
          - For this reason, this option is deprecated. It is maintained for
            backwards compatibility. Use the I(logdir) option in new playbooks.
            The I(logfile) and I(logdir) options are mutually exclusive.
        required: false
        default: none
        type: path
        aliases:
          - log_file
      level:
        description:
          - The level of information to be logged can be modified using this option
          - 1) By default, messages at level C(WARNING) or higher are logged.
          - 2) If the C(-v) or C(--verbose) command-line options to the
               C(ansible-playbook) command are specified, messages at level
               C(INFO) or higher are logged.
          - 3) If the C(-vv) (or more verbose) command-line option to the
               C(ansible-playbook) command is specified, or the C(ANSIBLE_DEBUG)
               environment variable is set, then messages at level C(DEBUG) or
               higher are logged.
          - 4) If C(level) is mentioned then messages at level C(level) or more are
               logged.
        required: false
        default: WARNING
        type: str
        choices:
          - INFO
          - DEBUG


"""

    # _SUB_CONNECT_DOCUMENTATION is just _CONNECT_DOCUMENTATION with each
    # line indented.
    _SUB_CONNECT_DOCUMENTATION = ""
    for line in _CONNECT_DOCUMENTATION.splitlines(True):
        _SUB_CONNECT_DOCUMENTATION += "    " + line

    # Build actual DOCUMENTATION string by putting the pieces together.
    CONNECTION_DOCUMENTATION = (
        """
    connection_options:"""
        + _CONNECT_DOCUMENTATION
        + """
    requirements:
      - U(junos-eznc|https://github.com/Juniper/py-junos-eznc) >= """
        + cfg.MIN_PYEZ_VERSION
        + """
      - Python >= 3.5
    notes:
      - The NETCONF system service must be enabled on the target Junos device.
"""
    )


# The common argument specification for connecting to Junos devices.
connection_spec = {
    "host": dict(
        type="str",
        # Required at top-level.
        required=False,
        aliases=["hostname", "ip"],
        # See documentation for real default behavior.
        # Default behavior coded in JuniperJunosActionModule.run()
        default=None,
    ),
    "user": dict(
        type="str",
        # Required at top-level.
        required=False,
        aliases=["username"],
        # See documentation for real default behavior.
        # Default behavior coded in JuniperJunosActionModule.run()
        default=None,
    ),
    "passwd": dict(
        type="str",
        required=False,
        aliases=["password"],
        # See documentation for real default behavior.
        # Default behavior coded in JuniperJunosActionModule.run()
        default=None,
        no_log=True,
    ),
    "cs_user": dict(
        type="str",
        aliases=["console_username"],
        required=False,
        default=None,
    ),
    "cs_passwd": dict(
        type="str",
        aliases=["console_password"],
        required=False,
        default=None,
        no_log=True,
    ),
    "ssh_private_key_file": dict(
        type="path",
        required=False,
        aliases=["ssh_keyfile"],
        # See documentation for real default behavior.
        # Default behavior coded in
        # JuniperJunosActionModule.run()
        default=None,
    ),
    "ssh_config": dict(type="path", required=False, default=None),
    "mode": dict(choices=[None, "telnet", "serial"], default=None),
    "console": dict(type="str", required=False, default=None),
    "port": dict(
        type="str",
        required=False,
        # See documentation for real default behavior.
        # Default behavior coded in JuniperJunosModule.__init__()
        default=None,
    ),
    "baud": dict(
        type="int",
        required=False,
        # See documentation for real default behavior.
        # Default behavior coded in JuniperJunosModule.__init__()
        default=None,
    ),
    "attempts": dict(
        type="int",
        required=False,
        # See documentation for real default behavior.
        # Default behavior coded in JuniperJunosModule.__init__()
        default=None,
    ),
    "timeout": dict(type="int", required=False, default=30),
    "huge_tree": dict(type="bool", required=False, default=False),
}

# Connection arguments which are mutually exclusive.
connection_spec_mutually_exclusive = [
    ["mode", "console"],
    ["port", "console"],
    ["baud", "console"],
    ["attempts", "console"],
    ["cs_user", "console"],
    ["cs_passwd", "console"],
]

# Specify the logging spec.
logging_spec = {
    "logfile": dict(type="path", required=False, default=None),
    "logdir": dict(type="path", required=False, default=None),
    "level": dict(choices=[None, "INFO", "DEBUG"], required=False, default=None),
}

# The logdir and logfile options are mutually exclusive.
logging_spec_mutually_exclusive = ["logfile", "logdir"]

# Other logging names which should be logged to the logfile
additional_logger_names = ["ncclient", "paramiko"]

# top_spec is connection_spec + logging_spec
top_spec = connection_spec

top_spec.update(logging_spec)
top_spec_mutually_exclusive = connection_spec_mutually_exclusive
top_spec_mutually_exclusive += logging_spec_mutually_exclusive

# "Hidden" arguments which are passed between the action plugin and the
# Junos module, but which should not be visible to users.
internal_spec = {
    "_module_utils_path": dict(type="path", default=None),
    "_module_name": dict(type="str", default=None),
    "_inventory_hostname": dict(type="str", default=None),
    "_connection": dict(type="str", default=None),
}

# Known RPC output formats
RPC_OUTPUT_FORMAT_CHOICES = ["text", "xml", "json"]

# Known configuration formats
CONFIG_FORMAT_CHOICES = ["xml", "set", "text", "json"]
# Known configuration databases
CONFIG_DATABASE_CHOICES = ["candidate", "committed"]
# Known configuration actions
CONFIG_ACTION_CHOICES = [
    "set",
    "merge",
    "update",
    "replace",
    "override",
    "overwrite",
    "patch",
]
# Supported configuration modes
CONFIG_MODE_CHOICES = ["exclusive", "private", "dynamic", "batch", "ephemeral"]
# Supported configuration models
CONFIG_MODEL_CHOICES = ["openconfig", "custom", "ietf", "True"]


class JuniperJunosModule(AnsibleModule):
    """A subclass of AnsibleModule used by all modules.

    All modules share common behavior which is implemented in
    this class.

    Attributes:
        dev: An instance of a PyEZ Device() object.

    Public Methods:
        exit_json: Close self.dev and call parent's exit_json().
        fail_json: Close self.dev and call parent's fail_json().
        check_pyez: Verify the PyEZ library is present and functional.
        check_jsnapy: Verify the JSNAPy library is present and functional.
        check_jxmlease: Verify the Jxmlease library is present and functional.
        check_lxml_etree: Verify the lxml Etree library is present and
                          functional.
        check_yaml: Verify the YAML library is present and functional.
        parse_arg_to_list_of_dicts: Parses string_val into a list of dicts.
        parse_ignore_warning_option: Parses the ignore_warning option.
        parse_rollback_option: Parses the rollback option.
        open: Open self.dev.
        close: Close self.dev.
        add_sw: Add an instance of jnp.junos.utils.sw.SW() to self.
        open_configuration: Open cand. conf. db in exclusive/private/dynamic/batch/ephemeral mode.
        close_configuration: Close candidate configuration database.
        get_configuration: Return the device config. in the specified format.
        rollback_configuration: Rollback device config. to the specified id.
        check_configuration: Check the candidate configuration.
        diff_configuration: Diff the candidate and committed configurations.
        load_configuration: Load the candidate configuration.
        commit_configuration: Commit the candidate configuration.
        ping: Execute a ping command from a Junos device.
        save_text_output: Save text output into a file.
    """

    # Method overrides
    def __init__(
        self,
        argument_spec=None,
        mutually_exclusive=None,
        min_pyez_version=cfg.MIN_PYEZ_VERSION,
        min_lxml_etree_version=cfg.MIN_LXML_ETREE_VERSION,
        min_jsnapy_version=None,
        min_jxmlease_version=None,
        min_yaml_version=None,
        **kwargs,
    ):
        """Initialize a new JuniperJunosModule instance.

        Combines module-specific parameters with the common parameters shared
        by all modules. Performs additional checks on options.
        Checks the minimum PyEZ version. Creates and opens the PyEZ Device instance.

        Args:
            agument_spec: Module-specific argument_spec added to top_spec.
            mutually_exclusive: Module-specific mutually exclusive added to
                                top_spec_mutually_exclusive.
            min_pyez_version: The minimum PyEZ version required by the module.
                              Since all modules require PyEZ this defaults to
                              MIN_PYEZ_VERSION.
            min_lxml_etree_version: The minimum lxml Etree version required by
                                    the module. Since most modules require
                                    lxml Etree this defaults to
                                    MIN_LXML_ETREE_VERSION.
            min_jsnapy_version: The minimum JSNAPy version required by the
                                module. If this is None, the default, it
                                means the module does not explicitly require
                                jsnapy.
            min_jxmlease_version: The minimum Jxmlease version required by the
                                  module. If this is None, the default, it
                                  means the module does not explicitly require
                                  jxmlease.
            min_yanml_version: The minimum YAML version required by the
                               module. If this is None, the default, it
                               means the module does not explicitly require
                               yaml.
            **kwargs: All additional keyword arguments are passed to
                      AnsibleModule.__init__().

        Returns:
            A JuniperJunosModule instance object.
        """

        if mutually_exclusive is None:
            mutually_exclusive = []
        if argument_spec is None:
            argument_spec = {}
        # initialize default values here for error scenario while super is called

        # by default local
        self.conn_type = "local"
        # Initialize the dev attribute
        self.dev = None
        # Initialize the config attribute
        self.config = None

        # Update argument_spec with the internal_spec
        argument_spec.update(internal_spec)
        # Update argument_spec with the top_spec
        argument_spec.update(top_spec)
        # Extend mutually_exclusive with connection_mutually_exclusive
        mutually_exclusive += top_spec_mutually_exclusive
        # Call parent's __init__()
        super(JuniperJunosModule, self).__init__(
            argument_spec=argument_spec,
            mutually_exclusive=mutually_exclusive,
            **kwargs,
        )

        # initialize the parameters
        self.initialize_params()

        # Remove any arguments in internal_spec
        for arg_name in internal_spec:
            self.params.pop(arg_name)

        # check software compatibility for various 3rd party tools used
        ret_output = cfg.check_sw_compatibility(
            min_pyez_version,
            min_lxml_etree_version,
            min_jsnapy_version,
            min_jxmlease_version,
            min_yaml_version,
        )

        if ret_output != "success":
            self.fail_json(msg="%s" % ret_output)

        self.pyez_factory_loader = jnpr.junos.factory.factory_loader
        self.pyez_factory_table = jnpr.junos.factory.table
        self.pyez_op_table = jnpr.junos.op
        self.pyez_exception = pyez_exception
        self.ncclient_exception = ncclient_exception
        self.etree = cfg.etree
        self.jxmlease = cfg.jxmlease
        self.yaml = cfg.yaml

        if min_jsnapy_version is not None:
            self.jsnapy = jnpr.jsnapy

        # Setup logging.
        self.logger = self._setup_logging()

        # Open the PyEZ connection
        if self.conn_type == "local":
            self.open()
        else:
            self._pyez_conn = self.get_connection()

    def initialize_params(self):
        """
        Initalize the parameters in common module
        """
        # priority for arguments is inventory < tasks < console

        self.module_name = self.params.get("_module_name")
        self.inventory_hostname = self.params.get("_inventory_hostname")
        self.conn_type = self.params.get("_connection")

        # Parse the console option
        self._parse_console_options()

        # Check that we have a user and host
        if not self.params.get("host"):
            self.fail_json(msg="missing required arguments: host")
        if not self.params.get("user"):
            self.fail_json(msg="missing required arguments: user")

        # Default port based on mode.
        if self.params.get("port") is None:
            if self.params.get("mode") == "telnet":
                self.params["port"] = 23
            elif self.params.get("mode") == "serial":
                self.params["port"] = "/dev/ttyUSB0"
            else:
                self.params["port"] = 830
        else:
            if self.params.get("mode") != "serial":
                try:
                    self.params["port"] = int(self.params["port"])
                except ValueError:
                    self.fail_json(
                        msg="The port option (%s) must be an "
                        "integer value." % (self.params["port"]),
                    )
            else:
                self.params["port"] = self.params["port"]

        if self.params.get("mode") == "telnet" or self.params.get("mode") == "serial":
            if self.params.get("baud") is None:
                # Default baud if serial or telnet mode
                self.params["baud"] = 9600
            if self.params.get("attempts") is None:
                # Default attempts if serial or telnet mode
                self.params["attempts"] = 10
        else:
            if self.params.get("baud") is not None:
                self.fail_json(
                    msg="The baud option (%s) is not valid when "
                    "mode == none." % (self.params.get("baud")),
                )
            if self.params.get("attempts") is not None:
                self.fail_json(
                    msg="The attempts option (%s) is not valid when "
                    "mode == none." % (self.params.get("attempts")),
                )

    def get_connection(self):
        if hasattr(self, "_pyez_connection"):
            return self._pyez_connection
        try:
            capabilities = self.get_capabilities()
        except ConnectionError:
            self.logger.debug("Connection might be local")
            return
            # module.fail_json(msg=to_text(exc, errors="surrogate_then_replace"))
        network_api = capabilities.get("network_api")
        if network_api == "pyez":
            self._pyez_connection = Connection(self._socket_path)
        else:
            self.fail_json(msg="Invalid connection type %s" % network_api)
        return self._pyez_connection

    def get_capabilities(self):
        if hasattr(self, "_pyez_junos_capabilities"):
            return self._pyez_junos_capabilities
        try:
            capabilities = Connection(self._socket_path).get_capabilities()
        except ConnectionError as exc:
            raise exc
            # module.fail_json(msg=to_text(exc, errors="surrogate_then_replace"))
        self._pyez_junos_capabilities = json.loads(capabilities)
        return self._pyez_junos_capabilities

    def exit_json(self, **kwargs):
        """Close self.dev and call parent's exit_json().

        Args:
            **kwargs: All keyword arguments are passed to
                      AnsibleModule.exit_json().
        """
        # Close the connection.
        if self.conn_type == "local":
            try:
                self.close()
            except TimeoutExpiredError:
                if hasattr(self, "logger"):
                    self.logger.debug("Ignoring dev.close() timeout error")
        if hasattr(self, "logger"):
            self.logger.debug("Exit JSON: %s", kwargs)
        # Call the parent's exit_json()
        super(JuniperJunosModule, self).exit_json(**kwargs)

    def fail_json(self, **kwargs):
        """Close self.dev and call parent's fail_json().

        Args:
            **kwargs: All keyword arguments are passed to
                      AnsibleModule.fail_json().
        """
        # Close the configuration
        self.close_configuration()
        # Close the connection.
        # if self.conn_type == "local":
        try:
            self.close()
        except TimeoutExpiredError:
            if hasattr(self, "logger"):
                self.logger.debug("Ignoring dev.close() timeout error")
        if hasattr(self, "logger"):
            self.logger.debug("Fail JSON: %s", kwargs)
        # Call the parent's fail_json()
        super(JuniperJunosModule, self).fail_json(**kwargs)

    # JuniperJunosModule-specific methods below this point.

    def _parse_console_options(self):
        """Parse the console option value.

        Parse the console option value and turn it into the equivalent:
        host, mode, baud, attempts, and port options.
        """
        if self.params.get("console") is not None:
            try:
                console_string = self.params.get("console")

                # Subclass ArgumentParser to simply raise a ValueError
                # rather than printing to stderr and calling sys.exit()
                class QuiteArgumentParser(ArgumentParser):
                    def error(self, message):
                        raise ValueError(message)

                # Parse the console_string.
                parser = QuiteArgumentParser(add_help=False)
                parser.add_argument("-t", "--telnet", default=None)
                parser.add_argument("-p", "--port", default=None)
                parser.add_argument("-b", "--baud", default=None)
                parser.add_argument("-a", "--attempts", default=None)
                parser.add_argument("--timeout", default=None)
                con_params = vars(parser.parse_args(console_string.split()))

                telnet_params = con_params.get("telnet", None)
                # mode == 'telnet'
                if telnet_params is not None:
                    # Split on ,
                    host_port = telnet_params.split(",", 1)
                    # Strip any leading/trailing whitespace or equal sign
                    # from host
                    host = host_port[0].strip(" ")
                    # Try to convert port to an int.
                    port = int(host_port[1])
                    # Successfully parsed. Set params values
                    self.params["mode"] = "telnet"
                    self.params["host"] = host
                    self.params["port"] = port
                # mode == serial
                else:
                    port = con_params.get("port", None)
                    baud = con_params.get("baud", None)
                    attempts = con_params.get("attempts", None)
                    timeout = con_params.get("timeout", None)  # not used
                    self.params["mode"] = "serial"
                    if port is not None:
                        self.params["port"] = port
                    if baud is not None:
                        self.params["baud"] = baud
                    if attempts is not None:
                        self.params["attempts"] = attempts

                # Remove the console option.
                self.params.pop("console")

            except ValueError as ex:
                self.fail_json(
                    msg="Unable to parse the console value (%s). "
                    "Error: %s" % (console_string, str(ex)),
                )
            except Exception:
                self.fail_json(
                    msg="Unable to parse the console value (%s). "
                    "The value of the console argument is "
                    "typically in the format '--telnet "
                    "<console_hostname>,<console_port_number>'." % (console_string),
                )

    def _setup_logging(self):
        """Setup logging for the module.

        Performs several tasks to setup logging for the module. This includes:
        1) Creating a Logger instance object for the name
           jnpr.ansible_module.<mod_name>.
        2) Sets the level for the Logger object depending on verbosity and
           debug settings specified by the user.
        3) Sets the level for other Logger objects specified in
           additional_logger_names depending on verbosity and
           debug settings specified by the user.
        4) If the logfile or logdir option is specified, attach a FileHandler
           instance which logs messages from jnpr.ansible_module.<mod_name> or
           any of the names in additional_logger_names.

        Returns:
            Logger instance object for the name jnpr.ansible_module.<mod_name>.
        """

        class CustomAdapter(logging.LoggerAdapter):
            """
            Prepend the hostname, in brackets, to the log message.
            """

            def process(self, msg, kwargs):
                return "[%s] %s" % (self.extra["host"], msg), kwargs

        # Default level to log.
        level = logging.WARNING
        # Log more if ANSIBLE_DEBUG or -v[v] is set.
        if self._debug is True:
            level = logging.DEBUG
        elif self._verbosity == 1:
            level = logging.INFO
        elif self._verbosity > 1:
            level = logging.DEBUG
        # Set level as mentioned in task
        elif self.params.get("level") is not None:
            level = self.params.get("level")
        # Get the logger object to be used for our logging.
        logger = logging.getLogger("jnpr.ansible_module." + self.module_name)
        # Attach the NullHandler to avoid any errors if no logging is needed.
        logger.addHandler(logging.NullHandler())
        # Set the logging level for the modules logging. This will also control
        # the amount of logging which goes into Ansible's log file.
        logger.setLevel(level)
        # Set the logging level for additional names. This will also control
        # the amount of logging which goes into Ansible's log file.
        for name in additional_logger_names:
            logging.getLogger(name).setLevel(level)
        # Get the name of the logfile based on logfile or logdir options.
        logfile = None
        if self.params.get("logfile") is not None:
            logfile = self.params.get("logfile")
        elif self.params.get("logdir") is not None:
            logfile = os.path.normpath(
                self.params.get("logdir") + "/" + self.params.get("host") + ".log",
            )
        # Create the FileHandler and attach it.
        if logfile is not None:
            try:
                handler = logging.FileHandler(logfile, mode="a")
                handler.setLevel(level)
                # Create a custom formatter.
                formatter = logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                )
                # add formatter to handler
                handler.setFormatter(formatter)
                # Handler should log anything from the 'jnpr.ansible_module.' namespace to
                # catch PyEZ, JSNAPY, etc. logs.
                logger.addHandler(handler)
                for name in additional_logger_names:
                    logging.getLogger(name).addHandler(handler)
            except IOError as ex:
                self.fail_json(
                    msg="Unable to open the log file %s. %s" % (logfile, str(ex)),
                )
        # Use the CustomAdapter to add host information.
        return CustomAdapter(logger, {"host": self.params.get("host")})

    def parse_arg_to_list_of_dicts(
        self,
        option_name,
        string_val,
        allow_bool_values=False,
    ):
        """Parses string_val into a list of dicts with bool and/or str values.

        In order to handle all of the different ways that list of dict type
        options may be specified, the arg_spec must set the option type to
        'str'. This requires us to parse the string_val ourselves into the
        required list of dicts. Handles Ansible-style keyword=value format for
        specifying dictionaries. Also handles Ansible aliases for boolean
        values if allow_bool_values is True.

        Args:
            option_name - The name of the option being parsed.
            string_val - The string to be parse.
            allow_bool_values - Whether or not boolean values are allowed.

        Returns:
            The list of dicts

        Fails:
            If there is an error parsing
        """
        # Nothing to do if no string_val were specified.
        if string_val is None:
            return None

        # Evaluate the string
        kwargs = self.safe_eval(string_val)

        if isinstance(kwargs, string_types):
            # This might be a keyword1=value1 keyword2=value2 type string.
            # The _check_type_dict method will parse this into a dict for us.
            try:
                kwargs = check_type_dict(kwargs)
            except TypeError as exc:
                self.fail_json(
                    msg="The value of the %s option (%s) is "
                    "invalid. Unable to translate into "
                    "a list of dicts. %s" % (option_name, string_val, str(exc)),
                )

        # Now, if it's a dict, let's make it a list of one dict
        if isinstance(kwargs, dict):
            kwargs = [kwargs]
        # Now, if it's not a list, we've got a problem.
        if not isinstance(kwargs, list):
            self.fail_json(
                msg="The value of the %s option (%s) is invalid. "
                "Unable to translate into a list of dicts." % (option_name, string_val),
            )
        # We've got a list, traverse each element to make sure it's a dict.
        return_val = []
        for kwarg in kwargs:
            # If it's now a string, see if it can be parsed into a dictionary.
            if isinstance(kwarg, string_types):
                # This might be a keyword1=value1 keyword2=value2 type string.
                # The _check_type_dict method will parse this into a dict.
                try:
                    kwarg = check_type_dict(kwarg)
                except TypeError as exc:
                    self.fail_json(
                        msg="The value of the %s option (%s) is "
                        "invalid. Unable to translate into a "
                        "list of dicts %s." % (option_name, string_val, str(exc)),
                    )
            # Now if it's not a dict, there's a problem.
            if not isinstance(kwarg, dict):
                self.fail_json(
                    msg="The value of the kwargs option (%s) is "
                    "%s. Unable to translate into a list "
                    "of dicts." % (option_name, string_val),
                )
            # check if allow_bool_values passed in kwargs
            if "allow_bool_values" in kwarg:
                allow_bool_values = kwarg.pop("allow_bool_values")

            # Now we just need to make sure the key is a string and the value
            # is a string or bool.
            return_item = {}
            for k, v in kwarg.items():
                if not isinstance(k, string_types):
                    self.fail_json(
                        msg="The value of the %s option (%s) "
                        "is invalid. Unable to translate into "
                        "a list of dicts." % (option_name, string_val),
                    )
                if allow_bool_values is True:
                    # Try to convert it to a boolean value. Will be None if it
                    # can't be converted.
                    try:
                        bool_val = boolean(v)
                    except TypeError:
                        bool_val = None
                    if bool_val is not None:
                        v = bool_val
                return_item[k] = v
            return_val.append(return_item)
        return return_val

    def parse_ignore_warning_option(self):
        """Parses the ignore_warning option.

        ignore_warning may be a bool, str, or list of str. The Ansible type
        checking doesn't support the possibility of more than one type.

        Returns:
            The validated value of the ignore_warning option. None if
            ignore_warning is not specified.

        Fails:
            If there is an error parsing ignore_warning.
        """
        # Nothing to do if ignore_warning wasn't specified.
        ignore_warn_list = self.params.get("ignore_warning")
        if ignore_warn_list is None:
            return ignore_warn_list
        if len(ignore_warn_list) == 1:
            try:
                bool_val = boolean(ignore_warn_list[0])
                if bool_val is not None:
                    return bool_val
            except TypeError:
                if isinstance(ignore_warn_list[0], string_types):
                    return ignore_warn_list[0]
            self.fail_json(
                msg="The value of the ignore_warning option "
                "(%s) is invalid. Unexpected type (%s)."
                % (ignore_warn_list[0], type(ignore_warn_list[0])),
            )
        elif len(ignore_warn_list) > 1:
            for ignore_warn in ignore_warn_list:
                if not isinstance(ignore_warn, string_types):
                    self.fail_json(
                        msg="The value of the ignore_warning "
                        "option (%s) is invalid. "
                        "Element (%s) has unexpected "
                        "type (%s)."
                        % (str(ignore_warn_list), ignore_warn, type(ignore_warn)),
                    )
            return ignore_warn_list
        else:
            self.fail_json(
                msg="The value of the ignore_warning option "
                "(%s) is invalid." % (ignore_warn_list),
            )

    def parse_rollback_option(self):
        """Parses the rollback option.

        rollback may be a str of 'rescue' or an int between 0 and 49. The
        Ansible type checking doesn't support the possibility of more than
        one type.

        Returns:
            The validate value of the rollback option. None if
            rollback is not specified.

        Fails:
            If there is an error parsing rollback.
        """
        # Nothing to do if rollback wasn't specified or is 'rescue'.
        rollback = self.params.get("rollback")
        if rollback is None or rollback == "rescue":
            return rollback
        if isinstance(rollback, string_types):
            try:
                # Is it an int between 0 and 49?
                int_val = int(rollback)
                if int_val >= 0 and int_val <= 49:
                    return int_val
            except ValueError:
                # Fall through to fail_json()
                pass
        self.fail_json(
            msg="The value of the rollback option (%s) is invalid. "
            "Must be the string 'rescue' or an int between "
            "0 and 49." % (str(rollback)),
        )

    def open(self):
        """Open the self.dev PyEZ Device instance.

        Failures:
            - ConnectError: When unable to make a PyEZ connection.
        """
        # Move all of the connection arguments into connect_args
        connect_args = {}
        for key in connection_spec:
            if self.params.get(key) is not None:
                connect_args[key] = self.params.get(key)

        try:
            # self.close()
            log_connect_args = dict(connect_args)
            log_connect_args["passwd"] = "NOT_LOGGING_PARAMETER"
            if "cs_passwd" in log_connect_args:
                log_connect_args["cs_passwd"] = "NOT_LOGGING_PARAMETER"

            self.logger.debug("Creating device parameters: %s", log_connect_args)
            timeout = connect_args.pop("timeout")
            self.dev = jnpr.junos.device.Device(**connect_args)
            self.logger.debug("Opening device.")
            self.dev.open()
            self.logger.debug("Device opened.")
            self.logger.debug("Setting default device timeout to %d.", timeout)
            self.dev.timeout = timeout
            self.logger.debug("Device timeout set.")
        # Exceptions raised by close() or open() are all sub-classes of
        # ConnectError, so this should catch all connection-related exceptions
        # raised from PyEZ.
        except pyez_exception.ConnectError as ex:
            self.fail_json(msg="Unable to make a PyEZ connection: %s" % (str(ex)))

    def close(self, raise_exceptions=False):
        """Close the self.dev PyEZ Device instance."""
        if self.dev is not None:
            try:
                # Because self.fail_json() calls self.close(), we must set
                # self.dev = None BEFORE calling dev.close() in order to avoid
                # the infinite recursion which would occur if dev.close()
                # raised a ConnectError.
                dev = self.dev
                self.dev = None
                dev.close()
                self.logger.debug("Device closed.")
            # Exceptions raised by close() are all sub-classes of
            # ConnectError or RpcError, so this should catch all
            # exceptions raised from PyEZ.
            except (pyez_exception.ConnectError, pyez_exception.RpcError) as ex:
                if raise_exceptions is True:
                    raise ex
                else:
                    # Ignore exceptions from closing. We're about to exit
                    # anyway and they will just mask the real error that
                    # happened.
                    pass

    def add_sw(self):
        """Add an instance of jnpr.junos.utils.sw.SW() to self."""
        self.sw = SW(self.dev)

    def open_configuration(self, mode, ignore_warning=None, ephemeral_instance=None):
        """Open candidate configuration database in exclusive or private mode.

        Failures:
            - ConnectError: When there's a problem with the PyEZ connection.
            - RpcError: When there's a RPC problem including an already locked
                        config or an already opened private config.
        """

        ignore_warn = ["uncommitted changes will be discarded on exit"]
        # if ignore_warning is a bool, pass the bool
        # if ignore_warning is a string add to the list
        # if ignore_warning is a list, merge them
        if ignore_warning is not None and isinstance(ignore_warning, bool):
            ignore_warn = ignore_warning
        elif ignore_warning is not None and isinstance(ignore_warning, str):
            ignore_warn.append(ignore_warning)
        elif ignore_warning is not None and isinstance(ignore_warning, list):
            ignore_warn = ignore_warn + ignore_warning

        if self.conn_type != "local":
            self._pyez_conn.open_configuration(mode, ignore_warn)
            return

        if self.config is None:
            if mode not in CONFIG_MODE_CHOICES:
                self.fail_json(msg="Invalid configuration mode: %s" % (mode))
            if mode != "ephemeral" and ephemeral_instance is not None:
                self.fail_json(
                    msg="Ephemeral instance is specified while the mode "
                    "is not ephemeral.Specify the mode as ephemeral or "
                    "do not specify the instance.",
                )
            if self.dev is None:
                self.open()
            config = jnpr.junos.utils.config.Config(self.dev, mode=mode)
            try:
                if config.mode == "exclusive":
                    config.lock()
                elif config.mode == "private":
                    self.dev.rpc.open_configuration(
                        private=True,
                        ignore_warning=ignore_warn,
                    )
                elif config.mode == "dynamic":
                    self.dev.rpc.open_configuration(
                        dynamic=True,
                        ignore_warning=ignore_warn,
                    )
                elif config.mode == "batch":
                    self.dev.rpc.open_configuration(
                        batch=True,
                        ignore_warning=ignore_warn,
                    )
                elif config.mode == "ephemeral":
                    if ephemeral_instance is None:
                        self.dev.rpc.open_configuration(
                            ephemeral=True,
                            ignore_warning=ignore_warn,
                        )
                    else:
                        self.dev.rpc.open_configuration(
                            ephemeral_instance=ephemeral_instance,
                            ignore_warning=ignore_warn,
                        )
            except (pyez_exception.ConnectError, pyez_exception.RpcError) as ex:
                self.fail_json(
                    msg="Unable to open the configuration in %s "
                    "mode: %s" % (config.mode, str(ex)),
                )
            self.config = config
            self.logger.debug("Configuration opened in %s mode.", config.mode)

    def close_configuration(self):
        """Close candidate configuration database.

        Failures:
            - ConnectError: When there's a problem with the PyEZ connection.
            - RpcError: When there's a RPC problem closing the config.
        """
        if self.conn_type != "local":
            self._pyez_conn.close_configuration()
            return

        if self.config is not None:
            # Because self.fail_json() calls self.close_configuration(), we
            # must set self.config = None BEFORE closing the config in order to
            # avoid the infinite recursion which would occur if closing the
            # configuration raised an exception.
            config = self.config
            self.config = None
            try:
                if config.mode == "exclusive":
                    config.unlock()
                elif config.mode in ["batch", "dynamic", "private", "ephemeral"]:
                    self.dev.rpc.close_configuration()
                self.logger.debug("Configuration closed.")
            except (pyez_exception.ConnectError, pyez_exception.RpcError) as ex:
                self.fail_json(msg="Unable to close the configuration: %s" % (str(ex)))

    def get_configuration(
        self,
        database="committed",
        format="text",
        options=None,
        filter=None,
        model=None,
        namespace=None,
        remove_ns=True,
    ):
        """Return the device configuration in the specified format.

        Return the database device configuration database in the format format.
        Pass the options specified in the options dict and the filter specified
        in the filter argument.

        Args:
            database: The configuration database to return. Choices are defined
                      in CONFIG_DATABASE_CHOICES.
            format: The format of the configuration to return. Choices are
                    defined in CONFIG_FORMAT_CHOICES.
            model: The namespace of the configuration to return. Choices are defined
                    in CONFIG_MODEL_CHOICES.
            namespace:  User can have their own defined namespace in the
                    custom yang models, In such cases they need to provide that
                    namespace so that it can be used to fetch yang modeled configs
            remove_ns: Flag to check if namespaces should be removed or not.
            filter: A string of XML, or '/'-separated configuration hierarchies,
                    which specifies a filter used to restrict the portions of the
                    configuration which are retrieved.
            options: Additional options, specified as a dictionary of key/value pairs, used
                        `when retrieving the configuration.
        Returns:
            A tuple containing:
            - The configuration in the requested format as a single
              multi-line string. Returned for all formats.
            - The "parsed" configuration as a JSON string. Set when
              format == 'xml' or format == 'json'. None when format == 'text'
              or format == 'set'
        Failures:
            - Invalid database.
            - Invalid format.
            - Options not a dict.
            - Invalid filter.
            - Format not understood by device.
        """
        if options is None:
            options = {}
        if database not in CONFIG_DATABASE_CHOICES:
            self.fail_json(
                msg="The configuration database % is not in the "
                "list of recognized configuration databases: "
                "%s." % (database, str(CONFIG_DATABASE_CHOICES)),
            )

        if format not in CONFIG_FORMAT_CHOICES:
            self.fail_json(
                msg="The configuration format % is not in the list "
                "of recognized configuration formats: %s."
                % (format, str(CONFIG_FORMAT_CHOICES)),
            )

        options.update({"database": database, "format": format})

        if self.conn_type == "local":
            if self.dev is None:
                self.open()

        self.logger.debug(
            "Retrieving device configuration. Options: %s  Filter %s",
            str(options),
            str(filter),
        )
        config = None
        try:
            if self.conn_type == "local":
                config = self.dev.rpc.get_config(
                    options=options,
                    filter_xml=filter,
                    model=model,
                    remove_ns=remove_ns,
                    namespace=namespace,
                )
            else:
                config = self.get_config(
                    options=options,
                    filter_xml=filter,
                    model=model,
                    remove_ns=remove_ns,
                    namespace=namespace,
                )
            self.logger.debug("Configuration retrieved.")
        except (self.pyez_exception.RpcError, self.pyez_exception.ConnectError) as ex:
            self.fail_json(msg="Unable to retrieve the configuration: %s" % (str(ex)))

        return_val = (None, None)
        if format == "text":
            if not isinstance(config, self.etree._Element):
                self.fail_json(
                    msg="Unexpected configuration type returned. "
                    "Configuration is: %s" % (str(config)),
                )
            if model is None and config.tag != "configuration-text":
                self.fail_json(
                    msg="Unexpected XML tag returned. "
                    "Configuration is: %s"
                    % (self.etree.tostring(config, pretty_print=True)),
                )
            return_val = (config.text, None)
        elif format == "set":
            if not isinstance(config, self.etree._Element):
                self.fail_json(
                    msg="Unexpected configuration type returned. "
                    "Configuration is: %s" % (str(config)),
                )
            if model is None and config.tag != "configuration-set":
                self.fail_json(
                    msg="Unexpected XML tag returned. "
                    "Configuration is: %s"
                    % (self.etree.tostring(config, pretty_print=True)),
                )
            return_val = (config.text, config.text.splitlines())
        elif format == "xml":
            if not isinstance(config, self.etree._Element):
                self.fail_json(
                    msg="Unexpected configuration type returned. "
                    "Configuration is: %s" % (str(config)),
                )
            if model is None and config.tag != "configuration":
                self.fail_json(
                    msg="Unexpected XML tag returned. "
                    "Configuration is: %s"
                    % (self.etree.tostring(config, pretty_print=True)),
                )
            return_val = (
                self.etree.tostring(config, pretty_print=True),
                self.jxmlease.parse_etree(config),
            )
        elif format == "json":
            return_val = (json.dumps(config), config)
        else:
            self.fail_json(
                msg="Unable to return configuration in %s format." % (format),
            )
        return return_val

    def rollback_configuration(self, id):
        """Rollback the device configuration to the specified id.

        Rolls back the configuration to the specified id. Assumes the
        configuration is already opened. Does NOT commit the configuration.

        Args:
            id: The id to which the configuration should be rolled back. Either
                an integer rollback value or the string 'rescue' to roll back
                to the previously saved rescue configuration.

        Failures:
            - Unable to rollback the configuration due to an RpcError or
              ConnectError.
        """
        if self.conn_type != "local":
            self._pyez_conn.rollback_configuration(id)
            return

        if self.dev is None or self.config is None:
            self.fail_json(msg="The device or configuration is not open.")

        if id == "rescue":
            self.logger.debug("Rolling back to the rescue configuration.")
            try:
                self.config.rescue(action="reload")
                self.logger.debug("Rescue configuration loaded.")
            except (
                self.pyez_exception.RpcError,
                self.pyez_exception.ConnectError,
            ) as ex:
                self.fail_json(
                    msg="Unable to load the rescue configuraton: " "%s" % (str(ex)),
                )
        elif id >= 0 and id <= 49:
            self.logger.debug("Loading rollback %d configuration.", id)
            try:
                self.config.rollback(rb_id=id)
                self.logger.debug("Rollback %d configuration loaded.", id)
            except (
                self.pyez_exception.RpcError,
                self.pyez_exception.ConnectError,
            ) as ex:
                self.fail_json(
                    msg="Unable to load the rollback %d "
                    "configuraton: %s" % (id, str(ex)),
                )
        else:
            self.fail_json(msg="Unrecognized rollback configuraton value: %s" % (id))

    def check_configuration(self):
        """Check the candidate configuration.

        Check the configuration. Assumes the configuration is already opened.
        Performs the equivalent of a "commit check", but does NOT commit the
        configuration.

        Failures:
            - An error returned from checking the configuration.
        """
        self.logger.debug("Checking the configuration.")
        if self.conn_type != "local":
            self._pyez_conn.check_configuration()
            return

        if self.dev is None or self.config is None:
            self.fail_json(msg="The device or configuration is not open.")

        try:
            self.config.commit_check()
            self.logger.debug("Configuration checked.")
        except (self.pyez_exception.RpcError, self.pyez_exception.ConnectError) as ex:
            self.fail_json(msg="Failure checking the configuraton: %s" % (str(ex)))

    def diff_configuration(self, ignore_warning=False):
        """Diff the candidate and committed configurations.

        Diff the candidate and committed configurations.

        Returns:
            A string with the configuration differences in text "diff" format.

        Failures:
            - An error returned from diffing the configuration.
        """
        self.logger.debug("Diffing candidate and committed configurations.")
        if self.conn_type != "local":
            diff = self._pyez_conn.diff_configuration(ignore_warning)
            return diff
        if self.dev is None or self.config is None:
            self.fail_json(msg="The device or configuration is not open.")

        try:
            diff = self.config.diff(rb_id=0, ignore_warning=ignore_warning)
            self.logger.debug("Configuration diff completed.")
            return diff
        except (self.pyez_exception.RpcError, self.pyez_exception.ConnectError) as ex:
            self.fail_json(msg="Failure diffing the configuraton: %s" % (str(ex)))

    def load_configuration(
        self,
        action,
        lines=None,
        src=None,
        template=None,
        vars=None,
        url=None,
        ignore_warning=None,
        format=None,
    ):
        """Load the candidate configuration.

        Load the candidate configuration from the specified src file using the
        specified action.

        Args:
            action - The type of load to perform: 'merge', 'replace', 'set',
                                                  'override', 'overwrite', and
                                                  'update', 'patch'
            lines - A list of strings containing the configuration.
            src - The file path on the local Ansible control machine to the
                  configuration to be loaded.
            template - The Jinja2 template used to renter the configuration.
            vars - The variables used to render the template.
            url - The URL to the candidate configuration.
            ignore_warning - What warnings to ignore.
            format - The format of the configuration being loaded.

        Failures:
            - An error returned from loading the configuration.
        """
        if self.conn_type == "local":
            if self.dev is None or self.config is None:
                self.fail_json(msg="The device or configuration is not open.")

        load_args = {}
        config = None
        if ignore_warning is not None:
            load_args["ignore_warning"] = ignore_warning
        if action == "set":
            format = "set"
        if format is not None:
            load_args["format"] = format
        if action == "merge":
            load_args["merge"] = True
        if action == "override" or action == "overwrite":
            load_args["overwrite"] = True
        if action == "update":
            load_args["update"] = True
        if action == "patch":
            load_args["patch"] = True
        if lines is not None:
            config = "\n".join(map(lambda line: line.rstrip("\n"), lines))
            self.logger.debug("Loading the supplied configuration.")
        if src is not None:
            abs_path_src = os.path.abspath(src)  # For PyEZ persistent
            load_args["path"] = abs_path_src
            self.logger.debug("Loading the configuration from: %s.", src)
        if template is not None:
            load_args["template_path"] = template
            load_args["template_vars"] = vars
            self.logger.debug(
                "Loading the configuration from the %s template.",
                template,
            )
        if url is not None:
            load_args["url"] = url
            self.logger.debug("Loading the configuration from %s.", url)

        if self.conn_type != "local":
            self._pyez_conn.load_configuration(config, load_args)
            return

        try:
            if config is not None:
                self.config.load(config, **load_args)
            else:
                self.logger.debug("Load args %s.", str(load_args))
                self.config.load(**load_args)
            self.logger.debug("Configuration loaded.")
        except (self.pyez_exception.RpcError, self.pyez_exception.ConnectError) as ex:
            self.fail_json(msg="Failure loading the configuraton: %s" % (str(ex)))

    def commit_configuration(
        self,
        ignore_warning=None,
        comment=None,
        confirmed=None,
        timeout=30,
        full=False,
        sync=False,
        force_sync=False,
    ):
        """Commit the candidate configuration.

        Commit the configuration. Assumes the configuration is already opened.

        Args:
            ignore_warning - Which warnings to ignore.
            comment - The commit comment
            confirmed - Number of minutes for commit confirmed.
            timeout - Timeout for commit configuration. Default timeout value is 30s.
            full - apply full commit
            sync - Check for commit syntax and sync between RE's
            force_sync - Ignore syntax check and force to sync between RE's

        Failures:
            - An error returned from committing the configuration.
        """
        if self.conn_type == "local":
            if self.dev.timeout:
                timeout = self.dev.timeout

        if self.conn_type != "local":
            self._pyez_conn.commit_configuration(
                ignore_warning=ignore_warning,
                comment=comment,
                confirmed=confirmed,
                timeout=timeout,
                full=full,
                force_sync=force_sync,
                sync=sync,
            )
            return

        if self.dev is None or self.config is None:
            self.fail_json(msg="The device or configuration is not open.")

        self.logger.debug("Committing the configuration.")
        try:
            self.config.commit(
                ignore_warning=ignore_warning,
                comment=comment,
                confirm=confirmed,
                timeout=timeout,
                full=full,
                force_sync=force_sync,
                sync=sync,
            )
            self.logger.debug("Configuration committed.")
        except (self.pyez_exception.RpcError, self.pyez_exception.ConnectError) as ex:
            self.fail_json(msg="Failure committing the configuraton: %s" % (str(ex)))

    def ping(self, params, acceptable_percent_loss=0, results=None):
        """Execute a ping command with the parameters specified in params.

        Args:
            params: dict of parameters passed directly to the ping RPC.
            acceptable_percent_loss: integer specifying maximum percentage of
                                     packets that may be lost and still
                                     consider the ping not to have failed.
            results: dict of results which should be included in the return
                     value, or which should be included if fail_json() is
                     called due to a failure.

        Returns:
            A dict of results. It contains all key/value pairs in the results
            argument plus the keys below. (The keys below will overwrite
            any corresponding key which exists in the results argument):

            msg: (str) A human-readable message indicating the result.
            packet_loss: (str) The percentage of packets lost.
            packets_sent: (str) The number of packets sent.
            packets_received: (str) The number of packets received.
            rtt_minimum: (str) The minimum round-trip-time, in microseconds,
                               of all ping responses received.
            rtt_maximum: (str) The maximum round-trip-time, in microseconds,
                               of all ping responses received.
            rtt_average: (str) The average round-trip-time, in microseconds,
                               of all ping responses received.
            rtt_stddev: (str) The standard deviation of round-trip-time, in
                              microseconds, of all ping responses received.
            warnings: (list of str) A list of warning strings, if any, produced
                                    from the ping.
            failed: (bool) Indicates if the ping failed. The ping fails
                           when packet_loss > acceptable_percent_loss.

        Fails:
            - If the ping RPC produces an exception.
            - If there are errors present in the results.
        """
        if results is None:
            results = {}
        # Assume failure until we know success.
        results["failed"] = True

        # Execute the ping.
        try:
            self.logger.debug("Executing ping with parameters: %s", str(params))
            if self.conn_type == "local":
                resp = self.dev.rpc.ping(normalize=True, **params)
            else:
                response = self._pyez_conn.ping_device(normalize=True, **params)
                resp = self.etree.fromstring(response)
            self.logger.debug("Ping executed.")
        except (self.pyez_exception.RpcError, self.pyez_exception.ConnectError) as ex:
            self.fail_json(msg="Unable to execute ping: %s" % (str(ex)))

        if not isinstance(resp, self.etree._Element):
            self.fail_json(msg="Unexpected ping response: %s" % (str(resp)))

        resp_xml = self.etree.tostring(resp, pretty_print=True)

        # Fail if any errors in the results
        errors = resp.findall("rpc-error[error-severity='error']/error-message")
        if len(errors) != 0:
            # Create a comma-plus-space-seperated string of the errors.
            # Calls the text attribute of each element in the errors list.
            err_msg = ", ".join(map(lambda err: err.text, errors))
            results["msg"] = "Ping returned errors: %s" % (err_msg)
            self.exit_json(**results)

        # Add any warnings into the results
        warnings = resp.findall("rpc-error[error-severity='warning']/error-message")
        if len(warnings) != 0:
            # Create list of the text attributes of each element in the
            # warnings list.
            results["warnings"] = list(map(lambda warn: warn.text, warnings))

        # Try to find probe summary
        probe_summary = resp.find("probe-results-summary")
        if probe_summary is None:
            results["msg"] = "Probe-results-summary not found in response: " "%s" % (
                resp_xml
            )
            self.exit_json(**results)

        # Extract some required fields and some optional fields
        r_fields = {}
        r_fields["packet_loss"] = probe_summary.findtext("packet-loss")
        r_fields["packets_sent"] = probe_summary.findtext("probes-sent")
        r_fields["packets_received"] = probe_summary.findtext("responses-received")
        o_fields = {}
        o_fields["rtt_minimum"] = probe_summary.findtext("rtt-minimum")
        o_fields["rtt_maximum"] = probe_summary.findtext("rtt-maximum")
        o_fields["rtt_average"] = probe_summary.findtext("rtt-average")
        o_fields["rtt_stddev"] = probe_summary.findtext("rtt-stddev")

        # Make sure we got values for required fields.
        for key in r_fields:
            if r_fields[key] is None:
                results["msg"] = "Expected field %s not found in " "response: %s" % (
                    key,
                    resp_xml,
                )
                self.exit_json(**results)
        # Add the required fields to the result.
        results.update(r_fields)

        # Extract integer packet loss
        packet_loss = 100
        if results["packet_loss"] is not None:
            try:
                packet_loss = round(float(results["packet_loss"]))
            except ValueError:
                results["msg"] = "Packet loss %s not an integer. " "Response: %s" % (
                    results["packet_loss"],
                    resp_xml,
                )
                self.exit_json(**results)

        if packet_loss < 100:
            # Optional fields are present if packet_loss < 100
            for key in o_fields:
                if o_fields[key] is None:
                    results["msg"] = (
                        "Expected field %s not found in "
                        "response: %s" % (key, resp_xml)
                    )
                    self.exit_json(**results)
        # Add the o_fields to the result (even if they're None)
        results.update(o_fields)

        # Set the result message.
        results["msg"] = "Loss %s%%, (Sent %s | Received %s)" % (
            results["packet_loss"],
            results["packets_sent"],
            results["packets_received"],
        )

        # Was packet loss within limits? If so, we didn't fail.
        if packet_loss <= acceptable_percent_loss:
            results["failed"] = False

        return results

    def save_text_output(self, name, format, text):
        """Save text output into a file based on 'dest' and 'dest_dir' params.

        The text provided in the text parameter is saved to a file on the
        local Ansible control machine based on the 'diffs_file', 'dest', and
        'dest_dir' module parameters. If neither parameter is specified,
        then this method is a no-op. If the 'dest' or 'diffs_file' parameter is
        specified, the value of the 'dest' or 'diffs_file' parameter is used as
        the path name for the destination file. In this case, the name and
        format parameters are ignored. If the 'dest_dir' parameter is
        specified, the path name for the destination file is:
        <hostname>_<name>.<format>.  If the destination file already exists,
        and the 'dest_dir' option is specified, or the 'dest' parameter is
        specified and the self.destfile attribute is not present, the file is
        overwritten. If the 'dest' parameter is specified and the
        self.destfile attribute is present, then the file is appended. This
        allows multiple text outputs to be written to the same file.

        Args:
            name: The name portion of the destination filename when the
                  'dest_dir' parameter is specified.
            format: The format portion of the destination filename when the
                  'dest_dir' parameter is specified.
            text: The text to be written into the destination file.

        Fails:
            - If the destination file is not writable.
        """
        file_path = None
        mode = "wb"
        if name == "diff":
            if self.params.get("diffs_file") is not None:
                file_path = os.path.normpath(self.params.get("diffs_file"))
            elif self.params.get("dest_dir") is not None:
                dest_dir = self.params.get("dest_dir")
                file_name = "%s.diff" % (self.inventory_hostname,)
                file_path = os.path.normpath(os.path.join(dest_dir, file_name))
        else:
            if self.params.get("dest") is not None:
                file_path = os.path.normpath(self.params.get("dest"))
                if getattr(self, "destfile", None) is None:
                    self.destfile = self.params.get("dest")
                else:
                    mode = "ab"
            elif self.params.get("dest_dir") is not None:
                dest_dir = self.params.get("dest_dir")
                # Substitute underscore for spaces.
                name = name.replace(" ", "_")
                # Substitute underscore for pipe
                name = name.replace("|", "_")
                name = "" if name == "config" else "_" + name
                file_name = "%s%s.%s" % (self.inventory_hostname, name, format)
                file_path = os.path.normpath(os.path.join(dest_dir, file_name))
        if file_path is not None:
            try:
                # Use ansible utility to convert objects to bytes
                # to achieve Python2/3 compatibility
                with open(file_path, mode) as save_file:
                    save_file.write(to_bytes(text, encoding="utf-8"))
                self.logger.debug("Output saved to: %s.", file_path)
            except IOError:
                self.fail_json(
                    msg="Unable to save output. Failed to "
                    "open the %s file." % (file_path),
                )

    def get_config(
        self,
        filter_xml=None,
        options=None,
        model=None,
        namespace=None,
        remove_ns=True,
        **kwarg,
    ):
        response = self._pyez_conn.get_config(
            filter_xml,
            options,
            model,
            namespace,
            remove_ns,
            **kwarg,
        )
        if options["format"] == "json":
            return response
        else:
            return self.etree.fromstring(response)

    def get_rpc(self, rpc, ignore_warning=None, format=None):
        rpc_1 = self.etree.tostring(rpc)
        rpc_str = xmltodict.parse(rpc_1)
        # json.dumps(rpc_str)
        response = self._pyez_conn.get_rpc_resp(
            rpc_str,
            ignore_warning=ignore_warning,
            format=format,
        )
        if format == "json":
            return response
        return self.etree.fromstring(response)

    def get_facts(self):
        facts = self._pyez_conn.get_facts()
        return facts

    def get_chassis_inventory(self):
        chassis = self._pyez_conn.get_chassis_inventory()
        return self.etree.fromstring(chassis)

    def _hashfile(self, afile, hasher, blocksize=65536):
        buf = afile.read(blocksize)
        while len(buf) > 0:
            hasher.update(buf)
            buf = afile.read(blocksize)
        return hasher.hexdigest()

    def local_md5(self, package, action):
        """
        Computes the MD5 checksum value on the local package file.
        :param str package:
            File-path to the package (tgz) file on the local server
        :returns: MD5 checksum (str)
        :raises IOError: when **package** file does not exist
        """
        try:
            checksum = self._hashfile(open(package, "rb"), hashlib.md5())
        except Exception as err:
            self.logger.error("unable to get the hash due to:{0}".format(err))
            if ("No such file" in format(err)) and action == "get":
                checksum = "no_file"
            else:
                raise err
            return checksum

        self.logger.info("local hash calculated")
        return checksum

    def remote_md5(self, remote_file, action):
        try:
            if self.conn_type == "local":
                rpc_reply = self.dev.rpc.get_checksum_information(path=remote_file)
                checksum = rpc_reply.findtext(".//checksum").strip()
            else:
                rpc_reply = self._pyez_conn.get_checksum_information(remote_file)
                resp = self.etree.fromstring(rpc_reply)
                checksum = resp.findtext(".//checksum").strip()
        except Exception as err:
            self.logger.error("unable to get rpc due to:{0}".format(str(err)))
            if ("No such file or directory" in format(err)) and (action == "put"):
                checksum = "no_file"
            else:
                raise err
            return checksum
        self.logger.info("rpc response received")
        return checksum

    def scp_file_copy_put(self, local_file, remote_file):
        """
        Transfers a file from the local system to a remote destination using SCP,
        only if the file is not already present or differs on the remote side.
        """
        self.logger.info("Computing local MD5 checksum on: {0}".format(local_file))
        local_checksum = self.local_md5(local_file, "put")
        self.logger.info("Local checksum: {0}".format(local_checksum))
        remote_checksum = self.remote_md5(remote_file, "put")
        if remote_checksum == "no_file" or remote_checksum != local_checksum:
            status = "File not present, need to transfer"
            self.logger.info(status)
            if self.conn_type == "local":
                with SCP(self.dev, progress=True) as scp1:
                    scp1.put(local_file, remote_file)
            else:
                self._pyez_conn.scp_file_copy_put(local_file, remote_file)
            self.logger.info(
                "computing remote MD5 checksum on: {0}".format(remote_file),
            )
            remote_checksum = self.remote_md5(remote_file, "put")
            self.logger.info("Remote checksum: {0}".format(remote_checksum))
            if remote_checksum != local_checksum:
                status = "Transfer failed (different MD5 between local and remote) {0} | {1}".format(
                    local_checksum,
                    remote_checksum,
                )
                self.logger.error(status)
                self.fail_json(msg=status)
                return [status, False]
            else:
                status = "File pushed OK"
                self.logger.info("Checksum check passed.")
                self.logger.info(status)
                return [status, True]
        else:
            status = "File already present, skipping the scp"
            self.logger.info(status)
            return [status, False]

    def scp_file_copy_put_without_checksum(self, local_file, remote_file):
        """
        Transfers a file from the local system to a remote destination using SCP
        without performing MD5 checksum verification.
        """
        if self.conn_type == "local":
            try:
                with SCP(self.dev, progress=True) as scp1:
                    scp1.put(local_file, remote_file)
                return ["File pushed OK", True]
            except Exception as e:
                return [f"Error: {str(e)}", False]
        else:
            self._pyez_conn.scp_file_copy_put(local_file, remote_file)
            return ["File pushed OK", True]

    def ftp_file_copy_put(self, local_file, remote_file):
        """
        Transfers a file from the local system to a remote destination using
        ftp, only if the file is not already present or differs on the remote side.
        """
        self.logger.info("Computing local MD5 checksum on: {0}".format(local_file))
        local_checksum = self.local_md5(local_file, "put")
        self.logger.info("Local checksum: {0}".format(local_checksum))
        remote_checksum = self.remote_md5(remote_file, "put")
        if remote_checksum == "no_file" or remote_checksum != local_checksum:
            status = "File not present, need to transfer"
            self.logger.info(status)
            if self.conn_type == "local":
                with FTP(self.dev) as ftp:
                    ftp.put(local_file, remote_file)
            else:
                self._pyez_conn.ftp_file_copy_put(local_file, remote_file)
            self.logger.info(
                "computing remote MD5 checksum on: {0}".format(remote_file),
            )
            remote_checksum = self.remote_md5(remote_file, "put")
            self.logger.info("Remote checksum: {0}".format(remote_checksum))
            if remote_checksum != local_checksum:
                status = "Transfer failed (different MD5 between local and remote) {0} | {1}".format(
                    local_checksum,
                    remote_checksum,
                )
                self.logger.error(status)
                self.fail_json(msg=status)
                return [status, False]
            else:
                status = "File pushed OK"
                self.logger.info("Checksum check passed.")
                self.logger.info(status)
                return [status, True]
        else:
            status = "File already present, skipping the scp"
            self.logger.info(status)
            return [status, False]

    def ftp_file_copy_put_without_checksum(self, local_file, remote_file):
        """
        Transfers a file from the local system to a remote destination using
        FTP without performing MD5 checksum verification.
        """
        if self.conn_type == "local":
            try:
                with FTP(self.dev) as ftp:
                    result = ftp.put(local_file, remote_file)
                if result:
                    return ["File pushed OK", True]
                else:
                    return ["Transfer failed", False]
            except Exception as e:
                return [f"Error: {str(e)}", False]
        else:
            result = self._pyez_conn.ftp_file_copy_put(local_file, remote_file)
            if result:
                return ["File pushed OK", True]
            else:
                return ["Transfer failed", False]

    def scp_file_copy_get(self, remote_file, local_file):
        """
        Retrieves a file from a remote system using SCP, verifying integrity via MD5 checksum.
        """
        self.logger.info("Computing remote MD5 checksum on: {0}".format(remote_file))
        remote_checksum = self.remote_md5(remote_file, "get")
        self.logger.info("Remote checksum: {0}".format(remote_checksum))
        local_checksum = self.local_md5(local_file, "get")
        if local_checksum == "no_file" or local_checksum != remote_checksum:
            status = "File not present, need to transfer"
            self.logger.info(status)
            if self.conn_type == "local":
                with SCP(self.dev, progress=True) as scp1:
                    scp1.get(remote_file, local_file)
            else:
                self._pyez_conn.scp_file_copy_get(remote_file, local_file)
            self.logger.info("computing local MD5 checksum on: {0}".format(local_file))
            local_checksum = self.local_md5(local_file, "get")
            self.logger.info("Local checksum: {0}".format(local_checksum))
            if remote_checksum != local_checksum:
                status = "Transfer failed (different MD5 between local and remote) {0} | {1}".format(
                    local_checksum,
                    remote_checksum,
                )
                self.logger.error(status)
                self.fail_json(msg=status)
                return [status, False]
            else:
                status = "File pushed OK"
                self.logger.info("Checksum check passed.")
                self.logger.info(status)
                return [status, True]
        else:
            status = "File already present, skipping the scp"
            self.logger.info(status)
            return [status, False]

    def scp_file_copy_get_without_checksum(self, remote_file, local_file):
        """
        Retrieves a file from a remote system using SCP, without checksum.
        """
        if self.conn_type == "local":
            try:
                with SCP(self.dev, progress=True) as scp1:
                    scp1.get(remote_file, local_file)
                return ["File pushed OK", True]
            except Exception as e:
                return [f"Error: {str(e)}", False]
        else:
            self._pyez_conn.scp_file_copy_get(remote_file, local_file)
            return ["File pushed OK", True]

    def ftp_file_copy_get(self, remote_file, local_file):
        """
        Retrieves a file from a remote system using FTP, verifying integrity via MD5 checksum.
        """
        self.logger.info("Computing remote MD5 checksum on: {0}".format(remote_file))
        remote_checksum = self.remote_md5(remote_file, "get")
        self.logger.info("Remote checksum: {0}".format(remote_checksum))
        local_checksum = self.local_md5(local_file, "get")
        if local_checksum == "no_file" or local_checksum != remote_checksum:
            status = "File not present, need to transfer"
            self.logger.info(status)
            if self.conn_type == "local":
                with FTP(self.dev) as ftp:
                    ftp.get(remote_file, local_file)
            else:
                self._pyez_conn.ftp_file_copy_get(remote_file, local_file)
            self.logger.info("computing local MD5 checksum on: {0}".format(local_file))
            local_checksum = self.local_md5(local_file, "get")
            self.logger.info("Local checksum: {0}".format(local_checksum))
            if remote_checksum != local_checksum:
                status = "Transfer failed (different MD5 between local and remote) {0} | {1}".format(
                    local_checksum,
                    remote_checksum,
                )
                self.logger.error(status)
                self.fail_json(msg=status)
                return [status, False]
            else:
                status = "File pushed OK"
                self.logger.info("Checksum check passed.")
                self.logger.info(status)
                return [status, True]
        else:
            status = "File already present, skipping the scp"
            self.logger.info(status)
            return [status, False]

    def ftp_file_copy_get_without_checksum(self, remote_file, local_file):
        """
        Retrieves a file from a remote system using FTP, without checksum.
        """
        if self.conn_type == "local":
            try:
                with FTP(self.dev) as ftp:
                    result = ftp.get(remote_file, local_file)
                if result:
                    return ["File pushed OK", True]
                else:
                    return ["Transfer failed", False]
            except Exception as e:
                return [f"Error: {str(e)}", False]
        else:
            result = self._pyez_conn.ftp_file_copy_get(remote_file, local_file)
        if result:
            return ["File pushed OK", True]
        else:
            return ["Transfer failed", False]
