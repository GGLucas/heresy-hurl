import json
import cherrypy

PROTOCOL_VER = 1.0

class API(object):
    def __init__(self, repo, lookup, index, access):
        self.repo, self.lookup, self.index, access = repo, lookup, index, access

    @cherrypy.expose
    def sync(self):
        try:
            request = json.load(cherrypy.request.body)
            data = self.repo.get_latest_versions(request["data"])

            cherrypy.response.headers['Content-Type'] = 'application/json'
            return json.dumps({ "protocol":  PROTOCOL_VER,
                                "data": data })
        except:
            return "['An error has occurred.']"

    @cherrypy.expose
    def search(self):
        try:
            request = json.load(cherrypy.request.body)

            # Search
            results, num, exact = self.index.search(request["data"])

            cherrypy.response.headers['Content-Type'] = 'application/json'
            return json.dumps({ "protocol":  PROTOCOL_VER, "data": {
                "count": num,
                "is_exact": exact,
                "results": list(results),
            }})
        except:
            return "['An error has occurred.']"

    @cherrypy.expose
    def info(self):
        try:
            request = json.load(cherrypy.request.body)
            data = request["data"]

            cherrypy.response.headers['Content-Type'] = 'application/json'
            return json.dumps({ "protocol":  PROTOCOL_VER, "data":
                self.repo.get_package_cakefile(data["branch"], data["package"])
            })
        except:
            return "['An error has occurred.']"
