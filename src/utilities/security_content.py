'''
Created on Jun 18, 2014

@author: sdejonckheere
'''
from pymongo.mongo_client import MongoClient
from finale.settings import MONGO_URL

client = MongoClient(MONGO_URL)

securities = client.securities['containers']

def get_security_information(security):
    all_data = securities.find_one({'_id': security.id})
    new_data = {}
    if all_data!=None:
        for entry in all_data.keys():
            new_data[entry.replace('%','.')] = all_data[entry]
    return new_data

def get_security_provider_information(security, provider):
    data = get_security_information(security)
    if data!=None:
        return data[provider]
    return data
    
def set_security_information(security, field, value, provider = None):
    valid_field_name = field.replace('.','%')
    data = get_security_information(security)
    if data==None:
        if provider==None:
            data = {'_id': security.id, valid_field_name: value}
        else:
            data = {'_id': security.id, provider:  {valid_field_name: value}}
        securities.insert(data)
    else:
        if provider==None:
            data[valid_field_name] = value
        else:
            data[provider][valid_field_name] = value
        securities.save(data)