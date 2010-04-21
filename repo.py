import dulwich
import yaml

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

class HurlRepo(dulwich.repo.Repo):
    def get_branches(self):
        branches = []

        for ref in self.get_refs():
            if ref.startswith("refs/heads/"):
                branches.append(ref[11:])

        return branches

    def branches_with_package(self, package):
        branches = []

        for ref in self.get_refs():
            if ref.startswith("refs/heads/"):
                branchname = ref[11:]
                tree = self.get_package_tree(branchname, package)

                for entry in tree.entries():
                    if entry[1] == "Cakefile":
                        branches.append(branchname)
                        break

        return branches

    def packages_in_branch(self, branch):
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
        if branch is not None and package is not None:
            tree = self.get_package_tree(branch, package)
        if tree is None:
            return None

        for entry in tree.entries():
            if entry[1] == filename:
                return self.get_blob(entry[2]).as_raw_string()

    def get_package_files(self, branch=None, package=None, tree=None):
        if branch is not None and package is not None:
            tree = self.get_package_tree(branch, package)
        if tree is None:
            return None

        files = []
        for entry in tree.entries():
                files.append(entry[1])
        return files
