import cherrypy

class Branch(object):
    def __init__(self, repo, lookup):
        self.repo, self.lookup = repo, lookup

    @cherrypy.expose
    def default(self, *branch):
        """
            List all packages in a branch.
        """
        branch = "/".join(branch)
        packages = self.repo.packages_in_branch(branch)

        if packages is None:
            raise cherrypy.HTTPError(404)

        return self.lookup.get_template("branch.html").render(
            branch=branch, packages=packages)


class BranchLog(object):
    def __init__(self, repo, lookup):
        self.repo, self.lookup = repo, lookup

    @cherrypy.expose
    def default(self, *branch):
        """
            Show a branch changelog.
        """
        branch = "/".join(branch)
        log = self.repo.get_package_log(branch, None)

        if log is None:
            raise cherrypy.HTTPError(404)

        return self.lookup.get_template("branch_log.html").render(
            branch=branch, log=log[:20])
