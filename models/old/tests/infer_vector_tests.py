
from gensim.models.doc2vec import Doc2Vec
from gensim.utils import simple_preprocess
from model_server.model_api import ModelApi
import numpy as np
import matplotlib.pyplot as plt
import json

model = Doc2Vec.load('/Users/jjauvion/Data/doc2vec_all_data_size_50.gensim')

def sim(v, w):
    return np.dot(v, w) / (np.linalg.norm(v) * np.linalg.norm(w))

vectors = []

for s in range(50):
    model.random.seed(0)
    vectors.append(model.infer_vector(simple_preprocess('Je souhaite inférer un vecteur pour un document juridique.'), steps=s))


for j in range(50):
    plt.plot([i[j] for i in vectors])

plt.show()

for j in range(50):
    print vectors[5][j] / vectors[10][j]


for j in range(49):
    print sim(vectors[j], vectors[j+1])



# Check ordering of docs with several calls
api = ModelApi('/Users/jjauvion/Data/doc2vec_all_data_size_50.gensim', '/Users/jjauvion/Data/juris_fr_dump_10000')

# Get url <--> index
url_index = {}
with open('/Users/jjauvion/Data/juris_fr_dump_10000', 'r') as f:
    for e, l in enumerate(f):
        doc = json.loads(l[:-1])
        url_index[doc['url']] = e
        if e==101:
            text=doc['text']


sim_1 = [url_index[i['document']['url']] for i in api.most_similar(text, 10000)]
sim_2 = [url_index[i['document']['url']] for i in api.most_similar(text, 10000)]

# Build the list of indices of sim_2 in sim_1
sim_2_ind = [sim_1.index(i) for i in sim_2]

plt.plot(sim_2_ind)
plt.show()


sims = [i['similarity'] for i in api.most_similar(text, 10000)]
plt.plot(sims) ; plt.show()




vect = [model.infer_vector(simple_preprocess(text)) for i in range(50)]
sims = [sim(vect[i], vect[i+1]) for i in range(49)]

plt.plot(sims) ; plt.show()

