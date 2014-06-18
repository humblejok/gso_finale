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


QUERIES = { 'guardian': {'securities': {'query': 'SELECT * FROM TIT', 'group_by':['cod_tit','cod_isin', 'cod_bloomberg']}},
            'saxo': {'operations': {'query': 'SELECT * FROM PRODUCT_PRODUCTEXECUTEDTRADES',
                                    'group_by':['id'],
                                    'joins':[{'name': 'details',
                                              'on':['trade_id'],
                                              'query': "select * from product_productexecutedtradesdetails where trade_id='%s'" }]
                                    }
                     },
            }

def convert_to_mongo(result):
    new_entry = {key: (result[key] if not isinstance(result[key], Decimal) else float(str(result[key]))) for key in result.keys()}
    new_entry = {key: (unicode(new_entry[key]) if not isinstance(new_entry[key], float) and new_entry[key]!=None else new_entry[key]) for key in new_entry.keys()}
    return new_entry

def import_external_data(datasource, data_type):
    query = QUERIES[datasource][data_type]['query']
    group_by = QUERIES[datasource][data_type]['group_by']
    LOGGER.info('Importing securities from ' + str(datasource))
    LOGGER.info('Using query:' + str(query))
    results = dbutils.query_to_dicts(query, datasource)
    database = getattr(client, datasource)
    database[data_type].drop()
    for result in results:
        # Clean the data        
        new_entry = convert_to_mongo(result)
        for group_id in group_by:
            if new_entry[group_id]!=None and new_entry[group_id]!='':
                LOGGER.info('Adding entry [' + group_id + '=' + str(new_entry[group_id]) + "]")
                new_entry['_id'] = new_entry[group_id]
                if QUERIES[datasource][data_type].has_key('joins'):
                    for join_info in QUERIES[datasource][data_type]['joins']:
                        values = [new_entry[identifier] for identifier in join_info['on']]
                        underlying_query = join_info['query']
                        for value in values:
                            underlying_query = underlying_query%value
                        new_entry[join_info['name']] = []
                        under_results = dbutils.query_to_dicts(underlying_query, datasource)
                        for under_result in under_results:
                            LOGGER.info('\tAdding underlying [' + join_info['name'] + ', ' + group_id + '=' + str(new_entry[group_id]) + "]")
                            # Clean the data        
                            under_entry = convert_to_mongo(under_result)
                            new_entry[join_info['name']].append(under_entry)
                try:
                    database[data_type].insert(new_entry)
                except DuplicateKeyError:
                    LOGGER.error("The following entry already exists:")
                    LOGGER.error(new_entry)

def get_operations(datasource, start_date=None, end_date=None):
    if start_date!=None:
        start_date = start_date.strftime('%Y-%m-%d')
    if end_date!=None:
        end_date = end_date.strftime('%Y-%m-%d')
    if start_date==None and end_date==None:
        query_filter = None
    else:
        key_field = 'trade_timestamp' if datasource=='saxo' else ''
        query_filter = {key_field: {}}
        if start_date!=None:
            query_filter[key_field]["$gte"] = start_date
        if end_date!=None:
            query_filter[key_field]["$lte"] = end_date
    print query_filter
    database = getattr(client, datasource)
    return database['operations'].find(query_filter).sort("_id", 1)

def get_security_information(datasource, isin=None, bloomberg=None, external_id=None):
    database = getattr(client, datasource)
    by_isin = database['securities'].find_one({'_id':isin})
    by_bloomberg = database['securities'].find_one({'_id':isin})
    by_external = database['securities'].find_one({'_id':external_id})
    return by_external if by_external!=None else by_bloomberg if by_bloomberg!=None else by_isin

def get_securities_by_isin(datasource, isin):
    database = getattr(client, datasource)
    if datasource=='guardian':
        return database['securities'].find({'cod_isin':isin})