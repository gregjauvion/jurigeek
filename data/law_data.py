import sqlite3
import MySQLdb
from contextlib import closing
from datetime import datetime
from data.parser import JurisFrData, JurisEurData, LawFrData
from utils.connect_utils import GetDbConnectionArgs, GetLawDbPath
import requests
import numpy as np
import logging
import json

DB_DETAILS = GetDbConnectionArgs()

JURIS_FR_TABLE = '_JURISPRUDENCE_FR'
JURIDICTIONS = ['ADMINISTRATIF', 'CONSTIT', 'JUDICIAIRE']

JURIS_EUR_TABLE = '_JURISPRUDENCE_EUR'
LAW_TABLE = 'articles'


def sqlite3_request(request):
    """ Executes MySQL request, ensuring that connection and cursor are closed.
    """
    with closing(sqlite3.connect(GetLawDbPath() )) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute(request)
            return cur.fetchall()

def mysql_request(request):
    """ Executes MySQL request, ensuring that connection and cursor are closed.
    """
    with closing(MySQLdb.connect(**DB_DETAILS)) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute(request)
            return cur.fetchall()


def get_law_fr(selectors):
    """ Returns a list of french jurisprudences.
    """

    # Create the where conditions
    wheres = []
    if 'DATE_DEBUT' in selectors:
        date_inf, date_sup = selectors['DATE_DEBUT']
        date_inf_str, date_sup_str = datetime.strftime(date_inf, '%Y-%m-%d'), datetime.strftime(date_sup, '%Y-%m-%d')
        wheres.append('(date_debut >= "{inf}" AND date_debut < "{sup}")'.format(inf=date_inf_str, sup=date_sup_str))
    if 'cid' in selectors:
        wheres.append('({0})'.format(' OR '.join(map(lambda x:'cid = "{0}"'.format(x), selectors['cid']))))
    if 'etat' in selectors:
        wheres.append('({0})'.format(' OR '.join(map(lambda x:'etat = "{0}"'.format(x), selectors['etat']))))
    if 'dossier' in selectors:
        wheres.append('({0})'.format(' OR '.join(map(lambda x:'dossier = "{0}"'.format(x), selectors['dossier']))))

    request = "select substr(cid, 9) as pk_id,  'https://www.legifrance.gouv.fr/affichTexte.do?cidTexte=' || cid as URL , group_concat(bloc_textuel, ' ') as HTML,   min(date_debut) as date_debut, cid from {table}{where} group by 1".format(table=LAW_TABLE, where='' if len(wheres)==0 else ' WHERE '+ 'AND '.join(wheres))
    return sqlite3_request(request)


def get_juris_fr(selectors):
    """ Returns a list of french jurisprudences.
    selectors is a dict to be able to filter with the following fields:
    - PK_ID: list of pk_id_inf, pk_id_sup
    - DATE: list of date_inf, date_sup
    - JURIDICTION: list of the juridictions to keep
    If a key is not specified, no filter is applied.
    """

    # Create the where conditions
    wheres = []
    if 'PK_ID' in selectors:
        pk_id_inf, pk_id_sup = selectors['PK_ID']
        wheres.append('(PK_ID >= {inf} AND PK_ID < {sup})'.format(inf=str(pk_id_inf), sup=str(pk_id_sup)))
    if 'DATE' in selectors:
        date_inf, date_sup = selectors['DATE']
        date_inf_str, date_sup_str = datetime.strftime(date_inf, '%Y-%m-%d'), datetime.strftime(date_sup, '%Y-%m-%d')
        wheres.append('(DATE >= "{inf}" AND DATE < "{sup}")'.format(inf=date_inf_str, sup=date_sup_str))
    if 'JURIDICTION' in selectors:
        wheres.append('({0})'.format(' OR '.join(map(lambda x:'JURIDICTION = "{0}"'.format(x), selectors['JURIDICTION']))))
    if 'EXT_ID' in selectors:
        wheres.append('({0})'.format(' OR '.join(map(lambda x:'EXT_ID = "{0}"'.format(x), selectors['EXT_ID']))))

    request = "SELECT PK_ID, URL, JURIDICTION, HTML, EXT_ID FROM {table}{where}".format(table=JURIS_FR_TABLE, where=' WHERE ' + ' AND '.join(wheres))
    return mysql_request(request)


