'''
Created on Jan 9, 2015

@author: sdejonckheere
'''
from universe.models import SecurityContainer, Attributes, TrackContainer,\
    CompanyContainer
import datetime
from utilities.valuation_content import get_positions_portfolio,\
    set_portfolios_valuation, get_account_history
from seq_common.utils.dates import epoch_time, from_epoch
import logging
from seq_common.utils import dates
from django.db.models import Q
from datetime import datetime as dt 
from utilities import valuation_content
from calendar import monthrange
from utilities.track_token import get_track
from utilities.track_content import set_track_content

LOGGER = logging.getLogger(__name__)

PERF_MAPPING = { 'FREQ_DAILY': ['day', 'wtd', 'mtd', 'qtd', 'std', 'ytd', 'si'],
                 'FREQ_WEEKLY': ['wtd', 'mtd', 'qtd', 'std', 'ytd', 'si'],
                 'FREQ_MONTHLY': ['mtd', 'qtd', 'std', 'ytd', 'si'],
                 'FREQ_QUARTERLY': ['qtd', 'std', 'ytd', 'si'],
                 'FREQ_SEMESTERLY': ['std', 'ytd', 'si'],
                 'FREQ_ANNUALLY': ['ytd', 'si']
                }

DATE_MAPPING = {'day': Attributes.objects.get(identifier='FREQ_DAILY', active=True),
                'wtd': Attributes.objects.get(identifier='FREQ_WEEKLY', active=True),
                'mtd': Attributes.objects.get(identifier='FREQ_MONTHLY', active=True),
                'qtd': Attributes.objects.get(identifier='FREQ_QUARTERLY', active=True),
                'std': Attributes.objects.get(identifier='FREQ_SEMESTERLY', active=True),
                'ytd': Attributes.objects.get(identifier='FREQ_ANNUALLY', active=True)
                }

def get_work_date(work_date, frequency):
    frequency_id = frequency.identifier
    if frequency_id=='FREQ_DAILY':
        work_date = dt.combine(work_date, dt.min.time())
    elif frequency_id=='FREQ_WEEKLY':
        work_date = dt.combine(dates.GetEndOfWeek(work_date), dt.min.time())
    elif frequency_id=='FREQ_MONTHLY':
        work_date = dt.combine(dates.GetEndOfMonth(work_date), dt.min.time())
    elif frequency_id=='FREQ_QUARTERLY':
        work_date = dates.GetEndOfMonth(work_date)
        while work_date.month%3!=0:
            work_date = dates.AddDay(work_date, 1)
            work_date = dates.GetEndOfMonth(work_date)
        work_date = dt.combine(work_date, dt.min.time())
    elif frequency_id=='FREQ_SEMESTERLY':
        work_date = dates.GetEndOfMonth(work_date)
        while work_date.month%6!=0:
            work_date = dates.AddDay(work_date, 1)
            work_date = dates.GetEndOfMonth(work_date)
        work_date = dt.combine(work_date, dt.min.time())
    elif frequency_id=='FREQ_ANNUALLY':
        work_date = dates.GetEndOfMonth(work_date)
        while work_date.month%12!=0:
            work_date = dates.AddDay(work_date, 1)
            work_date = dates.GetEndOfMonth(work_date)
        work_date = dt.combine(work_date, dt.min.time())
    return work_date

def get_current_period_duration(work_date, frequency):
    frequency_id = frequency.identifier
    if frequency_id=='FREQ_DAILY':
        return 1
    elif frequency_id=='FREQ_WEEKLY':
        return 7
    elif frequency_id=='FREQ_MONTHLY':
        return monthrange(work_date.year, work_date.month)[1]
    elif frequency_id=='FREQ_QUARTERLY':
        current_quarter = ((work_date.month-1)/3) + 1
        days = 0
        for c_month in range((current_quarter * 3) + 1, ((current_quarter+1) * 3) + 1):
            days += monthrange(work_date.year, c_month)[1]
        return days
    elif frequency_id=='FREQ_SEMESTERLY':
        current_quarter = ((work_date.month-1)/6) + 1
        days = 0
        for c_month in range((current_quarter * 6) + 1, ((current_quarter+1) * 6) + 1):
            days += monthrange(work_date.year, c_month)[1]
        return days
    elif frequency_id=='FREQ_ANNUALLY':
        days = 0
        for c_month in range(1, 13):
            days += monthrange(work_date.year, c_month)[1]
        return days
    
