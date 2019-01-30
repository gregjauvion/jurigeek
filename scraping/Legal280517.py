
# coding: utf-8

# In[ ]:

#get_ipython().magic(u'reset')


# In[70]:



from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys
import numpy as np
from parser import Parser
import pandas as pd
import requests
from sqlalchemy import types
from sqlalchemy import create_engine
import grequests
from bs4 import BeautifulSoup
import time
import sys

# In[71]:

##Utilitaire


def GetUrlFromElement(element):
    return element.find_element_by_tag_name('a').get_attribute('href')

def init_driver():
        driver = webdriver.Chrome( executable_path='/home/mehdi/gecko/chromedriver')
        #driver = webdriver.Chrome( executable_path='/usr/bin/google-chrome')
        #driver = webdriver.PhantomJS(executable_path='/home/mehdi/gecko/phantomjs')
        driver.wait = WebDriverWait(driver, 5)
        return driver

def ParseMe(html):
    parser=Parser()
    parser.parse(html)
    return {'header':parser.header, 'text':parser.text, 'title':parser.title}

class QueryClicker:
    """Initiates a driver and makes query"""

    def __init__(self, dates):
        self.driver=init_driver()
        self.driver.get("https://www.legifrance.gouv.fr/initRechJuriAdmin.do")
        self.StartDate=dates['StartDate']
        self.EndDate=dates['EndDate']

    def _get_ymd(self):
        """Simple Internal Methods to split a YYYY-MM-DD formatted Date"""
        d=dict()
        d['SplittedStartDate']=self.StartDate.split('-')[0], self.StartDate.split('-')[1]
        d['SplittedEndDate']=self.EndDate.split('-')[0], self.EndDate.split('-')[1]
        return d


    def MutateDriver(self):
        """Main Driver Call, here. It makes the call and gives back the header"""
        champDateDecision1A=self.driver.wait.until(EC.presence_of_element_located((By.NAME, 'champDateDecision1A')))
        champDateDecision1A.send_keys( self._get_ymd()['SplittedStartDate'][0] )
        
        checkboxPeriode=self.driver.wait.until(EC.presence_of_element_located((By.NAME, 'checkboxPeriode')))
        checkboxPeriode.click()
        champDateDecision2A=self.driver.wait.until(EC.presence_of_element_located((By.NAME, 'champDateDecision2A')))
        champDateDecision2A.send_keys( self._get_ymd()['SplittedEndDate'][0] )
    
        Rechercher=self.driver.wait.until(EC.presence_of_element_located((By.NAME, 'bouton')))
        #champDateDecision1M=Select(self.driver.wait.until(EC.presence_of_element_located((By.NAME, 'champDateDecision1M')))).select_by_value(self._get_ymd()[1])
        Rechercher.click()
        
    def GetTotalNumberOfResults(self):
            Text=self.driver.find_element_by_id('center').find_element_by_tag_name('h3').text
            return int(Text.split(': ')[1].split(' document')[0])

        

class HtmlFetcher:
        """This class aims at getting multiple URLS and Fetch it into Multiple HTML Content"""
        def __init__(self, UrlList):
                self.UrlList=UrlList
                self.HTMLPages=list()

        def FetchHtmlContent(self):
                #self.HTMLPages=[ requests.get(x).text for x in self.UrlList]
                ContentNotOk=True
		t0=time.time()
                while ContentNotOk:
                    rs = (grequests.get(u) for u in self.UrlList)
                    gets=grequests.map(rs, stream=False)
                    #We check if Content is taken
                    CheckContentTaken=np.sum([r is None for r in gets])
                    ContentNotOk=CheckContentTaken!=0
                    print "Length of Content is %s" % (CheckContentTaken)
                    if ContentNotOk: print "Hmmm, let's try to catch these urls again..."
                self.HTMLPages=[r.text for r in gets]
                for r in rs: r.close()
                print "Core HTML Fetching Took : %s" % (time.time() - t0)


class  DbInserter:
    
    def __init__(self, urlList, htmlPages, table_name="_TEST"):
        t0=time.time()
        self.l=[ParseMe(page) for page in htmlPages]
        print "Core HTML Parsing Took : %s" % (time.time() - t0)
        self.Headers=[(k['header']).encode('utf-8').decode('utf-8') for k in self.l]
        self.Titles=[(k['title']).encode('utf-8').decode('utf-8') for k in self.l]
        self.Texts=[(k['text']).encode('utf-8').decode('utf-8') for k in self.l]
        self.TextIds=[x.split('idTexte=')[1].split('&fastReqId=')[0] for x in urlList]
        self.TableName=table_name
        #print "Textids: %d / url list: %d / headers : %d / texts : %d / titles : %d" % (len(self.TextIds), len(urlList), len(self.Headers), len(self.Texts), len(self.Titles))
        self.Final=pd.DataFrame({'TEXT_ID':self.TextIds, 'URL':urlList, 'HEADER':self.Headers,'TEXT':self.Texts,'TITLE':self.Titles })

    def Insert(self):
        #sql = create_engine("mysql://%s:%s@%s/%s" % ('juriste', 'Jur1G33k', '192.168.1.21:8457', 'juris'))
        sql = create_engine("mysql://%s:%s@%s/%s" % ('juriste', 'Jur1G33k', '192.168.1.18:8453', 'juris'))
        #sql = create_engine("mysql://%s:%s@%s/%s" % ('juriste', 'Jur1G33k', '86.252.44.179:8457, 'juris'))
        db=sql.connect()
        Dtype={'TEXT_ID':types.CHAR(255), 'URL':types.TEXT, 'TITLE':types.TEXT, 'HEADER':types.TEXT, 'TEXT':types.UnicodeText}
        t0=time.time()
        self.Final.to_sql(if_exists='append', con=db, index=False,  name=self.TableName, dtype=Dtype)
        print "Core DB Insertion Took : %s" % (time.time() - t0)
        db.close()
        


        
