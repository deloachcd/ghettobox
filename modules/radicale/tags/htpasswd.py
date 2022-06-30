import bcrypt
import os


def tag(loader, node):
    mapping = loader.construct_mapping(node, deep=True)
    user = mapping["username"]
    passwd = mapping["passwd"]
    bcrypted = bcrypt.hashpw(passwd.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode(
        "utf-8"
    )
    htpasswd = f"{user}:{bcrypted}"

    if not os.path.exists("ansible/roles/radicale/files"):
        os.makedirs("ansible/roles/radicale/files")
    with open("ansible/roles/radicale/files/users", "w") as outfile:
        outfile.write(htpasswd)
    return None
