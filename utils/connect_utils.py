import json
import os

def GetDbConnectionArgs(schema = None):
    connect_path = os.path.dirname(os.path.realpath(__file__))
    with open(connect_path+"/juris_con.json") as f: 
	d = json.load(f)
    d["host"] = d["host"] if d["host"]!=os.uname()[1] else "localhost"
    d["db"] =  d["db"] if schema is None else schema
    return d

def GetLawDbPath(other_path=None):
    return '/home/mehdi/legi.db' if other_path==None else other_path
if __name__=="__main__":
   print GetDbConnectionArgs()
