

# -*- coding: utf-8 -*-

# In[99]:

import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys
from utils.connect_utils import GetDbConnectionArgs
import numpy as np

import grequests
import time
import sys
import locale
import datetime

locale.setlocale(locale.LC_ALL, 'fr_FR.UTF-8')


# In[26]:

def init_driver(driverPath):

        driver = webdriver.Chrome( executable_path = driverPath)
        driver.wait = WebDriverWait(driver, 5)
        driver.path  = driverPath
        return driver


# In[265]:

class QueryClicker:
    """Initiates a driver and makes query"""

    def __init__(self, driverPath, juridiction , dates):
        self.driver=init_driver(driverPath)
        self.driver.get(juridiction["url"])
        self.StartDate=dates['StartDate']
        self.EndDate=dates['EndDate']
        self.juridiction = juridiction['name']


    def MutateDriver(self):
        """Main Driver Call, here. It makes the call and gives back the header"""
        StartDate = self.StartDate.split('-')
        EndDate = self.EndDate.split('-')
        champDateDecision1A=self.driver.wait.until(EC.presence_of_element_located((By.NAME, 'champDateDecision1A')))
        champDateDecision1A.send_keys( StartDate[0] )
        
        checkboxPeriode=self.driver.wait.until(EC.presence_of_element_located((By.NAME, 'checkboxPeriode')))
        checkboxPeriode.click()
        champDateDecision2A=self.driver.wait.until(EC.presence_of_element_located((By.NAME, 'champDateDecision2A')))
        champDateDecision2A.send_keys( EndDate[0] )
    
        Rechercher=self.driver.wait.until(EC.presence_of_element_located((By.NAME, 'bouton')))
        Select(self.driver.wait.until(EC.presence_of_element_located((By.NAME, 'champDateDecision1M')))).select_by_value(StartDate[1])
        Select(self.driver.wait.until(EC.presence_of_element_located((By.NAME, 'champDateDecision2M')))).select_by_value(EndDate[1])
        Select(self.driver.wait.until(EC.presence_of_element_located((By.NAME, 'champDateDecision1J')))).select_by_value(StartDate[2])
        Select(self.driver.wait.until(EC.presence_of_element_located((By.NAME, 'champDateDecision2J')))).select_by_value(EndDate[2])
        self.driver.execute_script("return arguments[0].scrollIntoView(true);", Rechercher)
        Rechercher.click()
        
    def GetTotalNumberOfResults(self):
            Text=self.driver.find_element_by_id('center').find_element_by_tag_name('h3').text
            return int(Text.split(': ')[1].split(' document')[0])

        


# In[298]:

class HtmlFetcher:
        """This class aims at getting multiple URLS and Fetch it into Multiple HTML Content, and tuple generator"""
        def __init__(self, UrlList, LinksTitleList, juridiction):
                self.UrlList=UrlList
                self.HTMLPages=[]
                self.juridiction = juridiction
                self.dateList = []
                self.LinksTitleList  = LinksTitleList 

        def _FetchDateFromTitles(self, link_title):
            try: 
            	if self.juridiction == 'ADMINISTRATIF':
            	    dInitial= link_title.replace('\t','').replace('\n', '').split(',')[2].strip().encode('utf-8')
		    date_format = "%d/%m/%Y"
            	elif self.juridiction == 'CONSTIT':
            	    dInitial = link_title.replace('\t','').replace('\n', '').split('-')[2].strip().encode('utf-8') #=> FORMAT A TRAITER
		    date_format = "%d %B %Y"
            	elif self.juridiction == 'JUDICIAIRE':
		    ##little bit trickier
            	    Phrase = link_title.replace('\t','').replace('\n', '').split(',')
		    position = 1 if "Cour d'appel" in Phrase[0] else (2 if (("mixte" in Phrase[1]) or ("Assembl" in Phrase[1])) else 3) # => mixte stands for 'chambre mixte'
	            dInitial= Phrase[position].strip().encode('utf-8')
 		    date_format = "%d %B %Y"
                
            	d = datetime.datetime.strptime(dInitial, date_format)
            	final = datetime.date.strftime(d, '%Y-%m-%d')
            
		return final 
	    except:
		return None

        def _FetchExtId(self, url): return url.split('idTexte=')[1].split("&")[0]
            
        def FetchContentToBeInserted(self):
                ContentNotOk=True
                t0=time.time()
                while ContentNotOk:
                    rs = (grequests.get(u) for u in self.UrlList)
                    gets=grequests.map(rs, stream=False)
                    #We check if Content is taken
                    CheckContentTaken=np.sum([r is None for r in gets])
                    ContentNotOk=CheckContentTaken!=0
                    #print "Length of Content is %s" % (CheckContentTaken)
                    if ContentNotOk: print "Hmmm, let's try to catch these urls again..."
                #self.HTMLPages=[r.content.encode('utf-8').decode('utf-8') for r in gets]
                #self.HTMLPages=[r.text.encode('utf-8') for r in gets]
                #self.HTMLPages=[unicode(r.text.encode(r.encoding).decode(r.encoding))  for r in gets]
                self.HTMLPages=[r.content.decode(r.encoding).encode('utf-8')  for r in gets]
                for r in rs: r.close()
                for idx, html_page in enumerate(self.HTMLPages):
		    #(EXT_ID, JURIDICTION, DATE, URL, HTML)
		    url = self.UrlList[idx]
		    #print self._FetchExtId(url)
                    yield (self._FetchExtId(url),  self.juridiction,  self._FetchDateFromTitles(self.LinksTitleList[idx]), url,  html_page)
			 



