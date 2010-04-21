import dulwich
import yaml

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

class HurlRepo(dulwich.repo.Repo):
    def get_branches(self):
        """
            Get all branches in the entire repo.
        """
        branches = []

        for ref in self.get_refs():
            if ref.startswith("refs/heads/"):
                branches.append(ref[11:])

        return branches

    def get_packages(self):
        """
            Get all packages in the entire repo and the branches
            that they are in.
        """
        packages = {}

        for branch in self.get_branches():
            for package in self.packages_in_branch(branch):
                # First time we see this package, add it to the dict
                if package not in packages:
                    packages[package] = []

                # Add this branch as holding this package
                packages[package].append(branch)

        return packages


    def branches_with_package(self, package):
        """
            Get all branches that have a certain package in it.
        """
        branches = []

        for branch in self.get_branches():
            tree = self.get_package_tree(branch, package)

            if tree is not None:
                for entry in tree.entries():
                    if entry[1] == "Cakefile":
                        branches.append(branch)
                        break

        return branches

    def packages_in_branch(self, branch):
        """
            Get all packages in a certain branch.
        """
        packages = []
        sha = self.refs["refs/heads/"+branch]
        commit = self.commit(sha)
        tree = self.tree(commit.tree)

        for package in tree.entries():
            try:
                subtree = self.tree(package[2])
            except dulwich.errors.NotTreeError:
                continue

            for entry in subtree.entries():
                if entry[1] == "Cakefile":
                    packages.append(package[1])
                    break

        return packages

    def get_package_tree(self, branch, package):
        """
            Get the tree of files under a certain package in a branch.
        """
        sha = self.refs["refs/heads/"+branch]
        commit = self.commit(sha)
        tree = self.tree(commit.tree)

        for entry in tree.entries():
            if entry[1] == package:
                try:
                    subtree = self.tree(entry[2])
                    return subtree
                except dulwich.errors.NotTreeError:
                    return None

    def get_package_cakefile(self, branch=None, package=None, tree=None):
        """
            Get the parsed cakefile of a package in a branch.
        """
        if branch is not None and package is not None:
            tree = self.get_package_tree(branch, package)
        if tree is None:
            return None

        for entry in tree.entries():
            if entry[1] == "Cakefile":
                blob = self.get_blob(entry[2]).as_raw_string()
                cakefile = yaml.load(blob, Loader=Loader)
                del blob
                return cakefile

    def get_package_file(self, filename, branch=None, package=None, tree=None):
        """
            Get the contents of a file in the package directory.
        """
        if branch is not None and package is not None:
            tree = self.get_package_tree(branch, package)
        if tree is None:
            return None

        for entry in tree.entries():
            if entry[1] == filename:
                return self.get_blob(entry[2]).as_raw_string()

    def get_package_files(self, branch=None, package=None, tree=None):
        """
            Get a list of files in the package directory.
        """
        if branch is not None and package is not None:
            tree = self.get_package_tree(branch, package)
        if tree is None:
            return None

        files = []
        for entry in tree.entries():
                files.append(entry[1])
        return files
