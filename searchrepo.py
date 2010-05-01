import xappy

class HurlIndex(object):
    def __init__(self, dbpath):
        self.dbpath = dbpath
        self.conn = xappy.SearchConnection(dbpath)

    def search(self, terms):
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
