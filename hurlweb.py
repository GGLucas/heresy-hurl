import sys
import os
import cherrypy

from mako.template import Template
from mako.lookup import TemplateLookup

from repo import HurlRepo
from web.branch import Branch
from web.package import Package
from web.root import Root
from web.source import Source

def error_page_404(status, message, traceback, version):
    return "<h1>Error 404</h1><p>File not found</p>"

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Please specify a hurl repo to serve and a config.")
        sys.exit(1)

    # Configuration
    directory = os.path.dirname(os.path.abspath(__file__))
    repo = HurlRepo(sys.argv[1])
    lookup = TemplateLookup(directories=[os.path.join(directory, "templates")])

    # Update config
    cherrypy.config.update({"global": { "tools.staticdir.root": directory }})
    cherrypy.config.update({ "error_page.404": error_page_404 })
    cherrypy.config.update(sys.argv[2])

    # Mount trees
    cherrypy.tree.mount(Root(repo, lookup), "/", sys.argv[2])
    cherrypy.tree.mount(Package(repo, lookup), "/package", {})
    cherrypy.tree.mount(Branch(repo, lookup), "/branch", {})
    cherrypy.tree.mount(Source(repo, lookup), "/source", {})

    cherrypy.engine.start()
    cherrypy.engine.block()
