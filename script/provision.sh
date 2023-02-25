#!/bin/bash
source venv/bin/activate
ansible-playbook --ask-become-pass -i user/inventory.yml \
                 -e user/secrets.yml \
                 user/main.yml
deactivate
