#!/usr/bin/python

# Copyright: (c) 2024, Curtis Jones <cjones2@brocku.ca>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: a_record

short_description: Module to DNS records using DynuDNS api.

# If this is part of a collection, you need to use semantic versioning,
# i.e. the version is of the form "2.5.0" and not "2.4".
version_added: "1.0.0"

description: This module queries the DYNU DNS api and uses it to create A records.

options:
    ipv4_address:
        description: IPv4 Address to be the value for the record.
        required: false
        type: str

# Specify this value according to your collection
# in format of namespace.collection.doc_fragment_name
extends_documentation_fragment:
    - brocktech.dynu_dns.record
"""

EXAMPLES = r"""
# TODO - create examples.
"""

RETURN = r"""
# These are examples of possible return values, and in general should use other names for return values.
id:
    description: ID number for record
    type: int
    returned: when state=present
    sample: 1
hostname:
    description: Full hostname of record.
    type: str
    returned: when state=present
    sample: www.example.com
ipv4Address:
    description: IPv4 Address content of the record.
    type: str
    returned: when state=present
    sample: 192.168.1.1
"""

from ipaddress import ip_address, IPv4Address
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import fetch_url
from ansible_collections.brocktech.dynu_dns.plugins.module_utils.dynu_dns import (
    api_get_records,
    api_post_record,
    api_delete_record,
)


def create_or_update_record(module: AnsibleModule, result: dict):
    record = next(api_get_records(module, result), None)

    record_data = {"ipv4Address": module.params["ipv4_address"]}

    if record is None:
        record = api_post_record(
            module,
            result,
            None,
            record_data,
        )
        result["changed"] = True

    if record["ipv4Address"] != module.params["ipv4_address"]:
        record = api_post_record(
            module,
            result,
            record["id"],
            record_data,
        )
        result["changed"] = True

    result["id"] = record["id"]
    result["hostname"] = record["hostname"]
    result["ipv4Address"] = record["ipv4Address"]
    module.exit_json(**result)


def remove_record(module: AnsibleModule, result: dict):
    record = next(api_get_records(module, result), None)

    if record is None:
        module.exit_json(**result)

    api_delete_record(module, result, record["id"])
    result["changed"] = True
    module.exit_json(**result)


def run_module():
    # define available arguments/parameters a user can pass to the module
    module_args = dict(
        api_key=dict(type="str", required=True, no_log=True),
        zone=dict(type="str", required=True),
        node_name=dict(type="str", required=True),
        group=dict(type="str", required=False),
        time_to_live=dict(type="int", required=False, default=60),
        ipv4_address=dict(type="str", required=False),
        state=dict(
            type="str", required=False, default="present", choices=["present", "absent"]
        ),
    )

    module_args_required_if = [("state", "present", ["ipv4_address"], True)]

    # seed the result dict in the object
    # we primarily care about changed and state
    # changed is if this module effectively modified the target
    # state will include any data that you want your module to pass back
    # for consumption, for example, in a subsequent task
    result = dict(
        changed=False,
    )

    # the AnsibleModule object will be our abstraction working with Ansible
    # this includes instantiation, a couple of common attr would be the
    # args/params passed to the execution, as well as if the module
    # supports check mode
    module = AnsibleModule(
        argument_spec=module_args,
        required_if=module_args_required_if,
        supports_check_mode=True,
    )

    # if the user is working with this module in only check mode we do not
    # want to make any changes to the environment, just return the current
    # state with no modifications
    if module.check_mode:
        module.exit_json(**result)

    if "ipv4_address" in module.params:
        invalid_ipv4 = False
        try:
            invalid_ipv4 = (
                type(ip_address(module.params["ipv4_address"])) is not IPv4Address
            )
        except ValueError:
            invalid_ipv4 = True

        if invalid_ipv4:
            module.fail_json(
                msg=f"Error: {module.params["ipv4_address"]} is not a valid IPv4 Address",
                **result,
            )

    # always set the record type to A
    module.params["type"] = "A"

    match module.params["state"]:
        case "present":
            create_or_update_record(module, result)
        case "absent":
            remove_record(module, result)


def main():
    run_module()


if __name__ == "__main__":
    main()
