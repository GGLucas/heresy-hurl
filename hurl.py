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
                branches=self.repo.get_branches())

    @cherrypy.expose
    def default(self, branch, package=None):
        if package is None:
            return self.lookup.get_template("branch.html").render(
                branch=branch,
                packages=self.repo.packages_in_branch(branch))
        else:
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
                                     "tools.staticdir.root": directory,
                                    },
                          "/static": {
                                      "tools.staticdir.on": True,
                                      "tools.staticdir.dir": "static"
                                     }
                         })
