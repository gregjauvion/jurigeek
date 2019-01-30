#!/usr/bin/env python
# -*- coding: utf-8 -*- 

from gensim.utils import deaccent, to_unicode, simple_preprocess
from gensim.models import TfidfModel
from nltk.stem.snowball import FrenchStemmer
from collections import Counter, defaultdict
from itertools import imap
import numpy as np
import logging
import json
import re


###
# Define a custom preprocessor which keeps apostrophes (in conseil d'état for example)
# To do this, we need to redefine 'simple_preprocess' and 'tokenize' functions in gensim.utils'
###

CUSTOM_TOKENIZER = re.compile('([\w\d\-\']+)', re.UNICODE)

def custom_tokenize(text, lowercase=False, deacc=False, errors="strict", to_lower=False, lower=False):
    """ Same function as gensim one except we use CUSTOM_TOKENIZER to split the text.
    """
    lowercase = lowercase or to_lower or lower
    text = to_unicode(text, errors=errors)
    if lowercase:
        text = text.lower()
    if deacc:
        text = deaccent(text)
    for match in CUSTOM_TOKENIZER.finditer(text):
        yield match.group()

def custom_preprocess(doc, deacc=False, min_len=2, max_len=30):
    """ Same function as gensim one except we use custom_tokenize instead of tokenize.
    """
    tokens = [
        token for token in custom_tokenize(doc, lower=True, deacc=deacc, errors='ignore')
        if min_len <= len(token) <= max_len and not token.startswith('_')
    ]
    return tokens


###
# Define a custom stemmer. It is far from perfect but improves the documents similairy based on keywords.
# Existing stemmers are : nltk.stem.snowball.FrenchStemmer and nltk.stem.SnowballStemmer but they are too long.
# This stemmer is not used for the moment but could be useful in the future.
###

# This stemmer works the following way : all suffixes in the list SUFFIXES are removed if they are at the end of a word (for words of size >2)
SUFFIXES = ['e', 's', u'é', u'és', u'ée', u'ées', 'es', 'i', 'is', 'ie', 'ies', 'er', 'oir', 'ir', 'ai', 'ais', 'erai', 'eraient', 'erais', 'ent', 'ion', 'ions', 'ation', 'ations', 'atif', 'atifs', 'ative', 'atives',
        'ant', 'ants', 'ante', 'antes', u'ité', u'ités', 'ents', 'te', 'tes', 'eux', 'euse', 'euses', 'eant', 'eants', 'dre']
CUSTOM_STEMMING = re.compile('^(.{2}.*?)(%s)$' % ('|'.join(SUFFIXES)))

def repl(m):
    if m:
        return m.groups()[0]

def custom_stem(token):
    return re.sub(CUSTOM_STEMMING, repl, token)

def custom_stem_text(text):
    return ' '.join(map(custom_stem, simple_preprocess(text)))


###
# A custom vocabulary class
###

class Vocabulary():
    """ A vocabulary is formed with:
    - size_tokens_id: gives the mapping token <-> id for each window size
    - id_tokens: gives the mapping id <-> token (we do not need it per window size)
    - counts: the count for each token
    """

    UNKNOWN = '#UNKNOWN'

    def __init__(self, counts):

        sorted_tokens = sorted(counts, key=lambda x:-counts[x])
        self.id_tokens = {0: (Vocabulary.UNKNOWN,)}
        self.size_tokens_id = defaultdict(lambda :Counter())
        self.size_tokens_id[1][(Vocabulary.UNKNOWN,)] = 0

        for e,t in enumerate(sorted_tokens):
            self.id_tokens[e+1] = t
            self.size_tokens_id[len(t)][t] = e+1


    def get_tokens(self, document):
        """ Returns the tokens corresponding to a document.
        """
        tokens = []
        tokens_1 = custom_preprocess(document)
        nb = len(tokens_1)
        max_size = max(self.size_tokens_id.keys())
        e = 0
        while e<nb:
            found = False
            # Look for the token by decreasing size
            for s in range(min(max_size, nb-e), 0, -1):
                t = tuple(tokens_1[e:(e+s)])
                if t in self.size_tokens_id[s]:
                    tokens.append(t)
                    e += s
                    found = True
                    break
            if not found:
                tokens.append((Vocabulary.UNKNOWN,))
                e += 1
        return tokens


    def get_tokens_ids(self, document):
        return map(lambda x:self.get_id(x), self.get_tokens(document))


    def get_id(self, token):
        """ Return the id corresponding to a token (None if token does not exist).
        """
        if token in self.size_tokens_id[len(token)]:
            return self.size_tokens_id[len(token)][token]
        return None


    def get_token(self, id):
        """ Return the token corresponding to an id.
        """
        return self.id_tokens[id]


    @staticmethod
    def build(data_func, window_size=1, limit=5E-6):
        """Build a vocabulary.
        - data_func: function to return the data
        - window_size: the size of tokens considered is kept between 1 and window_size words
        - limit: the threshold (relative to total number of tokens) under which tokens are not kept and are mapped to #UNKNOWN
        """

        # Get the counts of the tokens, we use a LRU cache otherwise we could get memory errors
        tokens_counts = Counter()
        for e, l in enumerate(data_func()):
            if e%10000==0:
                logging.info('Vocabulary size: {0}'.format(str(len(tokens_counts))))
            tokens = custom_preprocess(l)
            for size in range(window_size, 0, -1):
                size_tokens = [tuple(tokens[i:(i+size)]) for i in range(len(tokens)-window_size+1)]
                for t in size_tokens:
                    if Vocabulary._validate(t):
                        tokens_counts[t] += 1

        # Delete the tokens under the threshold and add the UNKNOWN key in counts dict
        logging.info('Number of tokens before filtering: {0}'.format(str(len(tokens_counts))))
        nb_tokens = sum(len(custom_preprocess(l)) for l in data_func())
        threshold = limit * nb_tokens
        to_delete = [(t,c) for t,c in tokens_counts.iteritems() if c<threshold]
        for t,c in to_delete:
            del tokens_counts[t]
        logging.info('Number of tokens after filtering: {0}'.format(str(len(tokens_counts))))

        # Return the vocabulary
        return Vocabulary(tokens_counts)


    STOP_WORDS = set(['et', 'de', 'du', 'des', 'd\'un', 'd\'une', 'le', 'la', 'les', 'lui', 'qui', 'que', 'quoi', 'qu\'il', 'qu\'elle', 'qu\'ils', 'qu\'elles', 'qu\'en', 'qu\'au', 'qu\'aux', 'sur', 'pour', 'par', 'ce', 'cette', 'ces',
        'celui', 'celles', 'me', 'en', 'ne', 'au', 'ainsi', 'si', 'il', 'elle', 'ils', 'elles', 'ou', 'un', 'une',
        'avoir', 'est', 'sont', 'ont', 'avoir', 'n\'est', 'n\'a', 's\'est', 'sera', u'être', u'été', 'son', 'sa', 'ses', 'se', 'aux', 'dans',
        'duquel', 'lequel', 'laquelle', 'afin', 'notamment', 'lorsque', u'dés', 'pas', 'n\'y', 'dit', 'tant', 'avec', 'sans', 'cependant', 'des', 'entre', 'leur', 'leurs'])

    @staticmethod
    def _validate(token):
        """ Returns true if a token must be kept, false otherwise.
        """
        if len(token)==1:
            return True
        else:
            # If the token begins or ends with a stop word, we remove the token
            if token[0] in Vocabulary.STOP_WORDS or token[-1] in Vocabulary.STOP_WORDS:
                return False
        return True