def get_current_date_position(work_date, frequency):
    frequency_id = frequency.identifier
    if frequency_id=='FREQ_DAILY':
        return 1
    elif frequency_id=='FREQ_WEEKLY':
        week_day = work_date.isoweekday()
        return (week_day + 2) if week_day<=5 else (week_day - 5)
    elif frequency_id=='FREQ_MONTHLY':
        return work_date.day
    elif frequency_id=='FREQ_QUARTERLY':
        current_quarter = ((work_date.month-1)/3) + 1
        days = 0
        for c_month in range((current_quarter * 3) + 1, work_date.month + 1):
            if c_month==work_date.month:
                days += work_date.day
            else:
                days += monthrange(work_date.year, c_month)
        return days
    elif frequency_id=='FREQ_SEMESTERLY':
        current_quarter = ((work_date.month-1)/6) + 1
        days = 0
        for c_month in range((current_quarter * 6) + 1, work_date.month + 1):
            if c_month==work_date.month:
                days += work_date.day
            else:
                days += monthrange(work_date.year, c_month)
        return days
    elif frequency_id=='FREQ_ANNUALLY':
        days = 0
        for c_month in range(1, work_date.month + 1):
            if c_month==work_date.month:
                days += work_date.day
            else:
                days += monthrange(work_date.year, c_month)
        return days

