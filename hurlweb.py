# Global imports
import sys
import os
import cherrypy
import datetime

from mako.template import Template
from mako.lookup import TemplateLookup

# Get current directory
directory = os.path.dirname(os.path.abspath(__file__))
confpath = os.path.join(directory, "config")
sys.path.append(directory)

# Imports relative to current dir
from repo import HurlRepo
from web.branch import Branch
from web.package import Package
from web.root import Root
from web.source import Source

# Check if we have xapian
try:
    import searchrepo
    HAVE_XAPIAN = True
except ImportError:
    HAVE_XAPIAN = False

if HAVE_XAPIAN:
    from web.search import Search

# Check if we have auto-conversion
try:
    import arch2cake
    HAVE_ARCH2CAKE = True
except ImportError:
    HAVE_ARCH2CAKE = False

if HAVE_ARCH2CAKE:
    from web.abs import Abs

def error_page_404(status, message, traceback, version):
    return "<h1>Error 404</h1><p>File not found</p>"

# Update config
cherrypy.config.update({"global": { "tools.staticdir.root": directory }})
cherrypy.config.update({ "error_page.404": error_page_404 })
cherrypy.config.update(confpath)

# Initialise repo and templates
repo = HurlRepo(cherrypy.config["hurl"]["repo"])
lookup = TemplateLookup(directories=[os.path.join(directory, "templates")])

# Mount trees
cherrypy.tree.mount(Root(repo, lookup), "/", confpath)
cherrypy.tree.mount(Package(repo, lookup), "/package", confpath)
cherrypy.tree.mount(Branch(repo, lookup), "/branch", confpath)
cherrypy.tree.mount(Source(repo, lookup), "/source", confpath)

# Autoconverted packages
if HAVE_ARCH2CAKE:
    cherrypy.tree.mount(Abs(repo, lookup), "/abs", confpath)

# Search
if HAVE_XAPIAN:
    index = searchrepo.HurlIndex(cherrypy.config["hurl"]["index"])
    index.LOADED = datetime.datetime.now()
    cherrypy.tree.mount(Search(repo, lookup, index), "/search", confpath)

# WSGI Application
application = cherrypy.tree

if __name__ == '__main__':
    # Run standalone server
    cherrypy.engine.start()
    cherrypy.engine.block()
