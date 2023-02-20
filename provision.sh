#!/bin/sh
ansible-playbook --ask-become-pass -i inventory.yml main.yml
