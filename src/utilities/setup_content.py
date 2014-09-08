'''
Created on Jun 18, 2014

@author: sdejonckheere
'''

from pymongo.mongo_client import MongoClient
from finale.settings import MONGO_URL
from seq_common.utils.dates import epoch_time
import datetime

client = MongoClient(MONGO_URL)

object_type = client.object_type

def get_object_type():
    results = object_type.find().sort("_id", -1)
    if len()>0:
        return results[0]
    else:
        return {}
    
def set_object_type(values):
    values['_id'] = epoch_time(datetime.datetime.today())
    object_type.insert(values)