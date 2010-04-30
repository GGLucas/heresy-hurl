import os
import tarfile
import cherrypy
import time

try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

class Source(object):
    def __init__(self, repo, lookup):
        self.repo, self.lookup = repo, lookup

    @cherrypy.expose
    def default(self, filename):
        # Extract archive type
        if filename.endswith(".tar.gz"):
            cherrypy.response.headers['Content-Type'] \
                = 'application/x-tar-gz'

            mode = "w:gz"
        elif filename.endswith(".tar.bz2"):
            cherrypy.response.headers['Content-Type'] \
                = 'application/x-tar-bz2'

            mode = "w:bz2"
        else:
            raise cherrypy.NotFound()

        # Extract package and branch
        items = filename.split("-")
        branch = items.pop().split(".tar.")[0]
        package = "-".join(items)

        # Create tar archive
        content = StringIO.StringIO()
        tarf = tarfile.open(fileobj=content, mode=mode)
        tree = self.repo.get_package_tree(branch, package)

        for i, filename, ident in tree.entries():
            blob = self.repo.get_blob(ident).as_raw_string()
            length = len(blob)

            string = StringIO.StringIO()
            string.write(blob)
            string.seek(0)

            info = tarfile.TarInfo(name=os.path.join(package+"-"+branch, filename))
            info.size = length
            info.mtime = time.time()

            tarf.addfile(tarinfo=info, fileobj=string)

        tarf.close()
        return content.getvalue()
