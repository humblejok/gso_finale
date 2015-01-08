'''
Created on Jun 16, 2014

@author: sdejonckheere
'''
from utilities.external_content import get_operations, get_security_information,\
    get_securities_by_isin

import logging
import datetime
from datetime import datetime as dt
from utilities.xls_writer import simple_xlsx_dump
from universe.models import SecurityContainer
from finale import threaded
from utilities.track_token import get_closest_value, get_main_track_content

LOGGER = logging.getLogger(__name__)

saxo_accounts = {'80287/6126430U': {'currency':'USD', 'guardian':'CC02054'},
                 '80287/6126430DMA': {'currency':'USD', 'guardian':'CC02083'},
                 '80287/6137950CHF': {'currency':'CHF', 'guardian':'CC02089'},
                 '80287/6134640': {'currency':'EUR', 'guardian':'CC02095'},
                 '80287/6137950': {'currency':'USD', 'guardian':'CC02088'},
                 '80287/6675050': {'currency':'USD', 'guardian':'CC02093'},
                 '80287/6677130': {'currency':'USD', 'guardian':''},
                 '80287/6676740': {'currency':'USD', 'guardian':''},                 
                 }


def get_security_code(sec_name, sec_isin, sec_type):
    securities = get_securities_by_isin('guardian', sec_isin)
    for security in securities:
        if sec_type=='CFDs' and security[u'cfd']=='S':
            return security['cod_tit']
        elif sec_type!='CFDs':
            return security['cod_tit']
    return None

def get_security_divisor(sec_code):
    return get_security_information('guardian', None, None, sec_code)[u'divisore']

def get_exchange_rate_price(source_currency, destination_currency, value_date):
    currency = SecurityContainer.objects.filter(name__startswith=source_currency + destination_currency)
    if not currency.exists():
        threaded.bloomberg_data_query('NO_NEED', [source_currency + destination_currency + ' Curncy'], True)
    currency = SecurityContainer.objects.filter(name__startswith=source_currency + destination_currency)
    if currency.exists():
        value = get_closest_value(get_main_track_content(currency[0]), dt.combine(value_date, dt.min.time()))
        if value==None:
            return 1.0
        else:
            return value['value']

