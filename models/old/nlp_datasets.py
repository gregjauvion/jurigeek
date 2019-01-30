
from nltk.corpus import reuters
import os
import urllib
from six.moves import urllib as urllib_bis
import zipfile


###
# This module defines methods to get NLP datasets.
###

def nltk_reuters():
    """ Returns Reuters dataset given in nltk.
    List of (document, labels), labels being a list of labels for the document.
    """

    documents = []
    for i in reuters.fileids():
        documents.append((reuters.raw(i), reuters.categories(i)))
    return documents


def stanford_sentiment(dl_path):
    """ Stanford sentiment dataset, giving sentences with a sentiment score between 0 and 1.
    """

    # Download the dataset if it is not found
    url = 'http://nlp.stanford.edu/~socherr/stanfordSentimentTreebank.zip'
    path = '{0}/stanfordSentimentTreebank.zip'.format(dl_path)
    if os.path.exists(path):
        print 'Dataset has been found.'
    else:
        print 'Downloading dataset...'
        urllib.urlretrieve(url, path)

    # Open the dataset and build a list of (sentence, score)
    with zipfile.ZipFile(path) as z:
        # Build the dictionary giving each sentence from its id
        id_sentence = {}
        with z.open('stanfordSentimentTreebank/dictionary.txt') as f:
            for l in f:
                sentence, id_ = l.split('|')
                id_sentence[int(id_)] = sentence
        # Dictionary giving sentiment score from each id
        id_score = {}
        with z.open('stanfordSentimentTreebank/sentiment_labels.txt') as f:
            f.next()
            for l in f:
                id_, score = l.split('|')
                id_score[int(id_)] = float(score)

    return [(id_sentence[i], id_score[i]) for i in sorted(id_sentence)]


def mattmahoney_dc(dl_path):
    """ Dataset found here : http://mattmahoney.net/dc/
    Used in https://github.com/tensorflow/tensorflow/blob/r1.1/tensorflow/examples/tutorials/word2vec/word2vec_basic.py
    """

    # Step 1: Download the data.
    url = 'http://mattmahoney.net/dc/'
    filename = 'text8.zip'
    path = '{0}/{1}'.format(dl_path, filename)
    if not os.path.exists(path):
        filename, _ = urllib_bis.request.urlretrieve(url + filename, path)
    # Extract the downloaded file
    with zipfile.ZipFile(path) as f:
        data = f.read(f.namelist()[0])

    # Split in sentences of 100.000 words
    words = data.split(' ')
    splits = [words[(i*100000):((i+1)*100000)] for i in range(1+len(words)/100000)]

    return map(lambda x:' '.join(x), splits)




###
# Test
###

if __name__=='__main__':
    
    print '-- Reuters dataset --'
    r = nltk_reuters()
    print 'Nb documents: {0}'.format(str(len(r)))
    print 'A few lines:'
    for i in range(3):
        print r[i]

    print '\n-- Stanford dataset --'
    s = stanford_sentiment('/Users/jjauvion/Data')
    print 'Nb documents: {0}'.format(str(len(s)))
    print 'A few lines:'
    for i in range(3):
        print s[i]






