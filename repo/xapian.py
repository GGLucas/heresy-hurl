import os
import sys
import datetime
import xappy
import time

STORE_CONTENT = ([xappy.FieldActions.STORE_CONTENT], {})
INDEX_FREETEXT = ([xappy.FieldActions.INDEX_FREETEXT], {})
INDEX_NONDEFAULT = ([xappy.FieldActions.INDEX_FREETEXT], {"search_by_default": False})
INDEX_EXACT = ([xappy.FieldActions.INDEX_EXACT], {})

FIELDS = {
    "name": [STORE_CONTENT, INDEX_FREETEXT],
    "version": [STORE_CONTENT, INDEX_EXACT],
    "release": [STORE_CONTENT, INDEX_EXACT],
    "description": [STORE_CONTENT, INDEX_FREETEXT],
    "tags": [STORE_CONTENT, INDEX_FREETEXT],
    "dependencies": [INDEX_NONDEFAULT],
    "build-dependencies": [INDEX_NONDEFAULT],
}

class HurlXapianIndex(object):
    def __init__(self, dbpath, refresh_after=30):
        """
            Initialise a new hurl index object.
            @param dbpath: The database path used for the index.
            @param refresh_after: The amount of minutes after an index
                is considered stale and should be refreshed. Defaults
                to 30.
        """
        self.dbpath = dbpath
        self.refresh_after = refresh_after
        self.db, self.conn = None, None

    def _connect_read(self):
        """
            Make sure a read connection has been made.
        """
        if self.conn is None:
            self.conn = xappy.SearchConnection(self.dbpath)
            self.updated = datetime.datetime.now()
        # Check for stale index
        elif datetime.datetime.now()-self.updated > \
            datetime.timedelta(minutes=self.refresh_after):
            self.reload()
            self.updated = datetime.datetime.now()

    def _connect_write(self):
        """
            Make sure a write connection has been made.
        """
        if self.db is None:
            self.db = xappy.IndexerConnection(self.dbpath)

    def flush(self):
        """
            Flush the index to the source.
        """
        if self.db is None:
            return
        self.db.flush()

    def reload(self):
        """
            Reload the index from the source.
        """
        if self.conn is None:
            return
        self.conn.reopen()

    def search(self, terms):
        """
            Search the index for a set of terms.

            Returns a (results, num, exact) tuple, num being
            the amount of results found and exact being whether
            the amount of results was exact or approximated.
            Results is a list of dictionaries containing at least
            the keys "package", "branch", "tags" and "description".
        """
        # Make sure we can read
        self._connect_read()

        # Run query
        q = self.conn.query_parse(terms, default_op=self.conn.OP_AND)
        results = self.conn.search(q, 0, 10, sortby="-priority", collapse="package")

        # Sanitise results
        def iter_docs():
            for doc in results:
                data = doc.data
                print(repr(data))

                # Use only the first data entry
                for item in data:
                    data[item] = data[item][0]

                # Split up tags
                if "tags" in data:
                    data["tags"] = data["tags"].split()

                yield data

        return iter_docs(), results.matches_estimated, results.estimate_is_exact

    def count(self):
        """
            Count the amount of packages in the index.
        """
        # Make sure we can read
        self._connect_read()

        return self.conn.get_doccount()

    def create(self):
        """
            Create the index if it doesn't exist.
            Must be called before any write operations
            to have the desired effect.
        """
        # Don't create indexes that exist
        if self.db is not None or os.path.exists(self.dbpath):
            return

        # Connect
        self._connect_write()

        # Name fields
        for field in "branch", "user", "package":
            self.db.add_field_action(field, xappy.FieldActions.STORE_CONTENT)
            self.db.add_field_action(field, xappy.FieldActions.INDEX_FREETEXT,
                search_by_default=False)

        # Collapsable on package name
        self.db.add_field_action("package", xappy.FieldActions.COLLAPSE)

        # Priority field
        self.db.add_field_action("priority", xappy.FieldActions.STORE_CONTENT)
        self.db.add_field_action("priority", xappy.FieldActions.INDEX_EXACT)
        self.db.add_field_action("priority", xappy.FieldActions.SORTABLE,
                                 type='float')

        # Other fields
        for field, actions in FIELDS.items():
            for act in actions:
                self.db.add_field_action(field.replace("-", ""), *act[0], **act[1])

        self.db.flush()

    def index_repo(self, repo):
        """
            (Re)Index an entire repository.
        """
        for branch in repo.get_branches():
            self.index_branch(branch)

    def index_branch(self, repo, branch):
        """
            (Re)Index all the packages in one branch.
        """
        for package in repo.packages_in_branch(branch):
            self.index_package(repo, branch, package)

    def index_package(self, repo, branch, package):
        """
            (Re)Index a single package.
        """
        self._connect_write()

        # Get data
        cakefile = repo.get_package_cakefile(branch, package)

        if cakefile is None:
            return

        # Fill document
        doc = xappy.UnprocessedDocument()
        doc.fields.append(xappy.Field("package", package))
        doc.fields.append(xappy.Field("branch", branch))
        doc.fields.append(xappy.Field("user", branch.split("/")[0]))
        doc.fields.append(xappy.Field("priority", str(int(branch == "master"))))
        doc.id = branch+"/"+package

        # Add fields
        for field in FIELDS:
            if field in cakefile:
                data = cakefile[field]

                if hasattr(data, "__iter__"):
                    data = " ".join(data)

                doc.fields.append(xappy.Field(field.replace("-", ""), str(data)))

        # Add document to index
        self.db.replace(doc)

    def delete_package(self, branch, package):
        """
            Delete a single package from the index.
        """
        self._connect_write()
        self.db.delete(branch+"/"+package)

def listen(index, repo, queue_key=1313):
    """
        Listen on a message queue for new packages to index.
    """
    # Create the queue
    from sysv_ipc import MessageQueue, IPC_CREAT
    queue = MessageQueue(queue_key, IPC_CREAT)

    while True:
        line, typ = queue.receive()

        if line.strip():
            if typ == 3: # Deleted branch
                pks = repo.packages_in_branch(line) or []
                for pkg in pks:
                    print("D "+line+"/"+pkg)
                    index.delete_package(line, pkg)
                    index.flush()
            elif "/" in line:
                time.sleep(1)
                branch, package = map(str.strip, line.rsplit("/", 1))

                if typ == 1: # Changed
                    print("M "+branch+"/"+package)
                    index.index_package(repo, branch, package)
                    index.flush()
                elif typ == 2: # Deleted
                    print("D "+branch+"/"+package)
                    index.delete_package(branch, package)
                    index.flush()
            else:
                print("Error: `%s` is not a valid package.")

def main():
    from repo.git import HurlGitRepo

    if len(sys.argv) < 3:
        print("USAGE: %s REPO DATABASE [COMMAND]" % sys.argv[0])
        return

    repo = HurlGitRepo(sys.argv[1])
    index = HurlXapianIndex(sys.argv[2])
    index.create()

    if len(sys.argv) >= 4:
        if sys.argv[3] == "reindex":
            for branch in repo.get_branches():
                for pkg in repo.packages_in_branch(branch):
                    index.index_package(repo, branch, pkg)
        elif sys.argv[3] == "list":
            index._connect_read()
            for ident in index.conn.iterids():
                print(ident)
        elif sys.argv[3] == "nop":
            return
    else:
        listen(index, repo)

if __name__ == '__main__':
    main()
