'''
Created on Jun 18, 2014

@author: sdejonckheere
'''

from pymongo.mongo_client import MongoClient
from finale.settings import MONGO_URL

client = MongoClient(MONGO_URL)

mapping = client.mapping
providers = client.securities

def get_mapping(container_type):
    None

def get_provider_mapping(container_type):
    None
    
def get_provider_dataset(provider):
    None