def get_guardian_operation(saxo_codes, guardian_code, start_date, end_date, export_file):
    export_header = ['progr','rif','simulazione','spuntato','storicizzato','storno','annullato','data_ins','data_ope','ora_ope','data_val',
                     'cod_ope','cod_rap','cod_tit','cod_div_tit','cod_isin','cod_bloomberg','cod_esterno','qta','prezzo','rateo','cambiom',
                     'cambiod','cod_ctp','cod_dep_tit','cod_dep_liq','cod_dep_liq2','cod_div_reg','ctv_tit_dn','ctv_rat_dn','comp_dep_dn',
                     'coma_dep_dn','comp_alt_dn','coma_alt_dn','spese_dn','imposte_dn','ctv_tot_dn','margini_dn','ctv_tit_dr','ctv_rat_dr',
                     'omp_dep_dr','coma_dep_dr','comp_alt_dr','coma_alt_dr','spese_dr','imposte_dr','ctv_tot_dr','des_mov','rif_est',
                     'coordinate1','coordinate2','data_sto','progr_sto','prezzo_car','cod_div_ds','cambiom_ds','cambiod_ds','ctv_tot_ds',
                     'cod_mer','tipo_prezzo','tipo_tempo','cash']
    rows = [export_header]
    for trade in get_operations('saxo', start_date, end_date):
        if trade[u'product_account_id'] in saxo_codes:
            LOGGER.info("Working on row " + str(trade[u'trade_id']) + " with operation code " + str(trade[ u'trade_buy_sell']) + ": " + str(trade[u'trade_product']) + " of " + str(trade[u'trade_instrument']))
            try:
                trade_date = datetime.datetime.strptime(trade[u'trade_timestamp'],'%Y-%m-%d %H:%M:%S.%f')
            except:
                trade_date = datetime.datetime.strptime(trade[u'trade_timestamp'],'%Y-%m-%d %H:%M:%S')
            trade_time = trade_date.time()
            trade_date = trade_date.date()
            trade_details = {'fees': 0.0, 'taxes': 0.0, 'pnl': 0.0}
            for det in trade[u'details']:
                if det[u'trade_booking_type'] in [u'Commission',u'Exchange Fee',u'Partner Commission',u'Currency Cut Commission']:
                    trade_details['fees'] = trade_details['fees'] + det[u'trade_booked_amount']
                elif det[u'trade_booking_type'] in ['[Swiss Stamp Duty Foreign]','Tax Commission','[UK PTM Levy]', 'Stamp Duty']:
                    trade_details['taxes'] = trade_details['taxes'] + det[u'trade_booked_amount']
                elif det[u'trade_booking_type'] in ['P/L']:
                    trade_details['pnl'] = trade_details['pnl'] + det[u'trade_booked_amount']
                if not trade_details.has_key('rate'):
                    if det[u'trade_conversion_rate']!=0.0 and det[u'trade_conversion_rate']!=1.0 and det[u'trade_conversion_rate']!=None:
                        trade_details['rate'] = det[u'trade_conversion_rate'] 
            security_code = get_security_code(trade[u'trade_instrument'], trade[u'trade_isin'], trade[u'trade_product'])
            if security_code==None:
                LOGGER.warning("Could not find security: " + trade[u'trade_instrument'] + "/" + trade[u'trade_isin'] + "/" + trade[u'trade_product'])
                continue
            divide = get_security_divisor(security_code)
            buy_cfd = trade[u'trade_product']=='CFDs' and trade[u'trade_buy_sell']=='Bought'
            sell_cfd = trade[u'trade_product']=='CFDs' and trade[u'trade_buy_sell']=='Sold'
            gross_amount = trade[u'trade_amount'] * (trade[u'trade_price'] / (1.0 if divide==None or divide=='' else divide)) * -1.0
            if trade[u'trade_instrument_currency']!=saxo_accounts[trade[u'product_account_id']]['currency'] and not trade_details.has_key('rate'):
                LOGGER.info("\tNo rate but FX needed")
                exchange_rate = get_exchange_rate_price(trade[u'trade_instrument_currency'],saxo_accounts[trade[u'product_account_id']]['currency'],trade_date )
            else:
                exchange_rate = 1.0 if not trade_details.has_key('rate') or trade_details['rate']==0.0 else trade_details['rate']
            final_gross_amount = gross_amount * exchange_rate
            if final_gross_amount<0:
                final_net_amount = final_gross_amount + trade_details['fees'] + trade_details['taxes']
            else:
                final_net_amount = ((final_gross_amount * -1.0) + trade_details['fees'] + trade_details['taxes']) * -1.0
            row = ['','','','','','','',
                       trade_date,
                       trade_date,
                       str(trade_time)[0:5],
                       datetime.datetime.strptime(trade[ u'trade_value_date'],'%Y-%m-%d'),
                       'B' if trade[u'trade_buy_sell']=='Bought' else 'S',
                       guardian_code,
                       security_code, # TRADED SECURITY
                       trade[u'trade_instrument_currency'],
                       '', # ISIN
                       '', # BLOOMBERG
                       '',
                       trade[u'trade_amount'],
                       trade[u'trade_price'],
                       '',
                       exchange_rate if exchange_rate!=1.0 else None,
                       '',
                       'SAXO',
                       'DEPTIT',
                       ('LIQCFD' + saxo_accounts[trade[u'product_account_id']]['currency']) if trade[u'trade_product']=='CFDs' else saxo_accounts[trade[u'product_account_id']]['guardian'],
                       '', # NONE IF BUY OR SELL
                       saxo_accounts[trade[u'product_account_id']]['currency'],
                       gross_amount,'','','','','','','',gross_amount,'',                       
                       final_gross_amount if not buy_cfd else final_net_amount,'','','','','',trade_details['fees'] if not buy_cfd else 0.0, trade_details['taxes'] if not buy_cfd else 0.0, final_net_amount,
                       str(trade[ u'trade_buy_sell']) + " " + str(trade[u'trade_product']) + " of " + str(trade[u'trade_instrument']) + " [" + trade[u'trade_id'] + "]",'','','','','','','','','','','','','',
                       ''
                       ]
            rows.append(row)
            if sell_cfd and trade_details['pnl']!=0.0:
                row = ['','','','','','','',
                       trade_date,
                       trade_date,
                       str(trade_time)[0:5],
                       datetime.datetime.strptime(trade[ u'trade_value_date'],'%Y-%m-%d'),
                       'B' if trade_details['pnl']<0.0 else 'S',
                       guardian_code,
                       'LIQCFD' + saxo_accounts[trade[u'product_account_id']]['currency'],
                       '',
                       '', # ISIN
                       '', # BLOOMBERG
                       '',
                       -1.0 * trade_details['pnl'],
                       '',
                       '',
                       '',
                       '',
                       'SAXO',
                       '',
                       saxo_accounts[trade[u'product_account_id']]['guardian'],
                       '',
                       saxo_accounts[trade[u'product_account_id']]['currency'],
                       trade_details['pnl'],'','','','','','','',trade_details['pnl'],'',
                       trade_details['pnl'],'','','','','','', '', trade_details['pnl'],
                       "PnL for " + str(trade[ u'trade_buy_sell']) + " " + str(trade[u'trade_product']) + " of " + str(trade[u'trade_instrument']),'','','','','','','','','','','','','',
                       ''
                       ]
                LOGGER.info("\tCFD PnL have been found") 
                rows.append(row)
            if (buy_cfd or sell_cfd) and trade_details['taxes']!=0.0:
                prefix = 'Taxes ' if trade_details['fees']<0 else 'Commission'
                row = ['','','','','','','',
                       trade_date,
                       trade_date,
                       str(trade_time)[0:5],
                       datetime.datetime.strptime(trade[ u'trade_value_date'],'%Y-%m-%d'),
                       'DEBIT' if trade_details['fees']<0 else 'CREDIT',
                       guardian_code,
                       saxo_accounts[trade[u'product_account_id']]['currency'],
                       saxo_accounts[trade[u'product_account_id']]['currency'],
                       '', # ISIN
                       '', # BLOOMBERG
                       '',
                       trade_details['taxes'],
                       '',
                       '',
                       '',
                       '',
                       'SAXO',
                       '',
                       saxo_accounts[trade[u'product_account_id']]['guardian'],
                       '',
                       saxo_accounts[trade[u'product_account_id']]['currency'],
                       trade_details['taxes'],'','','','','','','',trade_details['taxes'],'',
                       trade_details['taxes'],'','','','','','', '', trade_details['taxes'],
                       prefix + " for " + str(trade[ u'trade_buy_sell']) + " " + str(trade[u'trade_product']) + " of " + str(trade[u'trade_instrument']),'','','','','','','','','','','','','',
                       ''
                       ]
                LOGGER.info("\tTaxes have been found") 
                rows.append(row)
            if (buy_cfd or sell_cfd) and trade_details['fees']!=0.0:
                prefix = 'Fees ' if trade_details['fees']<0 else 'Commission'
                row = ['','','','','','','',
                       trade_date,
                       trade_date,
                       str(trade_time)[0:5],
                       datetime.datetime.strptime(trade[ u'trade_value_date'],'%Y-%m-%d'),
                       'DEBIT' if trade_details['fees']<0 else 'CREDIT',
                       guardian_code,
                       saxo_accounts[trade[u'product_account_id']]['currency'],
                       saxo_accounts[trade[u'product_account_id']]['currency'],
                       '', # ISIN
                       '', # BLOOMBERG
                       '',
                       trade_details['fees'],
                       '',
                       '',
                       '',
                       '',
                       'SAXO',
                       '',
                       saxo_accounts[trade[u'product_account_id']]['guardian'],
                       '',
                       saxo_accounts[trade[u'product_account_id']]['currency'],
                       trade_details['fees'],'','','','','','','',trade_details['fees'],'',
                       trade_details['fees'],'','','','','','', '', trade_details['fees'],
                       prefix + " for " + str(trade[ u'trade_buy_sell']) + " " + str(trade[u'trade_product']) + " of " + str(trade[u'trade_instrument']),'','','','','','','','','','','','','',
                       ''
                       ]
                LOGGER.info("\tFees have been found")
                rows.append(row)

    simple_xlsx_dump(rows, export_file)
    