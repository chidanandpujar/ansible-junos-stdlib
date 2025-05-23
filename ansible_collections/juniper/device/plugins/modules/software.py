#!/usr/bin/python
# -*- coding: utf-8 -*-

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

ANSIBLE_METADATA = {
    "metadata_version": "1.1",
    "supported_by": "community",
    "status": ["stableinterface"],
}

DOCUMENTATION = """
---
extends_documentation_fragment:
  - juniper.device.juniper_junos_doc.connection_documentation
  - juniper.device.juniper_junos_doc.logging_documentation
module: software
author:
  - Jeremy Schulman
  - "Juniper Networks - Stacy Smith (@stacywsmith)"
short_description: Install software on a Junos device
description:
  - >
    Install a Junos OS image, or other software package, on a Junos device.
    This action is generally equivalent to the C(request system software add)
    operational-mode CLI command. It performs the following
    steps in order:


    #. Compare the currently installed Junos version to the desired version
       specified by the I(version) option.

       * If the current and desired versions are the same, stop and return
         I(changed) with a value of C(false).
       * If running in check mode, and the current and desired versions differ,
         stop and return I(changed) with a value of C(true).
       * Otherwise, proceed.
    #. If the I(local_package) option is specified, compute the MD5 checksum
       of the I(local_package) file on the local Ansible control machine.
    #. Check if the file exists at the I(remote_package) location on the target
       Junos device. If so, compute the MD5 checksum of the file on the target
       Junos device.
    #. If the I(cleanfs) option is C(true), the default, then perform the
       equivalent of the C(request system storage cleanup) CLI command.
    #. If the checksums computed in steps 2 and 3 differ, or if the
       I(remote_package) file does not exist on the target Junos device, then
       copy the package from I(local_package) on the local Ansible control
       machine to I(remote_package) on the target Junos device.
    #. Install the software pacakge from the I(remote_package) location on the
       target Junos device using the options specified.
    #. If the I(reboot) option is C(true), the default, initiate a reboot of
       the target Junos device.
options:
  all_re:
    description:
      - Whether or not to install the software on all Routing Engines of the
        target Junos device. If C(true), and the device has multiple Routing
        Engines, the software is installed on all Routing Engines. If C(false),
        the software is only installed on the current Routing Engine.
    required: false
    default: true
    type: bool
  member_id:
    description:
      -  install software on the specified members ids of VC.
    required: false
    default: none
    type: list
  checksum:
    description:
      - The pre-calculated checksum, using the I(checksum_algorithm) of the
        file specified by the I(local_package) option. Specifying this option
        is simply an optimization to avoid repeatedly computing the checksum of
        the I(local_package) file once for each target Junos host.
    required: false
    default: none
    type: str
  checksum_algorithm:
    description:
      - The algorithm to use when calculating the checksum of the local and
        remote software packages.
    required: false
    default: md5
    type: str
  checksum_timeout:
    description:
      - The number of seconds to wait for the calculation of the checksum to
        complete on the target Junos device.
    required: false
    default: 300 (5 minutes)
    type: int
  cleanfs:
    description:
      - Whether or not to perform a C(request system storage cleanup) prior to
        copying or installing the software.
    required: false
    default: true (unless I(no_copy) is C(true), then C(false))
    type: bool
  cleanfs_timeout:
    description:
      -  The number of seconds to wait for the
         C(request system storage cleanup) to complete on the target Junos
         device.
    required: false
    default: 300 (5 minutes)
    type: int
  force_host:
    description:
      - Forces the upgrade of the Host Software package on QFX-series devices.
    required: false
    default: false
    type: bool
  install_timeout:
    description:
      - The number of seconds to wait for the software installation to
        complete on the target Junos device.
    required: false
    default: 1800 (30 minutes)
    type: int
  issu:
    description:
      - Indicates if a unified in-service software upgrade (ISSU) should be
        attempted. ISSU enables the upgrade between two different
        Junos OS releases with no control plane disruption and minimal data
        plane traffic disruption.
      - In order for an ISSU to succeed, ISSU must be supported. This includes
        support for the current to desired Junos versions, the hardware
        of the target Junos device, and the current software configuration of
        the target Junos device.
      - The I(issu) and I(nssu) options are mutually exclusive.
    required: false
    default: false
    type: bool
  kwargs:
    description:
      - Additional keyword arguments and values which are passed to the
        C(<request-package-add>) RPC used to install the software package. The
        value of this option is a dictionary of keywords and values.
    required: false
    default: none
    type: dict
    aliases:
      - kwarg
      - args
      - arg
  local_package:
    description:
      - The path, on the local Ansible control machine, of a Junos software
        package. This Junos software package will be installed on the target
        Junos device.
      - If this option is specified, and a file with the same MD5 checksum
        doesn't already exist at the I(remote_package) location on the target
        Junos device, then the file is copied from the local Ansible control
        machine to the target Junos device.
      - If this option is not specified, it is assumed that the
        software package already exists on the target Junos device. In this
        case, the I(remote_package) option must be specified.
    required: false
    default: none
    type: path
    aliases:
      - package
  no_copy:
    description:
      - Indicates if the file containing the software package should be copied
        from the I(local_package) location on the local Ansible control
        machine to the I(remote_package) location on the target Junos device.
      - If the value is C(true), or if the I(local_package) option is not
        specified, then the copy is skipped and the file must already exist
        at the I(remote_package) location on the target Junos device.
    required: false
    default: false
    type: bool
  nssu:
    description:
      - Indicates if a non-stop software upgrade (NSSU) should be
        attempted. NSSU enables the upgrade between two different
        Junos OS releases with minimal data plane traffic disruption.
      - NSSU is specific to EX-series Virtual Chassis systems or EX-series
        stand-alone systems with redundant Routing Engines.
      - In order for an NSSU to succeed, NSSU must be supported. This includes
        support for the current to desired Junos versions, the hardware
        of the target Junos device, and the current software configuration of
        the target Junos device.
      - The I(nssu) and I(issu) options are mutually exclusive.
    required: false
    default: false
    type: bool
  reboot:
    description:
      - Indicates if the target Junos device should be rebooted after
        performing the software install.
    required: false
    default: true
    type: bool
  reboot_pause:
    description:
      - The amount of time, in seconds, to wait after the reboot is issued
        before the module returns. This gives time for the reboot to begin. The
        default value of 10 seconds is designed to ensure the device is no
        longer reachable (because the reboot has begun) when the next task
        begins. The value must be an integer greater than or equal to 0.
    required: false
    default: 10
    type: int
  remote_package:
    description:
      - This option may take one of two formats.
      - The first format is a URL, from the perspective of the target Junos
        device, from which the device retrieves the software package to be
        installed. The acceptable formats for the URL value may be found
         U(here|https://www.juniper.net/documentation/en_US/junos/topics/concept/junos-software-formats-filenames-urls.html).
      -  When using the URL format, the I(local_package) and I(no_copy) options
         must not be specified.
      - The second format is a file path, on the taget Junos device, to the
        software package.
      - If the I(local_package) option is also specified, and the
        I(no_copy) option is C(false), the software package will be copied
        from I(local_package) to I(remote_package), if necessary.
      - If the I(no_copy) option is C(true) or the I(local_package) option
        is not specified, then the file specified by this option must already
        exist on the target Junos device.
      - If this option is not specified, it is assumed that the software
        package will be copied into the C(/var/tmp) directory on the target
        Junos device using the filename portion of the I(local_package) option.
        In this case, the I(local_package) option must be specified.
      - Specifying the I(remote_package) option and not specifying the
        I(local_package) option is equivalent to specifying the
        I(local_package) option and the I(no_copy) option. In this case,
        you no longer have to explicitly specify the I(no_copy) option.
      - If the I(remote_package) value is a directory (ends with /), then
        the filename portion of I(local_package) will be appended to the
        I(remote_package) value.
      - If the I(remote_package) value is a file (does not end with /),
        then the filename portion of I(remote_package) must be the same as
        the filename portion of I(local_package).
    required: false
    default: C(/var/tmp/) + filename portion of I(local_package)
    type: path
  pkg_set:
    description:
      -  install software on the members in a mixed Virtual Chassis. Currently
         we are not doing target package check this option is provided.
    required: false
    default: false
    type: list
  validate:
    description:
      - Whether or not to have the target Junos device should validate the
        current configuration against the new software package.
    required: false
    default: false
    type: bool
  version:
    description:
      - The version of software contained in the file specified by the
        I(local_package) and/or I(remote_package) options. This value should
        match the Junos version which will be reported by the device once the
        new software is installed. If the device is already running a version
        of software which matches the I(version) option value, the software
        install is not necessary. In this case the module returns a I(changed)
        value of C(false) and an I(failed) value of C(false) and does not
        attempt to perform the software install.
    required: false
    default: Attempt to extract the version from the file name specified by
             the I(local_package) or I(remote_package) option values IF the
             package appears to be a Junos software package. Otherwise, C(none).
    type: str
    aliases:
      - target_version
      - new_version
      - desired_version
  vmhost:
    description:
      - Whether or not this is a vmhost software installation.
    required: false
    default: false
    type: bool
notes:
  - This module does support connecting to the console of a Junos device, but
    does not support copying the software package from the local Ansible
    control machine to the target Junos device while connected via the console.
    In this situation, the I(remote_package) option must be specified, and the
    specified software package must already exist on the target Junos device.
  - This module returns after installing the software and, optionally,
    initiating a reboot of the target Junos device. It does not wait for
    the reboot to complete, and it does not verify that the desired version of
    software specified by the I(version) option is actually activated on the
    target Junos device. It is the user's responsibility to confirm the
    software installation using additional follow on tasks in their playbook.
"""