###
# Class to determine keywords
###

class Keywords():
    """ This object is built with a vocabulary and a function returning the dataset.
    It builds a tfidf model on the corpus.
    Then, calling get_keywords(document, n) returns the n highest-ranked words in the document.
    """

    def __init__(self, vocabulary, data_func):
        self.vocabulary = vocabulary

        # Build a tf-idf model based on the dataset
        transformed_dataset = imap(lambda x: self._counts(x), data_func())
        self.tfidf = TfidfModel(transformed_dataset)

        self.stemmer = FrenchStemmer()


    def get_keywords(self, document, nb_keywords):
        """ Returns the nb_keywords highest-ranked words in the document.
        A dict is returned:
        - key: stemmed_word (stemmed with our custom stemmer)
        - values: list (tf-idf score, list of non-stemmed words). We keep non-stemmed words because we want to display non-stemmed words.
        The token ids are set to decrease memory footprint.

        The scores are normalized, to ensure sum(score**2) = 1
        """
        keywords_ids = sorted(self.tfidf[self._counts(document)], key=lambda x:-x[1])[:nb_keywords]

        ret = {}
        for id_, score in keywords_ids:
            token = self.vocabulary.get_token(id_)
            stemmed_token = ' '.join(tuple(map(self.stemmer.stem, token)))
            if stemmed_token in ret:
                ret[stemmed_token][0] += score
                ret[stemmed_token][1].append(id_)
            else:
                ret[stemmed_token] = [score, [id_]]

        # Normalize the scores
        norm = np.sqrt(sum(i[0]**2 for i in ret.values()))
        if norm>0:
            for token in ret:
                ret[token][0] /= norm

        return ret


    def _counts(self, document):
        """ Returns list of (t, c), where t is a token and c the number of times it appears in the document.
        """
        counts = Counter()
        for t in self.vocabulary.get_tokens_ids(document):
            counts[t] += 1

        return counts.items()


    @staticmethod
    def similarity(kw_1, kw_2):
        """ Computes a similarity between two documents based on tf-idf scores.
        The similarity score is the cosinus between kw_1 and kw_2 tokens.
        kw_1 and kw_2 are dicts returned by get_keywords function.
        """
        sim = 0
        for token in kw_1:
            if token in kw_2:
                sim += kw_1[token][0] * kw_2[token][0]

        return sim


###
# Some tests
###

if __name__=='__main__':
    from data.law_data import Reader
    # Read file
    dump_path = '/Users/jjauvion/Data/juris_fr_dump'
    data = lambda :imap(lambda x:json.loads(x[1][:-1])['text'], Reader(dump_path, limit=100))
    # Build vocabulary
    vocabulary = Vocabulary.build(data, window_size=3, limit=1E-4)
    kw = Keywords(vocabulary, data)
    # Return some keywords
    kws = []
    for e,d in enumerate(data()):
        if e>20:
            break
        kws.append(kw.get_keywords(d, 20))
    # Test similarity measure
    print Keywords.similarity(kws[0], kws[1])