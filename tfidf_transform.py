#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import numpy as np
"""
    https://zh.wikipedia.org/wiki/TF-IDF

    denominator of tf = number of all open ports in a specific router 
    nominator of tf = 1 if term occurs in a specific router else 0
    tf[term,doc] = occur(term, doc)/sigma<termk of all terms>(occur(termk,doc))
    term_frequency = occurence of a term[i]
    inverse_document_frequency = log( |D|/|{j: t[i] E d[j]}|)
    denominator of idf=number of doc containing term[i]
    nominator of idf=number of corpus=number of asus_routers
"""

def TfidfTransform(XX:np.ndarray)->np.ndarray:
    """
    XX: rows are samples, columns are dimensions
       row feature vector are laid on to next row feature vector
    """
    tf = np.copy(XX)
    # row-wise operation
    tf_denom = np.apply_along_axis(np.sum, 1, XX)
    tf_denom = np.reshape(tf_denom, (XX.shape[0],1))
    # tile single row to matrix
    tf_denom = np.tile(tf_denom, (1, XX.shape[1]))
    tf/=tf_denom

    nom_idf = XX.shape[0]
    idf = np.ones(XX.shape)*nom_idf
    # column-wise operation
    idf_denom = np.apply_along_axis(np.sum, 0, XX)
    idf_denom = np.reshape(idf_denom, (1, XX.shape[1]))
    idf_denom = np.tile(idf_denom, (XX.shape[0], 1))
    idf/=idf_denom
    idf=np.log(idf)
    return tf*idf


def TfidfTransform_Safe(XX:np.ndarray)->np.ndarray:
    YY = np.copy(XX)
    nom_idf = XX.shape[0]
    for document in range(XX.shape[0]):
        denom_tf = sum(XX[document, :])
        for term in range(XX.shape[1]):
            nom_tf = XX[document, term]
            if nom_tf==0:
                continue
            tf = nom_tf/denom_tf
            denom_idf = np.sum(XX[:,term])
            idf=np.log(nom_idf/denom_idf)
            YY[document,term]=tf*idf
    return YY


def main():
    XX = np.loadtxt('asus_router.matrix.txt')
    YY = TfidfTransform(XX)
    np.savetxt('asus_router.tfidf.txt.gz', YY)
def main1():
    XX = np.loadtxt('asus_router.matrix.txt')
    YY = TfidfTransform_Safe(XX)
    np.savetxt('asus_router.tfidf.safe.txt.gz', YY)

if __name__=='__main__':
    main()