EXAMPLES = """
---
- name: 'Explicit host argument'
  hosts: junos
  connection: local
  gather_facts: false

  tasks:
    - name: Execute a basic Junos software upgrade.
      juniper.device.software:
        local_package: "./images/"
      register: response

    - name: Print the complete response.
      ansible.builtin.debug:
        var: response

    - name: Upgrade Junos OS from package copied at device
      juniper.device.software:
        host: "10.x.x.x"
        user: "user"
        passwd: "user123"
        remote_package: "/var/tmp/junos-install-mx-x86-64-20.1R1.5.tgz"
        no_copy: false
        cleanfs: false
        validate: true
      register: response
"""


RETURN = """
changed:
  description:
    - Indicates if the device's state has changed, or if the state would have
      changed when executing in check mode. This value is set to C(true) when
      the version of software currently running on the target Junos device does
      not match the desired version of software specified by the I(version)
      option. If the current and desired software versions match, the value
      of this key is set to C(false).
  returned: success
  type: bool
check_mode:
  description:
    - Indicates whether or not the module ran in check mode.
  returned: success
  type: bool
failed:
  description:
    - Indicates if the task failed.
  returned: always
  type: bool
msg:
  description:
    - A human-readable message indicating the result of the software
      installation.
  returned: always
  type: str
"""