import MySQLdb

class  DbInserter:
    
    #def __init__(self, ToBePushedIntoDb, table_name="_TEST"):
    def __init__(self, ToBePushedIntoDb, query="INSERT IGNORE INTO _JURISPRUDENCE_FR (EXT_ID, JURIDICTION, DATE, URL, HTML) VALUES (%s, %s, %s, %s, %s)"):
        #t0=time.time()
        self.query=query
        self.ToBePushedIntoDb=ToBePushedIntoDb

    def Insert(self):
        t0 = time.time()
        db = MySQLdb.connect(**GetDbConnectionArgs())
       
	FinalData = list(self.ToBePushedIntoDb) 
        qry = str(self.query)
        cursor = db.cursor()
        cursor.executemany(qry, FinalData)
        cursor.close()
        db.commit()
        print "Core DB Insertion Took : %s" % (time.time() - t0)
        db.close()


# In[300]:

class Results:
    """Main class of our work : gets Results from the query driver, checks number of pages & gets you Urls"""
    def __init__(self, query):
        self.driver=query.driver
        self.TreatedPagesList=list()
        self.UrlList=list()
        self.LinksTitleList = list()
        self.juridiction = query.juridiction

    def _GetPageNumbersList(self):
        """Getting Number Of Pages Web Elements. At some point, it can raise a timeout exception.
        Hence, we must refresh the driver for some longer time"""
        
        try:
            Pagination=self.driver.wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'pagination'))).find_elements_by_css_selector('li')
        except TimeoutException:
            print "Waiting for server to answer. Let it sleep for a couple of minutes"
            time.sleep(120)
            self.driver.wait= WebDriverWait(self.driver, 100)
            Pagination=self.driver.wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'pagination'))).find_elements_by_css_selector('li')
            
        return Pagination
    
    def FetchAndInsert(self):
        """Fetch Pages, Insert, and update"""
        fetcher=HtmlFetcher(self.UrlList, self.LinksTitleList, self.juridiction)
        print "fetch First"
        ToBePushedIntoDb = fetcher.FetchContentToBeInserted()
        #EXT_ID, JURIDICTION, DATE, URL, HTML
        print "Now Insert into DB " 
           

        DbInserter( ToBePushedIntoDb = ToBePushedIntoDb).Insert()

    def GetAllElements(self, chunk=2000):
        """We have to handle multiple pages results. In order to do that, we create a clicker, tagged by the '>' element, until we dont find it anymore.
        When we dont find it, we stop on clicking ;-) """
        ContinueToClick=True
        while ContinueToClick:
                try:
                        for PageLink in self._GetPageNumbersList():
                                MainWindow=self.driver.current_window_handle
                                CurrentMainPageNumber=self.driver.current_url.split('page=')[1]
                                ThePage=SingleResultsPage(self, PageLink, CurrentMainPageNumber)
                                self.driver=ThePage.driver
                                d=ThePage.RetrievalAttemptOnPage()
                                if d!=-1:
                                        self.UrlList.extend(d['Urls'])
                                        self.LinksTitleList.extend(d['LinksTitles'])
                                        self.TreatedPagesList.append(d['TreatedPageNumber'])
                                self.driver=ThePage.driver
                                if self.driver.name=='chrome':
                                    ##This is a very important line, in order to go back to the main page
                                    self.driver.switch_to_window(MainWindow) 
                                if len(self.UrlList)>=chunk:
                                    print "Preparing to fetch and insert"
                                    self.FetchAndInsert()
                                    self.UrlList=[]
                                    self.LinksTitleList = []
                                    
                        self._GetPageNumbersList()[-1].find_element_by_link_text('>').click()
                        
                except NoSuchElementException:
                        ContinueToClick=False
                        print "Preparing to fetch and insert"
                        self.FetchAndInsert()
                        self.UrlList=[]
                        self.LinksTitleList = []
                        self.driver.quit()
        
            


