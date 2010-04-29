import sys
import os
import cherrypy
import tarfile
import time

from mako.template import Template
from mako.lookup import TemplateLookup

from repo import HurlRepo

try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

directory = os.path.dirname(os.path.abspath(__file__))

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

class Source(object):
    def __init__(self, repo, lookup):
        self.repo, self.lookup = repo, lookup

    @cherrypy.expose
    def default(self, filename):
        # Extract archive type
        if filename.endswith(".tar.gz"):
            cherrypy.response.headers['Content-Type'] \
                = 'application/x-tar-gz'

            mode = "w:gz"
        elif filename.endswith(".tar.bz2"):
            cherrypy.response.headers['Content-Type'] \
                = 'application/x-tar-bz2'

            mode = "w:bz2"
        else:
            return None #TODO: 404

        # Extract package and branch
        items = filename.split("-")
        branch = items.pop().split(".tar.")[0]
        package = "-".join(items)

        # Create tar archive
        content = StringIO.StringIO()
        tarf = tarfile.open(fileobj=content, mode=mode)
        tree = self.repo.get_package_tree(branch, package)

        for i, filename, ident in tree.entries():
            blob = self.repo.get_blob(ident).as_raw_string()
            length = len(blob)

            string = StringIO.StringIO()
            string.write(blob)
            string.seek(0)

            info = tarfile.TarInfo(name=os.path.join(package+"-"+branch, filename))
            info.size = length
            info.mtime = time.time()

            tarf.addfile(tarinfo=info, fileobj=string)

        tarf.close()
        return content.getvalue()

class Package(object):
    def __init__(self, repo, lookup):
        self.repo, self.lookup = repo, lookup

    @cherrypy.expose
    def default(self, package, branch=None, action=None, argument=None):
        if branch is None:
            # List all branches that have a package
            branches = self.repo.branches_with_package(package)

            return self.lookup.get_template("package_branches.html").render(
                package=package, branches=branches)
        else:
            if action == "file" and argument is not None:
                # List the raw cakefile blob
                if argument == "Cakefile" or argument.endswith(".patch"):
                    cherrypy.response.headers['Content-Type'] = 'text/plain'
                else:
                    cherrypy.response.headers['Content-Type'] = 'application/octet-stream'

                return str(self.repo.get_package_file(argument, branch, package))
            else:
                # List the package that's in the branch
                return self.lookup.get_template("package.html").render(
                    branch=branch,
                    package=package,
                    pkg=self.repo.get_package_cakefile(branch, package),
                    files=self.repo.get_package_files(branch, package))

class Branch(object):
    def __init__(self, repo, lookup):
        self.repo, self.lookup = repo, lookup

    @cherrypy.expose
    def default(self, branch=None):
        # List all packages in a branch
        return self.lookup.get_template("branch.html").render(
            branch=branch,
            packages=self.repo.packages_in_branch(branch))

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Please specify a hurl repo to serve and a config.")
        sys.exit(1)

    # Configuration
    repo = HurlRepo(sys.argv[1])
    lookup = TemplateLookup(directories=[os.path.join(directory, "templates")])

    # Update config
    cherrypy.config.update({"global": { "tools.staticdir.root": directory }})
    cherrypy.config.update(sys.argv[2])

    # Mount trees
    cherrypy.tree.mount(Root(repo, lookup), "/", sys.argv[2])
    cherrypy.tree.mount(Package(repo, lookup), "/package", {})
    cherrypy.tree.mount(Branch(repo, lookup), "/branch", {})
    cherrypy.tree.mount(Source(repo, lookup), "/source", {})

    cherrypy.engine.start()
    cherrypy.engine.block()
