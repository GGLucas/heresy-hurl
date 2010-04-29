import cherrypy

class Root(object):
    def __init__(self, repo, lookup):
        self.repo, self.lookup = repo, lookup

    @cherrypy.expose
    def index(self):
        return self.lookup.get_template("index.html").render()

    @cherrypy.expose
    def packages(self):
        return self.lookup.get_template("packages.html").render(
            packages=self.repo.get_packages())

    @cherrypy.expose
    def branches(self):
        return self.lookup.get_template("branches.html").render(
            branches=self.repo.get_branches())
