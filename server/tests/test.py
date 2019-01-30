
import json
import logging
import numpy as np
from models.nlp_keywords import Vocabulary, Keywords
from server import tfidf_api
from data.law_data import Reader
from itertools import imap
import pickle

NB_KEYWORDS = 25
VOCAB_LIMIT = 1E-6

path_to_data = '/Users/jjauvion/Data/juris_fr_dump_1000'

data_text = lambda :imap(lambda x:json.loads(x[1][:-1])['text'], Reader(path_to_data))
data_id = lambda :imap(lambda x:json.loads(x[1][:-1])['pk_id'], Reader(path_to_data))

#vocabulary = Vocabulary.build(data_text, window_size=3, limit=VOCAB_LIMIT)


api = tfidf_api.TfidfApi(path_to_data)


to_write = {'a': vocabulary.counts, 'b': vocabulary.id_tokens, 'c': vocabulary.size_tokens_id}
with open('vocab_data', 'w') as f:
    pickle.dump(to_write['a'], f)

model = Keywords(vocabulary, data_text)
model.tfidf.save('tfidf_model')

keywords = []
for text, id_ in zip(data_text(), data_id()):
    keywords.append((id_, model.get_keywords(text, NB_KEYWORDS)))

with open('kw_data', 'w') as f:
    pickle.dump(keywords, f)

import sys
sys.getsizeof(vocabulary.counts)

sys.getsizeof(model.tfidf.idfs)


kw_bis = []
for k in keywords:
    d = {}
    for i,j in k[1].iteritems():
        d[i] = [j[0], 1000]
    kw_bis.append((k[0], d))


d = {1:4}
for i,j in vocabulary.counts.iteritems():
    d[i] = j

print sys.getsizeof(d)



from guppy import hpy
h = hpy()
h.heap()
