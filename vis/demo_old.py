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
import datetime
import config

app = Flask(__name__)


def CheckLoginPwd(login, pwd):
    return login == u'dauser' and pwd == 'pp'

def PrettyServerInfo(elt):
    """ Build a dictionary with the interesting data for each document.
    elt has the following form:
    [3.641189356552878e-05, 123894, {u'proc\xe8s verbal': 0.43843716831971297, ...}]
    """
    print elt
    res = {}
    res['similarity'] = elt[0]
    res['PK_ID'] = elt[1]
    res['keywords'] = sorted(elt[2], key=lambda x:-elt[2][x])
    return res

def GetUrlsFromPkIds(pk_ids_list, table_name= '_JURISPRUDENCE_FR' ):
    pk_ids = ', '.join(map(str, pk_ids_list))
    qry = 'SELECT PK_ID, URL FROM '+ table_name + ' WHERE PK_ID in (' + pk_ids + ')'
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
        if request.form['input_types']=='link':
            #html = urllib.urlopen(input_text).read()
            #data = JurisFrData(input_text)
            text = data.text.encode('utf8')
            response = doc_client.most_similar(text, config.NB_SIMILAR)
        else:
            response = doc_client.most_similar(input_text, config.NB_SIMILAR)

        pretty_response = [PrettyServerInfo(elt) for elt in response['most_similar']]
        UrlsFromPkIds = GetUrlsFromPkIds([res['PK_ID'] for res in pretty_response])
        pk_id_url = {int(i): u for i, u in UrlsFromPkIds}
       
        ##Second Loop to finalize
        for i, res in enumerate(pretty_response):
            url = pk_id_url[res['PK_ID']]
            keywords =  ' , '.join(res['keywords'])
    	    response['most_similar'][i] = {'document': {'resume' : keywords}, 'similarity':res['similarity'], 'url':url }

        return render_template('collapsible.html', similar_documents=enumerate(response['most_similar']), case_study = input_text.decode('utf8'), input_types = input_types )
    else:
        return render_template('collapsible.html', input_types = input_types )


@app.route("/logout")
def logout():
    session['logged_in'] = False
    return home()


if __name__ == "__main__":
    app.secret_key = os.urandom(12)
    app.run(debug=True,host='0.0.0.0')
