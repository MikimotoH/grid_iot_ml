from sklearn.feature_extraction.text import CountVectorizer
countVectorizer = CountVectorizer(lowercase=False, token_pattern=r'[^ ]+')
import sqlite3
conn = sqlite3.connect('unknown_routers.sqlite3')
cursor = conn.cursor()
rows = cursor.execute("select IDSession,ip_addr from Routers WHERE LOWER(brand) LIKE 'asus%' ").fetchall()

from http_homepage_to_bagofwords import get_homepage_as_bagofwords
X = countVectorizer.fit_transform([' '.join(get_homepage_as_bagofwords(*_)) for _ in rows])

from sklearn.cluster import KMeans
kmeans = KMeans(n_clusters=36, n_jobs=-1);
labels = kmeans.fit_predict(X)

from sklearn.metrics import silhouette_score
silh = silhouette_score(X, labels)
print('silhouette_score=%s'%silh)

order_centroids = kmeans.cluster_centers_.argsort()[:,::-1]                
terms = countVectorizer.get_feature_names()                                

for lab in set(labels):
    print('label=%s'%lab)
    print('terms=%s'%[terms[ind] for ind in order_centroids[lab,:10]])
