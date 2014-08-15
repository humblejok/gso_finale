'''
Created on Jun 3, 2014

@author: sdejonckheere
'''
from pymongo.mongo_client import MongoClient
from django.db.models import Q
from finale.settings import MONGO_URL

from seq_common.db import dbutils
from decimal import Decimal
from pymongo.errors import DuplicateKeyError
from universe.models import SecurityContainer, Attributes, BloombergTrackContainerMapping

from finale.utils import get_bloomberg_provider, get_universe_from_datasource,\
    to_bloomberg_code
from finale.threaded import bloomberg_history_query

import logging
import threading
import uuid
from seq_common.utils.dates import epoch_time
from datetime import datetime as dt
import datetime

LOGGER = logging.getLogger(__name__)

client = MongoClient(MONGO_URL)


QUERIES = { 'guardian': {'securities': 
                            {'query': "select * from tit where cod_tiptit not like 'A%%' and cod_tiptit not like 'C%%' and cod_tiptit not in ('Z300', 'ZZZZ') and des_tit<>'N/D' order by des_tit",
                             'group_by':['cod_tit','cod_isin', 'cod_bloomberg'], 
                             'name': 'des_tit', 
                             'short_name': 'des_tit_bre',
                             'currency': 'cod_div',
                             'BLOOMBERG': 'cod_bloomberg', 
                             'ISIN': 'cod_isin', 
                             'EXTERNAL': 'cod_tit'},
                          'positions':
                            {'query':"select t1.cod_rap, r.des_rap, r.cod_sta, r.cod_lin, r.cod_gru, r.cod_ges, r.cod_pro, r.cod_ctp, r.cod_soc, t1.cod_tit, tit.cod_isin, tit.cod_bloomberg, tit.des_tit,\n\
                                      t1.cod_div_tit, tit.cod_tiptit, te.cod_emi, te.des_emi, tit.cod_isin, tit.cod_bloomberg, tit.cod_esterno, t1.qta, t1.prezzo_car, t1.prezzo, t1.rateo, t1.ctv_tot_dn,t1.ctv_imp,\n\
                                      t1.cod_div_reg, t1.cambio, t1.ctv_tot_dr, t1.peso, j.pat_tot_dr, t1.tipo_rec, tit.risk_class as rating, tit.data_rim, tit.ytm, tit.duration_mid, tit.security_type, tit.security_typ2,\n\
                                      tit.sigla_paese, tit.focus, tit.style, tit.ind_gru, tit.ind_sec, tit.ind_subgru, tit.issuer_industry, t1.richiesta, j.data_cal \n\
                                      from tmppostit1 t1 left join tmppostit0 t0 on t0.richiesta2=t1.richiesta left join tmpjobpar j on j.richiesta=t0.richiesta2\n\
                                      left join rap r on r.cod_rap=t1.cod_rap left join tit on tit.cod_tit=t1.cod_tit left join tabemi te on te.cod_emi=tit.cod_emi \n\
                                      where t0.richiesta1=(select max(richiesta1) request from tmppostit0) and t1.ordinamento='B' and r.cod_soc<>'NOSEQ' order by cod_rap, cod_tit",
                             'group_by':['data_cal', 'des_rap']
                             }
                         },
            'saxo': {'operations': {'query': 'SELECT * FROM PRODUCT_PRODUCTEXECUTEDTRADES',
                                    'group_by':['id'],
                                    'joins':[{'name': 'details',
                                              'on':['trade_id'],
                                              'query': "select * from product_productexecutedtradesdetails where trade_id='%s'" }]
                                    }
                     },
            }

def is_fund(data_source, data):
    is_fund = False
    if data_source=='guardian':
        fund_fields = ['fondo', 'fondo_azi', 'fondo_obb', 'fondo_bil', 'fondo_mon', 'fondo_ucits', 'hedge_fund', 'etf', 'fondo_recente']
        for field in fund_fields:
            if data[field]=='S':
                is_fund = True
    return is_fund

def is_bond(data_source, data):
    is_bond = False
    if data_source=='guardian':
        bond_fields = ['obbl_bank','obbl_govt','obbligazione']
        for field in bond_fields:
            if data[field]=='S':
                is_bond = True
    return is_bond

def is_stock(data_source, data):
    is_stock = False
    if data_source=='guardian':
        stock_fields = ['azione']
        for field in stock_fields:
            if data[field]=='S':
                is_stock = True
    return is_stock

def convert_to_mongo(result):
    new_entry = {key: (result[key] if not isinstance(result[key], Decimal) else float(str(result[key]))) for key in result.keys()}
    new_entry = {key: (unicode(new_entry[key]) if not isinstance(new_entry[key], float) and new_entry[key]!=None else new_entry[key]) for key in new_entry.keys()}
    return new_entry

      
