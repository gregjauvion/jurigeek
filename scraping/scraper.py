from __future__ import division
from pyvirtualdisplay import Display
import time
import json
from selenium import webdriver
#from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys
#from utils.connect_utils import GetDbConnectionArgs
from multiprocessing import Pool
from selenium.webdriver.chrome.options import Options
import grequests
import requests
from requests.packages.urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

import numpy as np
import datetime
import logging
#logging.basicConfig(level = logging.DEBUG)
import abc
import os
import sys



#######INPUT CLASS#######
class Input(object):
    '''This class is meant to be flexible later, in order to put text, voices, etc'''
     pass

class DateInput(Input):
    def __init__(self, **kwargs):
        self.start_date = kwargs['dates']['StartDate']
        self.end_date = kwargs['dates']['EndDate']
        self.source_url = kwargs['juridiction']["url"]
        self.juridiction = kwargs['juridiction']["name"]
    
    def __repr__(self):
        affiche += "\nPerimeter :" +"\n"
        affiche += "Oldest Date :"+ self.start_date + " / Last Date :"+self.end_date +"\n"
        affiche += "Juridiction : " + self.juridiction
        return affiche



######CRAWLER CLASS#####
class Crawler(object):
    '''Job of this class : with an emulated browser, takes a query as input, crawl listings, and gives a bunch of results.
    Results here are two kinds : 
     - list of meta-informations about text
     - list of urls to scrap (later or not)'''
    #BS for taking abstract static method

    def __init__(self, **kwargs):
        '''Please note that the query clicker takes input but is not instanciated until opening'''
        self.driver = None
        assert 'input' in kwargs
        assert 'nb_results_per_listing' in kwargs
        self._driver_path = kwargs['driverPath']
        self.instanciation_time = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H:%M:%S')
        self.activation_time =None
        self.input = Input(**kwargs)
        #Results parameters are initialized
        self._current_listing_number = 0
        self._nb_results_per_listing =kwargs['nb_results_per_listing'] #Abstract
        self._nb_listings =0
        self._nb_results  = 0
    
    @property 
    def nb_results(self): self._nb_results
    
    def update_nb_results(self):raise NotImplementedError("This is an abstract class, dude")

    @property
    def current_listing_number(self):return self._current_listing_number
    
    def update_listing_number(self):
        self._current_listing_number = self.driver.current_url.split('page=')[1].split('&')[0]
    
    def go_to_listing_number(self, listing_num):
        pattern = 'page='+str(listing_num)
        self.update_listing_number()
        new_url = self.driver.current_url.replace('page='+self.current_listing_number, pattern)
        self.driver.execute_script( "window.open()" )
        windows = self.driver.window_handles
        self.driver.switch_to.window(windows[-1])
        self.driver.get(new_url)
        self.update_listing_number()
	#if self._current_listing_number % 10 ==0 and verbose: 
	#    logging.info('Processing listing %d' % (str(listing_num)))

    @property
    def nb_results_per_listing(self):return self._nb_results_per_listing
    
     ##Estimate number of listings to scrap
    @property
    def nb_listings(self): return self._nb_listings
    
    def update_nb_listings(self):
        if self._current_listing_number==1:
            self._nb_listings = self._nb_results//self._nb_results_per_listing
            if self._nb_results % self._nb_results_per_listing > 0: self._nb_listings+=1
    
    def cross_through_listings(self):
        for listing_num in xrange(1,self.nb_listings+1):
            self.go_to_listing_number(listing_num)
            for item in self.populate_current_results_listing():yield item

    def mutate_driver(self):
        '''Overridded afterwards for site specifics'''
        self.fulfill_form()
        self._current_listing_number=1
        
    def __enter__(self):
        '''Based on static method below'''
	os.environ['PATH'] += os.pathsep + self._driver_path
        self.driver = self.init_driver()
	self.driver.wait = WebDriverWait(self.driver, 5)
        self.activation_time = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H:%M:%S')
        self.driver.get(self.input.source_url)

    def __exit__(self, type, value, traceback):
        self.driver.quit()
    
    def __repr__(self):
        affiche = "\nQuery instanciated at :"
        affiche += self.instanciation_time
	if self.activation_time != None: affiche +="and query activated at" + self.activation_time
        affiche += str(self.input)
        return affiche

    
    ###Simple wrappers for driver
    def detect_web_element(self, nature, web_name):
        """Selenium Facilities Wrapper. 
        Only thing that change is the name and nature of element to click, not initial parameters
        So we are taking care once and for all about these value"""
        return self.driver.wait.until(EC.presence_of_element_located((nature, web_name)))
    
    def select_to_web_element(self, nature, web_name, value):
        '''Selenium wrapper as well, for select menus'''
        element = self.detect_web_element(nature, web_name)
        self.driver.execute_script("return arguments[0].scrollIntoView(true);", element) #Element has to be detectable to put sthing on it
        Select(element).select_by_value(value)
    
    def request_to_web_element(self, nature, web_name, value):
        '''Selenium wrapper as well : if unselectable values, we have to send request, named as keys'''
        element = self.detect_web_element(nature, web_name)
        self.driver.execute_script("return arguments[0].scrollIntoView(true);", element) #Element has to be detectable to put sthing on it
        element.send_keys(value)

        
    def get_total_number_of_results(self):raise NotImplementedError("This is an abstract class, dude")
    def get_current_clickable_listings_on_search(self):raise NotImplementedError("This is an abstract class, dude")
    def fulfill_form(self):raise NotImplementedError("This is an abstract class, dude")
    def populate_current_results_listing(self):raise NotImplementedError("This is an abstract class, dude")

    @staticmethod
    def init_driver(driver_type='phantomJS'):
        if driver_type =='phantomJS':
	    return webdriver.PhantomJS()
        elif driver_type=='chrome':
            chrome_options = Options()  
            chrome_options.add_argument("--headless")
            chrome_options.binary_location = '/usr/bin/chromium'
            #All the arguments added for chromium to work on selenium
            chrome_options.add_argument("--no-sandbox") #This make Chromium reachable
            chrome_options.add_argument("--no-default-browser-check") #Overrides default choices
            chrome_options.add_argument("--no-first-run")
            chrome_options.add_argument("--disable-default-apps") 
            display = Display(visible = 0, size = (200,200 )).start()
            return webdriver.Chrome(chrome_options=chrome_options)
        else:
	    raise NotImplementedError('maybe firefox is working, we must try it out')

    def get_html_items(self):
        '''get url input from generator, returns html listings'''
        meta_infos = self.cross_through_listings()
        for result in meta_infos:
            result['ext_id']=self.get_ext_id(result['url'])
	    yield result

    def get_ext_id(self) : raise NotImplementedError('Absract class, dude')
  
    def give_batch_listings(self, max_nb_listings = 20):
        with self:
            self.mutate_driver()
	    queue = tuple(self.get_html_items())
	    return queue

    def scrap_html_batch(self):
        batch_results = self.give_batch_listings()
	batch_links = (x['url'] for x in batch_results)
	print("Inserting in batch..."+str(len(batch_results)))
        records = Scrapper.run(batch_links)
	return records



