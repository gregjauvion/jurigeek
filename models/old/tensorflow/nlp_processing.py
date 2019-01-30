
import gensim
from collections import Counter
import numpy as np


def build_vocabulary(dataset, vocabulary_size):
    """ Builds a vocabulary formed with the most common words in the dataset.
    Dataset is a list of lines; which are processed using gensim.utils.simple_preprocess function.

    Returns:
    - the vocabulary, i.e. mapping between words and indices. All words which are not among the most frequent are grouped under the word '#UNKNOWN', which has the index 0. Other words are sorted by decreasing counts.
    - the reverse vocabulary
    - the counts, i.e. the number of times each word appears
    """

    # Counts the number of times each word appears
    counts = Counter()
    for line in dataset:
        for w in gensim.utils.simple_preprocess(line):
            counts[w] += 1

    # Builds the vocabulary
    vocabulary = {'#UNKNOWN': 0}
    for e, w in enumerate(sorted(counts, key=lambda x:-counts[x])[:(vocabulary_size-1)]):
        vocabulary[w] = e + 1

    # Build the counts with the words of the vocabulary only
    counts_vocabulary = Counter()
    for w, c in counts.iteritems():
        if w in vocabulary:
            counts_vocabulary[w] += c
        else:
            counts_vocabulary['#UNKNOWN'] += c

    return vocabulary, {i: w for w, i in vocabulary.iteritems()}, counts_vocabulary


def batch_generator(dataset, batch_size, window_size=2):
    """ Generate batches from a dataset (which is a list of sentences).
    
    The batches are generated the following way:
    - each sentence is processed into tokens
    - for each token t, (2 * window_size) observations are built, where the label is the token, and the input is one of the word in the window

    It is implemented as a generator which loops indefinitely on the dataset.
    """

    inputs = np.empty((batch_size,), dtype=object)
    labels = np.empty((batch_size, 1), dtype=object)

    i_dataset, i_batch = 0, 0
    while True:
        # Get the current line
        if i_dataset==len(dataset):
            i_dataset = 0
        tokens = gensim.utils.simple_preprocess(dataset[i_dataset])
        i_dataset += 1

        # Build all (input,label) for the tokens of the sentence
        for e, target in enumerate(tokens):
            # Get all inputs for this token
            for w in range(max(e - window_size, 0), min(e + window_size + 1, len(tokens))):
                if w != e:
                    #inputs[i_batch] = target
                    #labels[i_batch, 0] = tokens[w]
                    inputs[i_batch] = tokens[w]
                    labels[i_batch, 0] = target

                    i_batch += 1
                    if i_batch==batch_size:
                        # Return a copy of inputs and labels
                        i_batch = 0
                        yield (np.copy(inputs), np.copy(labels))



###
# Some tests
###

if __name__=='__main__':

    # Build a vocabulary on some sentences
    dataset = [
        'Hello, this sentence is a test of sentence with a lot of times the word sentence.',
        'Here, the word word appears a lot to make appear word in the vocabulary.'
    ]
    vocabulary, reverse_vocabulary, counts = build_vocabulary(dataset, 5)
    print 'Vocabulary:', vocabulary
    print 'Reverse vocabulary:', reverse_vocabulary
    print 'Counts:', counts

    # Build some batches
    batches = batch_generator(dataset, 10, window_size=2)
    for i in range(10):
        inputs, labels = batches.next()
        print '\nNew batch:'
        for input, label in zip(inputs, labels):
            print input, label

