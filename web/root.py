import cherrypy

class Root(object):
    def __init__(self, repo, lookup):
        self.repo, self.lookup = repo, lookup

    @cherrypy.expose
    def index(self):
        return self.lookup.get_template("index.html").render()

    @cherrypy.expose
    def packages(self):
        in_master = {}
        for pkg in self.repo.packages_in_branch("master"):
            in_master[pkg] = True

        return self.lookup.get_template("packages.html").render(
            packages=self.repo.get_packages(), in_master=in_master)

    @cherrypy.expose
    def branches(self):
        return self.lookup.get_template("branches.html").render(
            branches=self.repo.get_branches())
