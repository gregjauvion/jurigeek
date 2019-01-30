
import tensorflow as tf
import numpy as np
import json


class Word2Vec():
    """ This class implements a custom Word2Vec implementation using Tensorflow.
    Started from https://github.com/tensorflow/tensorflow/blob/r1.1/tensorflow/examples/tutorials/word2vec/word2vec_basic.py.

    The model is learnt using the noise contrastive estimation approach.

    Some tricks described in the paper are not implemented yet:
    - hierarchical softmax
    - subsampling of frequent words
    - ...
    """

    EMBEDDINGS_SIZE_DEFAULT = 50
    NUM_SAMPLED_NCE_DEFAULT = 20
    START_LEARNING_RATE_DEFAULT = 1E-3

    def __init__(self, session, parameters):
        """
        - session: tensorflow session

        - parameters: a dict with all the model parameters (they are stored in a dict to be able to serialize/deserialize easily the model), which are the following
        -- 'embeddings_size': size of the words embeddings
        -- 'learning_rate': the initial learning rate used in the optimizer
        -- 'num_sampled_nce': number of negative examples sampled in the NCE estimation method (according to Word2Vec paper: 5-20 for small datasets, <5 for large ones)
        -- 'vocabulary': the vocabulary, which is a dict mapping each word with an index
        Default values are defined for all parameters.
        """

        self.session = session
        self.parameters = parameters

        # Retrieve all parameters
        self.embeddings_size = self.parameters['embeddings_size'] if 'embeddings_size' in self.parameters else EMBEDDINGS_SIZE_DEFAULT
        self.start_learning_rate = self.parameters['start_learning_rate'] if 'start_learning_rate' in self.parameters else LEARNING_RATE_DEFAULT
        self.num_sampled_nce = self.parameters['num_sampled_nce'] if 'num_sampled_nce' in self.parameters else NUM_SAMPLED_NCE_DEFAULT
        self.vocabulary = self.parameters['vocabulary']
        self.vocabulary_size = len(self.vocabulary)

        # Add in the graph all operations used for training
        self._train()

        # Operations needed to compute similarities efficiently
        self._similarities()

        # Operations defining the summary for Tensorboard
        self._summary()

        # Operations to be able to serialize the model
        self._save()

        # Initialize all variables of the graph, and ensure that it can not be modified anymore
        self.session.run(tf.global_variables_initializer())
        #self.session.graph.finalize()


    def _train(self):
        """ Define operations needed for training.
        For the moment, we assume that the context used to predict a word in the skip-gram approach is formed with one word only.
        """

        # The placeholders : inputs is the list of contexts for this batch (formed with one word), and labels gives the words to predict for this batch
        self.inputs = tf.placeholder(tf.int32, shape=[None])
        self.labels = tf.placeholder(tf.int32, shape=[None, 1])

        # The word embeddings
        self.embeddings = tf.get_variable('embeddings', initializer=tf.random_uniform([self.vocabulary_size, self.embeddings_size], -1.0, 1.0))
        # The embeddings used in this batch
        self.inputs_embeddings = tf.gather(self.embeddings, self.inputs)
        #self.inputs_embeddings = tf.nn.embedding_lookup(self.embeddings, self.inputs)

        # All weights used in the model
        self.weights = {
            'weights': tf.get_variable('weights', initializer=tf.truncated_normal([self.vocabulary_size, self.embeddings_size], stddev=1.0/np.sqrt(self.embeddings_size))),
            'biases': tf.get_variable('biases', initializer=tf.zeros([self.vocabulary_size]))
        }

        # The loss
        self.loss = tf.reduce_mean(
            tf.nn.nce_loss(
                weights=self.weights['weights'],
                biases=self.weights['biases'],
                labels=self.labels,
                inputs=self.inputs_embeddings,
                num_sampled=self.num_sampled_nce,
                num_classes=self.vocabulary_size))

        # The training step. Note: Adam optimizer does not work efficiently because inputs are sparse. Do not use it.
        # It seems that basic gradient descent works better for the moment.
        #self.train_step = tf.train.AdamOptimizer(self.start_learning_rate).minimize(self.loss)
        global_step = tf.Variable(0, trainable=False)
        self.learning_rate = tf.train.exponential_decay(self.start_learning_rate, global_step, 10000, 0.9, staircase=True) # Multiply learning rate per 0.9 every 10.000 steps
        self.train_step = tf.train.GradientDescentOptimizer(self.learning_rate).minimize(self.loss, global_step=global_step)


    def _similarities(self):
        """ Operations to compute similarities.
        """

        # Compute normalized embeddings, needed to compute cosine similarities
        norm = tf.sqrt(tf.reduce_sum(tf.square(self.embeddings), 1, keep_dims=True))
        self.normalized_embeddings = self.embeddings / norm

        # Compute cosine similarities with a batch of words
        self.words_for_similarity = tf.placeholder(tf.int32, shape=[None])
        # self.similarities is a matrix [size(words_for_similarity), vocabulary_size], giving the similarities between the set of words and all vocabulary
        self.similarities = tf.matmul(tf.gather(self.normalized_embeddings, self.words_for_similarity), self.normalized_embeddings, transpose_b=True)

        # 5 most similar words for each word
        sims, indices = tf.nn.top_k(self.similarities, k=5)
        self.most_similar_words = indices


    def _summary(self):

        with tf.name_scope('summary'):
            tf.summary.scalar('loss', self.loss)
            tf.summary.histogram('weights', self.weights['weights'])
            tf.summary.histogram('biases', self.weights['biases'])

            self.summary_op = tf.summary.merge_all()


    def _save(self):
        self.saver = tf.train.Saver()


    def train(self, inputs, labels, run_summary=False):
        """ Train the model with a batch of inputs.
        For the moment we must give words indices (mapping with vocabulary is done before calling this function)
        Summary is optional (because it makes computations way slower).
        """

        if run_summary:
            _, loss, summary, learning_rate = self.session.run([self.train_step, self.loss, self.summary_op, self.learning_rate], feed_dict={self.inputs: inputs, self.labels: labels})
        else:
            _, loss, learning_rate = self.session.run([self.train_step, self.loss, self.learning_rate], feed_dict={self.inputs: inputs, self.labels: labels})
            summary = None
        return loss, summary, learning_rate


    def get_embeddings(self, normalized=False):
        """ Returns the word embeddings (normalized if normalized is True).
        Not sure if normalization is a good thing to do...
        """
        embeddings = None
        if normalized:
            embeddings = self.session.run(self.normalized_embeddings)
        else:
            embeddings = self.session.run(self.embeddings)
        return embeddings


    def most_similar(self, words):
        """ Words is an array of words. Returns the most similar word for each word of the array.
        """
        return self.session.run(self.most_similar_words, feed_dict={self.words_for_similarity: words})


    def save(self, path):
        """ Serialize the model with its parameters at a given path.
        """

        self.saver.save(self.session, path)

        # Write the parameters
        with open('{p}.parameters'.format(p=path), 'w') as f:
            json.dump(self.parameters, f)


    @staticmethod
    def build(path, session):
        """ Build the network from the path it has been serialized to.
        """

        # Read the parameters and build the model
        with open('{0}.parameters'.format(path), 'r') as f:
            parameters = json.load(f)
        model = Word2Vec(session, parameters)

        # Restore the session
        model.saver.restore(session, path)

        return model
