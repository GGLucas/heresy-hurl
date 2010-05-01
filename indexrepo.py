#!/usr/bin/python -u
"""
    Module for scanning and indexing a repository
    into a xapian database.
"""
import sys
import repo
import xappy

STORE_CONTENT = ([xappy.FieldActions.STORE_CONTENT], {})
INDEX_FREETEXT = ([xappy.FieldActions.INDEX_FREETEXT], {})
INDEX_NONDEFAULT = ([xappy.FieldActions.INDEX_FREETEXT], {"search_by_default": False})
INDEX_EXACT = ([xappy.FieldActions.INDEX_EXACT], {})

FIELDS = {
    "name": [STORE_CONTENT, INDEX_FREETEXT],
    "description": [STORE_CONTENT, INDEX_FREETEXT],
    "tags": [STORE_CONTENT, INDEX_FREETEXT],
    "dependencies": [INDEX_NONDEFAULT],
    "build-dependencies": [INDEX_NONDEFAULT],
}

def create_index(db):
    db.add_field_action("package", xappy.FieldActions.STORE_CONTENT)
    db.add_field_action("package", xappy.FieldActions.INDEX_EXACT)
    db.add_field_action("package", xappy.FieldActions.COLLAPSE)

    db.add_field_action("branch", xappy.FieldActions.STORE_CONTENT)
    db.add_field_action("branch", xappy.FieldActions.INDEX_EXACT)

    for field, actions in FIELDS.items():
        for act in actions:
            db.add_field_action(field.replace("-", ""), *act[0], **act[1])

def scanrepo(repo, db):
    for branch in repo.get_branches():
        for doc in scanbranch(repo, branch):
            db.replace(doc)

def scanbranch(repo, branch):
    pkgs = []

    for package in repo.packages_in_branch(branch):
        pkgs.append(indexpackage(repo, branch, package))

    return pkgs

def indexpackage(repo, branch, package):
    # Get data
    cakefile = repo.get_package_cakefile(branch, package)

    # Fill document
    doc = xappy.UnprocessedDocument()
    doc.fields.append(xappy.Field("package", package))
    doc.fields.append(xappy.Field("branch", branch))
    doc.id = branch+"/"+package

    # Add fields
    for field in FIELDS:
        if field in cakefile:
            data = cakefile[field]

            if hasattr(data, "__iter__"):
                data = " ".join(data)

            doc.fields.append(xappy.Field(field.replace("-", ""), data))

    return doc

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("USAGE: %s REPO DATABASE [BRANCH [PACKAGE..]]" % sys.argv[0])

    repo = repo.HurlRepo(sys.argv[1])
    db = xappy.IndexerConnection(sys.argv[2])

    try:
        if len(sys.argv) == 3:
            scanrepo(repo, db)
        elif len(sys.argv) == 4:
            branch = sys.argv[3]

            if branch == "create":
                create_index(db)
            elif branch == "listen":
                while 1:
                    line = sys.stdin.readline()

                    if line.strip():
                        pkg, branch = map(str.strip, line.split("/", 1))
                        db.replace(indexpackage(repo, branch, pkg))
            else:
                for pkg in scanbranch(repo, branch):
                    db.replace(pkg)
        elif len(sys.argv) >= 5:
            branch = sys.argv[3]

            for pkg in sys.argv[4:]:
                db.replace(indexpackage(repo, branch, pkg))
    finally:
        db.close()
