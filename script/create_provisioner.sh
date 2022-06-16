#!/bin/bash
indented_cat() {
    awk -v N="$2" '{ for(i=0;i<N;i++) printf " "; print $0 }' "$1" 
}

if [[ ! -d ansible ]]; then
    mkdir ansible
else
    rm -r ansible/*
fi

for file in setup/inventory.ini $(find modules | grep inventory.ini | xargs); do
    cat $file
    echo
done > ansible/inventory.ini
chmod 600 ansible/inventory.ini
cat ansible/inventory.ini

cat > ansible/provision.yml << EOF
hosts: gb_host
roles:
  - setup
  - docker
  - nginx
$(grep -v '^\s*#' services.yml | tail -n +2)
  - finalize
EOF

cat ansible/provision.yml

create_ansible_role() {
    ROLE=$1
    # Generate a bunch of symlinks to create fleshed out ansible roles for our modules
    ROLE_HOME=ansible/$(basename $ROLE)
    mkdir -p $ROLE_HOME/tasks
    ln -s $ROLE/tasks.yml $ROLE_HOME/tasks/main.yml
}

# Construct templated docker-compose.yml file for all our containerized services
cat > docker-compose.yml.j2 << EOF
version: "3"
services:
EOF
for file in $(find modules | grep docker-compose.yml | xargs); do
    indented_cat $file 2
    echo
done >> docker-compose.yml.j2
cat docker-compose.yml.j2
