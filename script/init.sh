#!/bin/bash

create_inventory_file_from_template() {
    echo "Creating 'user/inventory.yml' from template..."
    cp templates/inventory.yml user/inventory.yml
}

if [[ ! -d venv ]]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install ansible
deactivate

if [[ ! -d user ]]; then
    mkdir user
fi

if [[ ! -e user/secrets.yml ]]; then
    echo "Creating 'user/secrets.yml' from template..."
    cp templates/secrets.yml user/secrets.yml
    chmod 600 user/secrets.yml
fi

if [[ -e user/inventory.yml ]]; then
    echo
    echo "Found a inventory.yml file in 'user' directory."
    read -p "Overwrite it from template? (y/n) " ANSWER
    if [[ $ANSWER == "y" ]]; then
        create_inventory_file_from_template
    fi
else
    create_inventory_file_from_template
fi

echo "Creating docker-compose.yml.j2 from template..."
cp templates/docker-compose.yml.j2 roles/finalize/templates/docker-compose.yml.j2
ln -s roles/finalize/templates/docker-compose.yml.j2 user/docker-compose.yml.j2

echo "Creating Caddyfile from template..."
cp templates/Caddyfile roles/caddy/files/Caddyfile
ln -s roles/caddy/files/Caddyfile user/Caddyfile

echo
echo "Initialized succesfully!"