def get_juris_eur(selectors):
    wheres = []
    if 'PK_ID' in selectors:
        pk_id_inf, pk_id_sup = selectors['PK_ID']
        wheres.append('(PK_ID >= {inf} AND PK_ID < {sup})'.format(inf=str(pk_id_inf), sup=str(pk_id_sup)))
    request = "SELECT PK_ID, EXT_ID, NOM_PARTIES, MATIERE, AFFAIRE, JURIDICTION, DATE, URL, HTML FROM {table}{where}".format(table=JURIS_EUR_TABLE, where='' if len(wheres)==0 else ' WHERE ' + ' AND '.join(wheres))
    return mysql_request(request)


def dump_law_fr(selectors, filename, dump_perim=False):

    # Retrieve data from database
    print 'Retrieve data...'
    data = get_law_fr(selectors)

    parsed_data = []
    for d in data:
        try:
            pk_id,  url,  html, date_debut, cid = d
            parsed_data.append({'pk_id': pk_id, 'text': LawFrData(html).text})
        except:
            print 'Error in parsing, id={0}'.format(str(d[0]))

    print 'Writing in file...'
    with open(filename, 'a') as f:
        for d in parsed_data:
            f.write(json.dumps(d) + '\n')
    
    if dump_perim:
        with open(filename+".perim.json", 'a') as f:
            json.dump(selectors, f)
        print 'Dump finished.'

    return

def dump_juris_fr(selectors, filename, dump_perim = False):
    """ Dump the result of get_juris_fr(selectors) in the file.
    If the file exists already, it will append the new content at the end.
    """

    # Retrieve data from database
    print 'Retrieve data...'
    data = get_juris_fr(selectors)

    print 'Writing in file...'
    with open(filename, 'a') as f:
        for pk_id, url, juridiction, html, ext_id in data:
            try:
                parsed = JurisFrData(html)
                d = parsed.get_dict()
                d.update({'pk_id': pk_id, 'url': url, 'juridiction': juridiction, 'ext_id': ext_id})
                f.write(json.dumps(d) + '\n')
            except:
                print 'Error in parsing, id={0}'.format(str(pk_id))

    if dump_perim:
    	with open(filename+".perim.json", 'a') as f:
    	    json.dump(selectors, f)
        print 'Dump finished.'

    return


def dump_juris_eur(selectors, filename, dump_perim=False):

    # Retrieve data from database
    print 'Retrieve data...'
    data = get_juris_eur(selectors)

    parsed_data = []
    for d in data:
        try:
            pk_id, _, nom_parties, matiere, affaire, juridiction, date, url, html = d
            parsed_data.append({'pk_id': pk_id, 'text': JurisEurData(html).text})
        except:
            print 'Error in parsing, id={0}'.format(str(d[0]))

    print 'Writing in file...'
    with open(filename, 'a') as f:
        for d in parsed_data:
            f.write(json.dumps(d) + '\n')
    
    if dump_perim:
        with open(filename+".perim.json", 'a') as f:
            json.dump(selectors, f)
        print 'Dump finished.'

    return


class Reader():
    """An iterable object to read a file.
    """
    def __init__(self, filename, limit=np.inf):
        self.filename = filename
        self.limit = limit

    def __iter__(self):
        with open(self.filename) as f:
            for e, l in enumerate(f):
                if e % 10000 == 0:
                    logging.info('{0} lines treated.'.format(str(e)))
                if e >= self.limit:
                    break
                yield e, l


###
# Some tests
###

if __name__=='__main__':
    
    # Some tests with selections
    data = get_juris_fr({'PK_ID': [0, 100]})
    dump_law_fr({'etat': ['VIGUEUR'], 'dossier':['TNC_en_vigueur', 'CODE_en_vigueur'] }, 'law_file')

    # Filter on dates
    data_filtered = get_juris_fr({'PK_ID': [0, 1000], 'DATE': [datetime(2017,07,04), datetime(2017,07,10)]})
    dates = sorted([i[3] for i in data_filtered])

    # Dump the data
    dump_juris_fr({'PK_ID': [0, 100]}, 'dump_test_file')
    dump_juris_fr({"EXT_ID" :["CETATEXT000034833587"]}, 'dump_test_file2', True)

    # Juris EUR test
    data = get_juris_eur({'PK_ID': [0, 100]})
    dump_juris_eur({'PK_ID': [0, 100]}, 'dump_juris_eur_test')
