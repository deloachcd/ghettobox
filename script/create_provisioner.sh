#!/bin/bash
set -euo pipefail

indented_cat() {
    awk -v N="$2" '{ for(i=0;i<N;i++) printf " "; print $0 }' "$1" 
}

if [[ ! -d ansible ]]; then
    mkdir ansible
else
    # TODO warn they're gonna nuke the existing provisioner!
    rm -r ansible/*
fi

# Ensure all non-hidden files end in a newline before we read them
for file in $(find . -not -path '*/.*'); do
    if test "$(tail -c 1 "$file")"; then
        echo >> "$file"
    fi
done

# Generate compound inventory file
for file in core/setup/inventory.ini $(find modules | grep inventory.ini | xargs); do
    cat $file
    echo
done > ansible/inventory.ini
chmod 600 ansible/inventory.ini
cat ansible/inventory.ini

enabled_services_list=$(grep -v '^\s*#' services.yml | tail -n +2)
cat > ansible/provision.yml << EOF
hosts: gb_host
roles:
  - {role: docker, become: yes, when: gb_install_docker}
  - setup
  - nginx
${enabled_services_list}
  - finalize
EOF
enabled_services=$(echo "$enabled_services_list" | awk '{ print $2 }')

create_basic_ansible_role() {
    ROLE=$1
    BACKLINK=$(echo $ROLE | awk '{ gsub(/[a-zA-Z0-9]+/, ".."); print $0 }')
    # Generate a bunch of symlinks to create fleshed out ansible roles for our modules
    ROLE_HOME=ansible/$(basename $ROLE)
    # Main logic
    mkdir -p $ROLE_HOME/tasks
    ln -s $BACKLINK/../$ROLE/tasks.yml $ROLE_HOME/tasks/main.yml
}

create_full_ansible_role() {
    ROLE=$1
    BACKLINK=$(echo $ROLE | awk '{ gsub(/[a-zA-Z0-9]+/, ".."); print $0 }')
    create_basic_ansible_role $ROLE
    # Files the main logic needs access to
    if [[ -d $ROLE/files ]]; then
        ln -s $BACKLINK/$ROLE/files $ROLE_HOME/files
    fi
    # Templates the main logic needs access to
    if [[ -d $ROLE/templates ]]; then
        ln -s $BACKLINK/$ROLE/templates $ROLE_HOME/templates
    fi
}

# Construct ansible roles
if [[ ! -e core/docker ]]; then
    # Assume ARM if arch is anything other than AMD64, because who is still running
    # a 32-bit operating system in 2022?
    if [[ $(uname -r) == "x86_64" ]]; then
        git clone https://github.com/geerlingguy/ansible-role-docker core/docker
    else
        git clone https://github.com/geerlingguy/ansible-role-docker_arm core/docker
    fi
fi
mkdir ansible/docker/tasks
ln -s core/docker ansible/docker

create_basic_ansible_role setup
mkdir -p ansible/firewall/tasks
for service in $enabled_services; do
    create_full_ansible_role modules/$service
    if [[ -e modules/$service/ports.list ]]; then
        cat modules/$service/ports.list >> ansible/firewall/ports.list
    fi
done
./script/add_ports_to_firewall_role.py > ansible/firewall/tasks/main.yml
rm ansible/firewall/ports.list

create_basic_ansible_role core/finalize
mkdir ansible/finalize/templates
# Construct templated docker-compose.yml file for all our containerized services
DOCKER_COMPOSE_FILE=ansible/finalize/templates/docker-compose.yml.j2
cat > $DOCKER_COMPOSE_FILE << EOF
version: "3"
services:
EOF
for file in $(find modules | grep docker-compose.yml | xargs); do
    indented_cat $file 2
    echo
done >> $DOCKER_COMPOSE_FILE
cat $DOCKER_COMPOSE_FILE

# TODO nginx reverse proxy
