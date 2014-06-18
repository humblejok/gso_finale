'''
Created on Jun 18, 2014

@author: sdejonckheere
'''
from pymongo.mongo_client import MongoClient
from finale.settings import MONGO_URL

client = MongoClient(MONGO_URL)

mapping = client.mapping
securities = client.securities

def get_security_information(security):
    None
    
    