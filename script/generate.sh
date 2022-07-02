#!/bin/bash
set -euo pipefail

source venv/bin/activate
python script/python/create_ansible.py
deactivate

cat > ansible/provision.sh << EOF
#!/bin/sh
ansible-playbook --ask-become-pass -i inventory.ini main.yml
EOF
chmod u+x ansible/provision.sh
