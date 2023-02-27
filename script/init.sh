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

if [[ ! -e user/main.yml ]]; then
    echo "Creating 'user/main.yml' from template..."
    cp templates/main.yml user/main.yml
fi

if [[ ! -e user/inventory.yml ]]; then
    echo "Creating 'user/inventory.yml' from template..."
    cp templates/inventory.yml user/inventory.yml
fi

if [[ ! -e user/secrets.yml ]]; then
    echo "Creating 'user/secrets.yml' from template..."
    cp templates/secrets.yml user/secrets.yml
    chmod 600 user/secrets.yml
fi

echo "Creating docker-compose.yml.j2 from template..."
cp templates/docker-compose.yml.j2 roles/finalize/templates/docker-compose.yml.j2
ln -sf roles/finalize/templates/docker-compose.yml.j2 user/docker-compose.yml.j2

echo "Creating Caddyfile from template..."
cp templates/Caddyfile roles/caddy/files/Caddyfile
ln -sf roles/caddy/files/Caddyfile user/Caddyfile

echo "Creating samba-config.yml from template..."
cp templates/samba-config.yml roles/samba/templates/config.yml
ln -sf roles/samba/templates/config.yml user/samba-config.yml

echo "Creating symlink to roles..."
cd user
ln -sf ../roles roles
cd ..

echo
echo "Initialized succesfully!"
