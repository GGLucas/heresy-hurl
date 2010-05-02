import datetime
import cherrypy
import json

class Search(object):
    def __init__(self, repo, lookup, index):
        self.repo, self.lookup, self.index = repo, lookup, index

    @cherrypy.expose
    def default(self, q=None):
        if q is None:
            raise cherrypy.NotFound()

        # Search
        results, num, exact = self.index.search(q)

        return self.lookup.get_template("search.html").render(
            results=results, num=num, exact=exact, query=q)

    @cherrypy.expose(".json")
    def json(self, q=None):
        # Search
        results, num, exact = self.index.search(q)

        return json.dumps({
            "count": num,
            "is_exact": exact,
            "results": list(results),
        })
