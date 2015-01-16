'''
Created on Jan 9, 2015

@author: sdejonckheere
'''
from universe.models import SecurityContainer
import datetime
from utilities.valuation_content import get_positions_portfolio,\
    set_portfolios_valuation, get_account_history
from seq_common.utils.dates import epoch_time
import logging
from seq_common.utils import dates
from django.db.models import Q
from datetime import datetime as dt 
from utilities import valuation_content

LOGGER = logging.getLogger(__name__)

class NativeValuationsComputer():
    def __init__(self):
        LOGGER.info("VALUATIONS Computation will be executed using the CPU")
        
    def compute_daily_valuation(self, container):
        currencies = ['CHF', 'USD', 'EUR']
        if not container.currency.short_name in currencies:
            currencies.append(container.currency.short_name)
        start_date = datetime.date(2014,1,1) if container.inception_date==None else container.inception_date
        today = datetime.date.today()
        valuation = {}
        all_positions = get_positions_portfolio(container)['data']
        while start_date<today:
            work_date = dt.combine(start_date, dt.min.time())
            key_date = str(epoch_time(work_date))
            valuation[key_date] = {'total': {}, 'cash': {}, 'cash_pf': 0.0, 'invested': {}, 'pnl': {}, 'fx_pnl': {}, 'movement':{}, 'performance': 0.0}
            for account in container.accounts.filter(~Q(account_type__identifier='ACC_SECURITY')):
                history = get_account_history(account)['data']
                if history!=None:
                    value = valuation_content.get_closest_value(history, work_date, True)
                    if value!=None:
                        if not valuation[key_date]['cash'].has_key(account.currency.short_name):
                            valuation[key_date]['cash'][account.currency.short_name] = {'portfolio': 0.0, 'account': 0.0}
                        valuation[key_date]['cash'][account.currency.short_name]['account'] += value['assets']
                        valuation[key_date]['cash'][account.currency.short_name]['portfolio'] += value['assets_pf']
                        valuation[key_date]['cash_pf'] += value['assets_pf']
                        if not valuation[key_date].has_key('spot_pf'):
                            valuation[key_date]['spot_pf'] = {}
                        valuation[key_date]['spot_pf'][account.currency.short_name] = value['spot_pf']
            if all_positions.has_key(key_date):
                for position in all_positions[key_date]:
                    if position not in ['increase', 'decrease']:
                        security = SecurityContainer.objects.get(id=position)
                        amount = all_positions[key_date][position]['total'] * all_positions[key_date][position]['price']
                        amount_portfolio = all_positions[key_date][position]['total'] * all_positions[key_date][position]['price_pf']
                        if not valuation[key_date]['invested'].has_key(security.currency.short_name):
                            valuation[key_date]['invested'][security.currency.short_name] = 0.0
                        if not valuation[key_date]['invested'].has_key('portfolio'):
                            valuation[key_date]['invested']['portfolio'] = 0.0
                        valuation[key_date]['invested'][security.currency.short_name] += amount
                        valuation[key_date]['invested']['portfolio'] += amount_portfolio 
            start_date = dates.AddDay(start_date, 1)
        set_portfolios_valuation({str(container.id): valuation})