def import_external_grouped_data(data_source, data_type):
    LOGGER.info('Loading working data')
    query = QUERIES[data_source][data_type]['query']
    group_by = QUERIES[data_source][data_type]['group_by']
    
    LOGGER.info('Importing ' + str(data_type) + ' from ' + str(data_source))
    LOGGER.info('Using query:' + str(query))
    results = dbutils.query_to_dicts(query, data_source)
    database = getattr(client, data_source)
    
    all_values = {}
    
    for result in results:
        keys = []
        for key in group_by:
            if isinstance(result[key], datetime.date):
                keys.append(epoch_time(dt.combine(result[key],dt.min.time())))
            else:
                keys.append(result[key].replace('.','___'))
        # Clean the data        
        new_entry = convert_to_mongo(result)
        
        current_values = all_values
        for key in keys[:-1]:
            if not current_values.has_key(key):
                current_values[key] = {}
            current_values = current_values[key]
        if not current_values.has_key(keys[-1]):
            current_values[keys[-1]] = []
        current_values[keys[-1]].append(new_entry)
    
    for key in all_values.keys():
        LOGGER.info("Inserting " + data_type + " with _id: " + str(key))
        database[data_type].remove({'_id': key})
        database[data_type].insert({'_id': key, 'values': all_values[key]})   
    
    
def import_external_data(data_source, data_type):
    LOGGER.info('Loading working data')
    query = QUERIES[data_source][data_type]['query']
    group_by = QUERIES[data_source][data_type]['group_by']
    external_alias = Attributes.objects.get(identifier='ALIAS_' + data_source.upper())
    
    if data_type=='securities':
        bloomberg_alias = Attributes.objects.get(identifier='ALIAS_BLOOMBERG')
        isin_alias = Attributes.objects.get(identifier='ALIAS_ISIN')
        sec_container_type = Attributes.objects.get(identifier='CONT_SECURITY')
        fund_container_type = Attributes.objects.get(identifier='CONT_FUND')
        bond_container_type = Attributes.objects.get(identifier='CONT_BOND')
        stock_container_type = Attributes.objects.get(identifier='CONT_SECURITY')
        security_type = Attributes.objects.get(identifier='SECTYP_SECURITY')
        fund_type = Attributes.objects.get(identifier='SECTYP_FUND')
        bond_type = Attributes.objects.get(identifier='SECTYP_BOND')
        stock_type = Attributes.objects.get(identifier='SECTYP_STOCK')

        daily = Attributes.objects.get(identifier='FREQ_DAILY', active=True)
        
        bloomberg_provider = get_bloomberg_provider()
        
        universe = get_universe_from_datasource(data_source)
        
        LOGGER.info('Cleaning already imported aliases for ' + data_source)
        securities = SecurityContainer.objects.filter(aliases__alias_type__short_name=data_source.upper()).distinct()
        for security in securities:
            for alias in security.aliases.all():
                if alias.alias_type.short_name==data_source.upper():
                    security.aliases.remove(alias)
            security.save()
        LOGGER.info('\tCleaning done')
    
    LOGGER.info('Importing ' + str(data_type) + ' from ' + str(data_source))
    LOGGER.info('Using query:' + str(query))
    results = dbutils.query_to_dicts(query, data_source)
    database = getattr(client, data_source)
    database[data_type].drop()
    
    name_field = QUERIES[data_source][data_type]['name']
    short_name_field = QUERIES[data_source][data_type]['short_name']
    
    all_tickers = []
    
    for result in results:
        # Clean the data        
        new_entry = convert_to_mongo(result)
        for group_id in group_by:
            if new_entry[group_id]!=None and new_entry[group_id]!='':
                # LOADING INTO MONGO
                LOGGER.info('Adding entry [' + group_id + '=' + str(new_entry[group_id]) + "]")
                new_entry['_id'] = new_entry[group_id]
                if QUERIES[data_source][data_type].has_key('joins'):
                    for join_info in QUERIES[data_source][data_type]['joins']:
                        values = [new_entry[identifier] for identifier in join_info['on']]
                        underlying_query = join_info['query']
                        for value in values:
                            underlying_query = underlying_query%value
                        new_entry[join_info['name']] = []
                        under_results = dbutils.query_to_dicts(underlying_query, data_source)
                        for under_result in under_results:
                            LOGGER.info('\tAdding underlying [' + join_info['name'] + ', ' + group_id + '=' + str(new_entry[group_id]) + "]")
                            # Clean the data        
                            under_entry = convert_to_mongo(under_result)
                            new_entry[join_info['name']].append(under_entry)
                try:
                    database[data_type].save(new_entry)
                except DuplicateKeyError:
                    LOGGER.error("The following entry already exists:")
            # CONVERTING TO FINALE
            if group_id==QUERIES[data_source][data_type]['EXTERNAL'] and data_type=='securities':
                bloomberg_ticker = result[QUERIES[data_source][data_type]['BLOOMBERG']]
                isin_code = result[QUERIES[data_source][data_type]['ISIN']]
                currency = result[QUERIES[data_source][data_type]['currency']]
                currency = Attributes.objects.filter(type='currency', short_name=currency)
                if currency.exists():
                    currency = currency[0]
                else:
                    currency = None
                
                security = SecurityContainer.objects.filter(aliases__alias_type__short_name=data_source.upper(), aliases__alias_value=result[group_id])
                external_append = False
                additional = ''
                if not security.exists():
                    security = SecurityContainer.objects.filter(aliases__alias_type__id=bloomberg_alias.id, aliases__alias_value=bloomberg_ticker)
                    additional = result[name_field]
                    external_append = True
                if is_fund(data_source, result):
                    container = fund_container_type
                    stype = fund_type
                elif is_bond(data_source, result):
                    container = bond_container_type
                    stype = bond_type
                elif is_stock(data_source, result):
                    container = stock_container_type
                    stype = stock_type
                else:
                    container = sec_container_type
                    stype = security_type
                if not security.exists():
                    LOGGER.info("Creating security with " + data_source + " id [" + str(result[group_id]) + "]")
                    security = SecurityContainer()
                    security.name = result[name_field]
                    security.short_name = result[short_name_field] if result[short_name_field]!=None and result[short_name_field]!='' else result[name_field]
                    security.save()
                    security.associated_companies.add(bloomberg_provider)
                    security.save()
                else:
                    LOGGER.info("Security with " + data_source + " id [" + str(result[group_id]) + "] already exists.")
                    security = security[0]
                security.update_alias(external_alias, result[group_id], additional, external_append)
                security.currency = currency
                security.frequency = daily
                security.type = container
                security.security_type = stype
                security.save()
                if bloomberg_ticker!=None and bloomberg_ticker!='':
                    all_tickers.append(bloomberg_ticker)
                elif isin_code!=None and isin_code!='':
                    all_tickers.append(isin_code)
                    
                if bloomberg_ticker!=None and bloomberg_ticker!='':
                    security.update_alias(bloomberg_alias, bloomberg_ticker)
                if isin_code!=None and isin_code!='':
                    security.update_alias(isin_alias, isin_code)
                universe.members.add(security)
    universe.save()
    
    all_containers = {}
    for member in universe.members.all():
        if not all_containers.has_key(member.type.identifier):
            all_containers[member.type.identifier] = []
        try:
            all_containers[member.type.identifier].append(member.aliases.get(alias_type__name='BLOOMBERG').alias_value)
        except:
            try:
                all_containers[member.type.identifier].append(member.aliases.get(alias_type__name='ISIN').alias_value)
            except:
                LOGGER.info("There is no Bloomberg nor ISIN code available for this security ["  + member.name + "]")
            
    for key in all_containers.keys():
        fields = BloombergTrackContainerMapping.objects.filter(Q(container__identifier='CONT_SECURITY') | Q(container__identifier=key), Q(active=True)).values_list('short_name__code', flat=True)
        all_containers[key] = [to_bloomberg_code(ticker,True) for ticker in all_containers[key]]
        history_key = uuid.uuid4().get_hex()
        bb_thread = threading.Thread(None, bloomberg_history_query, history_key, (history_key, all_containers[key], fields, True))
        bb_thread.start()
        bb_thread.join()