# Standard Library imports
import os.path
import re
import time


try:
    # Python 3.x
    from urllib.parse import urlparse
except ImportError:
    # Python 2.x
    from urlparse import urlparse


"""From Ansible 2.1, Ansible uses Ansiballz framework for assembling modules
But custom module_utils directory is supported from Ansible 2.3
Reference for the issue: https://groups.google.com/forum/#!topic/ansible-project/J8FL7Z1J1Mw """

# Ansiballz packages module_utils into ansible.module_utils

from ansible_collections.juniper.device.plugins.module_utils import juniper_junos_common


def parse_version_from_filename(filename):
    """Attempts to parse a version string from the filename of a Junos package.

    There is wide variety in the naming schemes used by Junos software
    packages. This function attempts to parse the version string from the
    filename, but may not be able to accurately do so. It's also not
    guaranteed that the filename of a package accurately reflects the version
    of software in the file. (A user may have renamed it.)
    If the filename does not appear to be a Junos package (maybe some other
    type of package which can be installed on Junos devices), then return None.

    Args:
        filename - The filename from which to parse the version string.

    Returns:
        The version string, or None if unable to parse.
    """
    # Known prefixes for filenames which contain Junos software packages.
    JUNOS_PACKAGE_PREFIXES = [
        "jbundle",
        "jinstall",
        "junos-install",
        "junos-srx",
        "junos-vmhost-install",
        "junos-vrr",
        "vmx-bundle",
        "junos-arm",
    ]
    for prefix in JUNOS_PACKAGE_PREFIXES:
        if filename.startswith(prefix):
            # Assumes the version string will be prefixed by -.
            # Assume major version will begin with two digits followed by dot.
            # Assume the version string ends with the last digit in filename.
            match = re.search(r"-(\d{2}\..*\d).*", filename)
            if match is not None:
                return match.group(1)
    return None


