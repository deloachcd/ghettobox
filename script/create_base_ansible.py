#!/usr/bin/env python3

import yaml

with open("templates/ghettobox.yml", "r") as infile:
    gb_yml = yaml.safe_load(infile.read())

inventory_yml = {
    "gb_host": {
        "hosts": {gb_yml["provisioner"]["host"]: ""},
        "vars": {
            "ansible_ssh_user": gb_yml["provisioner"]["vars"]["gb_user"],
            **gb_yml["provisioner"]["vars"],
        },
    }
}
base_playbook_yml = [{"hosts": "gb_host", "roles": []}]

for service in gb_yml["provisioner"]["services"]:
    if service["enabled"]:
        inventory_yml["gb_host"]["vars"] = {
            **inventory_yml["gb_host"]["vars"],
            **service["vars"],
        }
        base_playbook_yml[0]["roles"].append(service["name"])
print(yaml.safe_dump(inventory_yml))
print(yaml.safe_dump(base_playbook_yml))
