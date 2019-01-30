# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup
from datetime import datetime
import json

MONTHS = {u'janvier': 'January', u'février': 'February', u'mars': 'March', u'avril': 'April', u'mai': 'May', u'juin': 'June',
    u'juillet': 'July', u'août': 'August', u'septembre': 'September', u'octobre': 'October', u'novembre': 'November', u'décembre': 'December'}

class JurisFrData():

    def __init__(self, html):

        # Parse the html to get the parts we are interested in
        soup = BeautifulSoup(html, 'html.parser')
        content = soup.find(id='content')
        title = JurisFrData._prettify(content.find('h2', {'class': 'title'}).get_text()).split(', ')
        # The title is formed the following way: {administration}, {date}, {id}, {Inédit au recueil Lebon}
        self.administration = title[0]
        self.date = None
        while len(title)>1 and JurisFrData._parse_date(title[1])==None:
            title[0] = title[0] + ', ' + title[1]
            del title[1]
        if len(title)>1:
            # In 'CONSTITUTIONNEL' the date is not parsed for the moment, we need to get it differently
            self.date = JurisFrData._parse_date(title[1])

        # Get ids and if 'Inédit au recueil Lebon'
        if title[-1]==u'Inédit au recueil Lebon':
            self.ids = title[2:-1]
            self.lebon = True
        else:
            self.ids = title[2:]
            self.lebon = False

        # The content is splitted with the following tags:
        # - h3 'Références' (always here)
        # - h3 'Texte intégral' (always here) (sometimes 'Texte intégral' is written with \xc3\xa9, we replace it with \xe9)
        # - h3 'Analyse' (not always here)
        #   - strong 'Abstrats'
        #   - strong 'Résumé
        # - id='exportRTF' (always here)
        #
        # The text between these tags is obtained using the function _get_between which returns the text between two tags.
        #
        tags = content.find_all('h3')
        if len(tags)==2:
            # In this case h3 'Analyse' is not here, we go directly to last tag
            tags.extend([content.find(id='exportRTF')]*4)
        else:
            abstrats, resume = None, None
            for s in content.find_all('strong'):
                if s.string and 'Abstrats' in s.string:
                    abstrats = s
                if s.string and u'Résumé' in s.string:
                    resume = s
            tags.append(abstrats if abstrats else tags[-1])
            tags.append(resume if resume else tags[-1])
            tags.append(content.find(id='exportRTF'))

        parts = [JurisFrData._get_between(tags[i], tags[i+1]) for i in range(len(tags)-1)]
        parts = map(lambda x:JurisFrData._prettify(x), parts)

        self.references, self.text, self.abstrats, self.resume = parts[0], parts[1].replace(u'Texte intégral', ''), parts[3].replace('Abstrats :',''), parts[4].replace(u'Résumé :','')


    def get_dict(self):
        return {'administration': self.administration, 'date': datetime.strftime(self.date, '%d/%m/%Y') if self.date!=None else None, 
            'ids': self.ids, 'lebon': self.lebon, 'references': self.references, 'text': self.text, 'abstrats': self.abstrats, 'resume': self.resume}


    @staticmethod
    def _prettify(text):
        """ Process the text to remove \n, \t, \r. This function could be improved.
        """
        return text.replace('\r','').replace('\n',' ').replace('\t',' ').replace(u'\xc3\xa9', u'\xe9')

    @staticmethod
    def _parse_date(date):
        try:
            # In some cases the date is written %d/%m/%Y
            return datetime.strptime(date, '%d/%m/%Y')
        except ValueError:
            try:
                for m, n in MONTHS.iteritems():
                    date = date.replace(m, n)
                # In other cases the date is written '3 Janvier 2016'
                return datetime.strptime(date, '%d %B %Y')
            except:
                pass
        return None


    @staticmethod
    def _get_between(n1, n2):
        """Returns the text between two nodes n1 and n2.
        """
        if n1==n2:
            return ''
        c = n1.next
        text = ''
        while c != n2:
            if c.string:
                text += ' '+c.string
            c = c.next
        return text


class JurisEurData():

    def __init__(self, html):
        soup = BeautifulSoup(html)
        content = soup.find(id='document_content')
        # Remove all links (i.e. the footnote, and the paragraph numbers)
        for a in content.find_all('a'):
            a.extract()
        self.text = JurisFrData._prettify(content.get_text())

    def __str__(self):
        return json.dumps({'text': self.text})


class LawFrData():

    def __init__(self, html):
        soup = BeautifulSoup(html)
        content = soup.text
        self.text = JurisFrData._prettify(content)

    def __str__(self):
        return json.dumps({'text': self.text})
###
# Some tests
###

if __name__=='__main__':
    import urllib
    # One url with the 'Analyse' section with the abstrats, and one without
    url_with = 'https://www.legifrance.gouv.fr/affichJuriAdmin.do?oldAction=rechJuriAdmin&idTexte=CETATEXT000035245522&fastReqId=557473010&fastPos=1'
    url_without = 'https://www.legifrance.gouv.fr/affichJuriAdmin.do?oldAction=rechJuriAdmin&idTexte=CETATEXT000034940297&fastReqId=857677669&fastPos=2683'
    url_judiciaire = 'https://www.legifrance.gouv.fr/affichJuriJudi.do?oldAction=rechJuriJudi&idTexte=JURITEXT000031907424&fastReqId=568681160&fastPos=2761'
    url_curia = 'http://curia.europa.eu/juris/document/document.jsf?text=&docid=193061&pageIndex=0&doclang=fr&mode=req&dir=&occ=first&part=1&cid=73206'

    for url in [url_with, url_without, url_judiciaire]:
        html = urllib.urlopen(url).read()
        ext_id = url.split('idTexte=')[1].split('&')[0]
        data = JurisFrData(url, 'ADMINISTRATIF', html, ext_id)
        print data

    for url in [url_curia]:
        html = urllib.urlopen(url).read()
        data = JurisEurData(html)
        print data


