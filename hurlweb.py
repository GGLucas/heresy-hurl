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
from repo.git import HurlGitRepo
from web.branch import Branch, BranchLog
from web.package import Package, PackageLog, PackageFile
from web.root import Root
from web.api import API
from web.source import Source

# Check if we have xapian
try:
    from repo.xapian import HurlXapianIndex
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
repo = HurlGitRepo(cherrypy.config["hurl"]["repo"])
lookup = TemplateLookup(directories=[os.path.join(directory, "templates")])
access = None
index = None

# Initialise index
if HAVE_XAPIAN and "index" in cherrypy.config["hurl"]:
    index = HurlXapianIndex(cherrypy.config["hurl"]["index"],
            cherrypy.config["hurl"].get("index.expire", 30))

# Mount trees
cherrypy.tree.mount(Root(repo, lookup, index), "/", confpath)

cherrypy.tree.mount(Package(repo, lookup), "/package", confpath)
cherrypy.tree.mount(PackageLog(repo, lookup), "/package-log", confpath)
cherrypy.tree.mount(PackageFile(repo, lookup), "/package-file", confpath)

cherrypy.tree.mount(Branch(repo, lookup), "/branch", confpath)
cherrypy.tree.mount(BranchLog(repo, lookup), "/branch-log", confpath)

cherrypy.tree.mount(Source(repo, lookup), "/source", confpath)
cherrypy.tree.mount(API(repo, lookup, index, access), "/api", confpath)

# Autoconverted packages
if HAVE_ARCH2CAKE:
    cherrypy.tree.mount(Abs(repo, lookup), "/abs", confpath)

# Search
if index:
    cherrypy.tree.mount(Search(repo, lookup, index), "/search", confpath)

# WSGI Application
application = cherrypy.tree

if __name__ == '__main__':
    # Run standalone server
    cherrypy.engine.start()
    cherrypy.engine.block()
