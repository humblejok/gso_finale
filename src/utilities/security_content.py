'''
Created on Jun 18, 2014

@author: sdejonckheere
'''
from pymongo.mongo_client import MongoClient
from finale.settings import MONGO_URL

client = MongoClient(MONGO_URL)

mapping = client.mapping
securities = client.securities['containers']

def get_security_information(security):
    return securities.find_one({'_id': security.id})

def get_security_provider_information(security, provider):
    data = get_security_information(security)
    if data!=None:
        return data[provider]
    return data
    
def set_security_information(security, field, value, provider = None):
    data = get_security_information(security)
    if data==None:
        if provider==None:
            data = {'_id': security.id, field: value}
        else:
            data = {'_id': security.id, provider:  {field: value}}
        securities.insert(data)
    else:
        if provider==None:
            data[field] = value
        else:
            data[provider][field] = value
        securities.save(data)