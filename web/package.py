import cherrypy

class Package(object):
    def __init__(self, repo, lookup):
        self.repo, self.lookup = repo, lookup

    @cherrypy.expose
    def default(self, *ident):
        if len(ident) == 1:
            # We only have a package name,
            # list all branches that have it
            package = ident[0]
            branches = self.repo.branches_with_package(package)

            if not branches:
                raise cherrypy.HTTPError(404)

            return self.lookup.get_template("package_branches.html").render(
                package=package, branches=branches)
        else:
            # A fully qualified package was specified
            package = ident[-1]
            branch = "/".join(ident[:-1])

            pkg = self.repo.get_package_cakefile(branch, package)
            files = self.repo.get_package_files(branch, package)

            if pkg is None or files is None:
                raise cherrypy.NotFound()

            # Parse dependencies and sources
            if "dependencies" in pkg:
                pkg["dependencies"] = map(self.repo.parse_dependency,
                                          pkg["dependencies"])

            if "build-dependencies" in pkg:
                pkg["build-dependencies"] = map(self.repo.parse_dependency,
                                          pkg["build-dependencies"])

            if "sources" in pkg:
                pkg["sources"] = map(self.repo.parse_source,
                                        pkg["sources"])

            # List the package that's in the branch
            return self.lookup.get_template("package.html").render(
                branch=branch,
                package=package,
                pkg=pkg, files=files)

class PackageLog(object):
    def __init__(self, repo, lookup):
        self.repo, self.lookup = repo, lookup

    @cherrypy.expose
    def default(self, *ident):
        package = ident[-1]
        branch = "/".join(ident[:-1])

        log = self.repo.get_package_log(branch, package)
        pkg = self.repo.get_package_cakefile(branch, package)

        if pkg is None or log is None:
            raise cherrypy.NotFound()

        return self.lookup.get_template("package_log.html").render(
            branch=branch,
            package=package,
            pkg=pkg, log=log[:20])

class PackageFile(object):
    def __init__(self, repo, lookup):
        self.repo, self.lookup = repo, lookup

    @cherrypy.expose
    def default(self, *ident):
        if len(ident) <= 2:
            raise cherrypy.NotFound()

        filename = ident[-1]
        package = ident[-2]
        branch = "/".join(ident[:-2])

        if filename == "Cakefile" or filename.endswith(".patch"):
            cherrypy.response.headers['Content-Type'] = 'text/plain'
        else:
            cherrypy.response.headers['Content-Type'] = 'application/octet-stream'

        data = self.repo.get_package_file(filename, branch, package)

        if data:
            return data
        else:
            raise cherrypy.NotFound()
