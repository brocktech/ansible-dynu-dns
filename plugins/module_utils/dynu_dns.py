from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import fetch_url


def api_get_zone(module: AnsibleModule, result: dict) -> dict | None:
    headers = get_headers(module.params["api_key"])

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
