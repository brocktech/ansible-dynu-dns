from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import fetch_url

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
