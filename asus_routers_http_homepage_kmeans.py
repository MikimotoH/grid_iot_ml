import logging
from optparse import OptionParser

# Display progress logs on stdout
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

# parse commandline arguments
op = OptionParser()
op.add_option("--K", dest="n_clusters", type="int", default=8, 
        help="size of K for K-means clustering")
op.add_option("--brand", dest="brand", type="str", default="asus", 
        help="which brand of router to do clustering")
op.add_option("--verbose", action="store_true", dest="verbose", default=False, help="verbose")


(opts, args) = op.parse_args()
if len(args) > 0:
    op.print_help()
    op.error("this script takes no arguments.")
    sys.exit(1)

from sklearn.feature_extraction.text import CountVectorizer
countVectorizer = CountVectorizer(lowercase=False, token_pattern=r'[^ ]+')
import sqlite3
conn = sqlite3.connect('unknown_routers.sqlite3')
cursor = conn.cursor()
rows = cursor.execute("SELECT IDSession,ip_addr FROM Routers WHERE LOWER(brand) LIKE '%s%%' "%opts.brand.lower()).fetchall()

from http_homepage_to_bagofwords import get_homepage_as_bagofwords
X = countVectorizer.fit_transform([' '.join(get_homepage_as_bagofwords(*_)) for _ in rows])

from sklearn.cluster import KMeans
kmeans = KMeans(n_clusters=opts.n_clusters, n_jobs=-1);
labels = kmeans.fit_predict(X)

from sklearn.metrics import silhouette_score
silh = silhouette_score(X, labels)
print('silhouette_score=%s'%silh)

if opts.verbose:
    order_centroids = kmeans.cluster_centers_.argsort()[:,::-1] 
    terms = countVectorizer.get_feature_names()
    import pprint
    pp = pprint.PrettyPrinter(width=120)
    for lab in set(labels):
        print('\n')
        print('label=%s'%lab)
        pp.pprint('terms=%s'%[terms[ind] for ind in order_centroids[lab,:10]])
        pp.pprint('nmaplog=%s' % [rows[i] for i,_ in enumerate(labels) if _==lab])