class JurisFrCrawler(Crawler):


    def fulfill_form(self):
        start_year, start_month, start_day = self.input.start_date.split('-')
        end_year, end_month, end_day = self.input.end_date.split('-')
        #Boolean true if selectable element, false if string
        
        web_elements_dict = {
	    'champDateDecision1A':(start_year, False),
	    'champDateDecision2A':(end_year, False),
	    'champDateDecision1M':(start_month, True),
	    'champDateDecision2M':(end_month, True),
	    'champDateDecision1J':(start_day, True),
	    'champDateDecision2J':(end_day, True)
        }
        #Always click on the period box
        checkboxPeriode=self.detect_web_element('name', 'checkboxPeriode')
        checkboxPeriode.click()
        
        ##Put the inputs into the form
        for key,v in web_elements_dict.iteritems():
            value, is_selectable = v 
            if is_selectable : self.select_to_web_element(nature = 'name', web_name = key, value = value) 
            else : self.request_to_web_element(nature = 'name', web_name = key, value = value) 
        
        Rechercher=self.detect_web_element('name', 'bouton')
        ##Element has to be visible to the driver screen, so we add the following line
        self.driver.execute_script("return arguments[0].scrollIntoView(true);", Rechercher)
        Rechercher.click()
      
    def mutate_driver(self):
        super(JurisFrCrawler, self).mutate_driver()
        self.update_nb_results()
        self.update_nb_listings()
        self.update_listing_number()
        
    def update_nb_results(self):
        Text=self.driver.find_element_by_id('center').find_element_by_tag_name('h3').text
        self._nb_results = int(Text.split(': ')[1].split(' document')[0])
    
    def populate_current_results_listing(self):
        '''Returns one listing into exploitable data. Must return a dict with element keys'''
        
        liste_resultats = self.detect_web_element('tag name', 'ol').find_elements_by_css_selector('li')
        for item in liste_resultats:
            x = item.find_element_by_tag_name('a')
            url = x.get_attribute('href')
            link_title = x.get_attribute('innerHTML')
            yield {'url':url, 'link_title':link_title}

    @staticmethod
    def get_ext_id(url):
        return url.split('idTexte=')[1].split('&')[0]


