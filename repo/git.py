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
        commit = self[sha]
        tree = self[commit.tree]

        for package in tree.entries():
            subtree = self[package[2]]

            if isinstance(subtree, dulwich.objects.Tree):
                for entry in subtree.entries():
                    if entry[1] == "Cakefile":
                        packages.append(package[1])
                        break

        return packages

    def get_branch_readme(self, branch):
        """
            Get the contents of a branch README if it exists.
        """
        try:
            sha = self.get_refs()["refs/heads/"+branch]
        except KeyError:
            return None

        commit = self[sha]
        tree = self[commit.tree]

        for entry in tree.entries():
            if entry[1] == "README":
                blob = self[entry[2]]
                return blob.as_raw_string()

        return None

    def get_package_tree(self, branch, package):
        """
            Get the tree of files under a certain package in a branch.
        """
        try:
            sha = self.get_refs()["refs/heads/"+branch]
        except KeyError:
            return None

        commit = self[sha]
        tree = self[commit.tree]

        for entry in tree.entries():
            if entry[1] == package:
                subtree = self[entry[2]]

                if isinstance(subtree, dulwich.objects.Tree):
                    return subtree
                else:
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
                blob = self[entry[2]].as_raw_string()
                cakefile = yaml.load(blob, Loader=Loader)
                del blob
                return cakefile

    def get_package_readme(self, branch=None, package=None, tree=None):
        """
            Get the contents of a package's README if it exists.
        """
        if branch is not None and package is not None:
            tree = self.get_package_tree(branch, package)
        if tree is None:
            return None

        for entry in tree.entries():
            if entry[1] == "README":
                blob = self[entry[2]]
                return blob.as_raw_string()
        return None

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
                return self[entry[2]].as_raw_string()
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

    def get_latest_versions(self, packages):
        """
            Get information about all packages from the list
            that were updated from their specified versions.
        """
        # TODO: We really need to implement some sort of caching here,
        # parsing all these cakefiles is ridiculous.
        updated = []
        for branch, package, version in packages:
            cakefile = self.get_package_cakefile(branch, package)

            # Check existence
            if cakefile is None:
                continue

            # Check version
            ver = str(cakefile["version"])+"-"+str(cakefile["release"])
            if ver != str(version):
                # List of dependencies
                deps = [] if "dependencies" not in cakefile else \
                       cakefile["dependencies"]

                # List of conflicting packages
                conflicts = [] if "conflicts" not in cakefile else \
                            cakefile["conflicts"]

                updated.append({
                    "package": package,
                    "branch": branch,
                    "version": ver,
                    "dependencies": deps,
                    "conflicts": conflicts})
        return updated

    def get_package_log(self, branch, package=None):
        """
            Get log entries for a branch or a package in
            a branch.
        """
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

            # Add log entry
            if package is None:
                log.append([data, message])
            else:
                tree = self[commit.tree]
                parent_trees = [self[self[par].tree]
                    for par in commit._get_parents()]

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
         str(pkg[match.group(1)]) if match.group(1) in pkg
        else "(null)", string)

    def parse_source(self, source, pkg=None):
        """
            Parse source entry.
        """
        external = ("http://", "ftp://")

        if isinstance(source, list):
            if pkg is not None:
                source[0] = self.insert_fields(pkg, source[0])
            external = any(source[0].startswith(src) for src in external)
            return [source[0], external, source[0]]
        elif isinstance(source, dict):
            if "git" in source:
                name = source["git"]
                if "branch" in source:
                    name += " branch "+source["branch"]
                return [name, True, ""]
        else:
            if pkg is not None:
                source = self.insert_fields(pkg, source)
            external = any(source.startswith(src) for src in external)
            return [source, external, source]

    def resolve(self, name):
        """
            Resolve a package identifier to a (branch, package) pair.
        """
        name = name.split("/")
        if len(name) == 1:
            return "master", name[0]
        elif len(name) == 2:
            if name[0] == "master":
                return "master", name[1]
            else:
                return name[0]+"/default", name[1]
        else:
            return "/".join(name[:-1]), name[-1]
