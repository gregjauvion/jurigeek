#!/usr/bin/env python
# -*- coding: utf-8 -*- 

import os, sys
sys.path.append(os.getcwd())

import json
import logging
import numpy as np
from models.nlp_keywords import Vocabulary, Keywords
from data.law_data import Reader
from itertools import imap

NB_KEYWORDS = 25
VOCAB_LIMIT = 5E-6

class TfidfApi():
    """ Simple API to the tf-idf model.
    It is built with the path to a corpus, i.e a file where each line is a json with keys 'pk_id' and 'text'.
    The tf-idf model is built on the corpus, and the keywords for all documents in the corpus are stored in memory.
    """
    def __init__(self, path_to_data, nb_keywords=NB_KEYWORDS):
        logging.info('Loading model on path {0}'.format(path_to_data))

        self.nb_keywords = nb_keywords
        
        # Build tf-idf model
        data_text = lambda :imap(lambda x:json.loads(x[1][:-1])['text'], Reader(path_to_data))
        data_id = lambda :imap(lambda x:json.loads(x[1][:-1])['pk_id'], Reader(path_to_data))
        logging.info('Building vocabulary')
        self.vocabulary = Vocabulary.build(data_text, window_size=3, limit=VOCAB_LIMIT)
        logging.info('Building model')
        self.model = Keywords(self.vocabulary, data_text)

        # Build the keywords for all documents of the corpus
        logging.info('Building documents keywords')
        self.keywords = []
        for text, id_ in zip(data_text(), data_id()):
            self.keywords.append((id_, self.model.get_keywords(text, self.nb_keywords)))


    def most_similar(self, document, nb_similar):
        """ Returns the most similar documents based on keywords similairities.
        """

        doc_keywords = self.model.get_keywords(document, self.nb_keywords)
	logging.info("Document '{d}', Keywords '{k}'".format(d=document, k=str(doc_keywords)))

        similarities = [Keywords.similarity(doc_keywords, kws) for id_, kws in self.keywords]
        similars = sorted(enumerate(similarities), key=lambda x:-x[1])[:nb_similar]

        return [(s, self.keywords[i][0], self.set_tokens(self.keywords[i][1])) for i, s in similars]


    def set_tokens(self, keywords):
        """ Replace ids by tokens and keep the first keyword only.
        """

        ret = {}
        for i, j in keywords.iteritems():
            kw = ' '.join(self.vocabulary.get_token(j[1][0]))
            ret[kw] = j[0]

        return ret


    def get_keywords(self, document):
        """ Returns the keywords for a given document.
        """

        return self.set_tokens(self.model.get_keywords(document, self.nb_keywords))


###
# Tests
###

if __name__=="__main__":
    path = '/Users/jjauvion/Data/juris_fr_dump_test'
    api = TfidfApi(path)
    q1 = u'Le juge administratif peut-il moduler les pénalités de retard appliquées par la personne publique ? Dans quelles conditions ?'
    q2 = u'Comment le juge contrôle la régularité de la méthode de notation des offres?'
    a1 = api.most_similar(q1, 10)
    a2 = api.most_similar(q2, 10)