class JurisEurCrawler(Crawler):
    
    def __init__(self, **kwargs):
        '''We override by adding a good shaping check bookean '''
        super(JurisEurCrawler, self).__init__(**kwargs)
        self.listings_have_good_shape = False

    def mutate_driver(self):
        '''We shape the driver the good way'''
        super(JurisEurCrawler, self).mutate_driver()
        self.put_listings_in_good_shape()
        self.update_nb_results()
        self.update_nb_listings()
        self.update_listing_number()


    def fulfill_form(self):
        self.request_to_web_element('id', 'mainForm:dateFromInput', self.slash_the_date(self.input.start_date))
        self.request_to_web_element('id', 'mainForm:dateToInput', self.slash_the_date(self.input.end_date))
        Rechercher = self.detect_web_element('class name', 'btn_search')
        self.driver.execute_script("return arguments[0].scrollIntoView(true);", Rechercher) 
        Rechercher.click()
 
    
    def update_nb_results(self):
        Text=self.detect_web_element('id', 'nbreResultats').text
        self._nb_results = int(Text.split(' document')[0].strip())
        print self._nb_results

    def populate_current_results_listing(self):
        '''Returns one listing into exploitable data. Must return a dict with element keys'''
        #First, we click on the listing in order to get an easy, parsable way
        #self.detect_web_element('id', 'mainForm:j_id56').click()
        
        #Then we detect the body of the table
        liste_resultats = self.detect_web_element('id', 'listeDocuments').find_element_by_tag_name('tbody')
        element_keys_web_name =  {
            'table_cell_aff':'AFFAIRE',
            'table_cell_doc':'JURIDICTION',
            'table_cell_date':'DATE', 
            'table_cell_nom_usuel':'NOM_PARTIE',
            'table_cell_links_curia':'MATIERE', 
            'table_cell_links_eurlex':'url'
        }
        
        #Parcourt les lignes de la listing
        for line in liste_resultats.find_elements_by_class_name('table_document_ligne'): 
            result = {}
            #Process fields now
            for web_element_name, v in element_keys_web_name.iteritems():
                if v == 'url':
                    result[v]=line.find_element_by_css_selector('a').get_attribute('href')
                else:
                    curr_value=line.find_element_by_class_name(web_element_name).text
                    ##Quelques transfos suivant les cas.
                    if not(curr_value=='') :
                        if v=='DATE':
			    curr_value =  datetime.datetime.strptime(curr_value, '%d/%m/%Y')
		        result[v]=curr_value
            
            yield result

    def cross_through_listings(self):
        '''Overriding parent method, for making it in the good shape before crossing through'''
        #self.update_listing_number()
        self.put_listings_in_good_shape()
        return super(JurisEurCrawler, self).cross_through_listings()

    def put_listings_in_good_shape(self):
        if self.listings_have_good_shape==False:
            MakeTheGoodShape = self.detect_web_element('id', 'mainForm:j_id56')
            self.driver.execute_script("return arguments[0].scrollIntoView(true);", MakeTheGoodShape)
	    MakeTheGoodShape.click()
            self.listings_have_good_shape=True
        
    @staticmethod
    def slash_the_date(x):
        return datetime.datetime.strftime(datetime.datetime.strptime(x, '%Y-%m-%d'), '%d/%m/%Y')


    @staticmethod
    def get_ext_id(url):
        return url.split('docid=')[1].split('&')[0]


