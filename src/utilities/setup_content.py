'''
Created on Jun 18, 2014

@author: sdejonckheere
'''

from pymongo.mongo_client import MongoClient
from finale.settings import MONGO_URL, STATICS_GLOBAL_PATH
from seq_common.utils.dates import epoch_time
import datetime
from universe.models import Attributes
from django.template.context import Context
from django.template import loader
import os

client = MongoClient(MONGO_URL)

setup = client.setup

def get_object_type():
    results = setup.object_type.find().sort("_id", -1)
    if results.count()>0:
        return results[0]
    else:
        return {}
    
def set_object_type(values):
    values['_id'] = epoch_time(datetime.datetime.today())
    setup.object_type.insert(values)
    all_types = Attributes.objects.filter(active=True, type='object_type')
    for a_type in all_types:
        
        context = Context({"selection": values[a_type.identifier]})
        template = loader.get_template('rendition/object_type/lists/object_type_choices.html')
        rendition = template.render(context)
        # TODO Implement multi-langage
        outfile = os.path.join(STATICS_GLOBAL_PATH, a_type.identifier + '_en.html')
        with open(outfile,'w') as o:
            o.write(rendition.encode('utf-8'))
    
def get_container_type():
    results = setup.container_type.find().sort("_id", -1)
    if results.count()>0:
        return results[0]
    else:
        return {}
    
def set_container_type(values):
    values['_id'] = epoch_time(datetime.datetime.today())
    setup.container_type.insert(values)