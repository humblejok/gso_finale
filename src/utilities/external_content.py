'''
Created on Jun 3, 2014

@author: sdejonckheere
'''
from pymongo.mongo_client import MongoClient
from finale.settings import MONGO_URL
import logging
from seq_common.db import dbutils
from decimal import Decimal
from pymongo.errors import DuplicateKeyError

LOGGER = logging.getLogger(__name__)

client = MongoClient(MONGO_URL)

def import_securities(datasource, query, group_by):
    LOGGER.info('Importing securities from ' + str(datasource))
    LOGGER.info('Using query:' + str(query))
    results = dbutils.query_to_dicts(query, 'guardian')
    database = getattr(client, datasource)
    database['securities'].drop()
    for result in results:
        LOGGER.info('Working on an entry')
        # Clean the data        
        new_entry = {key: (result[key] if not isinstance(result[key], Decimal) else float(str(result[key]))) for key in result.keys()}
        new_entry = {key: (unicode(new_entry[key]) if not isinstance(new_entry[key], float) and new_entry[key]!=None else new_entry[key]) for key in new_entry.keys()}
        for group_id in group_by:
            if new_entry[group_id]!=None and new_entry[group_id]!='':
                LOGGER.info('Adding entry [' + group_id + '=' + str(new_entry[group_id]) + "]")
                new_entry['_id'] = new_entry[group_id]
                try:
                    database['securities'].insert(new_entry)
                except DuplicateKeyError:
                    LOGGER.error("The following entry already exists:")
                    LOGGER.error(new_entry)
                    
def get_security_information(datasource, isin=None, bloomberg=None, external_id=None):
    database = getattr(client, datasource)
    by_isin = database['securities'].find_one({'_id':isin})
    by_bloomberg = database['securities'].find_one({'_id':isin})
    by_external = database['securities'].find_one({'_id':external_id})
    return by_external if by_external!=None else by_bloomberg if by_bloomberg!=None else by_isin