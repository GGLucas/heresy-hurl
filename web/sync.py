import json
import cherrypy

class Sync(object):
    def __init__(self, repo, lookup):
        self.repo, self.lookup = repo, lookup

    @cherrypy.expose(".json")
    def json(self):
        try:
            packages = json.load(cherrypy.request.body)
            return json.dumps(self.repo.get_latest_versions(packages))
        except:
            return "['An error has occurred.']"