####
#EUR LEX IS HARD TO AUTOMIZE, THEREFORE WE HAVE TO TAKE MANUALLY CSVS
####
class LawEurCrawler(Crawler):
    '''Here we face multiple issues. First, one must connect in order to get a limited amount of data (<5Mo). Second, its not paginated
	First solution is here to connect'''
    def mutate_driver(self):
        super(LawEurCrawler, self).mutate_driver()
        self.driver.get("https://ecas.ec.europa.eu/cas/login")
        ##We have to connect as well
        print('we now submit')
        self.request_to_web_element('name', 'username', '[USERNAME]')
        print('we have submmitted')
        submit = self.detect_web_element('name', 'whoamiSubmit')
        self.driver.execute_script("return arguments[0].scrollIntoView(true);", submit)
        submit.click()
        self.request_to_web_element('name', 'password', "[PWD]")
        mpd_submit =  self.detect_web_element('name', '_submit')
        self.driver.execute_script("return arguments[0].scrollIntoView(true);", mpd_submit)
        mpd_submit.click()
        self.driver.get(self.input.source_url)
    
    def fulfill_form(self):
        pass 


class Scrapper(object):
    '''Quite inspired by https://nikomo.fi/2017/08/grequests-asynchronous-requests-in-python/'''
    NUM_SESSIONS = 10
    
    def __init__(self, url_links):
	self.url_links = url_links
     
    def create_sessions(self):
        sessions = [requests.Session() for i in xrange(self.NUM_SESSIONS)]
	retries = Retry(total=5,backoff_factor=0.1,status_forcelist=[500, 502, 503, 504])
        for s in sessions:
            s.mount('http://', HTTPAdapter(max_retries=retries))
            s.mount('https://', HTTPAdapter(max_retries=retries))
        return sessions

    def scrap(self):
        sessions = self.create_sessions()
	html_texts, reqs =[], []
	for i, url in enumerate(self.url_links):
	    reqs.append(grequests.get(url, session=sessions[i % self.NUM_SESSIONS], timeout = 5))
        responses = grequests.map(reqs, size=self.NUM_SESSIONS)
        for response in responses:
            if response.status_code ==200:html_content = response.content.decode(response.encoding).encode('utf-8') 
            else: continue
            html_texts.append(html_content)
	return html_texts


    @classmethod
    def run(cls, url_links):
        scrapper= cls(url_links)
        return scrapper.scrap()


if __name__=='__main__':
    with open(sys.argv[1]) as conf:
        queryConf = json.load(conf)

    t0 = time.time()

    the_input = Input(**queryConf)
    queryConf['input'] = the_input
    queryConf['nb_results_per_listing'] = 20

    t0 = time.time()

    query=JurisEurCrawler(**queryConf)
    html_results = query.scrap_html_batch()
    #query=JurisFrCrawler(**queryConf)
    #query=LawEurCrawler(**queryConf)
    #listings_to_parse = query.give_results()
    print(len(html_results), " ",  time.time() - t0)
    time_per_result = (t1 - t0) / len(html_results)
    print(time_per_result)
    #time.sleep(10)
    #print(html_results[:2])
    #    final_tuple = list(query.cross_through_listings())
    #    print len(final_tuple), query.nb_results, query.nb_listings
    #t1 = time.time()
    #print(time_per_result)