class NativeValuationsComputer():
    def __init__(self):
        LOGGER.info("VALUATIONS Computation will be executed using the CPU")

    def generate_tracks(self, container, frequency, valuation):
        LOGGER.info("Computing tracks of " + container.name + " with frequency " + frequency.name)
        perf_type = Attributes.objects.get(identifier='NUM_TYPE_PERF', active=True)
        nav_type = Attributes.objects.get(identifier='NUM_TYPE_NAV', active=True)
        final_status = Attributes.objects.get(identifier='NUM_STATUS_FINAL', active=True)
        official_type = Attributes.objects.get(identifier='PRICE_TYPE_OFFICIAL', active=True)
        finale_company = CompanyContainer.objects.get(name='FinaLE Engine')
        
        nav_track = get_track(container, {'track_type': 'NUM_TYPE_NAV', 'track_frequency':frequency.identifier, 'track_default': False, 'track_datasource': 'DATASOURCE_FINALE'})
        perf_track = get_track(container, {'track_type': 'NUM_TYPE_PERF', 'track_frequency':frequency.identifier, 'track_default': False, 'track_datasource': 'DATASOURCE_FINALE'})
        
        nav_content = []
        perf_content = []
        
        if nav_track==None:
            nav_track = TrackContainer()
            nav_track.effective_container = container
            nav_track.type = nav_type
            nav_track.quality = official_type
            nav_track.source = finale_company
            nav_track.status = final_status
            nav_track.frequency = frequency
            nav_track.frequency_reference = None
            nav_track.save()
        if perf_track==None:
            perf_track = TrackContainer()
            perf_track.effective_container = container
            perf_track.type = perf_type
            perf_track.quality = official_type
            perf_track.source = finale_company
            perf_track.status = final_status
            perf_track.frequency = frequency
            perf_track.frequency_reference = None
            perf_track.save()
        perf_key = PERF_MAPPING[frequency.identifier][0]
        if container.inception_date==None:
            nav_content.append({'date': datetime.datetime(2013,12,31), 'value': 100.0})
        else:
            nav_content.append({'date': dt.combine(dates.AddDay(container.inception_date, -1), dt.min.time()), 'value': 100.0})
            previous = 100.0
        for key_date in sorted(valuation.keys()):
            working_date = dt.combine(from_epoch(long(key_date)), dt.min.time())
            if get_work_date(working_date, frequency)==working_date:
                perf_content.append({'date': working_date, 'value': valuation[key_date]['performances']['mdietz'][perf_key]/100.0})
                previous = previous * (1.0 + valuation[key_date]['performances']['mdietz'][perf_key]/100.0)
                nav_content.append({'date': working_date, 'value':previous})
            
        set_track_content(perf_track, perf_content, True)
        set_track_content(nav_track, nav_content, True)

    def compute_valuation(self, container, frequency):
        #TODO Correct the bug with frequency different of daily
        LOGGER.info("Computing valuation of " + container.name + " with frequency " + frequency.name)
        start_date = datetime.date(2014,1,1) if container.inception_date==None else container.inception_date
        today = datetime.date.today()
        valuation = {}
        all_positions = get_positions_portfolio(container)
        all_positions = all_positions['data'] if all_positions!=None else {}
        previous_key = None
        previous_date = None
        while start_date<today:
            work_date = get_work_date(start_date, frequency)
            key_date = str(epoch_time(work_date))
            period_duration = float(get_current_period_duration(work_date, frequency))
            period_position = float(get_current_date_position(work_date, frequency))
            if not valuation.has_key(key_date):
                valuation[key_date] = {'total': {'portfolio': 0.0}, 'forward': {}, 'forward_pf': 0.0,'cash': {}, 'cash_pf': 0.0, 'spot_pf': {}, 'invested': {}, 'invested_fop':{}, 'pnl': {'portfolio': 0.0}, 'fx_pnl': {}, 'movement':{'portfolio': 0.0, 'portfolio_tw': 0.0}, 'performances': {'mdietz': {'day': 0.0, 'wtd': 0.0, 'mtd': 0.0, 'qtd': 0.0, 'std': 0.0, 'ytd': 0.0}}}
            elif key_date==previous_key:
                valuation[key_date]['cash'] = {}
                valuation[key_date]['forward'] = {}
                valuation[key_date]['cash_pf'] = 0.0
                valuation[key_date]['forward_pf'] = 0.0
                valuation[key_date]['spot_pf'] = {}
                valuation[key_date]['invested'] = {}
            for account in container.accounts.filter(~Q(account_type__identifier='ACC_SECURITY')):
                history = get_account_history(account)
                if history!=None:
                    history = history['data']
                    if not valuation[key_date]['pnl'].has_key(account.currency.short_name):
                        valuation[key_date]['pnl'][account.currency.short_name] = 0.0
                    if not valuation[key_date]['movement'].has_key(account.currency.short_name):
                        valuation[key_date]['movement'][account.currency.short_name] = 0.0
                    if history!=None:
                        value = valuation_content.get_closest_value(history, dt.combine(start_date, dt.min.time()), True)
                        if account.account_type.identifier=='ACC_CURRENT':
                            account_key = 'cash'
                        elif account.account_type.identifier=='ACC_FORWARD':
                            account_key = 'forward'
                        if not valuation[key_date][account_key].has_key(account.currency.short_name):
                            valuation[key_date][account_key][account.currency.short_name] = {'portfolio': 0.0, 'account': 0.0}
                        if not valuation[key_date]['movement'].has_key(account.currency.short_name):
                            valuation[key_date]['movement'][account.currency.short_name] = 0.0
                        if value!=None:
                            valuation[key_date][account_key][account.currency.short_name]['account'] += value['assets']
                            valuation[key_date][account_key][account.currency.short_name]['portfolio'] += value['assets_pf']
                            valuation[key_date][account_key + '_pf'] += value['assets_pf']
                            valuation[key_date]['spot_pf'][account.currency.short_name] = value['spot_pf']
                            valuation[key_date]['movement'][account.currency.short_name] += value['mvt_no_pnl']
                            valuation[key_date]['movement']['portfolio'] += value['mvt_no_pnl_pf']
                            valuation[key_date]['movement']['portfolio_tw'] += value['mvt_no_pnl_pf'] * ((period_duration - period_position + 1.0)/period_duration)
                            valuation[key_date]['pnl'][account.currency.short_name] += value['mvt_pnl']
                            valuation[key_date]['pnl']['portfolio'] += value['mvt_pnl_pf']
            if not valuation[key_date]['invested'].has_key('portfolio'):
                valuation[key_date]['invested']['portfolio'] = 0.0
            if not valuation[key_date]['invested_fop'].has_key('portfolio'):
                valuation[key_date]['invested_fop']['portfolio'] = 0.0
            current_positions = valuation_content.get_closest_value(all_positions, work_date, True)
            if current_positions!=None:
                for position in current_positions:
                    if position not in ['increase', 'decrease', 'increase_fop', 'decrease_fop']:
                        security = SecurityContainer.objects.get(id=position)
                        amount = current_positions[position]['total'] * current_positions[position]['price']
                        amount_portfolio = current_positions[position]['total'] * current_positions[position]['price_pf']
                        if not valuation[key_date]['invested'].has_key(security.currency.short_name):
                            valuation[key_date]['invested'][security.currency.short_name] = 0.0
                        valuation[key_date]['invested'][security.currency.short_name] += amount
                        valuation[key_date]['invested']['portfolio'] += amount_portfolio
                    elif position in ['increase_fop', 'decrease_fop']:
                        valuation[key_date]['invested_fop']['portfolio'] += (current_positions[position]['portfolio'] * (1.0 if position=='increase_fop' else -1.0))
            valuation[key_date]['total']['portfolio'] = valuation[key_date]['cash_pf'] + valuation[key_date]['invested']['portfolio']
            # Modified dietz
            if previous_key!=key_date:
                mdietz_up = valuation[key_date]['total']['portfolio'] - valuation[key_date]['invested_fop']['portfolio'] - (valuation[previous_key]['total']['portfolio'] if previous_key!=None else 0.0)  - valuation[key_date]['movement']['portfolio']
                mdietz_down = (valuation[previous_key]['total']['portfolio'] if previous_key!=None else 0.0) + valuation[key_date]['movement']['portfolio_tw']
                if mdietz_down!=0.0:
                    mdietz = mdietz_up / mdietz_down
                else:
                    mdietz = 0.0
            first = True
            for key_perf in PERF_MAPPING[frequency.identifier]:
                if first:
                    valuation[key_date]['performances']['mdietz'][key_perf] = mdietz * 100.0
                else:
                    if previous_date!=None:
                        if key_perf=='si' or (previous_key!=key_date and get_work_date(previous_date, DATE_MAPPING[key_perf])==get_work_date(start_date, DATE_MAPPING[key_perf])):
                            valuation[key_date]['performances']['mdietz'][key_perf] = (((valuation[previous_key]['performances']['mdietz'][key_perf]/100.0 + 1.0) * (mdietz + 1.0)) - 1.0) * 100.0
                        elif get_work_date(previous_date, DATE_MAPPING[key_perf])!=get_work_date(start_date, DATE_MAPPING[key_perf]):
                            valuation[key_date]['performances']['mdietz'][key_perf] = mdietz * 100.0
                    else:
                        valuation[key_date]['performances']['mdietz'][key_perf] = mdietz * 100.0
                first = False
            if key_date!=previous_key:
                previous_key = key_date
                previous_date = start_date
            start_date = dates.AddDay(start_date, 1)
        set_portfolios_valuation({str(container.id): valuation})
        for wrk_frequency in DATE_MAPPING.values():
            self.generate_tracks(container, wrk_frequency, valuation)

    def compute_daily_valuation(self, container):
        currencies = ['CHF', 'USD', 'EUR']
        if not container.currency.short_name in currencies:
            currencies.append(container.currency.short_name)
        start_date = datetime.date(2014,1,1) if container.inception_date==None else container.inception_date
        today = datetime.date.today()
        valuation = {}
        all_positions = get_positions_portfolio(container)
        all_positions = all_positions['data'] if all_positions!=None else {}
        previous_key = None
        previous_date = None
        while start_date<today:
            work_date = dt.combine(start_date, dt.min.time())
            key_date = str(epoch_time(work_date))
            valuation[key_date] = {'total': {'portfolio': 0.0}, 'cash': {}, 'cash_pf': 0.0, 'spot_pf': {}, 'invested': {}, 'pnl': {'portfolio': 0.0}, 'fx_pnl': {}, 'movement':{'portfolio': 0.0}, 'performances': {'mdietz': {'day': 0.0, 'wtd': 0.0, 'mtd': 0.0, 'ytd': 0.0}}}
            for account in container.accounts.filter(~Q(account_type__identifier='ACC_SECURITY')):
                history = get_account_history(account)['data']
                if not valuation[key_date]['pnl'].has_key(account.currency.short_name):
                    valuation[key_date]['pnl'][account.currency.short_name] = 0.0
                if not valuation[key_date]['movement'].has_key(account.currency.short_name):
                    valuation[key_date]['movement'][account.currency.short_name] = 0.0
                if history!=None:
                    value = valuation_content.get_closest_value(history, work_date, True)
                    if not valuation[key_date]['cash'].has_key(account.currency.short_name):
                        valuation[key_date]['cash'][account.currency.short_name] = {'portfolio': 0.0, 'account': 0.0}
                    if not valuation[key_date]['movement'].has_key(account.currency.short_name):
                        valuation[key_date]['movement'][account.currency.short_name] = 0.0
                    if value!=None:
                        valuation[key_date]['cash'][account.currency.short_name]['account'] += value['assets']
                        valuation[key_date]['cash'][account.currency.short_name]['portfolio'] += value['assets_pf']
                        valuation[key_date]['cash_pf'] += value['assets_pf']
                        valuation[key_date]['spot_pf'][account.currency.short_name] = value['spot_pf']
                        valuation[key_date]['movement'][account.currency.short_name] += value['mvt_no_pnl']
                        valuation[key_date]['movement']['portfolio'] += value['mvt_no_pnl_pf']
                        valuation[key_date]['pnl'][account.currency.short_name] += value['mvt_pnl']
                        valuation[key_date]['pnl']['portfolio'] += value['mvt_pnl_pf']
            if not valuation[key_date]['invested'].has_key('portfolio'):
                valuation[key_date]['invested']['portfolio'] = 0.0
            if all_positions.has_key(key_date):
                for position in all_positions[key_date]:
                    if position not in ['increase', 'decrease']:
                        security = SecurityContainer.objects.get(id=position)
                        amount = all_positions[key_date][position]['total'] * all_positions[key_date][position]['price']
                        amount_portfolio = all_positions[key_date][position]['total'] * all_positions[key_date][position]['price_pf']
                        if not valuation[key_date]['invested'].has_key(security.currency.short_name):
                            valuation[key_date]['invested'][security.currency.short_name] = 0.0
                        valuation[key_date]['invested'][security.currency.short_name] += amount
                        valuation[key_date]['invested']['portfolio'] += amount_portfolio
            valuation[key_date]['total']['portfolio'] = valuation[key_date]['cash_pf'] + valuation[key_date]['invested']['portfolio']
            # Modified dietz
            if previous_key!=None:
                mdietz_up = valuation[key_date]['total']['portfolio'] - valuation[previous_key]['total']['portfolio'] - valuation[key_date]['movement']['portfolio']
                mdietz_down = valuation[previous_key]['total']['portfolio'] + valuation[key_date]['movement']['portfolio']
                if mdietz_down!=0.0:
                    mdietz = mdietz_up / mdietz_down
                else:
                    mdietz = 0.0
                if previous_date.month==start_date.month:
                    valuation[key_date]['performances']['mdietz']['mtd'] = ((valuation[previous_key]['performances']['mdietz']['mtd']/100.0 + 1.0) * (mdietz + 1.0)) - 1.0
                else:
                    valuation[key_date]['performances']['mdietz']['mtd'] = mdietz
                if previous_date.year==start_date.year:
                    valuation[key_date]['performances']['mdietz']['ytd'] = ((valuation[previous_key]['performances']['mdietz']['ytd']/100.0 + 1.0) * (mdietz + 1.0)) - 1.0
                else:
                    valuation[key_date]['performances']['mdietz']['ytd'] = mdietz
            else:
                # Implement fees on day one
                mdietz = 0.0
            valuation[key_date]['performances']['mdietz']['day'] = mdietz * 100.0
            valuation[key_date]['performances']['mdietz']['mtd'] = valuation[key_date]['performances']['mdietz']['mtd'] * 100.0
            valuation[key_date]['performances']['mdietz']['ytd'] = valuation[key_date]['performances']['mdietz']['ytd'] * 100.0
            previous_key = key_date
            previous_date = start_date
            start_date = dates.AddDay(start_date, 1)
        set_portfolios_valuation({str(container.id): valuation})