class Results:
    """Main class of our work : gets Results from the query driver, checks number of pages & gets you Urls"""
    def __init__(self, query):
        self.driver=query.driver
        self.TreatedPagesList=list()
        self.UrlList=list()

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
        fetcher=HtmlFetcher(self.UrlList)
        print "fetch First"
        fetcher.FetchHtmlContent()
        #sql = create_engine("mysql://%s:%s@%s/%s" % ('juriste', 'Jur1G33k', '192.168.1.21:8457', 'juris'))
        #db=sql.connect()
        print "Now Insert into DB"
        DbInserter( self.UrlList, fetcher.HTMLPages, table_name="_ADMINISTRATIF").Insert()

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
                                        self.TreatedPagesList.append(d['TreatedPageNumber'])
                                self.driver=ThePage.driver
                                if self.driver.name=='chrome':
                                    ##This is a very important line, in order to go back to the main page
                                    self.driver.switch_to_window(MainWindow) 
                                if len(self.UrlList)>=chunk:
                                    print "Preparing to fetch and insert"
                                    self.FetchAndInsert()
                                    self.UrlList=[]
                                    
                        self._GetPageNumbersList()[-1].find_element_by_link_text('>').click()
                except NoSuchElementException:
                        ContinueToClick=False
                        print "Preparing to fetch and insert"
                        self.FetchAndInsert()
                        self.UrlList=[]
                        self.driver.quit()
        
            
class SingleResultsPage:
        """This class stands for one result page displayed. From this page we will get URLS. The way of getting (or not) URL Results depends on Link Nature"""
        def __init__(self, Results, PageLink, MainPageNumber):
                self.driver=Results.driver
                self.CurrentPage=PageLink
                self.TreatedPagesList=Results.TreatedPagesList
                self.MainPageNumber=MainPageNumber
                              
        def GetUrlsFromOnePage(self):
            """Getting ol tag + li css selector seems to give sound results """
            ResultsDisplayed=self.driver.wait.until(EC.presence_of_element_located((By.TAG_NAME, 'ol'))).find_elements_by_css_selector('li')
            return map(GetUrlFromElement, ResultsDisplayed)

        def RetrievalAttemptOnPage(self):
                """This Method gets one result page, from the link. We might first distinguish if we already are on Current link (no need to click)
                So We Skip it, or we are on a forwad/before link, either.
                If Page is not skipped, we take its content thanks to the above method GetUrlsFromOnePage"""
                if self.CurrentPage.text=='<':
                        #print "Skipping Precedent Page"
                        return -1
                
                elif self.CurrentPage.text==self.MainPageNumber:
                        if int(self.CurrentPage.text) % 50==0:
                            print "Now Treating Page ", self.CurrentPage.text
                        return {'Urls':self.GetUrlsFromOnePage(), 'TreatedPageNumber':self.CurrentPage.text}

                elif self.CurrentPage.text=='>':
                        #print "Skipping Forward Page (We'll get to it when we arrive)"
                        return -1

                else:
                        if int(self.CurrentPage.text) % 100==0:
                            print "Now Treating Page ", self.CurrentPage.text
                        AttemptOnPage=self.CurrentPage.find_element_by_tag_name('a')
                        PageToBeClicked=AttemptOnPage.get_attribute('href').split('page=')[1]
                        if PageToBeClicked in self.TreatedPagesList: return -1
                        if self.driver.name=='chrome':
                                AttemptOnPage.send_keys(Keys.CONTROL+Keys.RETURN)
                                self.driver.find_element_by_tag_name('body').send_keys(Keys.CONTROL+Keys.TAB)
                                self.driver.switch_to_window(self.driver.window_handles[-1])
                                d={'Urls':self.GetUrlsFromOnePage(), 'TreatedPageNumber':PageToBeClicked}
                                self.driver.close()
                        else:
                                NewDriver=init_driver()
                                NewDriver.get(AttemptOnPage.get_attribute('href'))
                                ResultsDisplayed=NewDriver.wait.until(EC.presence_of_element_located((By.TAG_NAME, 'ol'))).find_elements_by_css_selector('li')
                                d={'Urls':map(GetUrlFromElement, ResultsDisplayed), 'TreatedPageNumber':PageToBeClicked}
                                NewDriver.quit()
                        
                        return d
                    


# In[ ]:

if __name__=="__main__":
    print "LETS GO !!!"
    import time
    t0=time.time()
    d={'StartDate':'2014-05-01', 'EndDate':'2016-05-01'}
    query=QueryClicker(d)
    query.MutateDriver()
    TotalNumberOfResults=query.GetTotalNumberOfResults()
    print 'Seems to be %s Results to catch' % (TotalNumberOfResults)
    Results=Results(query)
    Results.GetAllElements(chunk=int(sys.argv[1]))
    
    print "Integrity Check..."
    
    if len(np.unique(Results.UrlList))==TotalNumberOfResults:
            print 'Sounds Good, Dude !!!'
            Results.driver.quit()
            print "Duh, There's a problem. %s unique Urls fetched vs. %s Displayed" % (len(np.unique(Results.UrlList)), TotalNumberOfResults)


    print time.time() - t0


# In[57]:



# In[ ]:



