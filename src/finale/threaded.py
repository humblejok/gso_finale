'''
Created on Mar 27, 2014

@author: sdejonckheere
'''
from ctypes.test.test_errno import threading
import uuid

from django.core.cache import cache

from providers import BloombergTasks
from universe.models import populate_security_from_bloomberg_protobuf, \
    FinancialContainer, SecurityContainer, populate_tracks_from_bloomberg_protobuf


def bloomberg_data_query(response_key, prepared_entries, use_terminal):
    cache.set(response_key, 0.0)
    response = BloombergTasks.send_bloomberg_get_data(prepared_entries, ticker_type='TICKER', use_terminal=use_terminal)
    cache.set('data_' + response_key, response)
    cache.set('type_' + response_key, 'securities')
    cache.set(response_key, 0.5)
    securities = populate_security_from_bloomberg_protobuf(response)
    cache.set(response_key, 1.0)
    
    result = []
    
    new_securities_count = 0
    
    for security in securities.keys():
        
        with_isin = []
        with_bloomberg = []
        
        isin_field = securities[security].aliases.filter(alias_type__name='ISIN')
        if isin_field.exists():
            with_isin = sorted(SecurityContainer.objects.filter(aliases__alias_type__name='ISIN', aliases__alias_value=isin_field[0].alias_value), key=lambda x: x.id)
        bloomberg_field = securities[security].aliases.filter(alias_type__name='BLOOMBERG')
        if bloomberg_field.exists():
            with_bloomberg = sorted(SecurityContainer.objects.filter(aliases__alias_type__name='BLOOMBERG', aliases__alias_value=bloomberg_field[0].alias_value), key=lambda x: x.id)
        if len(with_isin)>1:
            securities[security].delete()
            result.append(with_isin[0])
        elif len(with_bloomberg)>1:
            securities[security].delete()
            result.append(with_bloomberg[0])
        else:
            new_securities_count += 1
            result.append(securities[security])
    cache.set('securities_' + response_key, result)
    history_key = uuid.uuid4().get_hex()
    if new_securities_count>0:
        bb_thread = threading.Thread(None, bloomberg_history_query, history_key, (history_key, prepared_entries, use_terminal))
        bb_thread.start()
    
def bloomberg_history_query(response_key, prepared_entries, use_terminal):
    cache.set(response_key, 0.0)
    response = BloombergTasks.send_bloomberg_get_history(prepared_entries, ticker_type='TICKER', use_terminal=use_terminal)
    cache.set('data_' + response_key, response)
    cache.set('type_' + response_key, 'historical')
    cache.set(response_key, 0.5)
    populate_tracks_from_bloomberg_protobuf(response)
    cache.set(response_key, 1.0)
      
