'''
Created on Mar 27, 2014

@author: sdejonckheere
'''
from ctypes.test.test_errno import threading
from django.db.models import Q
from django.core.cache import cache
from providers import BloombergTasks
from universe.models import populate_security_from_bloomberg_protobuf, \
    SecurityContainer, populate_tracks_from_bloomberg_protobuf,\
    BloombergDataContainerMapping, BloombergTrackContainerMapping
from finale.utils import to_bloomberg_code
    
import uuid


def bloomberg_data_query(response_key, prepared_entries, use_terminal):
    cache.set(response_key, 0.0)
    all_fields = BloombergDataContainerMapping.objects.all().values_list('short_name__code', flat=True)
    response = BloombergTasks.send_bloomberg_get_data(prepared_entries, ticker_type='TICKER', use_terminal=use_terminal, fields=all_fields)
    cache.set('data_' + response_key, response)
    cache.set('type_' + response_key, 'securities')
    cache.set(response_key, 0.5)
    securities, final_tickers, errors = populate_security_from_bloomberg_protobuf(response)
    
    result = []
    
    new_securities_count = 0
    
    for security in securities.keys():
        with_isin = []
        with_bloomberg = []
        
        isin_field = securities[security].aliases.filter(alias_type__name='ISIN')
        if isin_field.exists():
            with_isin = sorted(securities[security].__class__.objects.filter(aliases__alias_type__name='ISIN', aliases__alias_value=isin_field[0].alias_value), key=lambda x: x.id)
        bloomberg_field = securities[security].aliases.filter(alias_type__name='BLOOMBERG')
        if bloomberg_field.exists():
            with_bloomberg = sorted(securities[security].__class__.objects.filter(aliases__alias_type__name='BLOOMBERG', aliases__alias_value=bloomberg_field[0].alias_value), key=lambda x: x.id)
        if len(with_isin)>1:
            securities[security].bloomberg_data.all().delete()
            securities[security].delete()
            result.append(with_isin[0])
        elif len(with_bloomberg)>1:
            securities[security].delete()
            result.append(with_bloomberg[0])
        else:
            new_securities_count += 1
            result.append(securities[security])
    cache.set('securities_' + response_key, result)
    cache.set('errors_' + response_key, errors)
    cache.set(response_key, 1.0)
    # Getting all kind of containers
    all_containers = {}
    for security in result:
        if not all_containers.has_key(security.__class__.__name__):
            all_containers[security.__class__.__name__] = []
        all_containers[security.__class__.__name__].append(security.aliases.get(alias_type__name='BLOOMBERG').alias_value)
    
    for key in all_containers.keys():
        fields = BloombergTrackContainerMapping.objects.filter(Q(container__short_name='SecurityContainer') | Q(container__short_name=key), Q(active=True)).values_list('short_name__code', flat=True)
        all_containers[key] = [to_bloomberg_code(ticker,use_terminal) for ticker in all_containers[key]]
        history_key = uuid.uuid4().get_hex()
        bb_thread = threading.Thread(None, bloomberg_history_query, history_key, (history_key, all_containers[key], fields, True))
        bb_thread.start()
        bb_thread.join()
    
def bloomberg_history_query(response_key, prepared_entries, fields, use_terminal):
    cache.set(response_key, 0.0)
    response = BloombergTasks.send_bloomberg_get_history(prepared_entries, ticker_type='TICKER', fields=fields, use_terminal=use_terminal)
    cache.set('data_' + response_key, response)
    cache.set('type_' + response_key, 'historical')
    cache.set(response_key, 0.5)
    populate_tracks_from_bloomberg_protobuf(response)
    cache.set(response_key, 1.0)