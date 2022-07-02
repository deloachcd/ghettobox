#!/usr/bin/env python3

import oyaml as yaml
import os
import shutil
import subprocess
import importlib
import jinja2
import re

# global variables for logging encountered YAML tags, and storing/mapping functions
# for handling them, loaded from modules
yml_tags = []
tag_handlers = {}

# flag to skip docker role cloning and confirmation to nuke existing ansible provisioner
develop = False


def dump_yaml(yaml_obj, path):
    with open(path, "w") as outfile:
        outfile.write(yaml.safe_dump(yaml_obj))


def write_yaml(yaml_obj, path):
    with open(path, "w") as outfile:
        outfile.write(yaml_obj)


def load_yaml(path):
    with open(path) as infile:
        yaml_obj = yaml.safe_load(infile.read())
    return yaml_obj


def rewind(_file):
    _file.seek(0)


def get_tag_logging_loader():
    """Returns a loader which logs all YAML tags, so that they can be
    dynamically loaded from enabled services"""
    global yml_tags

    def log_tag(loader, node):
        yml_tags.append(node.tag)
        return None

    loader = yaml.SafeLoader
    loader.add_constructor(None, log_tag)
    return loader


def get_inventory_loader():
    global tag_handlers

    yml_loader = yaml.SafeLoader
    yml_loader.add_constructor(None, lambda loader, node: node)
    for tag, handler in tag_handlers.items():
        yml_loader.add_constructor(tag, handler)
    return yml_loader


def service2role(service_name, service_path):
    """Uses global variables and direct file access to generate ansible roles
    from service modules by reading their service.yml files"""
    global docker_compose_yml
    global lan_access_ports
    global wan_access_ports

    service_yml = load_yaml(os.path.join(service_path, "service.yml"))

    # Copy tasks from specification to where ansible will see them
    service_root = f"ansible/roles/{service_name}"
    os.makedirs(os.path.join(service_root, "tasks"))
    if "tasks" in service_yml.keys():
        dump_yaml(service_yml["tasks"], f"ansible/roles/{service_name}/tasks/main.yml")

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
        module_path = os.path.join(service_path, directory)
        ansible_path = os.path.join(service_root, directory)
        if os.path.exists(module_path) and not os.path.exists(ansible_path):
            shutil.copytree(module_path, ansible_path)
        elif os.path.exists(module_path):
            for fname in os.listdir(module_path):
                fullpath = os.path.join(module_path, fname)
                shutil.copy(fullpath, ansible_path)

    # Write's nginx config snippet for the proxy to nginx directory
    if "proxy" in service_yml.keys():
        write_yaml(
            service_yml["proxy"],
            f"ansible/roles/nginx/files/services/{service_name}.conf",
        )

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
        for name, service in service_yml["compose"].items():
            docker_compose_yml["services"][name] = service


# Recursively delete existing provisioner if exists to have a blank slate
# for new one
if os.path.exists("ansible/") and not develop:
    print(
        "Warning: existing ansible provisioner files will be deleted to create a new one."
    )
    answer = input("Continue? (y/n) ")
    if answer == "y" or answer == "yes":
        shutil.rmtree("ansible/")
    else:
        print("Aborting.")
        exit(0)
elif os.path.exists("ansible/"):
    shutil.rmtree("ansible/")

# Create empty directories to be populated with provisioner files
os.makedirs("ansible/roles")

# First pass over ghettobox.yml with basic YAML loader to get tags and enabled services
gb_file = open("user/ghettobox.yml", "r")
gb_file_content = gb_file.read()
gb_yml = yaml.load(gb_file_content, Loader=get_tag_logging_loader())

# Utilize YAML object to construct jinja2 object for variable substitution
jinja2_data = {}
for key, value in gb_yml["vars"].items():
    jinja2_data[key] = value
for service in gb_yml["services"]:
    if service["enabled"]:
        for key, value in service["vars"].items():
            jinja2_data[key] = value

# Render a version of our YAML file, but with variables substituted
gb_file_substituted = jinja2.Template(gb_file_content).render(jinja2_data)

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

# Now that we've populated tag_handlers, we can load from our variable
# substituted file to get the YAML object we'll be working with to
# create our roles
gb_yml = yaml.load(gb_file_substituted, Loader=get_inventory_loader())
gb_file.close()

# global variables for accessing inventory, firewall ansible tasks and
# docker-compose file shared by all services
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

firewall_service_yml = load_yaml("core/firewall/service.yml")
# go through firewall tasks, find the tasks for applying access from LAN
# and WAN to ports specified in modules, and point to to the list they
# will loop through with "lan_access_ports" and "wan_access_ports" variables,
# respectively
for task in firewall_service_yml["tasks"][0]["block"]:
    if "[lan_anchor_task]" in task["name"]:
        task["name"] = task["name"].replace(" [lan_anchor_task]", "")
        lan_access_ports = task["loop"]
    elif "[wan_anchor_task]" in task["name"]:
        task["name"] = task["name"].replace(" [wan_anchor_task]", "")
        wan_access_ports = task["loop"]

# The roles in this list are generated before the ones in our modules
base_playbook_yml = [
    {
        "hosts": "gb_host",
        "roles": [{"role": "docker", "become": "yes"}, "setup", "nginx", "firewall"],
    }
]

### now that all global variables are defined, roles can be generated from services

## docker
# NOTE I don't use submodules to checkout this external git repo, because submodules are
#      the most broken, unintuitive trash feature that git includes.
if gb_yml["vars"]["host_arch"].upper() == "ARM":
    docker_upstream = "https://github.com/geerlingguy/ansible-role-docker_arm"
else:
    docker_upstream = "https://github.com/geerlingguy/ansible-role-docker"
# TODO get rid of this after script is relatively stable
if not develop:
    subprocess.run(
        ["git", "clone", f"{docker_upstream}", "ansible/roles/docker"], check=True
    )

## setup
service2role("setup", "core/setup")

## nginx reverse proxy
service2role("nginx", "core/nginx")
if not os.path.exists("ansible/roles/nginx/files/services"):
    os.makedirs("ansible/roles/nginx/files/services")

## firewall (tasks dynamically updated through services before dumping)
os.makedirs("ansible/roles/firewall/tasks")

## services defined in modules
for service in gb_yml["services"]:
    if service["enabled"]:
        ## get rid of keys with empty values
        # NOTE cast .items() to list to prevent runtime error from
        # dict size changing during iteration
        for key, value in list(service["vars"].items()):
            if not value or value == "":
                del service["vars"][key]
        ## write service variables to inventory
        inventory_yml["gb_host"]["vars"] = {
            **inventory_yml["gb_host"]["vars"],
            **service["vars"],
        }
        # write service name to roles
        base_playbook_yml[0]["roles"].append(service["name"])
        # Create ansible role from the service specification
        if os.path.exists(f"modules/{service['name']}/service.yml"):
            service2role(service["name"], f"modules/{service['name']}")

## finalize
base_playbook_yml[0]["roles"].append("finalize")
os.makedirs("ansible/roles/finalize/templates")
dump_yaml(docker_compose_yml, "ansible/roles/finalize/templates/docker-compose.yml.j2")
service2role("finalize", "core/finalize")

dump_yaml(firewall_service_yml["tasks"], "ansible/roles/firewall/tasks/main.yml")
dump_yaml(base_playbook_yml, "ansible/main.yml")
dump_yaml(inventory_yml, "ansible/inventory.yml")

print("Successfully generated provisioner in 'ansible' directory.")
