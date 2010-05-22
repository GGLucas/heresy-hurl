import json
import cherrypy
import logging

PROTOCOL_VER = 1.0

class API(object):
    def __init__(self, repo, lookup, index, access):
        self.repo, self.lookup, self.index, self.access = \
            repo, lookup, index, access

    @cherrypy.expose
    def version(self):
        return str(PROTOCOL_VER)

    @cherrypy.expose
    def sync(self):
        try:
            request = json.load(cherrypy.request.body)
            data = self.repo.get_latest_versions(request["data"])

            return retdata(data)
        except:
            logging.exception("JSON api error.")
            return retdata(None, {"error": "Unexpected error."})

    @cherrypy.expose
    def search(self):
        try:
            request = json.load(cherrypy.request.body)

            # Search
            results, num, exact = self.index.search(request["data"])

            return retdata({
                "count": num,
                "is_exact": exact,
                "results": list(results),
            })
        except:
            logging.exception("JSON api error.")
            return retdata(None, {"error": "Unexpected error."})

    @cherrypy.expose
    def info(self):
        try:
            request = json.load(cherrypy.request.body)
            branch, pkg = self.repo.resolve(request["data"])
            data = self.repo.get_package_cakefile(branch, pkg)

            if data is None:
                return retdata(None)

            data.update({
                "branch": branch,
                "package": pkg})

            return retdata(data)
        except:
            logging.exception("JSON api error.")
            return retdata(None, {"error": "Unexpected error."})

    @cherrypy.expose
    def register(self):
        try:
            request = json.load(cherrypy.request.body)
            data = request["data"]

            return retdata(
                self.access.add_user(str(data["username"]), data["password"])
            )
        except:
            logging.exception("JSON api error.")
            return retdata(None, {"error": "Unexpected error."})

    @cherrypy.expose
    def addkey(self):
        try:
            request = json.load(cherrypy.request.body)
            data = request["data"]

            user = self.access.verify_user(str(data["username"]),
                                           data["password"])
            if not user:
                return retdata(-1)

            return retdata(self.access.add_key(user, data["key"]))
        except:
            logging.exception("JSON api error.")
            return retdata(None, {"error": "Unexpected error."})

    @cherrypy.expose
    def removekey(self):
        try:
            request = json.load(cherrypy.request.body)
            data = request["data"]

            user = self.access.verify_user(str(data["username"]),
                                           data["password"])
            if not user:
                return retdata(-1)

            return retdata(self.access.remove_key(user, int(data["key"])))
        except:
            logging.exception("JSON api error.")
            return retdata(None, {"error": "Unexpected error."})

    @cherrypy.expose
    def listkeys(self):
        try:
            request = json.load(cherrypy.request.body)
            data = request["data"]

            user = self.access.verify_user(str(data["username"]),
                                           data["password"])
            if not user:
                return retdata(-1)

            return retdata(self.access.list_keys(user))
        except:
            logging.exception("JSON api error.")
            return retdata(None, {"error": "Unexpected error."})

    @cherrypy.expose
    def changepassword(self):
        try:
            request = json.load(cherrypy.request.body)
            data = request["data"]

            user = self.access.verify_user(str(data["username"]),
                                           data["password"])
            if not user:
                return retdata(-1)

            return retdata(self.access.change_password(user, data["newpassword"]))
        except:
            logging.exception("JSON api error.")
            return retdata(None, {"error": "Unexpected error."})


def retdata(data, extra=None):
    """
        Return data in the correct format.
    """
    cherrypy.response.headers['Content-Type'] = 'application/json'
    out = { "protocol":  PROTOCOL_VER, "data": data }

    # Extra data
    if extra is not None:
        out.update(extra)

    return json.dumps(out)
