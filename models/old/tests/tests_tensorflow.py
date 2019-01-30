
from datasets import stanford_sentiment, mattmahoney_dc
from nlp_processing import build_vocabulary, batch_generator
from nlp_models import Word2Vec, plot_embeddings, get_2d_embeddings
from nlp_evaluation import simlex, cosine, evaluate
import matplotlib.pyplot as plt
import tensorflow as tf
import numpy as np
import time


###
# Some global variables for this script
###

# Path to download the data
dl_path = '/Users/jjauvion/Data'

# Path to store the model
svg_path = 'tests_results'



###
# Build the vocabulary, the data generator and train the model
###


dataset = 'MATTMATHONEY'

# Build the vocabulary
vocabulary_size = 50000
if dataset=='STANFORD':
	dataset = stanford_sentiment()
	documents = map(lambda x:x[0], dataset)
elif dataset=='MATTMATHONEY':
	dataset = mattmahoney_dc(dl_path)
	documents = dataset

vocabulary, reverse, counts = build_vocabulary(documents, vocabulary_size)

# Share of words unknown in the vocabulary
print counts['#UNKNOWN'] / float(sum(counts.values()))

# The batch generator
window_size, batch_size = 5, 64
batches = batch_generator(documents, batch_size, window_size=window_size)

# Build a batch where words have been replaced with indices in the vocabulary
def replace_words(w_inputs, w_labels, vocabulary):
	size = w_inputs.shape[0]
	inputs, labels = np.empty((size,)), np.empty((size, 1))
	for i in range(len(w_inputs)):
		inputs[i] = vocabulary[w_inputs[i]] if w_inputs[i] in vocabulary else 0
		labels[i, 0] = vocabulary[w_labels[i, 0]] if w_labels[i, 0] in vocabulary else 0
	return inputs, labels

# Train the model
tf.reset_default_graph()
session = tf.Session()

parameters = {'embeddings_size': 100, 'start_learning_rate': 0.5, 'num_sampled_nce': 500, 'vocabulary': vocabulary}

load_model = False
if load_model:
	model = Word2Vec.build('{0}/svg'.format(svg_path), session)
else:
	model = Word2Vec(session, parameters)

nb_steps, nb_steps_stats, avg_loss = 500000, 1000, 0
begin_time = time.time()

for step in range(nb_steps):
	# Build the batch
	w_inputs, w_labels = batches.next()
	inputs, labels = replace_words(w_inputs, w_labels, vocabulary)

	# Train
	loss, _, learning_rate = model.train(inputs, labels)
	avg_loss += loss

	# Output from time to time
	if (step+1) % nb_steps_stats == 0:
		print step+1, avg_loss/nb_steps_stats, learning_rate, int(time.time()-begin_time)
		avg_loss = 0

# Serialize the model once training is finished
model.save('{0}/svg'.format(svg_path))



###
# Read a serialized model and evalute the embeddings
###

# Load the model
tf.reset_default_graph()
with tf.Session() as session:
	model = Word2Vec.build('{0}/svg'.format(svg_path), session)
	embeddings = model.get_embeddings(normalized=False)

# Rebuild the reverse vocabulary
reverse = {i: w for w, i in model.vocabulary.iteritems()}

plt.scatter([i[0] for i in embeddings[:1000,]],[i[1] for i in embeddings[:1000,]])
plt.show()


### Choose some words randomly, and print the most similar words
words = np.random.choice(sorted(counts, key=lambda x:-counts[x])[100:500], 20, replace=False)
int_words = np.array([vocabulary[w] for w in words])
most_similar = model.most_similar(int_words)
most_similar_words = np.empty((20, 5), dtype=object)
for i in range(20):
	for j in range(5):
		most_similar_words[i,j] = reverse[most_similar[i, j]]
print most_similar_words

# Print the most similar words for some word
[reverse[i] for i in model.most_similar([vocabulary['lincoln']])[0]]


### 2D-plot of the embeddings
nb_plots = 500
embeddings_2d = get_2d_embeddings(embeddings[:nb_plots,:])
labels = [reverse[i] for i in range(nb_plots)]
plot_embeddings(embeddings_2d, labels)


### Evaluate the embeddings on simlex dataset
dict_embeddings = {reverse[i]: embeddings[i,:] for i in range(embeddings.shape[0])}
similarities = simlex(dl_path)
result, nb_not_found = evaluate(dict_embeddings, similarities)

plt.scatter([i[0] for i in result], [i[1] for i in result])
plt.show()

np.corrcoef([i[0] for i in result], [i[1] for i in result])
