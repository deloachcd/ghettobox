#!/bin/bash
set -euo pipefail

source venv/bin/activate
python script/create_ansible.py
deactivate
