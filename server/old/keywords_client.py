
import json
import urllib, urllib2

HOST = 'localhost'
PORT = 8082

class KeywordsClient():

    def __init__(self, host=HOST, port=PORT):
        """Build the url to request the server.
        """
        self.url = 'http://{h}:{p}'.format(h=host, p=str(port))


    def post(self, request, values=None):
        """Sends a POST request to the server and returns the response.
        - request : the request to send
        - values : a dictionary with the data to send
        """
        req = urllib2.Request(self.url + '/' + request, urllib.urlencode(values if values else {}))
        # The response is formed the following way : header which finished with \n, and then the response
        response = urllib2.urlopen(req).read()
        output = response.split('\n')[1]
        return json.loads(output)


    def keywords(self, document, nb_keywords):
        """Get most similar documents.
        """
        return self.post('keywords', values={'document': document, 'nb_keywords': nb_keywords})


###
# Test
###

if __name__ == '__main__':
    import time
    client = KeywordsClient()
    print client.keywords('Ceci est un document administratif du tribunal de Paris.', 5)
    print client.keywords('Ceci est un autre document.', 10)
