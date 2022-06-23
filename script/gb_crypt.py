import bcrypt
import passlib


class smbpasswd:
    @staticmethod
    def lmhash(s):
        return passlib.hash.lmhash.encrypt(s).upper()

    @staticmethod
    def nthash(s):
        return passlib.hash.nthash.encrypt(s).upper()


class htpasswd:
    # ripped off from https://gist.github.com/zobayer1/d86a59e45ae86198a9efc6f3d8682b49
    @staticmethod
    def encrypt(username, password):
        bcrypted = bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt(rounds=12)
        ).decode("utf-8")
        return f"{username}:{bcrypted}"
