#!/usr/bin/env python3
import sys
import yaml

with open("ansible/firewall/ports.list", "r") as infile:
    portdefs = infile.readlines()

with open("core/firewall/tasks.yml", "r") as infile:
    playbook_obj = yaml.safe_load(infile.read())

lan_entries = playbook_obj[0]["block"][2]["loop"]
wan_entries = playbook_obj[0]["block"][3]["loop"]
for portdef in portdefs:
    scope, port = portdef.replace("\n", "").split(" ")
    port = int(port)  # just for consistency, really
    if scope == "lan":
        lan_entries.append(port)
    elif scope == "wan":
        wan_entries.append(port)

print(yaml.safe_dump(playbook_obj))
