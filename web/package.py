import cherrypy

class Package(object):
    def __init__(self, repo, lookup):
        self.repo, self.lookup = repo, lookup

    @cherrypy.expose
    def index(self):
        raise cherrypy.HTTPError(404)

    @cherrypy.expose
    def default(self, package=None, branch=None, action=None, argument=None):
        if package is None:
            raise cherrypy.HTTPError(404)

        if branch is None:
            # List all branches that have a package
            branches = self.repo.branches_with_package(package)

            if not branches:
                raise cherrypy.HTTPError(404)

            return self.lookup.get_template("package_branches.html").render(
                package=package, branches=branches)
        else:
            if action == "file" and argument is not None:
                # List the raw cakefile blob
                if argument == "Cakefile" or argument.endswith(".patch"):
                    cherrypy.response.headers['Content-Type'] = 'text/plain'
                else:
                    cherrypy.response.headers['Content-Type'] = 'application/octet-stream'

                data = self.repo.get_package_file(argument, branch, package)
                if data:
                    return data
                else:
                    raise cherrypy.HTTPError(404)

            elif action == "log" and argument is None:
                log = self.repo.get_package_log(branch, package)
                pkg = self.repo.get_package_cakefile(branch, package)

                if pkg is None or log is None:
                    raise cherrypy.HTTPError(404)

                return self.lookup.get_template("package_log.html").render(
                    branch=branch,
                    package=package,
                    pkg=pkg, log=log[:20])

            elif action is None:
                pkg = self.repo.get_package_cakefile(branch, package)
                files = self.repo.get_package_files(branch, package)

                if pkg is None or files is None:
                    raise cherrypy.HTTPError(404)

                # List the package that's in the branch
                return self.lookup.get_template("package.html").render(
                    branch=branch,
                    package=package,
                    pkg=pkg, files=files)
            else:
                raise cherrypy.HTTPError(404)
