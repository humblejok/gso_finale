'''
Created on Mar 27, 2014

@author: sdejonckheere
'''
from django.core.cache import cache
from providers import BloombergTasks

def bloomberg_data_query(response_key, prepared_entries):
    cache.set(response_key, 0.0)
    response = BloombergTasks.send_bloomberg_get_data(prepared_entries, ticker_type='TICKER')
    cache.set('data_' + response_key, response)
    cache.set(response_key, 0.5)
    
    