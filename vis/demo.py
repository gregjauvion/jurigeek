# coding: utf-8

import os, sys
import argparse
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from server.model_client import ModelClient
from data.parser import JurisFrData
from data.law_data import mysql_request
from flask import Flask, flash, redirect, render_template, request, session, abort, url_for, jsonify
import urllib
import json
import random
import numpy as np
from datetime import datetime
import config

app = Flask(__name__)

# List of eligible (user, pwd). Should be in a database.
USERS = [
    ('dauser', 'pp'),
    ('rachel', 'rachel'),
    ('test', 'test')
]

def CheckLoginPwd(login, pwd):
    return (login, pwd) in USERS

def PrettyServerInfo(elt):
    """ Build a dictionary with the interesting data for each document.
    elt has the following form:
    [3.641189356552878e-05, 123894, {u'proc\xe8s verbal': 0.43843716831971297, ...}]
    """
    res = {}
    res['similarity'] = elt[0]
    res['PK_ID'] = elt[1]
    res['keywords'] = sorted(elt[2], key=lambda x:-elt[2][x])
    return res

def GetUrlsFromPkIds(pk_ids_list, table_name= '_JURISPRUDENCE_FR' ):
    pk_ids = ', '.join(map(str, pk_ids_list))
    qry = 'SELECT PK_ID, URL, HTML FROM '+ table_name + ' WHERE PK_ID in (' + pk_ids + ')'
    return  mysql_request(qry)


@app.route('/')
def home():
    if not session.get('logged_in'):
        return render_template('login.html')
    else:
        return redirect("/textPage")

@app.route('/login', methods=['POST'])
def do_admin_login():
    if CheckLoginPwd(request.form['username'] ,  request.form['password']):
        session['logged_in'] = True
    else:
        flash('wrong password!')
    return home()


@app.route('/textPage', methods =  ['GET', 'POST'])
def GetTextInput():
    input_types =  ['link', 'text']
    if request.method == 'POST':
        # Get the input text and retrieves most similar documents
        doc_client = ModelClient(config.SERVER_IP, config.JURIS_FR_PORT)

        input_text = request.form['case_study'].encode('utf8')
        ##Depending on whether its a link or a text, we process differently
        response = doc_client.most_similar(input_text, config.NB_SIMILAR)

        pretty_response = [PrettyServerInfo(elt) for elt in response['most_similar']]
        UrlsFromPkIds = GetUrlsFromPkIds([res['PK_ID'] for res in pretty_response])
        pk_id_url_html = {int(i): (u, h) for i, u, h in UrlsFromPkIds}
       
        # Second Loop to finalize
        similar_documents = []
        for i, res in enumerate(pretty_response):
            # Keep documents with similarity>0 only
            if res['similarity']>0:
                url, html = pk_id_url_html[res['PK_ID']]
                data = JurisFrData(html)
                date = datetime.strftime(data.date, '%d/%m/%Y') if data.date is not None else ''
                administration = data.administration.replace(u'Ã‰', u'É') if data.administration is not None else ''
                similar_documents.append({'keywords': res['keywords'][:15], 'similarity':res['similarity'], 'url':url, 'date': date, 'administration': administration})

        return render_template('similars.html', similar_documents=enumerate(similar_documents), input=input_text.decode('utf8'))
    else:
        return render_template('similars.html')


@app.route("/logout")
def logout():
    session['logged_in'] = False
    return home()


if __name__ == "__main__":
    app.secret_key = os.urandom(12)
    app.run(debug=True,host='0.0.0.0')
