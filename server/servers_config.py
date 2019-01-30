
from subprocess import Popen
from shlex import split

HOST = '137.74.117.17'

# Define the ports for the different data sources
PORT_JURIS_FR = 8081
PORT_JURIS_EUR = 8082
PORT_LAW_FR = 8083

# Define the paths to the data dumps
JURIS_FR_DUMP = '/home/gregoire/data/juris_fr_dump'
JURIS_EUR_DUMP = '/home/gregoire/data/juris_eur_dump'
LAW_FR_DUMP = '/home/prod/data/law_fr_dump'


###
# Does not work for the moment because we need to sudo before...
# But still useful to get the commands to run the servers.
###

def run_juris_fr():
    cmd = 'nohup python server/model_server.py --host {h} --port {po} --path {pa} &'.format(h=HOST, po=str(PORT_JURIS_FR), pa=JURIS_FR_DUMP)
    #Popen(shlex.split(cmd))

def run_juris_eur():
    cmd = 'nohup python server/model_server.py --host {h} --port {po} --path {pa} &'.format(h=HOST, po=str(PORT_JURIS_EUR), pa=JURIS_EUR_DUMP)
    #Popen(shlex.split(cmd))

def run_law_fr():
    cmd = 'nohup python server/model_server.py --host {h} --port {po} --path {pa} &'.format(h=HOST, po=str(PORT_LAW_FR), pa=LAW_FR_DUMP)
