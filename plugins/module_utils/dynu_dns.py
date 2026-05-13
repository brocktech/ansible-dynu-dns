from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import fetch_url
from collections.abc import Generator

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


def api_get_zone(module: AnsibleModule, result: dict) -> dict | None:
    headers = get_headers(module)

    zones, zones_info = fetch_url(
        module=module,
        url=f"{base_url}",
        headers=headers,
        method="GET",
    )

    if zones_info["status"] != 200:
        module.fail_json(
            msg=f"Failed to list domain zones. Error: {zones_info["body"]}",
            **result,
        )

    res_json = module.from_json(zones.read())

    return next(
        (zone for zone in res_json["domains"] if zone["name"] == module.params["zone"]),
        None,
    )


def api_get_records(
    module: AnsibleModule, result: dict, zone_id: str | None
) -> Generator[dict]:
    if zone_id is None:
        zone_query = api_get_zone(module, result)
        if zone_query is None:
            module.fail_json(
                msg=f"Could not find zone with name: {module.params["zone"]}",
                **result,
            )
        zone_id = zone_query

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
            msg=f"Failed to delete `{module.params["type"]}` -> {module.params["node_name"]}.{module.params["zone"]} Error: {record_delete["body"]}",
            **result,
        )

    result["changed"] = True
    module.exit_json(**result)
