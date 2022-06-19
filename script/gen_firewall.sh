#!/bin/bash

services=$(grep -v '^\s*#' services.yml | tail -n +2 | awk '{ print $2 }')
files="core/nginx/ports.list"
for service in $services; do
    if [[ -e modules/$service/ports.list ]]; then
        files="$files modules/$service/ports.list"
    fi
done
# Ensure ports.list files have a newline at the end
for file in $files; do
    if test "$(tail -c 1 "$file")"; then
        echo >> "$file"
    fi
done
echo $files

# Doing things the easy way, but maybe not the most efficient way
ports=$(cat $files)
lan_ports="["$(  echo "$ports" | grep 'global' | awk '{ print $2","}' | xargs)"]"
wan_ports="["$(  echo "$ports" | grep 'local'  | awk '{ print $2","}' | xargs)"]"
proxy_ports="["$(echo "$ports" | grep 'proxy'  | awk '{ print $2","}' | xargs)"]"

# Generate our Ansible for firewall configuration
python3 << EOF
import yaml

firewall_provision = [
    {"name": "LAN ports provisioning", "loop": $lan_ports},
    {"name": "Proxied ports provisioning", "loop": $proxy_ports},
    {"name": "WAN ports provisioning", "loop": $wan_ports},
]
print(yaml.safe_dump(firewall_provision))
EOF

