'''
Created on Mar 27, 2014

@author: sdejonckheere
'''
from django.core.cache import cache
from providers import BloombergTasks
from universe.models import populate_security_from_bloomberg_protobuf,\
    FinancialContainer

def bloomberg_data_query(response_key, prepared_entries):
    cache.set(response_key, 0.0)
    response = BloombergTasks.send_bloomberg_get_data(prepared_entries, ticker_type='TICKER', use_terminal=True)
    cache.set('data_' + response_key, response)
    cache.set('type_' + response_key, 'securities')
    cache.set(response_key, 0.5)
    securities = populate_security_from_bloomberg_protobuf(response)
    cache.set(response_key, 1.0)
    result = []
    for security in securities.keys():
        isin_field = securities[security].aliases.filter(alias_type__name='ISIN')
        item = [securities[security]]
        if isin_field.exists():
            look_alikes = FinancialContainer.objects.filter(aliases__alias_type__name='ISIN', aliases__alias_value=isin_field.alias_value).exclude(id=securities[security].id)
            for alike in look_alikes:
                item.append(alike)
        result.append(item)
    cache.set('securities_' + response_key, result)
    
def from_cache(response_key):
    securities = populate_security_from_bloomberg_protobuf(cache.get('data_' + response_key))
    result = []
    for security in securities.keys():
        isin_field = securities[security].aliases.filter(alias_type__name='ISIN')
        item = [securities[security]]
        if isin_field.exists():
            look_alikes = FinancialContainer.objects.filter(aliases__alias_type__name='ISIN', aliases__alias_value=isin_field.alias_value).exclude(id=securities[security].id)
            for alike in look_alikes:
                item.append(alike)
        result.append(item)
        
