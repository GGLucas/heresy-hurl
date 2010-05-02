import datetime
import xappy

class HurlIndex(object):
    def __init__(self, dbpath, refresh_after=30):
        self.dbpath = dbpath
        self.refresh_after = refresh_after
        self.conn = xappy.SearchConnection(dbpath)
        self.updated = datetime.datetime.now()

    def search(self, terms):
        if datetime.datetime.now()-self.updated > \
            datetime.timedelta(minutes=self.refresh_after):
            self.conn.reopen()

        q = self.conn.query_parse(terms, default_op=self.conn.OP_AND)
        results = self.conn.search(q, 0, 10, collapse="package")
        return ([doc.data for doc in results],
            results.matches_estimated, results.estimate_is_exact)

def main():
    import sys
    index = HurlIndex(sys.argv[1])
    terms = ' '.join(sys.argv[2:])
    results = index.search(terms)

    from pprint import pprint
    pprint(results)

if __name__ == '__main__':
    main()
