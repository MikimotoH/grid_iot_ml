# coding: utf-8
import nmap_utils
import csv
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.linear_model import SGDClassifier
from sklearn.svm import LinearSVC
from sklearn.svm import SVC
from sklearn.grid_search import GridSearchCV
from sklearn.pipeline import Pipeline
import numpy as np
from os import path
from random import shuffle
from itertools import groupby
import time
import sys
from collections import Counter

def get_nmaplog(idsession:int, ip_addr:str)->str:
    return ' '.join(_.strip() for _ in nmap_utils.tokenize_nmaplog_host(idsession, ip_addr) if _.strip())

def save_train_data(train_data:list, filename:str):
    with open(filename, 'w') as fout:
        for datum, label,idsession,ipaddr in train_data:
            fout.write((' '*4).join([datum, str(label), str(idsession), ipaddr])+'\n')


def load_train_data(filename:str)->list:
    with open(filename, 'r') as fin:
        for line in fin:
            datum,label,idsession,ipaddr = line.split(' '*4)
            yield datum,int(label),int(idsession),ipaddr


def unzip(zipped, index)->list:
    return list(zip(*zipped))[index]
def num_uniq(ls:list)->int:
    return len(set(ls))


num_cv_folds=3
max_train_count = 500

try:
    train_data = list(load_train_data('linksys_models_train_data.txt'))
    print("Train Data: %s categories, total samples=%s data"%( num_uniq(unzip(train_data,1)), len(train_data)))
except FileNotFoundError:
    with open("Linksys_models.csv") as fin:
        csvreader = csv.reader(fin)
        #  IDSession, ip_addr, model
        rows = [(int(r[0]), r[1], r[2].lower()) for r in csvreader if r is not None and len(r)>=3]
        
    # filter out non-existing file
    rows = [r for r in rows if path.exists("nmaplog/%s.xml"%r[0])]
    rows.sort(key=lambda r:r[2])
    model_counts = [(k,len(list(g))) for k,g in groupby(rows, key=lambda r:r[2])]

    # filter out model_counts too low
    model_counts = [ m for m in model_counts if m[1]>=num_cv_folds ]
    # prepare train_data
    train_data = []
    print("start to tokenize")
    time0 = time.perf_counter()
    for label,model_count in enumerate(model_counts):
        model,_ = model_count
        idip = [(r[0],r[1]) for r in rows if r[2]==model]
        shuffle(idip)
        idip = idip[:max_train_count]
        train_data += [ (get_nmaplog(*_), label, _[0], _[1]) for _ in idip]
    time1 = time.perf_counter()
    print("Tokenizer took %0.3f seconds to generate %s categories, totally N=%s data"%(time1-time0, num_uniq(unzip(train_data,1)), len(train_data)))
    save_train_data(train_data, 'linksys_models_train_data.txt')

shuffle(train_data)

def run_grid_search(pipeline, parameters):
    grid_search = GridSearchCV(pipeline, parameters, n_jobs=-1, verbose=1, cv=num_cv_folds)
    grid_search.fit( unzip(train_data,0), unzip(train_data,1) )
    best_parameters = grid_search.best_estimator_.get_params()
    print("Best score : %0.3f" % grid_search.best_score_)
    print("Best parameter:")
    try:
        for param_name in sorted(parameters.keys()):
            print("    %s: %r" % (param_name, best_parameters[param_name]))
    except AttributeError:
        for param_name in sorted(parameters[0].keys()):
            print("    %s: %r" % (param_name, best_parameters[param_name]))


