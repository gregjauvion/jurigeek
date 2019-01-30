
from gensim.models.word2vec import Word2Vec
from nlp_datasets import stanford_sentiment, mattmahoney_dc
from nlp_evaluation import simlex, cosine, evaluate, plot_embeddings, get_2d_embeddings
import matplotlib.pyplot as plt
import numpy as np
import time
from scipy.stats import spearmanr


###
# Train gensim Word2Vec
###

# Path to download the data
dl_path = '/Users/jjauvion/Data'

# Build the dataset
dataset = 'STANFORD'
if dataset=='STANFORD':
	dataset = map(lambda x:x[0], stanford_sentiment(dl_path))
elif dataset=='MATTMATHONEY':
	dataset = mattmahoney_dc(dl_path)

# Build the model
sentences = [d.split(' ') for d in dataset]
model = Word2Vec(size=100)
model.build_vocab(sentences)

# Train the model
for i in range(20):
	print i
	model.train(sentences, total_examples=model.corpus_count, epochs=1)


###
# Test the model
###

model.most_similar('man')

# Build the word embeddings
words = sorted(model.wv.vocab.keys(), key=lambda x:model.wv.vocab[x].index)
words_embeddings = {w: model.wv.word_vec(w) for w in words}

# Compute similarities
similarities = simlex(dl_path)
result, nb_not_found = evaluate(words_embeddings, similarities)

spearman_corr = spearmanr([i[0] for i in result], [i[1] for i in result])
print spearman_corr

# Plot the similarities
plt.scatter([i[0] for i in result], [i[1] for i in result])
plt.show()


# 2D plot of embeddings
nb_words = 250
to_plot_embeddings = np.zeros((nb_words, size))
for i in range(nb_words):
	to_plot_embeddings[i,:] = words_embeddings[words[i]]
embeddings_2d = get_2d_embeddings(to_plot_embeddings, pca=True)
labels = words[:nb_words]

plot_embeddings(embeddings_2d, labels)


