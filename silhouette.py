#!/usr/bin/env python3
# coding: utf-8
import numpy as np
import statistics as stats
import ipdb
import pdb
import traceback
import math

def silhouette(XX:np.ndarray, labels:np.ndarray):
    def similarity(vecA:np.ndarray, vecB:np.ndarray)->np.float:
        from math import sqrt
        return (vecA @ vecB)/(sqrt( (vecA @ vecA)*(vecB @ vecB) ))
    def distance(i:int, j:int)->np.float:
        return 1 - similarity(XX[i], XX[j])

    def a(index: int):
        """
        the average dissimilarity of i with all other data within the same cluster
        """
        cluster = [i for i,label in enumerate(labels) if label==labels[index] and i !=index]
        if len(cluster)==0:
            return 0
        return stats.mean(distance(jindex,index) for jindex in cluster)
    def b(i):
        """
        Let b(i) be the lowest average dissimilarity of i to any other cluster, of which i is not a member. 
        The cluster with this lowest average dissimilarity is said to be the "neighbouring cluster" of i 
          because it is the next best fit cluster for point i.
        """
        dist = np.zeros(len(set(labels)))
        dist[labels[i]] = float('inf')
        for label in set(labels) - {labels[i]}:
            dist[label] = stats.mean(distance(i,j) for j,_ in enumerate(labels) if _==label)
        return min(dist)
    def s(index: int)->np.float:
        return (b(index) - a(index)) / max(b(index),a(index))

    num_rows = XX.shape[0]
    def s2(i):
        simi = np.sum(XX*XX[i],axis=1)/np.sqrt(np.sum(XX*XX,axis=1)*np.sum(XX[i]*XX[i]))
        dist = 1 - simi
        if sum(labels == labels[i]) <= 1:
            a_i = 0
        else:
            a_i = np.mean(dist[np.array([_==labels[i] and i!=k for k,_ in enumerate(labels)])])
        b_i = min( np.mean(dist[np.array([_==lab for _ in labels])]) for lab in set(labels)-{labels[i]} )
        if str(a_i).lower() =='nan' or str(b_i).lower()=='nan':
            pdb.set_trace()

        return (b_i-a_i)/ max(b_i,a_i)

    return stats.mean(s2(i) for i in range(XX.shape[0]))

def main():
    from sklearn.cluster import KMeans
    XX = np.loadtxt('asus_router.tfidf.txt.gz')
    for cluster in range(5, 21):
        labels = KMeans(cluster, n_jobs=-1).fit_predict(XX)
        silh = silhouette(XX, labels)
        print('cluster=%s, silhouette=%s'%(cluster, silh))

if __name__ == '__main__':
    main()