"""
Multinomial Naive Bayesian 
"""
pipeline = Pipeline([
    ('vect', TfidfVectorizer()), 
    ('clf', MultinomialNB()),
])
parameters = {
    'vect__token_pattern':(r"[^\ ]+",),
    'vect__ngram_range': ((1,2), ),
    'vect__stop_words': ('english', ),
    'vect__max_df': (0.2, ), # When building the vocabulary ignore terms that have a document frequency strictly higher than the given threshold (corpus-specific stop words)
    'vect__min_df': (0,), # When building the vocabulary ignore terms that have a document frequency strictly lower than the given threshold. This value is also called cut-off in the literature.
    'vect__use_idf': (False,),
    'clf__alpha':(np.exp2(-1074), ),
    'clf__fit_prior':(True,),
}
print("\n--- MultinomialNB (NaiveBayesian Classifier) ---")
run_grid_search(pipeline, parameters)
print("\n")


"""
SGD Classifier (Stochastic Gradient Descent)
"""
pipeline = Pipeline([
    ('vect', TfidfVectorizer()), 
    ('clf', SGDClassifier()),
])
parameters = {
    'vect__token_pattern':(r"[^\ ]+",),
    'vect__ngram_range': ((1,2),),
    'vect__stop_words': ('english', ),
    'vect__max_df': (0.2,), # When building the vocabulary ignore terms that have a document frequency strictly higher than the given threshold (corpus-specific stop words)
    'vect__use_idf': (False, ),
    'clf__loss':('hinge', 'perceptron', ), # 'hinge':SVM; 
    'clf__alpha':(1e-5, 1e-6, ), # regularization term
    'clf__penalty':('elasticnet',),
    'clf__l1_ratio':(0.15, 0.25, ), # when Elastic-net, the ratio to mix L1 with L2
    # 'clf__learning_rate': ('optimal', 'invscaling',),
    # 'clf__warm_start':(False,),
    # 'clf__n_jobs': (-1,),
    # 'clf__average': (False,),
}
print("\n--- SGDClassifier ---")
run_grid_search(pipeline, parameters)
print("\n")


"""
Linear SVC (Support Vector Machine Classifier)
"""
pipeline = Pipeline([
    ('vect', TfidfVectorizer()), 
    ('clf', LinearSVC()),
])
parameters = [
    {
        'vect__token_pattern':(r"[^\ ]+",),
        'vect__ngram_range': ((1,2),),
        'vect__stop_words': ('english', ),
        'vect__max_df': (0.3,),
        'vect__use_idf': (False, ),
        'clf__C':(4,),
        'clf__loss':('squared_hinge',),
        'clf__penalty': ('l1',),
        'clf__dual': (False,),
    },
    #{
    #    'vect__token_pattern':(r"[^\ ]+",),
    #    'clf__loss':('squared_hinge',),
    #    'clf__penalty': ('l2',),
    #    'clf__dual': (True,False,),
    #},
    #{
    #    'vect__token_pattern':(r"[^\ ]+",),
    #    'clf__loss':('hinge',),
    #    'clf__penalty': ('l2',),
    #    'clf__dual': (True,),
    #},
]
print("\n--- LinearSVC Linear Support Vector Machine Classifier ---")
run_grid_search(pipeline, parameters)
print("\n")


# """
# SVC (Support Vector Machine Classifier)
# """
# pipeline = Pipeline([
#     ('vect', TfidfVectorizer()), 
#     ('clf', SVC()),
# ])
# parameters = {
#     'vect__token_pattern':(r"[^\ ]+",),
#     'clf__C':(1,), #2,0.5,), # penalty parameter C of the error term
#     'clf__kernel': ('linear', 'poly', 'sigmoid', ), # 'rbf'
#     'clf__degree': (2, ), # used when kernel=='poly'
#     'clf__probability': (False, True,), # Whether to enable probability estimates
#     'clf__shrinking': (True,), # False,), # Whether to use the shrinking heuristic
#     'clf__coef0': (0,), #  0.1, 0.2, 0.4, -0.1, -0.2, -0.4),
#     'clf__decision_function_shape': (None,), # 'ovr', 'ovo',),
#     'clf__class_weight': (None,), # 'balanced',),
#     'clf__verbose':(False,),
# }
# print("\n--- SVC Support Vector Machine Classifier ---")
# run_grid_search(pipeline, parameters)
# print("\n")

