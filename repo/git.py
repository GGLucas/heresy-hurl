import datetime
import dulwich
import yaml
import re

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

class HurlGitRepo(dulwich.repo.Repo):
    def get_branches(self):
        """
            Get all branches in the entire repo.
        """
        branches = []

        for ref in self.get_refs():
            if ref.startswith("refs/heads/"):
                branches.append(ref[11:])

        # Move "master" and "staging" to the top
        branches.sort(key=lambda br: not (br == "master" or 
                                   br.startswith("staging")))

        return branches

    def count_branches(self):
        """
            Count the amount of branches in the repo.
        """
        count = 0

        for ref in self.get_refs():
            if ref.startswith("refs/heads/"):
                count += 1

        return count

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
        try:
            sha = self.get_refs()["refs/heads/"+branch]
        except KeyError:
            return None

        packages = []
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
        try:
            sha = self.get_refs()["refs/heads/"+branch]
        except KeyError:
            return None

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
        return None

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

    def get_package_log(self, branch, package=None):
        try:
            sha = self.get_refs()["refs/heads/"+branch]
        except KeyError:
            return None

        log = []

        for commit in self.revision_history(sha):
            # Get data
            lines = commit.as_raw_string().split("\n")
            data = {}

            # Parse data
            line = lines.pop(0)
            while line:
                print(line)
                key, value = line.split(" ", 1)
                data[key] = value
                line = lines.pop(0)

            message = "\n".join(lines)

            # Fall back to committer
            if "committer" in data and "author" not in data:
                data["author"] = data["committer"]

            # Get commit
            if "commit" not in data:
                data["commit"] = commit.id

            # Parse date
            if "author" in data:
                data["author"] = data["author"].split()
                data["date"] = data["author"][-2:]
                data["author"] = " ".join(data["author"][:-2])
                data["date"][0] = datetime.datetime.fromtimestamp(int(data["date"][0]))

            print(data)

            # Add log entry
            if package is None:
                log.append([data, message])
            else:
                tree = self.tree(commit.tree)
                parent_trees = [self.tree(self.commit(par).tree)
                    for par in commit.get_parents()]

                changed = False

                for elem in tree.entries():
                    if elem[1] == package:
                        if not parent_trees:
                            changed = True
                            break

                        found = False
                        for parent in parent_trees:
                            for parelem in parent.entries():
                                if parelem[1] == package:
                                    found = True
                                    if parelem[2] != elem[2]:
                                        changed = True
                                    break

                        if not found:
                            changed = True

                        break

                if changed:
                    log.append([data, message])

        return log

    def parse_dependency(self, dep):
        """
            Parse a dependency string into a package, version and operator
            part.
        """
        for opr in (">=", "<=", ">", "<", "="):
            if opr in dep:
                dependency = [s.strip() for s in dep.partition(opr)]
                break
        else:
            dependency = [dep]

        return dependency

    def insert_fields(self, pkg, string):
        """
            Replace variable fields in a string.
        """
        return re.sub(r"\$\{([^}]*)\}", lambda match: 
         pkg[match.group(1)] if match.group(1) in pkg
        else "(null)", string)
