'''
Created on Jan 9, 2015

@author: sdejonckheere
'''
from universe.models import SecurityContainer
from utilities.track_token import get_main_track_content, get_closest_value
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
            valuation[key_date] = {'total': {}, 'cash': {}, 'invested': {}, 'pnl': {}, 'fx_pnl': {}, 'movement':{}, 'performance': 0.0}
            for account in container.accounts.filter(~Q(account_type__identifier='ACC_SECURITY')):
                history = get_account_history(account)['data']
                if history!=None:
                    value = valuation_content.get_closest_value(history, work_date, True)
                    if value!=None:
                        if not valuation[key_date]['cash'].has_key(account.currency.short_name):
                            valuation[key_date]['cash'][account.currency.short_name] = 0.0
                        valuation[key_date]['cash'][account.currency.short_name] += value['assets']
            if all_positions.has_key(key_date):
                for position in all_positions[key_date]:
                    if position not in ['increase', 'decrease']:
                        security = SecurityContainer.objects.get(id=position)
                        amount = all_positions[key_date][position]['total'] * all_positions[key_date][position]['price']
                        if not valuation[key_date]['invested'].has_key(security.currency.short_name):
                            valuation[key_date]['invested'][security.currency.short_name] = 0.0
                        valuation[key_date]['invested'][security.currency.short_name] += amount
            start_date = dates.AddDay(start_date, 1)
        set_portfolios_valuation({str(container.id): valuation})