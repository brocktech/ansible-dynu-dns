from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import fetch_url
from collections.abc import Generator
from enum import StrEnum, auto
from ipaddress import ip_address, IPv4Address

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


def validate_dns_hostname(module: AnsibleModule, result: dict, param: str):
    # dns records are case insensitive so we just make everything lowercase for simplicity.
    module.params[param] = module.params[param].lower()

    dns_allowed_characters = set(ascii_lowercase + digits + "-")

    labels = module.params[param].split(".")

    if len(labels) < 2:
        module.fail_json(
            msg=f"Error: {module.params[param]} is not a valid host name. Hostnames require at least to labels in order to be resolvable.",
            **result,
        )

    for label in labels:
        if not set(label).issubset(dns_allowed_characters):
            error = f"Error->Param({param}): {module.params[param]} is not a valid host name. Hostnames only allow alpha-numeric characters and the hyphen (-). Invalid label: `{label}`"
            module.fail_json(msg=error, **result)


def validate_ipv4_address(module: AnsibleModule, result: dict, param: str):
    invalid_ipv4 = False
    try:
        invalid_ipv4 = type(ip_address(module.params[param])) is not IPv4Address
    except ValueError:
        invalid_ipv4 = True

    if invalid_ipv4:
        module.fail_json(
            msg=f"Error: {module.params[param]} is not a valid IPv4 Address",
            **result,
        )


class ApiVerb(StrEnum):
    """Describe the different verbs we use to interact with the Dynu API."""

    CREATE = auto()
    """Create an item in the database, assumes item does not already exist or is being appended."""

    UPDATE = auto()
    """Update an item in the database, assumes item already exists."""

    DELETE = auto()
    """Remove and item from the database, succeeds if item is already not present."""

    LIST = auto()
    """List items in the database."""


def check_api_error(module: AnsibleModule, result: dict, verb: ApiVerb, info: dict):
    status = info["status"]
    if status != 200:
        body = info["body"] if "body" in info else "No message provided by API"
        record_type = (
            f"{module.params["type"]} record" if "type" in module.params else "record"
        )
        target = (
            f"{module.params["node_name"]}.{module.params["zone"]}"
            if verb != ApiVerb.LIST
            else f"{module.params["zone"]}"
        )
        plural = "s" if verb is ApiVerb.LIST else ""
        module.fail_json(
            msg=f"Failed to {verb.value} {record_type}{plural} for {target} -> Error ({status}): {body}",
            **result,
        )


def api_get_zones(module: AnsibleModule, result: dict) -> list[dict]:
    """Connect with Dynu API to get a list of zones on the account associated with **API-Key**.

    :arg module: Object representing the running ansible module, contains vars used for connection.
    :type module: :class:`ansible.module_utils.basic.AnsibleModule`
    :arg result: Dictionary that contains state that we are going to return to Ansible. Properties here can be used in playbooks.
    :type result: dict

    :returns: List of dictionaries that describe the zones available in the account.
    """
    headers = get_headers(module)

    zones, zones_info = fetch_url(
        module=module,
        url=f"{base_url}",
        headers=headers,
        method="GET",
    )

    status = zones_info["status"]
    if status != 200:
        body = (
            zones_info["body"] if "body" in zones_info else "No message provided by API"
        )
        module.fail_json(
            msg=f"Failed to list domain zones. Error ({status}): {body}",
            **result,
        )

    res_json = module.from_json(zones.read())

    return res_json["domains"]


def get_zone_id(module: AnsibleModule, result: dict) -> int:
    if "zone_id" in module.params:
        return module.params["zone_id"]

    zone = next(
        (
            zone
            for zone in api_get_zones(module, result)
            if zone["name"] == module.params["zone"]
        ),
        None,
    )

    if zone is None:
        module.fail_json(
            msg=f"Could not find zone with name: {module.params["zone"]}",
            **result,
        )

    module.params["zone_id"] = zone["id"]
    return zone["id"]


def api_get_records(module: AnsibleModule, result: dict) -> Generator[dict]:
    zone_id = get_zone_id(module, result)

    headers = get_headers(module)

    records, records_info = fetch_url(
        module=module,
        url=f"{base_url}/{zone_id}/record",
        headers=headers,
        method="GET",
    )

    check_api_error(module, result, ApiVerb.LIST, records_info)

    res_json = module.from_json(records.read())

    records_list = (
        (
            record
            for record in res_json["dnsRecords"]
            if record["nodeName"] == module.params["node_name"]
            and record["recordType"] == module.params["type"]
        )
        if "type" in module.params
        else (
            record
            for record in res_json["dnsRecords"]
            if record["nodeName"] == module.params["node_name"]
        )
    )

    return records_list


def api_delete_record(module: AnsibleModule, result: dict, record_id: int):
    zone_id = get_zone_id(module, result)

    headers = get_headers(module)

    _, record_delete = fetch_url(
        module=module,
        url=f"{base_url}/{zone_id}/record/{record_id}",
        headers=headers,
        method="DELETE",
    )

    check_api_error(module, result, ApiVerb.DELETE, record_delete)


def api_post_record(
    module: AnsibleModule,
    result: dict,
    record_id: int | None,
    record_data: dict,
) -> dict:
    zone_id = get_zone_id(module, result)

    headers = post_headers(module)

    base_record_data = {
        "nodeName": module.params["node_name"],
        "recordType": module.params["type"],
        "ttl": module.params["time_to_live"],
        "state": True,
        "group": module.params.get("group", ""),
    }

    verb = ApiVerb.CREATE
    url = f"{base_url}/{zone_id}/record"

    if record_id is not None:
        verb = ApiVerb.UPDATE
        url = f"{url}/{record_id}"

    record_post, record_post_info = fetch_url(
        module=module,
        url=url,
        headers=headers,
        method="POST",
        data=module.jsonify(base_record_data | record_data),
    )

    check_api_error(module, result, ApiVerb.UPDATE, record_post_info)

    json = module.from_json(record_post.read())

    return json
