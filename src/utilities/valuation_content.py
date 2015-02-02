'''
Created on Jan 9, 2015

@author: sdejonckheere
'''
from pymongo.mongo_client import MongoClient
from finale.settings import MONGO_URL
from seq_common.utils.dates import epoch_time, from_epoch

client = MongoClient(MONGO_URL)

valuation = client.valuation


def set_portfolios_valuation(valuations):
    for valuation_id in valuations.keys():
        valuation['valuation_portfolios'].remove({'_id': str(valuation_id)})
        valuation['valuation_portfolios'].insert({'_id': str(valuation_id), 'data': valuations[valuation_id]})

def set_accounts_history(accounts_history):
    for account_id in accounts_history.keys():
        valuation['valuation_accounts'].remove({'_id': str(account_id)})
        valuation['valuation_accounts'].insert({'_id': str(account_id), 'data': accounts_history[account_id]})

def set_positions_securities(positions):
    for security_id in positions.keys():
        valuation['valuation_securities'].remove({'_id': str(security_id)})
        valuation['valuation_securities'].insert({'_id': str(security_id), 'data': positions[security_id]})
    
def set_positions_portfolios(positions):
    for portfolio_id in positions.keys():
        valuation['valuation_pf_securities'].remove({'_id': str(portfolio_id)})
        valuation['valuation_pf_securities'].insert({'_id': str(portfolio_id), 'data': positions[portfolio_id]})

def get_positions_portfolio(portfolio):
    return valuation['valuation_pf_securities'].find_one({'_id': str(portfolio.id)})

def get_account_history(account):
    return valuation['valuation_accounts'].find_one({'_id': str(account.id)})

def get_portfolio_valuations(portfolio):
    return valuation['valuation_portfolios'].find_one({'_id': str(portfolio.id)})

def get_valuation_content_display(content, start_date=None, end_date=None):
    key_start = 0
    if start_date!=None:
        key_start = epoch_time(start_date)
    key_end = float('inf')
    if end_date!=None:
        key_end = epoch_time(end_date)
    all_values = {from_epoch(long(key_date)).strftime('%Y-%m-%d'): content[key_date] for key_date in sorted(content.keys()) if key_start<=long(key_date) and key_end>=long(key_date)}
    return all_values

def get_closest_date(all_data, value_date, epoch_search=True):
    if value_date==None:
        return None
    previous = None
    if epoch_search:
        searched_date = str(epoch_time(value_date))
    elif not isinstance(value_date, basestring):
        searched_date = value_date.strftime('%Y-%m-%d')
    else:
        searched_date = value_date
    key_dates = sorted(all_data.keys())
    for key in key_dates:
        if key==searched_date:
            return key
        elif key>searched_date:
            if previous==None:
                return None
            else:
                return previous
        previous = key
    return None if previous==None else previous

def get_closest_value(all_data, value_date, epoch_search=True):
    if value_date==None:
        return None
    previous = None
    if epoch_search:
        searched_date = str(epoch_time(value_date))
    elif not isinstance(value_date, basestring):
        searched_date = value_date.strftime('%Y-%m-%d')
    else:
        searched_date = value_date
    key_dates = sorted(all_data.keys())
    for key in key_dates:
        if key==searched_date:
            return all_data[key]
        elif key>searched_date:
            if previous==None:
                return None
            else:
                return all_data[previous]
        previous = key
    return None if previous==None else all_data[previous]