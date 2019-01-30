
# coding: utf-8

import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys
import numpy as np
import pandas as pd
import requests
import grequests
from bs4 import BeautifulSoup
import time
import sys
import MySQLdb
import datetime
from ScrapAndStore import QueryClicker, init_driver, DbInserter
from itertools import chain


class QueryClickerCuria(QueryClicker):
    """Initiates a driver and makes query"""

    def MutateDriver(self):
        """Main Driver Call, here. It makes the call and gives back the header"""
    	dateFromInput = self.driver.wait.until(EC.presence_of_element_located((By.ID, 'mainForm:dateFromInput')))
    	dateToInput = self.driver.wait.until(EC.presence_of_element_located((By.ID, 'mainForm:dateToInput')))
    	dateFromInput.send_keys(datetime.datetime.strftime(datetime.datetime.strptime(self.StartDate, '%Y-%m-%d'), '%d/%m/%Y'))
    	dateToInput.send_keys(datetime.datetime.strftime(datetime.datetime.strptime(self.EndDate, '%Y-%m-%d'), '%d/%m/%Y'))
    	self.driver.wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'btn_search'))).click()


    def GetTotalNumberOfResults(self):
            Text=self.driver.find_element_by_id('center').find_element_by_tag_name('h3').text
            return int(Text.split(': ')[1].split(' document')[0])



def GetElementsByColumn(Documents, ElementName):
    """This function takes text from table results in Curia. Warning on table_cell_aff which is defined twice, so we distinguish text and non text (just want clas       s with text on this one"""
    texts = [t.text.replace("\n", " ").encode('utf-8').strip() for t in Documents.find_elements_by_class_name(ElementName)]
    l = list()
    for elt in texts:
	if ElementName == 'table_cell_aff' and elt=='':
	    pass
        else:
            if ElementName =='table_cell_date':
	        elt = datetime.datetime.strptime(elt, '%d/%m/%Y') 
	    yield elt

def PrepareDataToPush(TableDocuments, ExpectedNumberOfLines):
    '''Prepare data in appropriate form'''

    #Since we took elements by columns, cause it was faster, now we have to rearrange our results into a generator of lines
    PreparedDict = {k:GetElementsByColumn(TableDocuments, v) for k,v in MetaElements.iteritems()}

    ###Prepare Other elements
    UrlListOnePage=[l.find_element_by_css_selector('a').get_attribute('href') for l in TableDocuments.find_elements_by_class_name('table_cell_links_eurlex')]
    PreparedDict['URL'] = (u for u in UrlListOnePage)
    PreparedDict['EXT_ID'] = (u.split('docid=')[1].split('&')[0] for u in UrlListOnePage)
    rs = (grequests.get(u) for u in UrlListOnePage)
    gets=grequests.map(rs, stream=False)
    PreparedDict['HTML'] = (g.text.encode('utf-8') for g in gets if gets is not None) 
    
    for _ in range(ExpectedNumberOfLines): 
        t = tuple()
        for k in PreparedDict.keys():t=t+(PreparedDict[k].next(),)
	yield t


if __name__=="__main__":
    with open(sys.argv[1]) as conf:
	    queryConf = json.load(conf)
    print "LETS GO !!!"
    import time
    t0=time.time()
    QueryInputs = {'driverPath':queryConf['driverPath'], 'juridiction': queryConf['juridiction'],  'dates':queryConf['dates']}
    query=QueryClickerCuria(**QueryInputs )
    query.MutateDriver()
    ContinueToClick = True
    NotTheGoodShape = True
    CurrentChunkElementsLength = 0
    Results = (_ for _ in ()) ##Empty generator init
    MetaElementsKeys =  ['AFFAIRE', 'JURIDICTION', 'DATE', 'NOM_PARTIES', 'MATIERE' ]
    MetaElementsVals =  ['table_cell_aff', 'table_cell_doc', 'table_cell_date', 'table_cell_nom_usuel', 'table_cell_links_curia' ]
    MetaElements = dict(zip(MetaElementsKeys, MetaElementsVals))
    qry = '''INSERT IGNORE INTO _JURISPRUDENCE_EUR  (EXT_ID, URL, NOM_PARTIES, MATIERE, HTML, AFFAIRE, DATE, JURIDICTION) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)''' 
    while ContinueToClick:
        try:
	    if NotTheGoodShape:
    		query.driver.wait.until(EC.presence_of_element_located((By.ID, 'mainForm:j_id56'))).click()
		NotTheGoodShape = False
		
    	    TableDocuments = query.driver.wait.until(EC.presence_of_element_located((By.ID, 'listeDocuments'))).find_element_by_tag_name('tbody')
	    t0 = time.time()
	    PageElementsLength = 20 ##DIRTY

	    SinglePageResults = list(PrepareDataToPush(TableDocuments, PageElementsLength))
	    Results = chain(Results, SinglePageResults)
            CurrentChunkElementsLength = PageElementsLength + CurrentChunkElementsLength

	    if CurrentChunkElementsLength>=int(queryConf['chunk']):
		DbInserter( ToBePushedIntoDb = Results, query = qry).Insert()
		Results =  (_ for _ in ()) 
		CurrentChunkElementsLength = 0

	    NextPageButton = query.driver.find_element_by_xpath("//a[img/@src='http://curia.europa.eu/juris/img/common/btn_next.gif']")
	    query.driver.execute_script("return arguments[0].scrollIntoView(true);", NextPageButton)
	    NextPageButton.click()
			
	except NoSuchElementException:
	    ContinueToClick = False
	    DbInserter( ToBePushedIntoDb = Results, query = qry).Insert()
	    Results =  (_ for _ in ()) 
	    CurrentChunkElementsLength = 0
    
    query.driver.quit()
    print time.time() - t0


