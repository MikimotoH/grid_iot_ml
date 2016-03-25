import logging
from optparse import OptionParser
import numpy as np

from lxml import etree

from http_homepage_to_bagofwords import get_homepage_as_bagofwords
from http_homepage_to_bagofwords import get_host

def iter_to_str(it:iter)->str:
    return '['+', '.join('"%s"'%_ for _ in it) +']'
def uprint(msg:str)->int:
    import sys; return sys.stdout.buffer.write((msg+'\n').encode('utf8'))

def wrap_print(text:str)->int:
    import textwrap
    lines = textwrap.wrap(text, width=120)
    for line in lines:
        uprint(line)

def is_windows(id_session:int, host_ip:str):
    host = get_host(id_session, host_ip)
    return any(('Windows' in _.attrib['name']) for _ in host.xpath('.//osmatch'))

def main():
    # Display progress logs on stdout
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

    # parse commandline arguments
    op = OptionParser()
    op.add_option("--K", dest="n_clusters", type="int", default=None, 
            help="size of K for K-means clustering")
    op.add_option("--brand", dest="brand", type="str", default="asus", 
            help="which brand of router to do clustering")
    op.add_option("--verbose", action="store_true", dest="verbose", default=False, 
            help="list each clusters popular terms")
    op.add_option("--popular-terms", dest="popular_terms", type="int", default=10,
            help="list popular terms of each cluster")
    op.add_option("--show-idsession", action="store_true", dest="show_idsession", default=False, 
            help="show all (IDSession,host_ip) of each cluster")


    (opts, args) = op.parse_args()
    if len(args) > 0:
        op.print_help()
        op.error("this script takes no arguments.")
        sys.exit(1)

    import sqlite3
    conn = sqlite3.connect('unknown_routers.sqlite3')
    cursor = conn.cursor()
    rows = cursor.execute("SELECT IDSession,ip_addr FROM Routers WHERE LOWER(brand) LIKE '%s%%' "%opts.brand.lower()).fetchall()

    # filter out Windows PC
    print('Before removing Windows, samples=%s'%len(rows))
    rows = [_ for _ in rows if not is_windows(*_)]
    print('After removing Windows, samples=%s'%len(rows))

    from sklearn.feature_extraction.text import CountVectorizer
    countVectorizer = CountVectorizer(lowercase=False, token_pattern=r'[^\t]+', stop_words='english')
    X = countVectorizer.fit_transform(['\t'.join(get_homepage_as_bagofwords(*_)) for _ in rows])

    from sklearn.feature_extraction.text import TfidfTransformer
    tfidf = TfidfTransformer()
    X = tfidf.fit_transform(X)

    from sklearn.cluster import KMeans
    if opts.n_clusters is None:
        # https://en.wikipedia.org/wiki/Determining_the_number_of_clusters_in_a_data_set#Finding_Number_of_Clusters_in_Text_Databases
        # Can, F.; Ozkarahan, E. A. (1990). "Concepts and effectiveness of the
        #   cover-coefficient-based clustering methodology for text databases".
        #   ACM Transactions on Database Systems 15 (4): 483.
        #   doi:10.1145/99935.99938. especially see Section 2.7.
        nonzero_terms = np.sum( np.abs(X).todense() > np.finfo(float).eps) 
        opts.n_clusters = int(X.shape[0]*X.shape[1]/nonzero_terms)
        print('n_clusters = %s'%opts.n_clusters)
    kmeans = KMeans(n_clusters=opts.n_clusters, n_jobs=-1);
    labels = kmeans.fit_predict(X)

    from sklearn.metrics import silhouette_score
    silh = silhouette_score(X, labels)
    print('silhouette_score=%s'%silh)

    if opts.verbose:
        # argsort(): Returns the indices that would sort an array row by row
        order_centroids = kmeans.cluster_centers_.argsort()[:,::-1] 
        terms = countVectorizer.get_feature_names()
        # wrap_print('terms=%s'%terms)
        for lab in set(labels):
            print('label=%s'%lab)
            print('size of cluster[%d]=%d'%(lab, sum(labels==lab)))
            representation = np.argmin(np.sum(np.abs(X-kmeans.cluster_centers_[lab]), axis=1))
            print('representation (IDSession,host_ip)=(%s,%s)'%rows[representation])
            term_strengths = [kmeans.cluster_centers_[lab,ind] for ind in order_centroids[lab,:opts.popular_terms]]
            # cut strength too low
            term_strengths = [_ for _ in term_strengths if _>np.finfo(float).eps]
            popular_terms = [terms[ind] for ind in order_centroids[lab,:len(term_strengths)]]
            wrap_print('terms=%s'%popular_terms)
            import pandas
            df = pandas.DataFrame(list(zip(popular_terms, term_strengths)), columns=['terms','strength'])
            print(df)
            if opts.show_idsession:
                wrap_print('nmaplog=%s'% [rows[i] for i,_ in enumerate(labels) if _==lab])
            print('\n')

if __name__=='__main__':
    try:
        main()
    except Exception as ex:
        import traceback
        traceback.print_exc()
        import pdb
        pdb.set_trace()

