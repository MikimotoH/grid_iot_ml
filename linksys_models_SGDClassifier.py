# coding: utf-8
import nmap_utils
import csv
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.linear_model import SGDClassifier
from sklearn.grid_search import GridSearchCV
from sklearn.pipeline import Pipeline
import numpy as np
from os import path

def get_nmaplog(idsession:int, ip_addr:str)->str:
    return '\t'.join(_ for _ in nmap_utils.tokenize_nmaplog_host(idsession, ip_addr) if _.strip())

with open("Linksys_models.csv") as fin:
    csvreader = csv.reader(fin)
    #  IDSession, ip_addr, model
    rows = [(int(r[0]), r[1], r[2].lower()) for r in csvreader if r is not None and len(r)>=3]
    
# filter out non-existing file
rows = [r for r in rows if path.exists("nmaplog/%s.xml"%r[0])]
rows.sort(key=lambda r:r[2])
from itertools import groupby
model_counts = [(k,len(list(g))) for k,g in groupby(rows, key=lambda r:r[2])]

# models = list(set(r[2].lower() for r in rows))
# model_counts = [sum(r[2]==model for r in  rows) for model in models]
# model_counts = list(zip(models, model_counts))

# filter out model_counts too low
model_counts = [ m for m in model_counts if m[1]>=10]
max_traintest_count = 1000
train_prop = 0.9
# prepare train_data
train_data, test_data= [],[]
for label,model_count in enumerate(model_counts):
    model,_ = model_count
    idip = [(r[0],r[1]) for r in rows if r[2].lower()==model]
    from random import shuffle
    shuffle(idip)
    idip = idip[:max_traintest_count]
    train_idip = idip[:int(len(idip)*0.9)]
    test_idip = idip[int(len(idip)*0.9):]

    train_data += [ (get_nmaplog(*idip), label) for idip in train_idip]
    test_data += [ (get_nmaplog(*idip), label) for idip in test_idip]
shuffle(train_data)

pipeline = Pipeline([
    ('vect', CountVectorizer()), 
    ('tfidf', TfidfTransformer()),
    ('clf', SGDClassifier()),
])
parameters = {
    # 'vect__max_df':(0.5, 0.75, 1.0),
    'vect__token_pattern':(r"[^\t]+",),
    # 'vect__ngram_range': ((1,1), (1,2)),
    'clf__alpha':(0.00001, 0.000001),
    'clf__penalty':('l2', 'elasticnet'),
}
grid_search = GridSearchCV(pipeline, parameters, n_jobs=-1, verbose=1)
grid_search.fit(list(zip(*train_data))[0], list(zip(*train_data))[1] )
best_parameters = grid_search.best_estimator_.get_params()
print("Best score : %0.3f" % grid_search.best_score_)
print("Best parameter set:")
for param_name in sorted(parameters.keys()):
    print("\t%s: %r" % (param_name, best_parameters[param_name]))

test_score = grid_search.score(list(zip(*test_data))[0], list(zip(*test_data))[1])
print("Test score: %0.3f" % test_score)

