#!/usr/bin/env python3

import yaml
import os
import shutil
import subprocess
import importlib


def get_inventory_loader():
    # If the !dynamic tag is encountered, forward inventory YAML node from
    # ghettobox.yml to modules/{name}/loader.py
    def dynamic_constructor(loader, node):
        mapping = loader.construct_mapping(node, deep=True)
        module_name = list(mapping.keys())[0]
        import_path = f"modules.{module_name}.loader"
        module = importlib.import_module(import_path)
        module.parser(node)
        return {}

    loader = yaml.SafeLoader
    loader.add_constructor("!dynamic", dynamic_constructor)
    return loader


def service2role(service_name, service_path):
    # TODO make more flexible, so that everything is optional
    return
    with open(os.path.join(service_path, "service.yml"), "r") as infile:
        service_yml = yaml.safe_load(infile.read())

    # Write tasks from specification to where ansible will see them
    os.makedirs(f"ansible/roles/{service_name}/tasks")
    with open(f"ansible/roles/{service_name}/tasks/main.yml", "w") as outfile:
        outfile.write(yaml.safe_dump(service_yml["service"]["tasks"]))

    for directory in [
        "handlers",
        "templates",
        "files",
        "vars",
        "defaults",
        "meta",
        "library",
        "module_utils",
        "lookup_plugins",
    ]:
        directory_path = os.path.join(service_path, directory)
        if os.path.exists(directory_path):
            shutil.copytree(
                directory_path, os.path.join(f"ansible/roles/{service_name}", directory)
            )
    # TODO proxy
    # TODO firewall
    # TODO docker-compose


develop = True

with open("templates/ghettobox.yml", "r") as infile:
    gb_yml = yaml.load(infile.read(), Loader=get_inventory_loader())

inventory_yml = {
    "gb_host": {
        "hosts": {gb_yml["host"]: ""},
        "vars": {
            "ansible_ssh_user": gb_yml["vars"]["gb_user"],
            **gb_yml["vars"],
        },
    }
}

# TODO warn or archive
if os.path.exists("ansible/"):
    shutil.rmtree("ansible/")

os.makedirs("ansible/roles")

# The roles in this list are generated before the ones in our modules
base_playbook_yml = [
    {"hosts": "gb_host", "roles": ["docker", "setup", "proxy", "firewall"]}
]

## First, the externally-developed role to install docker is checked out
# NOTE I don't use submodules to checkout this external git repo, because submodules are
#      the most broken, unintuitive trash feature that git includes.
if gb_yml["vars"]["host_arch"].upper() == "ARM":
    docker_upstream = "https://github.com/geerlingguy/ansible-role-docker"
else:
    docker_upstream = "https://github.com/geerlingguy/ansible-role-docker_arm"
# TODO get rid of this after script is relatively stable
if not develop:
    subprocess.run(
        ["git", "clone", f"{docker_upstream}", "ansible/roles/docker"], check=True
    )


for service in gb_yml["services"]:
    if service["enabled"]:
        # write service variables to inventory
        # TODO encrypted password files for samba and radicale
        inventory_yml["gb_host"]["vars"] = {
            **inventory_yml["gb_host"]["vars"],
            **service["vars"],
        }
        # write service name to roles
        base_playbook_yml[0]["roles"].append(service["name"])
        # Create ansible role from the service specification
        if not os.path.exists(f"modules/{service['name']}/service.yml"):
            print(f"WARN: Cannot find service.yml for {service['name']}")
        else:
            service2role(service["name"], f"modules/{service['name']}")
base_playbook_yml[0]["roles"].append("finalize")
