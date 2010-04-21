import sys
import os
import cherrypy

from mako.template import Template
from mako.lookup import TemplateLookup

from repo import HurlRepo

directory = os.path.dirname(os.path.abspath(__file__))

class Hurl(object):
    def __init__(self, location):
        self.repo = HurlRepo(location)
        self.lookup = TemplateLookup(directories=[os.path.join(directory, "templates")])

    @cherrypy.expose
    def index(self):
        return self.lookup.get_template("index.html").render(
                packages=self.repo.get_packages())

    @cherrypy.expose
    def default(self, package, branch=None):
        if package == "branch":
            # List all packages in a branch
            return self.lookup.get_template("branch.html").render(
                branch=branch,
                packages=self.repo.packages_in_branch(branch))

        if branch is None:
            # List all branches that have a package
            return self.lookup.get_template("package_branches.html").render(
                package=package,
                branches=self.repo.branches_with_package(package))
        else:
            # List the package that's in the branch
            return self.lookup.get_template("package.html").render(
                branch=branch,
                package=package,
                pkg=self.repo.get_package_cakefile(branch, package))

if __name__ == '__main__':
    application = Hurl("testrepo")
    print(directory)
    cherrypy.quickstart(application, '/',
                        {
                          "global": {
                                     "server.socket_host": '0.0.0.0',
                                     "server.socket_port": 80,
                                     "tools.staticdir.root": directory,
                                    },
                          "/static": {
                                      "tools.staticdir.on": True,
                                      "tools.staticdir.dir": "static"
                                     }
                         })
