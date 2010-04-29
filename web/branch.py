import cherrypy

class Branch(object):
    def __init__(self, repo, lookup):
        self.repo, self.lookup = repo, lookup

    @cherrypy.expose
    def index(self):
        raise cherrypy.HTTPError(404)

    @cherrypy.expose
    def default(self, branch=None, action=None):
        """
            List all packages in a branch.
        """

        if action is None:
            packages = self.repo.packages_in_branch(branch)

            if packages is None:
                raise cherrypy.HTTPError(404)

            return self.lookup.get_template("branch.html").render(
                branch=branch, packages=packages)
        elif action == "log":
            log = self.repo.get_package_log(branch, None)

            if log is None:
                raise cherrypy.HTTPError(404)

            return self.lookup.get_template("branch_log.html").render(
                branch=branch, log=log[:20])

        else:
                raise cherrypy.HTTPError(404)
