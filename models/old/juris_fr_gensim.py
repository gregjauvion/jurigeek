
from datetime import datetime
from data.law_data import dump_juris_fr, Reader
from gensim.utils import simple_preprocess
from gensim.models.word2vec import Word2Vec
from gensim.models.doc2vec import Doc2Vec, TaggedDocument
from models.nlp_evaluation import get_2d_embeddings
from utils.connect_utils import GetDbConnectionArgs
from itertools import imap
import logging
import argparse
import MySQLdb
import numpy as np
import json
import os



def dump_data(dump_path):
    # Dump some data locally
    for i in range(0, 200000, 2000):
        print i
        dump_juris_fr({'PK_ID': [i, i+2000]}, dump_path)


def get_data(dump_path, limit=None):
    # Build the document iterator
    reader = Reader(dump_path, limit=limit) if limit!=None else Reader(dump_path)
    return imap(lambda x: TaggedDocument(simple_preprocess(json.loads(x[1][:-1])['text']), str(x[0])), reader)


# def word2vec(dump_path, save_path, size):
#   data = imap(lambda x: x.words, get_data(dump_path))
#   model = Word2Vec(size=size)
#   model.build_vocab(data)
#   for i in range(20):
#       print i
#       model.train(data, total_examples=model.corpus_count, epochs=1)
#   model.save(save_path)


def doc2vec(dump_path, save_path, model_params, limit=None):
    data = lambda : get_data(dump_path, limit=limit)
    model = Doc2Vec(**model_params["hyperparams"])
    model.build_vocab(data())
    for i in xrange(model_params['epochs']):
        print i
	#We keep the loop in order to keep the ability to change the learning rate
        model.train(data(), total_examples=model.corpus_count, epochs=1)
    model.save(save_path)
    return np.mean(model.score( [' '.join(a[0]) for a in data()] )) ##IMPORTANT : at 0, to handle


def doc2vec_grid(data_selectors_list, dump_path,save_path,  model_params_list, limit=None, save_run_to_db=False):
    '''End to End training and saving'''
    #First we call data and we put it into file
    for data_selectors in data_selectors_list:
	if not os.path.isfile(dump_path):
	    dump_juris_fr(data_selectors, dump_path, True)
	for model_params in model_params_list:
    	    score = doc2vec(dump_path, save_path, model_params,  None)
	if save_run_to_db:
	    InsertModelResultsIntoDb(save_path, data_selectors, model_params, score)


def InsertModelResultsIntoDb(save_path, data_selectors, model_params, score):
    '''Construct a generator to inject onto db'''
    #We flatten params dict first, by putting epochs added to hyperparams
    all_params = model_params['hyperparams']
    all_params['epochs'] = model_params['epochs']

    #Now we flatten data selectors params
    if 'PK_ID' in data_selectors:
	all_params['PK_ID_INF'],  all_params['PK_ID_SUP']  = data_selectors['PK_ID'][0], data_selectors['PK_ID'][1]
    if 'DATE' in data_selectors: 
	all_params['DATE_MIN'], all_params['DATE_MAX']= datetime.strftime(data_selectors['DATE'],'%Y-%m-%d'), datetime.strftime(data_selectors['DATE'],'%Y-%m-%d')
    if 'JURIDICTION' in data_selectors: all_params['JURIDICTION'] = data_selectors['JURIDICTION']
    if 'EXT_ID' in data_selectors: all_params['EXT_IDS'] = '/'.join(data_selectors['EXT_ID'])

    all_params['MODEL_PATH'] = os.path.abspath(save_path)
    all_params['SCORE'] = score

    #We finally insert Run date
    all_params["TS_RUN"] = datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M:%S" )

    inserted_keys = [k.upper() for k in  all_params.keys()]
    inserted_values = (v for v in all_params.values())
    qry = " INSERT INTO DOC2VEC_RUNS  (" +",".join(inserted_keys)+")"

    placeholder ="("+  ','.join(['%s' for _ in inserted_keys]) + ")"
    qry = qry + "VALUES" +  placeholder
    
    db = MySQLdb.connect(**GetDbConnectionArgs('models'))
    cursor = db.cursor()
    cursor.execute(qry, inserted_values)
    cursor.close()
    db.commit()
    db.close()

    


if __name__=='__main__':
    logging.basicConfig(filename='/var/log/model_learning.log', level=logging.INFO, format='%(asctime)s %(message)s')
    # Define the command-line arguments parser
    parser = argparse.ArgumentParser()
    parser.add_argument('--model')
    parser.add_argument('--path-to-data')
    parser.add_argument('--path-to-model')
    args = parser.parse_args()

    if args.model=='word2vec':
        # TODO
        pass
    elif args.model=='doc2vec':
	model_params = {"hyperparams":{"size":100, "window":5, "min_count":5, "alpha":.025, 'hs':1, 'negative':0}, "epochs":1}
        #logging.info('Learning doc2vec model: data path = {d}, model dump path = {m}'.format(d=str(args.path_to_data), m=str(args.path_to_model)))
        #doc2vec(args.path_to_data, args.path_to_model, size, limit=None)
        #logging.info('Grid learning doc2vec model: data path = {d}, model dump path = {m}'.format(d=str(args.path_to_data), m=str(args.path_to_model)))
	data_selectors = {'PK_ID': [0, 1000]}
        doc2vec_grid([data_selectors], args.path_to_data, args.path_to_model, [model_params], None, True)
        logging.info('Learning finished.')
