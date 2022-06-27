#!/usr/bin/env python3

import yaml
import os
import shutil
import subprocess
import importlib

yml_tags = []
tag_handlers = {}


def rewind(_file):
    _file.seek(0)


def get_tag_logging_loader():
    # Returns a loader which logs all YAML tags, so that they can be
    # dynamically loaded from enabled services
    global yml_tags

    def log_tag(loader, node):
        yml_tags.append(node.tag)
        return None

    loader = yaml.SafeLoader
    loader.add_constructor(None, log_tag)
    return loader


def service2role(service_name, service_path):
    global docker_compose_yml

    with open(os.path.join(service_path, "service.yml"), "r") as infile:
        service_yml = yaml.safe_load(infile.read())

    # Copy tasks from specification to where ansible will see them
    os.makedirs(f"ansible/roles/{service_name}/tasks")
    if "tasks" in service_yml.keys():
        with open(f"ansible/roles/{service_name}/tasks/main.yml", "w") as outfile:
            outfile.write(yaml.safe_dump(service_yml["tasks"]))

    # Copy directories containing supplemental files to where ansible will see them
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
        if os.path.exists(directory_path) and not os.path.exists(
            f"ansible/roles/{service_name}"
        ):
            shutil.copytree(
                directory_path, os.path.join(f"ansible/roles/{service_name}", directory)
            )

    # Write's nginx config snippet for the proxy to nginx directory
    if "proxy" in service_yml.keys():
        with open(
            f"ansible/roles/nginx/files/nginx/services/{service_name}.conf", "w"
        ) as outfile:
            outfile.write(service_yml["proxy"])

    # TODO firewall

    # Write docker-compose configuration for service to compound docker-compose.yml
    # template
    if "compose" in service_yml.keys():
        docker_compose_yml["services"][service_name] = service_yml["compose"][
            service_name
        ]


develop = True

# First pass over file with basic YAML loader to get tags and enabled services
with open("templates/ghettobox.yml", "r") as infile:
    gb_yml = yaml.load(infile.read(), Loader=get_tag_logging_loader())

# We look for definitions for all tags in our modules
for service in gb_yml["services"]:
    if os.path.exists(f"modules/{service['name']}/tags"):
        for tag in yml_tags:
            modname = service["name"]
            tagname = tag[1:]
            if os.path.exists(f"modules/{modname}/tags/{tagname}.py"):
                import_path = f"modules.{modname}.tags.{tagname}"
                module = importlib.import_module(import_path)
                tag_handlers[tag] = module.tag
print(tag_handlers)


def get_inventory_loader():
    # If the !dynamic tag is encountered, forward inventory YAML node from
    # ghettobox.yml to modules/{name}/loader.py

    yml_loader = yaml.SafeLoader
    yml_loader.add_constructor(None, lambda loader, node: None)
    for tag, handler in tag_handlers.items():
        yml_loader.add_constructor(tag, handler)
    return yml_loader


# TODO don't re-open the file again because that's ugly
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
docker_compose_yml = {"version": "3", "services": {}}

# TODO warn or archive
if os.path.exists("ansible/"):
    shutil.rmtree("ansible/")

os.makedirs("ansible/roles")

# The roles in this list are generated before the ones in our modules
base_playbook_yml = [
    {"hosts": "gb_host", "roles": ["docker", "setup", "nginx", "firewall"]}
]

## docker
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

## setup
service2role("setup", "core/setup")

## nginx reverse proxy
if not os.path.exists("ansible/roles/nginx/files/nginx/services"):
    os.makedirs("ansible/roles/nginx/files/nginx/services")
service2role("nginx", "core/nginx")

## firewall

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
        if os.path.exists(f"modules/{service['name']}/service.yml"):
            service2role(service["name"], f"modules/{service['name']}")
base_playbook_yml[0]["roles"].append("finalize")

print(yaml.safe_dump(inventory_yml))
print(yaml.safe_dump(base_playbook_yml))
print(yaml.safe_dump(docker_compose_yml))
