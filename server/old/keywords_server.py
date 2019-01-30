
import json
import cgi
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import logging, time, argparse
import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.nlp_keywords import Vocabulary, Keywords
from data.law_data import Reader
from itertools import imap

# The server runs on port 8081
PORT = 8082

WINDOW_SIZE = 4

logging.basicConfig(filename='/var/log/keywords_server.log', level=logging.INFO, format='%(asctime)s %(message)s')


class KeywordsServer(HTTPServer):
    def __init__(self, server_address, request_handler_class, path_to_documents):
        logging.info("Building KeywordsServer.")
        HTTPServer.__init__(self, server_address, request_handler_class)

        self.path_to_documents = path_to_documents
        get_data = lambda :imap(lambda x:json.loads(x[1][:-1])['text'], Reader(self.path_to_documents))

        # Build the vocabulary
        logging.info('Building vocabulary...')        
        vocabulary = Vocabulary.build(get_data, window_size=WINDOW_SIZE, limit=5E-6)
        logging.info('Vocabulary built.')

        logging.info('Building keywords...')
        self.keywords = Keywords(vocabulary, get_data)
        logging.info('Keywords built.')

        self.nb_requests = 0


class KeywordsServerHandler(BaseHTTPRequestHandler):
    """The handler used to return keywords.
    """
    def do_POST(self):
        # Chunk the outputs (needed if outputs are big)
        self.send_header('Transfer-Encoding', 'chunked')

        # Get POST variables
        length = int(self.headers['content-length'])
        postvars = cgi.parse_qs(self.rfile.read(length), keep_blank_values=1)

        response = {}

        # Handle the request
        if self.path=='/keywords':
            # Retrieve the POST variables (i.e. the document and the number of similar documents to get)
            document = postvars['document'][0]
            nb_keywords = int(postvars['nb_keywords'][0])

            logging.info("Request {n}: keywords.".format(n=str(self.server.nb_requests)))

            # Get the most similar documents
            response = {'keywords': self.server.keywords.get_keywords(document, nb_keywords)}

        # Return the response
        self.server.nb_requests += 1
        self.wfile.write(json.dumps(response))


def run(path_to_documents, host, port=PORT):
    """Function used to run the server.
    """
    http = KeywordsServer((host, port), KeywordsServerHandler, path_to_documents)
    http.serve_forever()


###
# Run the server
###

if __name__ == '__main__':
    # Define the command-line arguments parser
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--path-to-documents')
    args = parser.parse_args()
    # Run the server
    # Ex.: sudo ipython -i -c "%run model_server/keywords_server.py --host localhost --path-to-documents model_server/tests/juris_fr_dump_100"
    run(args.path_to_documents, args.host)
