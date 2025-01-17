#!/usr/bin/python

# Copyright: (c) 2024, Curtis Jones <cjones2@brocku.ca>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: user

short_description: Module to DNS records using DynuDNS api.

# If this is part of a collection, you need to use semantic versioning,
# i.e. the version is of the form "2.5.0" and not "2.4".
version_added: "1.0.0"

description: This module queries the DYNU DNS api nad created DNS records.

options:
    api_key:
        description: API Key to authenticate to the server.
        required: true
        type: str
    zone:
        description: DNS name of the zone to create the record under.
        required: true
        type: str
    node_name:
        description: Name of the DNS node.
        required: true
        type: str
    type:
        description: DNS Record type.
        required: false
        type: str
        default: 'A'
        choices:
            - 'A'
            - 'AAAA'
    group:
        description: Name of group to associate with.
        required: false
        type: str
    state:
        description: Name of group to associate with.
        required: false
        default: 'present'
        type: str
        choices:
            - 'present'
            - 'absent'

# Specify this value according to your collection
# in format of namespace.collection.doc_fragment_name
# extends_documentation_fragment:
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
value:
    description: Content of the record.
    type: str
    returned: when state=present
    sample: 192.168.1.1
"""

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import fetch_url
from ansible.module_utils.dynu_dns import api_get_zone


base_url = "https://api.dynu.com/v2/dns"
json_mime = "application/json"


def get_headers(module: AnsibleModule) -> dict:
    return {"Accept": json_mime, "API-Key": module.params["api_key"]}


def post_headers(module: AnsibleModule) -> dict:
    return {
        "Accept": json_mime,
        "Content-Type": json_mime,
        "API-Key": module.params["api_key"],
    }


def api_get_zone_id(module: AnsibleModule, result: dict) -> int:
    zone = api_get_zone(module, result)

    if zone is None:
        module.fail_json(
            msg=f"Could not find zone with name: {module.params["zone"]}",
            **result,
        )

    return zone["id"]


def api_get_record(module: AnsibleModule, result: dict, zone_id: str) -> dict | None:
    headers = get_headers(module)

    records, records_info = fetch_url(
        module=module,
        url=f"{base_url}/{zone_id}/record",
        headers=headers,
        method="GET",
    )

    if records_info["status"] != 200:
        module.fail_json(
            msg=f"Failed to list records in {module.params["zone"]}. Error: {records_info["body"]}",
            **result,
        )

    res_json = module.from_json(records.read())

    return next(
        (
            record
            for record in res_json["dnsRecords"]
            if record["nodeName"] == module.params["node_name"]
        ),
        None,
    )


def api_create_record(module: AnsibleModule, result: dict, zone_id: int):
    headers = post_headers(module)

    record_create, record_create_info = fetch_url(
        module=module,
        url=f"{base_url}/{zone_id}/record",
        headers=headers,
        method="POST",
        data=module.jsonify(
            {
                "nodeName": module.params["node_name"],
                "recordType": module.params["type"],
                "ttl": 60,
                "state": True,
                "group": module.params.get("group", ""),
                "ipv4Address": module.params["value"],
            }
        ),
    )

    if record_create_info["status"] != 200:
        module.fail_json(
            msg=f"Failed to create {module.params["node_name"]}.{module.params["zone"]} Error: {record_create_info["body"]}",
            **result,
        )

    json = module.from_json(record_create.read())

    result["changed"] = True
    result["id"] = json["id"]
    result["hostname"] = json["hostname"]
    result["value"] = json["content"]
    module.exit_json(**result)


def api_update_record(
    module: AnsibleModule, result: dict, zone_id: int, record_id: int
):
    headers = post_headers(module)

    record_update, record_update_info = fetch_url(
        module=module,
        url=f"{base_url}/{zone_id}/record/{record_id}",
        headers=headers,
        method="POST",
        data=module.jsonify(
            {
                "nodeName": module.params["node_name"],
                "recordType": module.params["type"],
                "ttl": 60,
                "state": True,
                "group": module.params.get("group", ""),
                "ipv4Address": module.params["value"],
            }
        ),
    )

    if record_update_info["status"] != 200:
        module.fail_json(
            msg=f"Failed to update {module.params["node_name"]}.{module.params["zone"]} Error: {record_update_info["body"]}",
            **result,
        )

    json = module.from_json(record_update.read())

    result["changed"] = True
    result["id"] = json["id"]
    result["hostname"] = json["hostname"]
    result["value"] = json["content"]
    module.exit_json(**result)


def api_remove_record(
    module: AnsibleModule, result: dict, zone_id: int, record_id: int
):
    headers = get_headers(module)

    _, record_delete = fetch_url(
        module=module,
        url=f"{base_url}/{zone_id}/record/{record_id}",
        headers=headers,
        method="DELETE",
    )

    if record_delete["status"] != 200:
        module.fail_json(
            msg=f"Failed to delete {module.params["node_name"]}.{module.params["zone"]} Error: {record_delete["body"]}",
            **result,
        )

    result["changed"] = True
    module.exit_json(**result)


def create_or_update_record(module: AnsibleModule, result: dict, zone_id: int):
    record = api_get_record(module, result, zone_id)

    if record is None:
        api_create_record(module, result, zone_id)

    if record["content"] != module.params["value"]:
        api_update_record(module, result, zone_id, record["id"])

    result["id"] = json["id"]
    result["hostname"] = json["hostname"]
    result["value"] = json["content"]
    module.exit_json(**result)


def remove_record(module: AnsibleModule, result: dict, zone_id: int):
    record = api_get_record(module, result, zone_id)

    if record is None:
        module.exit_json(**result)

    api_remove_record(module, result, zone_id, record["id"])


def run_module():
    # define available arguments/parameters a user can pass to the module
    module_args = dict(
        api_key=dict(type="str", required=True, no_log=True),
        zone=dict(type="str", required=True),
        node_name=dict(type="str", required=True),
        value=dict(type="str", required=False),
        type=dict(type="str", required=False, default="A", choices=["A", "AAAA"]),
        group=dict(type="str", required=False),
        state=dict(
            type="str", required=False, default="present", choices=["present", "absent"]
        ),
    )

    module_args_required_if = [("state", "present", ("value"))]

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

    zone_id = api_get_zone_id(module, result)

    match module.params["state"]:
        case "present":
            create_or_update_record(module, result, zone_id)
        case "absent":
            remove_record(module, result, zone_id)


def main():
    run_module()


if __name__ == "__main__":
    main()
