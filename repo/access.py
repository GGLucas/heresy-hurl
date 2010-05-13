import shelve
import os
import time
import hashlib
import re
from threading import Lock

SSH_LOCK = Lock()


class HurlAccess(object):
    def __init__(self, userdb, commentdb, authkeys):
        self.userdb_file, self.commentdb_file, self.authkeys_file = \
            userdb, commentdb, authkeys

        self.userdb = shelve.DbfilenameShelf(self.userdb_file)
        self.commentdb = shelve.DbfilenameShelf(self.commentdb_file)
        self.keydb = SSHKeys(self.authkeys_file)

    def add_user(self, username, password):
        """
            Add a new user to the hurl repository.
        """
        if username in self.userdb:
            return 1

        if not re.match("^[A-Za-z0-9_-]+$", username):
            return 2

        user = HurlUser(username)
        user.set_password(password)

        self.userdb[username] = user
        self.userdb.sync()

        return 0

    def verify_user(self, username, password):
        """
            Verify if the correct password was specified.
        """
        if username not in self.userdb:
            return False

        if self.userdb[username].check_password(password):
            return self.userdb[username]
        else:
            return False

    def add_key(self, user, pubkey):
        """
            Add a public key to a user.
        """
        ind = [key for key, value in user.keys.items() if value == pubkey]
        if ind:
            return ind[0]
        else:
            num = max(user.keys.keys())+1 if user.keys else 0
            user.keys[num] = pubkey

            self.keydb.add(user.username, num, pubkey)
            self.userdb[user.username] = user
            self.userdb.sync()
            return num

    def change_password(self, user, password):
        """
            Change a user's password.
        """
        user.set_password(password)
        self.userdb[user.username] = user
        self.userdb.sync()
        return 0

    def remove_key(self, user, num):
        """
            Remove a public key from a user.
        """
        # Check if key num exists
        if num not in user.keys:
            return 1

        # Update user database
        del user.keys[num]
        self.userdb[user.username] = user
        self.userdb.sync()

        # Update keyfile
        self.keydb.remove(user.username, num)
        return 0


    def list_keys(self, user):
        """
            List all registered pubkeys a user has.
        """
        return user.keys


class SSHKeys(object):
    def __init__(self, authkeys):
        self.authkeys_file = authkeys

    def add(self, username, num, key):
        """
            Add a new key to the access database.
        """
        with SSH_LOCK:
            with open(self.authkeys_file, "a") as fd:
                fd.write(
                         ("""#hurl:%s:%d\n""" % (username, num)) +
                         ("""command="env HURLUSER=%s git shell",""" % username) +
                          """no-port-forwarding,no-X11-forwarding,""" +
                          """no-agent-forwarding,no-pty """ + 
                          key.replace("\n", "") + "\n")

    def remove(self, username, num):
        """
            Remove a key from the access database.
        """
        search_for =  "#hurl:%s:%d\n" % (username, num)

        with SSH_LOCK:
            with open(self.authkeys_file, "r") as source:
                lines = list(source.readlines())

            with open(self.authkeys_file, "w") as target:
                if lines:
                    line = lines.pop(0)
                    while lines and line:
                        if line == search_for:
                            if lines:
                                lines.pop(0)
                        else:
                            target.write(line)

                        if lines:
                            line = lines.pop(0)


class HurlUser(object):
    def __init__(self, username):
        self.username = username
        self.keys = {}

    def _hash(self, password):
        """
            Hash something correctly.
        """
        hasher = hashlib.sha1()
        hasher.update(password)
        return hasher.hexdigest()

    def set_password(self, password):
        """
            Set user's password.
        """
        self.password = self._hash(password)

    def check_password(self, password):
        """
            Check if this is the user's password.
        """
        return self.password == self._hash(password)
