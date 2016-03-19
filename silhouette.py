#!/usr/bin/env python3
# coding: utf-8
import numpy as np
import statistics as stats
import ipdb
import pdb
import traceback

def similarity(vecA:np.ndarray, vecB:np.ndarray)->np.float:
    """
    https://en.wikipedia.org/wiki/Cosine_similarity
    """
    from math import sqrt
    return np.dot(vecA, vecB)/sqrt(np.dot(vecA, vecA)*np.dot(vecB, vecB))

def silhouette_safe(XX, labels)->float:
    def distance(i:int, j:int)->np.float:
        return 1 - similarity(XX[i], XX[j])
    def a(index: int):
        cluster = [i for i,label in enumerate(labels) if label==labels[index] and i !=index]
        if len(cluster)==0:
            return 0
        return stats.mean(distance(jindex,index) for jindex in cluster)
    def b(i):
        dist = np.zeros(len(set(labels)))
        dist[labels[i]] = float('inf')
        for label in set(labels) - {labels[i]}:
            dist[label] = stats.mean(distance(i,j) for j,_ in enumerate(labels) if _==label)
        return np.min(dist)
    def s(i):
        a_i = a(i)
        b_i = b(i)
        return (b_i-a_i)/ max(b_i,a_i)
    return stats.mean(s(i) for i in range(XX.shape[0]))

def silhouette(XX:np.ndarray, labels:np.ndarray):
    """
    https://en.wikipedia.org/wiki/Silhouette_%28clustering%29

    """
    def s(i):
        simi = np.sum(XX*XX[i],axis=1)/np.sqrt(np.sum(XX*XX,axis=1)*np.sum(XX[i]*XX[i]))
        dist = 1 - simi

        # a(i)
        # the average dissimilarity of i with all other data within the same cluster
        labs = (labels==labels[i])
        labs[i]=False
        if np.sum(labs) == 0:
            a_i = 0
        else:
            a_i = np.mean(dist[labs])
        if str(a_i).lower() =='nan':
            pdb.set_trace()

        # Let b(i) be the lowest average dissimilarity of i to any other cluster, of which i is not a member. 
        # The cluster with this lowest average dissimilarity is said to be the "neighbouring cluster" of i 
        #   because it is the next best fit cluster for point i.
        b_i = min( np.mean(dist[labels==l]) for l in set(labels)-{labels[i]} )
        if str(b_i).lower()=='nan':
            pdb.set_trace()

        return (b_i-a_i)/ max(b_i,a_i)

    return stats.mean(s(i) for i in range(XX.shape[0]))

def main():
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score
    XX = np.loadtxt('asus_router.tfidf.txt.gz')
    for cluster in range(2, 52):
        labels = KMeans(cluster, n_jobs=-1).fit_predict(XX)
        silh = silhouette(XX, labels)
        print('cluster=%s, silhouette=%s'%(cluster, silh))
        silh2 = silhouette_score(XX,labels, metric='cosine')
        print('cluster=%s, sklearn.silhouette_score=%s'%(cluster, silh2))

if __name__ == '__main__':
    main()

