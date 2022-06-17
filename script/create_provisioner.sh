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

for file in core/setup/inventory.ini $(find modules | grep inventory.ini | xargs); do
    cat $file
    echo
done > ansible/inventory.ini
chmod 600 ansible/inventory.ini
cat ansible/inventory.ini

cat > ansible/provision.yml << EOF
hosts: gb_host
roles:
  - docker
  - setup
  - proxy
$(grep -v '^\s*#' services.yml | tail -n +2)
  - finalize
EOF

cat ansible/provision.yml

create_basic_ansible_role() {
    ROLE=$1
    # Generate a bunch of symlinks to create fleshed out ansible roles for our modules
    ROLE_HOME=ansible/$(basename $ROLE)
    # Main logic
    mkdir -p $ROLE_HOME/tasks
    ln -s $ROLE/tasks.yml $ROLE_HOME/tasks/main.yml
}

create_full_ansible_role() {
    ROLE=$1
    create_basic_ansible_role $ROLE
    # Files the main logic needs access to
    if [[ -d $ROLE/files ]]; then
        ln -s $ROLE/files $ROLE_HOME/files
    fi
    # Templates the main logic needs access to
    if [[ -d $ROLE/templates ]]; then
        ln -s $ROLE/templates $ROLE_HOME/templates
    fi
}

# TODO create roles from modules

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

# TODO firewall
# TODO nginx reverse proxy
