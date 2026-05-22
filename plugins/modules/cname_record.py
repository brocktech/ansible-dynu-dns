#!/usr/bin/python

# Copyright: (c) 2024, Curtis Jones <cjones2@brocku.ca>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: cname_record

short_description: Module to manage CNAME records using DynuDNS api.

# If this is part of a collection, you need to use semantic versioning,
# i.e. the version is of the form "2.5.0" and not "2.4".
version_added: "1.0.0"

description: This module queries the DYNU DNS api and uses it to create CNAME records.

options:
    host:
        description: Hostname of the alias destination.
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
target:
    description: Target of the alias.
    type: str
    returned: when state=present
    sample: x.y.z.example.com
"""

from string import ascii_lowercase, digits
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import fetch_url
from ansible_collections.brocktech.dynu_dns.plugins.module_utils.dynu_dns import (
    api_get_records,
    api_post_record,
    api_delete_record,
    validate_dns_hostname,
)


def create_or_update_record(module: AnsibleModule, result: dict):
    record = next(api_get_records(module, result), None)

    record_data = {"host": module.params["host"]}

    if record is None:
        record = api_post_record(
            module,
            result,
            None,
            record_data,
        )
        result["changed"] = True

    if record["host"] != module.params["host"]:
        record = api_post_record(
            module,
            result,
            record["id"],
            record_data,
        )
        result["changed"] = True

    result["id"] = record["id"]
    result["hostname"] = record["hostname"]
    result["host"] = record["host"]


def remove_record(module: AnsibleModule, result: dict):
    record = next(api_get_records(module, result), None)

    if record is None:
        return

    api_delete_record(module, result, record["id"])
    result["changed"] = True


def run_module():
    # define available arguments/parameters a user can pass to the module
    module_args = dict(
        api_key=dict(type="str", required=True, no_log=True),
        zone=dict(type="str", required=True),
        node_name=dict(type="str", required=True),
        group=dict(type="str", required=False),
        time_to_live=dict(type="int", required=False, default=60),
        host=dict(type="str", required=False),
        state=dict(
            type="str", required=False, default="present", choices=["present", "absent"]
        ),
    )

    module_args_required_if = [("state", "present", ["host"], True)]

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

    # always set the record type to A
    module.params["type"] = "CNAME"

    match module.params["state"]:
        case "present":
            validate_dns_hostname(module, result, "host")
            create_or_update_record(module, result)
        case "absent":
            remove_record(module, result)

    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
