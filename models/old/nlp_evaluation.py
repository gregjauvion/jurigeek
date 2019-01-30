
import os
import urllib
import zipfile
import numpy as np
import matplotlib.pyplot as plt
from sklearn.manifold import TSNE
from sklearn.decomposition import PCA


def simlex(dl_path):
    """ Simlex is a dataset with word similarities, used to evaluate word embeddings.
    """
    
    # Download the dataset if it is not found
    url = 'https://www.cl.cam.ac.uk/~fh295/SimLex-999.zip'
    path = '{0}/SimLex-999.zip'.format(dl_path)
    if os.path.exists(path):
        print 'Dataset has been found.'
    else:
        print 'Downloading dataset...'
        urllib.urlretrieve(url, path)

    # Open the dataset and build a list of (sentence, score)
    with zipfile.ZipFile(path) as z:
        similarities = []
        with z.open('SimLex-999/SimLex-999.txt') as f:
            print 'Header: ', f.next()
            for l in f:
                w1, w2, _, sim, _, _, _, _, _, _ = l.split('\t')
                similarities.append((w1, w2, float(sim)))

    return similarities


def cosine(e1, e2):
    """ Returns the cosine similarity between vectors e1 and e2.
    """

    return np.dot(e1, e2) / (np.linalg.norm(e1) * np.linalg.norm(e2))


def evaluate(embeddings, similarities):
    """ Evaluate the embeddings, in a dictionary with key=word, value=embedding.
    similarities is the output of function simlex.
    """

    nb_pairs_not_found = 0
    similarities_computed = []
    for w1, w2, sim in similarities:
        if (not w1 in embeddings) or (not w2 in embeddings):
            nb_pairs_not_found += 1
        else:
            e1, e2 = embeddings[w1], embeddings[w2]
            similarities_computed.append((sim/10., cosine(e1, e2)))

    return similarities_computed, nb_pairs_not_found


###
# Some methods to analyze embeddings
###

def plot_embeddings(two_dim_embs, labels, filename=None):
    """ Plots the 2D-embeddings with their labels.
    If filename is None, shows the plot instead of saving it.
    """

    fig = plt.figure(figsize=(8, 8))
    for i, label in enumerate(labels):
        x, y = two_dim_embs[i, :]
        plt.scatter(x, y)
        plt.annotate(label,
            xy=(x, y),
            xytext=(5, 2),
            textcoords='offset points',
            ha='right',
            va='bottom',
            fontsize=8)

    if filename==None:
        plt.show()
    else:
        plt.savefig(filename)
        plt.close()

    return


def get_2d_embeddings(embeddings, pca=True):
    """ Returns the embeddings in a 2D representation.
    """

    dim_reduction = None
    if pca:
        dim_reduction = PCA(n_components=2)
    else:
        dim_reduction = TSNE(perplexity=30, n_components=2, init='pca', n_iter=5000)
    return dim_reduction.fit_transform(embeddings)
