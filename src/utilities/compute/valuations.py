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
        tracks = {}
        if not container.currency.short_name in currencies:
            currencies.append(container.currency.short_name)
        start_date = datetime.date(2014,1,1) if container.inception_date==None else container.inception_date
        today = datetime.date.today()
        valuation = {}
        previsous_key = None
        all_positions = get_positions_portfolio(container)['data']
        while start_date<today:
            work_date = dt.combine(start_date, dt.min.time())
            key_date = str(epoch_time(work_date))
            valuation[key_date] = {'total': {}, 'cash': {}, 'invested': {}, 'pnl': {}, 'fx_pnl': {}, 'movement':{}, 'performance': 0.0}
            for account in container.accounts.filter(~Q(account_type__identifier='ACC_SECURITY')):
                history = get_account_history(account)['data']
                if history!=None:
                    value = valuation_content.get_closest_value(history, work_date, False)
                    if value!=None:
                        if not valuation[key_date]['cash'].has_key(account.currency.short_name):
                            valuation[key_date]['cash'][account.currency.short_name] = 0.0
                        valuation[key_date]['cash'][account.currency.short_name] += value['assets']
            for position_date in sorted(all_positions.keys(), reverse=True):
                if key_date>=position_date:
                    break
                position_date = None
            if position_date!=None:
                for position in all_positions[position_date]:
                    security = SecurityContainer.objects.get(id=position)
                    if not tracks.has_key(position):
                        track = get_main_track_content(security)
                        tracks[position] = track
                    value = get_closest_value(tracks[position], work_date)
                    if value!=None:
                        amount = all_positions[position_date][position]['total'] * value['value']
                        if not valuation[key_date]['invested'].has_key(security.currency.short_name):
                            valuation[key_date]['invested'][security.currency.short_name] = 0.0
                        valuation[key_date]['invested'][security.currency.short_name] += amount
                    else:
                        LOGGER.error('Value is missing for ' + security.name + ' @ ' + str(start_date))
            if previsous_key!=None:
                None
            start_date = dates.AddDay(start_date, 1)
        print valuation
        set_portfolios_valuation({str(container.id): valuation})
    