# In[301]:

class SingleResultsPage:
        """This class stands for one result page displayed. From this page we will get URLS. The way of getting (or not) URL Results depends on Link Nature"""
        def __init__(self, Results, PageLink, MainPageNumber):
            self.driver=Results.driver
            self.CurrentPage=PageLink
            self.TreatedPagesList=Results.TreatedPagesList
            self.MainPageNumber=MainPageNumber
            self.juridiction = Results.juridiction

        def GetUrlsFromOnePage(self):
            """Getting ol tag + li css selector seems to give sound results """
            ResultsDisplayed=self.driver.wait.until(EC.presence_of_element_located((By.TAG_NAME, 'ol'))).find_elements_by_css_selector('li')
            return [elt.find_element_by_tag_name('a').get_attribute('href') for elt in ResultsDisplayed]
        
        def GetUrlsAndLinksTitlesFromOnePage(self):
            """Getting ol tag + li css selector seems to give sound results """
            ResultsDisplayed=self.driver.wait.until(EC.presence_of_element_located((By.TAG_NAME, 'ol'))).find_elements_by_css_selector('li')
            Urls=[elt.find_element_by_tag_name('a').get_attribute('href') for elt in ResultsDisplayed]
            LinksTitles = [elt.find_element_by_tag_name('a').get_attribute('innerHTML') for elt in ResultsDisplayed]
            return {'Urls':Urls, 'LinksTitles':LinksTitles}
        

        def RetrievalAttemptOnPage(self):
            """This Method gets one result page, from the link. We might first distinguish if we already are on Current link (no need to click)
            So We Skip it, or we are on a forwad/before link, either.
            If Page is not skipped, we take its content thanks to the above method GetUrlsFromOnePage"""


            if self.CurrentPage.text=='<':
                    #print "Skipping Precedent Page"
                    return -1

            elif self.CurrentPage.text==self.MainPageNumber:
                    if self.CurrentPage.text in self.TreatedPagesList: return -1
                    
                    if int(self.CurrentPage.text) % 50==0:
                        print "Now Treating Main Page %s" % (self.CurrentPage.text)
                    UrlsAndLinks = self.GetUrlsAndLinksTitlesFromOnePage()
                    d = {}
                    d['Urls']=UrlsAndLinks['Urls']
                    d['TreatedPageNumber'] = self.CurrentPage.text
                    d['LinksTitles']= UrlsAndLinks['LinksTitles']
                    
                    return d

            elif self.CurrentPage.text=='>':
                    #print "Skipping Forward Page (We'll get to it when we arrive)"
                    return -1

            else:
                    if int(self.CurrentPage.text) % 50==0:
                        print "Now Treating Page %s, which is not the main " % (self.CurrentPage.text)
                        
                    AttemptOnPage=self.CurrentPage.find_element_by_tag_name('a')
                    PageToBeClicked=AttemptOnPage.get_attribute('href').split('page=')[1]

                    if PageToBeClicked in self.TreatedPagesList: return -1
                    
                    AttemptOnPage.send_keys(Keys.CONTROL+Keys.RETURN)
                    self.driver.find_element_by_tag_name('body').send_keys(Keys.CONTROL+Keys.TAB)
                    self.driver.switch_to_window(self.driver.window_handles[-1])
                    d = {}
                    d['TreatedPageNumber'] = PageToBeClicked
                    UrlsAndLinks = self.GetUrlsAndLinksTitlesFromOnePage()
                    d['Urls']=UrlsAndLinks['Urls']
                    d['LinksTitles']= UrlsAndLinks['LinksTitles']
                    self.driver.close()

                    return d
                    

if __name__=="__main__":
    with open(sys.argv[1]) as conf:
            queryConf = json.load(conf)
    print "LETS GO !!!"
    import time
    t0=time.time()
    query=QueryClicker(driverPath=queryConf['driverPath'], juridiction = queryConf['juridiction'],  dates = queryConf['dates'])
    query.MutateDriver()
    TotalNumberOfResults=query.GetTotalNumberOfResults()
    print 'Seems to be %s Results to catch' % (TotalNumberOfResults)
    Results=Results(query)
    Results.GetAllElements(chunk=int(queryConf['chunk']))

    print "Integrity Check..."
    if len(np.unique(Results.UrlList))==TotalNumberOfResults:
            print 'Sounds Good, Dude !!!'
            Results.driver.quit()
    else: 
            print "Duh, There's a problem. %s unique Urls fetched vs. %s Displayed" % (len(np.unique(Results.UrlList)), TotalNumberOfResults)

    print time.time() - t0