def define_progress_callback(junos_module):
    """Create callback which can be passed to SW.install(progress=progress)"""

    def myprogress(_0, report):
        """A progress function which logs report at level INFO.

        Args:
          _0: The PyEZ device object. Unused because the logger already knows.
          report: The string to be logged.
        """
        junos_module.logger.info(report)

    return myprogress


def main():
    CHECKSUM_ALGORITHM_CHOICES = ["md5", "sha1", "sha256"]

    # Define the argument spec.
    software_argument_spec = dict(
        local_package=dict(
            required=False,
            aliases=["package"],
            type="path",
            default=None,
        ),
        remote_package=dict(
            required=False,
            type="path",
            # Default is '/var/tmp/' + filename from the
            # local_package option, if set.
            default=None,
        ),
        pkg_set=dict(required=False, type="list", default=None),
        version=dict(
            required=False,
            aliases=["target_version", "new_version", "desired_version"],
            type="str",
            # Default is determined from filename portion of
            # remote_package option.
            default=None,
        ),
        no_copy=dict(required=False, type="bool", default=False),
        reboot=dict(required=False, type="bool", default=True),
        reboot_pause=dict(required=False, type="int", default=10),
        issu=dict(required=False, type="bool", default=False),
        nssu=dict(required=False, type="bool", default=False),
        force_host=dict(required=False, type="bool", default=False),
        validate=dict(required=False, type="bool", default=False),
        cleanfs=dict(required=False, type="bool", default=True),
        all_re=dict(required=False, type="bool", default=True),
        member_id=dict(required=False, type="list", default=None),
        vmhost=dict(required=False, type="bool", default=False),
        checksum=dict(required=False, type="str", default=None),
        checksum_algorithm=dict(
            required=False,
            choices=CHECKSUM_ALGORITHM_CHOICES,
            type="str",
            default="md5",
        ),
        checksum_timeout=dict(required=False, type="int", default=300),
        cleanfs_timeout=dict(required=False, type="int", default=300),
        install_timeout=dict(required=False, type="int", default=1800),
        kwargs=dict(
            required=False,
            aliases=["kwarg", "args", "arg"],
            type="dict",
            default=None,
        ),
    )
    # Save keys for later. Must do because software_argument_spec gets
    # modified.
    option_keys = list(software_argument_spec.keys())

    # Create the module instance.
    junos_module = juniper_junos_common.JuniperJunosModule(
        argument_spec=software_argument_spec,
        # Mutually exclusive options.
        mutually_exclusive=[["issu", "nssu"]],
        # One of local_package and remote_package is required.
        required_one_of=[["local_package", "remote_package", "pkg_set"]],
        supports_check_mode=True,
    )

    # Straight from params
    local_package = junos_module.params.pop("local_package")
    remote_package = junos_module.params.pop("remote_package")
    pkg_set = junos_module.params.pop("pkg_set")
    target_version = junos_module.params.pop("version")
    no_copy = junos_module.params.pop("no_copy")
    reboot = junos_module.params.pop("reboot")
    reboot_pause = junos_module.params.pop("reboot_pause")
    install_timeout = junos_module.params.pop("install_timeout")
    cleanfs = junos_module.params.pop("cleanfs")
    all_re = junos_module.params.pop("all_re")
    member_id = junos_module.params.pop("member_id")
    kwargs = junos_module.params.pop("kwargs")

    url = None
    remote_dir = None
    if remote_package is not None:
        # Is the remote package a URL?
        parsed_url = urlparse(remote_package)
        if parsed_url.scheme == "":
            # A file on the remote host.
            (remote_dir, remote_filename) = os.path.split(remote_package)
        else:
            url = remote_package
            (_0, remote_filename) = os.path.split(parsed_url.path)
    else:
        # Default remote_dir value
        remote_dir = "/var/tmp"
        remote_filename = ""

    if url is not None and local_package is not None:
        junos_module.fail_json(
            msg="There remote_package (%s) is a URL. "
            "The local_package option is not allowed." % remote_package,
        )

    if url is not None and no_copy is True:
        junos_module.fail_json(
            msg="There remote_package (%s) is a URL. "
            "The no_copy option is not allowed." % remote_package,
        )

    if url is None:
        local_filename = None
        if local_package is not None:
            # Expand out the path.
            local_package = os.path.abspath(local_package)
            (local_dir, local_filename) = os.path.split(local_package)
            if local_filename == "":
                junos_module.fail_json(
                    msg="There is no filename component to "
                    "the local_package (%s)." % local_package,
                )
        elif remote_package is not None:
            # remote package was, so we must assume no_copy.
            no_copy = True

        if no_copy is False:
            if local_package is not None and not os.path.isfile(local_package):
                junos_module.fail_json(
                    msg="The local_package (%s) is not a "
                    "valid file on the local Ansible "
                    "control machine." % local_package,
                )
            elif pkg_set is not None:
                pkg_set = [os.path.abspath(item) for item in pkg_set]
                for pkg_set_item in pkg_set:
                    if not os.path.isfile(pkg_set_item):
                        junos_module.fail_json(
                            msg="The pkg (%s) is not a valid file on the local"
                            " Ansible control machine." % pkg_set_item,
                        )

        if remote_filename == "":
            # Use the same name as local_filename
            remote_filename = local_filename

        if local_filename is not None and remote_filename != local_filename:
            junos_module.fail_json(
                msg="The filename of the remote_package "
                "(%s) must be the same as the filename "
                "of the local_package (%s)." % (remote_filename, local_filename),
            )

    # If no_copy is True, then we need to turn off cleanfs to keep from
    # deleting the software package which is already present on the device.
    if no_copy is True:
        cleanfs = False

    if target_version is None and pkg_set is None:
        target_version = parse_version_from_filename(remote_filename)
    junos_module.logger.debug("New target version is: %s.", target_version)

    # Initialize the results. Assume not changed and failure until we know.
    results = {
        "msg": "",
        "changed": False,
        "check_mode": junos_module.check_mode,
        "failed": True,
    }

    if junos_module.conn_type == "local":
        facts = dict(junos_module.dev.facts)
    else:
        facts = junos_module.get_facts()
        # facts checking has been done as part of persitent connection itself.

    # Check version info to see if we need to do the install.
    if target_version is not None:
        if all_re is True:
            junos_info = facts["junos_info"]
            for current_re in junos_info:
                if (facts["vmhost"]) and (current_re in facts["vmhost_info"]):
                    current_version = facts["vmhost_info"][current_re][
                        "vmhost_version_set_b"
                    ]
                    if (
                        facts["vmhost_info"][current_re]["vmhost_current_root_set"]
                        == "p"
                    ):
                        current_version = parse_version_from_filename(
                            facts["vmhost_info"][current_re]["vmhost_version_set_b"],
                        )
                    else:
                        current_version = parse_version_from_filename(
                            facts["vmhost_info"][current_re]["vmhost_version_set_p"],
                        )
                else:
                    current_version = junos_info[current_re]["text"]
                if target_version != current_version:
                    junos_module.logger.debug(
                        "Current version on %s: %s. Target version: %s.",
                        current_version,
                        current_re,
                        target_version,
                    )
                    results["changed"] = True
                else:
                    results["msg"] += (
                        "Current version on %s: %s same as Targeted "
                        "version: %s.\n" % (current_version, current_re, target_version)
                    )
        else:
            if junos_module.conn_type == "local":
                re_name = junos_module.dev.re_name
            else:
                re_name = junos_module._pyez_conn.get_re_name()
            if (facts["vmhost"]) and (re_name in facts["vmhost_info"]):
                if facts["vmhost_info"][re_name]["vmhost_current_root_set"] == "p":
                    current_version = parse_version_from_filename(
                        facts["vmhost_info"][re_name]["vmhost_version_set_b"],
                    )
                else:
                    current_version = parse_version_from_filename(
                        facts["vmhost_info"][re_name]["vmhost_version_set_p"],
                    )
            else:
                current_version = facts["version"]
            if target_version != current_version:
                junos_module.logger.debug(
                    "Current version on %s: %s. Target version: %s.",
                    current_version,
                    re_name,
                    target_version,
                )
                results["changed"] = True
            else:
                results[
                    "msg"
                ] += "Current version on %s: %s same as Targeted " "version: %s.\n" % (
                    current_version,
                    re_name,
                    target_version,
                )
    else:
        # A non-Junos install. Always attempt to install.
        results["changed"] = True

    # Do the install if necessary
    if results["changed"] is True and not junos_module.check_mode:
        junos_module.logger.debug("Beginning installation of %s.", remote_filename)
        # Calculate the install parameters
        install_params = {}
        if url is not None:
            install_params["package"] = url
        elif local_package is not None:
            install_params["package"] = local_package
        elif pkg_set is not None:
            install_params["pkg_set"] = pkg_set
        else:
            install_params["package"] = remote_filename
        if remote_dir is not None:
            install_params["remote_path"] = remote_dir
        if junos_module.conn_type != "local":
            install_params["progress"] = True
        else:
            install_params["progress"] = define_progress_callback(junos_module)
        install_params["cleanfs"] = cleanfs
        install_params["no_copy"] = no_copy
        install_params["timeout"] = install_timeout
        install_params["all_re"] = all_re
        install_params["member_id"] = member_id
        for key in option_keys:
            value = junos_module.params.get(key)
            if value is not None:
                install_params[key] = value
        if kwargs is not None:
            install_params.update(kwargs)

        junos_module.logger.debug("Install parameters are: %s", str(install_params))
        if junos_module.conn_type != "local":
            try:
                results["msg"] = junos_module._pyez_conn.software_api(install_params)
            except Exception as err:  # pylint: disable=broad-except
                if "ConnectionError" in str(type(err)):
                    # If Exception is ConnectionError, it is excpected
                    # Device installation inititated succesfully
                    junos_module.logger.debug("Package successfully installed.")
                    results["msg"] += "Package successfully installed."
                else:
                    # If exception is not ConnectionError
                    # we will raise the exception
                    raise
            junos_module.logger.debug("Package successfully installed")
        else:
            try:
                junos_module.add_sw()
                ok, msg_ret = junos_module.sw.install(**install_params)
                if ok is not True:
                    results["msg"] = "Unable to install the software %s", msg_ret
                    junos_module.fail_json(**results)
                msg = (
                    "Package %s successfully installed. Response from device is: %s"
                    % (
                        install_params.get("package") or install_params.get("pkg_set"),
                        msg_ret,
                    )
                )
                results["msg"] = msg
                junos_module.logger.debug(msg)
            except (
                junos_module.pyez_exception.ConnectError,
                junos_module.pyez_exception.RpcError,
            ) as ex:
                results["msg"] = "Installation failed. Error: %s" % str(ex)
                junos_module.fail_json(**results)
        if reboot is True:
            junos_module.logger.debug("Initiating reboot.")
            if junos_module.conn_type != "local":
                try:
                    # Handling reboot of specific VC members
                    if member_id is not None:
                        results["msg"] += junos_module._pyez_conn.reboot_api(
                            all_re,
                            install_params.get("vmhost"),
                            member_id=member_id,
                        )
                    else:
                        results["msg"] += junos_module._pyez_conn.reboot_api(
                            all_re,
                            install_params.get("vmhost"),
                        )
                except Exception as err:  # pylint: disable=broad-except
                    if "ConnectionError" in str(type(err)):
                        # If Exception is ConnectionError, it is excpected
                        # Device reboot inititated succesfully
                        junos_module.logger.debug("Reboot RPC executed.")
                        results["msg"] += " Reboot succeeded."
                    else:
                        # If exception is not ConnectionError
                        # we will raise the exception
                        raise
                junos_module.logger.debug("Reboot RPC successfully initiated.")
            else:
                try:
                    # Try to deal with the fact that we might not get the closing
                    # </rpc-reply> and therefore might get an RpcTimeout.
                    # (This is a known Junos bug.) Set the timeout low so this
                    # happens relatively quickly.
                    restore_timeout = junos_module.dev.timeout
                    if junos_module.dev.timeout > 5:
                        junos_module.logger.debug(
                            "Decreasing device RPC timeout to 5 seconds.",
                        )
                        junos_module.dev.timeout = 5
                    try:
                        if member_id is not None:
                            got = junos_module.sw.reboot(
                                0,
                                None,
                                all_re,
                                None,
                                install_params.get("vmhost"),
                                member_id=member_id,
                            )
                        else:
                            got = junos_module.sw.reboot(
                                0,
                                None,
                                all_re,
                                None,
                                install_params.get("vmhost"),
                            )
                        junos_module.dev.timeout = restore_timeout
                    except Exception:  # pylint: disable=broad-except
                        junos_module.dev.timeout = restore_timeout
                        if not facts["vmhost"]:  # To handle vmhost reboot PR 1375936
                            raise
                    junos_module.logger.debug("Reboot RPC executed.")

                    if got is not None:
                        results["msg"] += (
                            " Reboot successfully initiated. "
                            "Reboot message: %s" % got
                        )
                    else:
                        # This is the else clause of the for loop.
                        # It only gets executed if the loop finished without
                        # hitting the break.
                        results["msg"] += (
                            " Did not find expected response " "from reboot RPC. "
                        )
                        junos_module.fail_json(**results)
                except junos_module.pyez_exception.RpcTimeoutError as ex:
                    # This might be OK. It might just indicate the device didn't
                    # send the closing </rpc-reply> (known Junos bug).
                    # Try to close the device. If it closes cleanly, then it was
                    # still reachable, which probably indicates a problem.
                    try:
                        junos_module.close(raise_exceptions=True)
                        # This means the device wasn't already disconnected.
                        results["msg"] += (
                            " Reboot failed. It may not have been " "initiated."
                        )
                        junos_module.fail_json(**results)
                    except (
                        junos_module.pyez_exception.RpcError,
                        junos_module.pyez_exception.RpcTimeoutError,
                        junos_module.pyez_exception.ConnectError,
                    ):
                        # This is expected. The device has already disconnected.
                        results["msg"] += " Reboot succeeded."
                    except junos_module.ncclient_exception.TimeoutExpiredError:
                        # This is not really expected. Still consider reboot success as
                        # Looks like rpc was consumed but no response as its rebooting.
                        results["msg"] += " Reboot succeeded. Ignoring close error."
                except (
                    junos_module.pyez_exception.RpcError,
                    junos_module.pyez_exception.ConnectError,
                ) as ex:
                    results["msg"] += " Reboot failed. Error: %s" % (str(ex))
                    junos_module.fail_json(**results)
                else:
                    try:
                        junos_module.close()
                    except junos_module.ncclient_exception.TimeoutExpiredError:
                        junos_module.logger.debug(
                            "Ignoring TimeoutError for close call",
                        )

                junos_module.logger.debug("Reboot RPC successfully initiated.")
            if reboot_pause > 0:
                junos_module.logger.debug("Sleeping for %d seconds", reboot_pause)
                time.sleep(reboot_pause)

    # If we made it this far, it's success.
    results["failed"] = False

    junos_module.exit_json(**results)


if __name__ == "__main__":
    main()
