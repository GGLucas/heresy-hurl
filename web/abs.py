import os
import yaml
import cherrypy
import tarfile
import time
from arch2cake import arch2cake, varrep

try:
    from yaml import CDumper as Dumper
except ImportError:
    from yaml import Dumper

try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

def getcakefile(path):
    # Converted cakefile
    fd = open(path, "r")
    data = arch2cake(fd)
    build = data["build"].split("\n")
    del data["build"]
    fd.close()

    return yaml.dump(data, Dumper=Dumper, default_flow_style=False) + \
           "build: |\n" + "  " + varrep("\n  ".join(build[:-1])) + "\n"

class Abs(object):
    def __init__(self, repo, lookup):
        self.repo, self.lookup = repo, lookup

    @cherrypy.expose
    def index(self):
        absroot = cherrypy.request.app.config['arch']['absroot']

        return self.lookup.get_template("abs_repos.html").render(
            repositories=[fld for fld in os.listdir(absroot)
                       if os.path.isdir(os.path.join(absroot, fld))])

    @cherrypy.expose
    def default(self, repo=None, package=None, filename=None):
        absroot = cherrypy.request.app.config['arch']['absroot']

        if package is None:
            reporoot = os.path.join(absroot, repo)

            # No updir allowed
            if ".." in repo:
                raise cherrypy.NotFound()

            # Get hurl-available packages
            in_hurl = {}
            for pkg in self.repo.get_packages():
                in_hurl[pkg] = True

            if os.path.exists(reporoot):
                return self.lookup.get_template("abs_packages.html").render(
                    repo=repo, packages=os.listdir(reporoot),
                    in_hurl=in_hurl)
            else:
                raise CherryPy.NotFound()

        if package.endswith(".tar.gz"):
            filename = package
            package = package[:-7]

        if filename is None:
            # No updir allowed
            if ".." in repo or ".." in package:
                raise cherrypy.NotFound()

            pkgroot = os.path.join(absroot, repo, package)

            return self.lookup.get_template("abs_package.html").render(
                repo=repo, package=package, files=os.listdir(pkgroot),
                available=self.repo.branches_with_package(package))

        pkgroot = os.path.join(absroot, repo, package)
        filepath = os.path.join(pkgroot, filename)

        # No updir allowed
        if ".." in filename or ".." in package or ".." in repo:
            raise cherrypy.NotFound()

        # Check for file type
        if filename in ("Cakefile", "PKGBUILD") or filename.endswith(".patch") \
           or filename.endswith(".install"):
            cherrypy.response.headers['Content-Type'] = 'text/plain'
        else:
            cherrypy.response.headers['Content-Type'] = 'application/octet-stream'

        # Check if file exists
        if filename == "Cakefile":
            # Show converted cakefile
            def stream():
                yield getcakefile(os.path.join(pkgroot, "PKGBUILD"))
            return stream()
        elif filename == package+".tar.gz":
            # Create tar archive
            content = StringIO.StringIO()
            tarf = tarfile.open(fileobj=content, mode="w:gz")

            # Set MIME
            cherrypy.response.headers['Content-Type'] \
                = 'application/x-tar-gz'

            # Add regular files
            os.chdir(os.path.join(absroot, repo))
            for fname in os.listdir(pkgroot):
                if fname != "PKGBUILD":
                    tarf.add(os.path.join(package, fname))

            # Add cakefile
            data = getcakefile(os.path.join(pkgroot, "PKGBUILD"))

            string = StringIO.StringIO()
            string.write(data)
            string.seek(0)

            info = tarfile.TarInfo(name=os.path.join(package, "Cakefile"))
            info.size = len(data)
            info.mtime = time.time()

            tarf.addfile(tarinfo=info, fileobj=string)

            # Return data
            tarf.close()
            return content.getvalue()

        elif os.path.exists(filepath):
            # Stream single file
            def stream():
                fd = open(filepath, "r")
                for line in fd:
                    yield line
                fd.close()
            return stream()
        else:
            raise cherrypy.NotFound()
    default._cp_config = { "response.stream": True }
