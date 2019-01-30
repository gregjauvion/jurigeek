
import os, sys
sys.path.append(os.getcwd())

import json
import cgi
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import logging, time, argparse
from server.tfidf_api import TfidfApi

logging.basicConfig(filename='/var/log/model_server.log', level=logging.INFO, format='%(asctime)s %(message)s')


class ModelServer(HTTPServer):
    def __init__(self, server_address, request_handler_class, path_to_data):

        logging.info('Building ModelServer with path {0}'.format(path_to_data))
        HTTPServer.__init__(self, server_address, request_handler_class)

        self.path_to_data = path_to_data
        self.api = TfidfApi(path_to_data)

	logging.info('The server is ready.')

        self.nb_requests = 0


class ModelServerHandler(BaseHTTPRequestHandler):
    """The handler used to call the model and return the result.

    Note: it is possible to multi-thread it (needed if each request takes a long time to be processed and if there are a lot of parallel requests).
    """
    def do_POST(self):
        # Chunk the outputs (needed if outputs are big)
        self.send_header('Transfer-Encoding', 'chunked')

        # Get POST variables
        length = int(self.headers['content-length'])
        postvars = cgi.parse_qs(self.rfile.read(length), keep_blank_values=1)

        response = {}

        # Return the most similar documents with their keywords
        if self.path=='/most_similar':
            # Retrieve the POST variables (i.e. the document and the number of similar documents to get)
            document = postvars['document'][0]
            nb_similar = int(postvars['nb_similar'][0])

            logging.info("Request {n}: most_similar '{d}'".format(n=str(self.server.nb_requests), d=document))

            # Get the most similar documents
            response = {'most_similar': self.server.api.most_similar(document, nb_similar)}

        # Load a new corpus
        if self.path=='/reload':
            path_to = postvars['path'][0]
            logging.info('/reload, path={p}'.format(p=path_to))
            self.server.api = TfidfApi(path_to)

        # Return the response
        self.server.nb_requests += 1
        self.wfile.write(json.dumps(response))


def run(path_to_data, host, port):
    """Function used to run the server.
    """
    http = ModelServer((host, port), ModelServerHandler, path_to_data)
    http.serve_forever()


###
# Run the server
###

if __name__ == '__main__':
    # Define the command-line arguments parser
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--port')
    parser.add_argument('--path')
    args = parser.parse_args()
    # Run the server
    # Ex.: sudo ipython -i -c "%run model_server/model_server.py --host localhost --port 8081 --path model_server/tests/juris_fr_dump_100"
    run(args.path, args.host, int(args.port))
