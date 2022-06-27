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
    global lan_access_ports
    global wan_access_ports

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

    # Dynamically construct list of ports to open firewall to, through
    # global pointer variables
    if "firewall" in service_yml.keys():
        for portdef in service_yml["firewall"]:
            if portdef["scope"] == "lan" or portdef["scope"] == "local":
                lan_access_ports.append(portdef["port"])
            if portdef["scope"] == "wan" or portdef["scope"] == "any":
                wan_access_ports.append(portdef["port"])

    # Write docker-compose configuration for service to compound docker-compose.yml
    # template
    if "compose" in service_yml.keys():
        docker_compose_yml["services"][service_name] = service_yml["compose"][
            service_name
        ]


develop = True

# First pass over ghettobox.yml with basic YAML loader to get tags and enabled services
gb_file = open("templates/ghettobox.yml", "r")
gb_yml = yaml.load(gb_file.read(), Loader=get_tag_logging_loader())
rewind(gb_file)

# Search for handlers for all encountered tags in our modules
for service in gb_yml["services"]:
    if os.path.exists(f"modules/{service['name']}/tags"):
        for tag in yml_tags:
            modname = service["name"]
            tagname = tag[1:]
            if os.path.exists(f"modules/{modname}/tags/{tagname}.py"):
                import_path = f"modules.{modname}.tags.{tagname}"
                module = importlib.import_module(import_path)
                tag_handlers[tag] = module.tag


def get_inventory_loader():
    # If the !dynamic tag is encountered, forward inventory YAML node from
    # ghettobox.yml to modules/{name}/loader.py

    yml_loader = yaml.SafeLoader
    yml_loader.add_constructor(None, lambda loader, node: None)
    for tag, handler in tag_handlers.items():
        yml_loader.add_constructor(tag, handler)
    return yml_loader


# Second pass over ghettobox.yml, construct complete object now that we've
# retrieved all the tag handlers we're going to be able to find from our
# modules
gb_yml = yaml.load(gb_file.read(), Loader=get_inventory_loader())
gb_file.close()

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

with open("core/firewall/service.yml") as infile:
    firewall_tasks_yml = yaml.safe_load(infile.read())

# go through firewall tasks, find the tasks for applying access from LAN
# and WAN to ports specified in modules, and point to to the list they
# will loop through with "lan_access_ports" and "wan_access_ports" variables,
# respectively
for task in firewall_tasks_yml["tasks"][0]["block"]:
    if "[lan_anchor_task]" in task["name"]:
        task["name"] = task["name"].replace("[lan_anchor_task]", "")
        lan_access_ports = task["loop"]
    elif "[wan_anchor_task]" in task["name"]:
        task["name"] = task["name"].replace("[wan_anchor_task]", "")
        wan_access_ports = task["loop"]

# TODO nginx base config file templated

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
os.makedirs("ansible/roles/firewall/tasks")
with open("ansible/roles/firewall/tasks/main.yml", "w") as outfile:
    outfile.write(yaml.safe_dump(firewall_tasks_yml))

## services defined in modules
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
print(yaml.safe_dump(firewall_tasks_yml))