def get_positions(data_source, working_date):
    database = getattr(client, data_source)
    key = epoch_time(dt.combine(working_date,dt.min.time()))
    LOGGER.info("Getting positions with _id: " + str(key))
    return database['positions'].find_one({'_id': key})

def get_operations(data_source, start_date=None, end_date=None):
    if start_date!=None:
        start_date = start_date.strftime('%Y-%m-%d')
    if end_date!=None:
        end_date = end_date.strftime('%Y-%m-%d')
    if start_date==None and end_date==None:
        query_filter = None
    else:
        key_field = 'trade_timestamp' if data_source=='saxo' else ''
        query_filter = {key_field: {}}
        if start_date!=None:
            query_filter[key_field]["$gte"] = start_date
        if end_date!=None:
            query_filter[key_field]["$lte"] = end_date
    database = getattr(client, data_source)
    return database['operations'].find(query_filter).sort("_id", 1)

def get_security_information(data_source, isin=None, bloomberg=None, external_id=None):
    database = getattr(client, data_source)
    by_isin = database['securities'].find_one({'_id':isin})
    by_bloomberg = database['securities'].find_one({'_id':isin})
    by_external = database['securities'].find_one({'_id':external_id})
    return by_external if by_external!=None else by_bloomberg if by_bloomberg!=None else by_isin

def get_securities_by_isin(data_source, isin):
    database = getattr(client, data_source)
    if data_source=='guardian':
        return database['securities'].find({'cod_isin':isin})