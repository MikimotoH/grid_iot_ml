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
import lzma
from statistics import mean as avg
from sklearn.metrics import classification_report


def get_nmaplog(idsession:int, ip_addr:str)->str:
    return ' '.join(_.strip() for _ in nmap_utils.tokenize_nmaplog_host(idsession, ip_addr) if _.strip())


def save_train_data(train_data:list, filename:str):
    with lzma.open(filename, 'wt') as fout:
        for datum, label,idsession,ipaddr,model in train_data:
            fout.write((' '*4).join([datum, str(label), str(idsession), ipaddr, model])+'\n')


def load_train_data(filename:str)->list:
    with lzma.open(filename, 'rt') as fin:
        for line in fin:
            line = line.rstrip()
            datum,label,idsession,ipaddr,model = line.split(' '*4)
            yield datum,int(label),int(idsession),ipaddr,model


def unzip(zipped, index)->list:
    return list(zip(*zipped))[index]
def num_uniq(ls:list)->int:
    return len(set(ls))


num_cv_folds=3 # number of cross validation folds
max_train_count = sys.maxsize

""" load train_data or extract from nmaplog """
try:
    train_data = list(load_train_data('linksys_models_train_data.txt.xz'))
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
        train_data += [ (get_nmaplog(*_), label, _[0], _[1], model) for _ in idip]
    time1 = time.perf_counter()
    print("Tokenizer took %0.3f seconds to generate %s categories, totally N=%s data"%(time1-time0, num_uniq(unzip(train_data,1)), len(train_data)))
    save_train_data(train_data, 'linksys_models_train_data.txt.xz')

num_categories = num_uniq(unzip(train_data,1))
model_names = [ next(_[4] for _ in train_data if _[1]==cat) for cat in range(num_categories)]

shuffle(train_data)

def run_grid_search(pipeline, parameters) -> dict:
    from pprint import PrettyPrinter
    pp = PrettyPrinter()
    print("parameters:\n    ", end='')
    pp.pprint(parameters)
    grid_search = GridSearchCV(pipeline, parameters, n_jobs=-1, verbose=1, cv=num_cv_folds)
    grid_search.fit( unzip(train_data,0), unzip(train_data,1) )

    prediction = grid_search.predict(unzip(train_data,0))
    print(classification_report(unzip(train_data,1), prediction, target_names=model_names))

    best_parameters = grid_search.best_estimator_.get_params()
    print("Best score : %0.3f" % grid_search.best_score_)
    ret = {}
    print("Best parameter:")
    try:
        for param_name in sorted(parameters.keys()):
            print("    %s: %r" % (param_name, best_parameters[param_name]))
            ret[param_name] = (best_parameters[param_name],)
    except AttributeError:
        for param_name in sorted(parameters[0].keys()):
            print("    %s: %r" % (param_name, best_parameters[param_name]))
            ret[param_name] = (best_parameters[param_name],)
    print("")
    return ret


"""
Multinomial Naive Bayesian 
"""
pipeline = Pipeline([
    ('vect', TfidfVectorizer()), 
    ('clf', MultinomialNB()),
])
nb_parameters = {
    'vect__token_pattern':(r"[^\ ]+",),
    'vect__ngram_range': ((1,2), ),
    'vect__stop_words': ('english', ),
    'vect__max_df': (0.15,), # When building the vocabulary ignore terms that have a document frequency strictly higher than the given threshold (corpus-specific stop words)
    'vect__min_df': (0,), # When building the vocabulary ignore terms that have a document frequency strictly lower than the given threshold. This value is also called cut-off in the literature.
    'vect__use_idf': (False,),
    'clf__alpha':(np.exp2(-1074), ),
    'clf__fit_prior':(True,),
}
print("\n--- MultinomialNB (NaiveBayesian Classifier) ---")
run_grid_search(pipeline, nb_parameters)



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
    'vect__stop_words': ('english',),
    'vect__max_df': (0.15, ),
    'vect__min_df': (0,), # 2/len(train_data), ), 
    'vect__use_idf': (True, ),
    'vect__sublinear_tf': (True,), # False,),
    'clf__loss':('hinge',), # 'squared_loss', 'huber', 'epsilon_insensitive', ), 
    'clf__alpha':(1e-5,), # 1e-4), # regularization term
    'clf__penalty':('elasticnet',),
    'clf__l1_ratio': (0.09,), # 0.11,),
    # 'clf__learning_rate': ('optimal', ),
    # 'clf__warm_start':(False,),
    'clf__n_jobs': (-1, ),
    'clf__average': (False, ),
}
print("\n--- SGDClassifier ---")
best_sgd_params = run_grid_search(pipeline, parameters)
best_vect_params = {k:v for k,v in best_sgd_params.items() if k.startswith('vect')}


"""
Linear SVC (Support Vector Machine Classifier)
"""
pipeline = Pipeline([
    ('vect', TfidfVectorizer()), 
    ('clf', LinearSVC()),
])
parameters = [
    {
        **best_vect_params,
        'clf__C': (3,4,5,6,),
        'clf__loss':('squared_hinge',),
        'clf__penalty': ('l1',),
        'clf__dual': (False,),
    },
    {
        **best_vect_params,
        'clf__C': (3,4,5,6,),
        'clf__loss':('squared_hinge',),
        'clf__penalty': ('l2',),
        'clf__dual': (True,False,),
    },
    {
        **best_vect_params,
        'clf__C': (3,4,5,6,),
        'clf__loss':('hinge',),
        'clf__penalty': ('l2',),
        'clf__dual': (True,),
    },
]
print("\n--- LinearSVC Linear Support Vector Machine Classifier ---")
run_grid_search(pipeline, parameters)

