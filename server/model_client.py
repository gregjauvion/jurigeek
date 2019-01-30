
import json
import urllib, urllib2


class ModelClient():

    def __init__(self, host, port):
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


    def most_similar(self, document, nb_similar):
        """Get most similar documents.
        """
        return self.post('most_similar', values={'document': document, 'nb_similar': nb_similar})


    def reload(self, path):
        return self.post('reload', values={'path': path})


###
# Test
###

if __name__ == '__main__':

    client = ModelClient(host='localhost', port=8081)
    print client.most_similar('Ceci est un document.', 3)
    print client.most_similar('Ceci est un autre document.', 3)

    print 'Reload corpus:'
    client.reload('model_server/tests/juris_fr_dump_100')
