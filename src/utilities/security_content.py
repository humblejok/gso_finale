'''
Created on Jun 18, 2014

@author: sdejonckheere
'''
from pymongo.mongo_client import MongoClient
from finale.settings import MONGO_URL
from universe.models import Attributes

client = MongoClient(MONGO_URL)

securities = client.securities['containers']

def enhance_security_information(custom_data, custom_info):
    enhanced_data = {}
    if custom_data!=None:
        for field in custom_data.keys():
            if custom_info.has_key(field) and custom_info[field]['type'] in ['FIELD_TYPE_CHOICE']:
                enhanced_data[field] = Attributes.objects.get(identifier=custom_data[field], type=custom_info[field]['attribute'], active=True).get_short_json()
            else:
                enhanced_data[field] = custom_data[field] 
    return enhanced_data

def get_security_information(security, clean=True):
    all_data = securities.find_one({'_id': security.id})
    if all_data!=None and clean:
        new_data = {}
        for entry in all_data.keys():
            new_data[entry.replace('%','.')] = all_data[entry]
        all_data = new_data
    return all_data

def get_security_provider_information(security, provider):
    data = get_security_information(security)
    if data!=None:
        return data[provider]
    return data
    
def set_security_information(security, field, value, provider = None):
    valid_field_name = field.replace('.','%')
    data = get_security_information(security, False)
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
        
        
def get_price_divisor(container):
    if container.type.identifier=='CONT_BOND':
        return 100.0
    else:
        additional_information = get_security_information(container)
        if additional_information!=None:
            if additional_information.has_key('Valuation-specifities.Price-divisor'):
                return float(additional_information['Valuation-specifities.Price-divisor'])
        return 1.0