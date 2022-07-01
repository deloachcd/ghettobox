#!/bin/bash

create_gb_file_from_template() {
    echo "Creating 'user/ghettobox.yml' from template."
    cp templates/ghettobox.yml user/ghettobox.yml
    chmod 600 user/ghettobox.yml
}

if [[ ! -d venv ]]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt
deactivate

if [[ ! -d user ]]; then
    mkdir user
fi

if [[ -e user/ghettobox.yml ]]; then
    echo
    echo "Found a ghettobox.yml file in 'user' directory."
    read -p "Overwrite it from template? (y/n) " ANSWER
    if [[ $ANSWER == "y" ]]; then
        create_gb_file_from_template
    fi
else
    create_gb_file_from_template
fi
echo
echo "Initialized succesfully!"
