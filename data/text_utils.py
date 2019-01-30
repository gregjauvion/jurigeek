# -*- coding: utf-8 -*-

import re
from nltk.corpus import stopwords
from collections import Counter

# TO DO : AMEND LIST OF STOP WORDS
#Maybe with global top words taken all over the documents
##Recognize named entities would be a nice fit
STOP_WORDS =  set(stopwords.words('french'))
STOP_WORDS.update(['ainsi', 'le', 'la', 'les', 'tout', 'tous', u'décisions', u'arrêtés', u'dispositions', u'arrêt', u'ce', u'cette'])
STOP_WORDS.update(['justice', 'code', 'droit', 'droits', 'juge', 'mme','administratif', 'administrative', 'conseil', 'tribunal', 'ordonnance', 'contrat', u'considérant', 'article'])
STOP_WORDS.update(['cour', 'appel', 'mm.', 'loi', 'dossier', 'jugement', 'conclusions', u'décision', u'lieu', u'arrêt', 'etat', 'articles'])
STOP_WORDS.update(['janvier', u'février', u'mars', u'avril', u'mai', u'juin', u'juillet', u'août', u'septembre', u'octobre', u'novembre', u'décembre'])

def NaiveGetTopWords(text, stop_words, N):
    '''Take Most common words out of an already parsed text'''
    words = [w for w in re.split("[, \-!?:']+", text.encode('utf-8').decode('utf-8').lower()) if w not in stop_words  and len(w)>2 and not w.isdigit() ]
    return dict(Counter(words).most_common(N))


if __name__== '__main__':
    with open('/home/mehdi/repos/jurigeek/dump_test_file') as f : texts = f.readlines()
    import json
    import random
    FinalDict = json.loads(texts[random.randint(0, len(texts))])
    topwords_inputs = {'text':FinalDict['text'], 'stop_words':STOP_WORDS, 'N':20}
    print NaiveGetTopWords(**topwords_inputs)
