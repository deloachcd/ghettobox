import os
from passlib.hash import nthash


def tag(loader, node):
    mapping = loader.construct_mapping(node, deep=True)
    user = mapping["username"]
    md4 = nthash.hash(mapping["passwd"]).upper()
    smbpasswd = f"{user}:1000:XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX:{md4}:[U          ]:LCT-62BA653F:"

    if not os.path.exists("ansible/roles/samba/files"):
        os.makedirs("ansible/roles/samba/files")
    with open("ansible/roles/samba/files/smbpasswd", "w") as outfile:
        outfile.write(smbpasswd)
    return None
