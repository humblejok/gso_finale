from universe.models import FinancialOperation, Attributes, AccountContainer,\
    PortfolioContainer, SecurityContainer
from seq_common.utils.dates import epoch_time
import logging
from utilities.valuation_content import set_accounts_history,\
    set_positions_portfolios, set_positions_securities
import copy
from utilities.track_token import get_main_track_content, get_closest_value,\
    get_exchange_rate
import datetime
from datetime import datetime as dt 
from seq_common.utils import dates
from django.db.models import Q

LOGGER = logging.getLogger(__name__)

def create_security_movement(container, source, target, details, label):
    current_account_type = Attributes.objects.get(identifier='ACC_CURRENT', active=True)
    security_account_type = Attributes.objects.get(identifier='ACC_SECURITY', active=True)
    
    operation = FinancialOperation()
    operation.name = label if label!=None else generate_security_movement_label(target, details)
    operation.short_name = generate_security_movement_short_label(target, details)
    operation.status = Attributes.objects.get(identifier='OPE_STATUS_EXECUTED', active=True) if not details.has_key('status') else details['status']
    operation.operation_type = generate_security_movement_operation_type(details)
    operation.creation_date = details['operation_date']
    operation.operator = None
    operation.validator = None
    operation.source = get_account(container, details, current_account_type)
    operation.target = target['security']
    operation.spot = details['spot_rate']
    operation.repository = get_account(container, details, security_account_type)
    operation.quantity = target['quantity']
    operation.amount = target['quantity'] * target['price'] * details['spot_rate']
    operation.price = target['price']
    operation.operation_date = details['trade_date']
    operation.operation_pnl = 0.0
    operation.value_date = details['value_date']
    operation.termination_date = details['value_date']
    operation.associated_operation = None
    operation.save()
    create_expenses(operation, operation.source, details['source_expenses'])
    create_expenses(operation, operation.source, details['target_expenses'])
    return operation

def create_security_dividend(container, source, target, details, label):
    current_account_type = Attributes.objects.get(identifier='ACC_CURRENT', active=True)
    dividend = Attributes.objects.get(identifier='OPE_TYPE_DIVIDEND', active=True)
    
    operation = FinancialOperation()
    operation.name = 'Dividends on security ' + target['security'].name + ' of ' + str(target['price']) + ' per share'
    operation.short_name = 'Dividends on security ' + target['security'].name
    operation.status = Attributes.objects.get(identifier='OPE_STATUS_EXECUTED', active=True) if not details.has_key('status') else details['status']
    operation.operation_type = dividend
    operation.creation_date = details['operation_date']
    operation.operator = None
    operation.validator = None
    operation.source = get_account(container, details, current_account_type)
    operation.target = target['security']
    operation.spot = details['spot_rate']
    operation.repository = None
    operation.quantity = target['quantity']
    operation.amount = target['quantity'] * target['price'] * details['spot_rate']
    operation.price = target['price']
    operation.operation_date = details['trade_date']
    operation.operation_pnl = operation.amount
    operation.value_date = details['value_date']
    operation.termination_date = details['value_date']
    operation.associated_operation = None
    operation.save()
    create_expenses(operation, operation.source, details['source_expenses'])
    create_expenses(operation, operation.source, details['target_expenses'])
    return operation

def create_cash_movement(container, source, target, details, label):
    current_account_type = Attributes.objects.get(identifier='ACC_CURRENT', active=True)
    
    operation = FinancialOperation()
    operation.name = label if label!=None else generate_cash_movement_label(source, target)
    operation.short_name = generate_cash_movement_short_label(source, target)
    operation.status = Attributes.objects.get(identifier='OPE_STATUS_EXECUTED', active=True) if not details.has_key('status') else details['status']
    operation.operation_type = generate_cash_movement_operation_type(source, target, details)
    operation.creation_date = details['operation_date']
    operation.operator = None
    operation.validator = None
    operation.source = get_account(container, source, current_account_type) if source!=None else None
    operation.target = get_account(container, target, current_account_type) if target!=None else None
    operation.spot = generate_cash_movement_spot(source, target, details)
    operation.repository = None
    operation.quantity = None
    operation.amount = get_cash_movement_amount(source, target, details)
    operation.price = None
    operation.operation_date = details['trade_date']
    operation.operation_pnl = 0.0
    operation.value_date = details['value_date']
    operation.termination_date = details['value_date']
    operation.associated_operation = None
    operation.save()
    create_expenses(operation, operation.source, details['source_expenses'])
    create_expenses(operation, operation.target, details['target_expenses'])
    return operation

def create_spot_movement(container, source, target, details, label):
    current_account_type = Attributes.objects.get(identifier='ACC_CURRENT', active=True)
    operation = FinancialOperation()
    operation.name = label if label!=None else generate_spot_movement_label(source, target, details)
    operation.short_name = generate_spot_movement_short_label(source, target, details)
    operation.status = Attributes.objects.get(identifier='OPE_STATUS_EXECUTED', active=True) if not details.has_key('status') else details['status']
    operation.operation_type = generate_spot_movement_operation_type(source, target, details)
    operation.creation_date = details['operation_date']
    operation.operator = None
    operation.validator = None
    operation.source = get_account(container, source, current_account_type)
    operation.target = get_account(container, target, current_account_type)
    operation.spot = details['spot_rate']
    operation.repository = None
    operation.quantity = None
    operation.amount = get_cash_movement_amount(source, target, details)
    operation.price = None
    operation.operation_date = details['trade_date']
    operation.operation_pnl = 0.0
    operation.value_date = details['value_date']
    operation.termination_date = details['value_date']
    operation.associated_operation = None
    operation.save()
    create_expenses(operation, operation.source, details['source_expenses'])
    create_expenses(operation, operation.target, details['target_expenses'])
    return operation

def create_expenses(parent_operation, account, information):
    expenses = ['fees', 'tax', 'commission']
    for expense in expenses:
        if information[expense]!=0.0:
            operation = FinancialOperation()
    
            operation.name = parent_operation.name + ' (' + expense + ')'
            operation.short_name = parent_operation.name + ' (' + expense + ')'
            operation.status = parent_operation.status
            operation.operation_type = Attributes.objects.get(identifier='OPE_TYPE_' + expense.upper(), active=True)
            operation.creation_date = parent_operation.creation_date
            operation.operator = None
            operation.validator = None
            operation.source = account
            operation.target = None
            operation.spot = 1.0
            operation.repository = None
            operation.quantity = None
            operation.amount = -abs(information[expense])
            operation.price = None
            operation.operation_date = parent_operation.operation_date
            operation.operation_pnl = 0.0
            operation.value_date = parent_operation.value_date
            operation.termination_date = parent_operation.termination_date
            operation.associated_operation = operation
    
            operation.save()

def generate_security_movement_operation_type(details):
    return Attributes.objects.get(identifier='OPE_TYPE_' + details['operation'] + ('' if details['impact_pnl'] else '_FOP'), active=True)

def get_cash_movement_amount(source, target, details):
    if source==None and target!=None:
        return abs(details['amount'])
    elif source!=None and target==None:
        return -abs(details['amount'])
    else:
        return abs(details['amount'])

def generate_cash_movement_spot(source, target, details):
    if source==None and target!=None:
        return None
    elif source!=None and target==None:
        return None
    else:
        return abs(details['amount'])/abs(details['initial_amount'])

def get_account(container, description, account_type):
    if description.has_key('account_id') and description['account_id']!=None and not account_type.identifier=='ACC_SECURITY':
        accounts = container.accounts.filter(name=description['account_id'])
    else:
        accounts = container.accounts.filter(currency__short_name=description['currency'], account_type=account_type)
    if accounts.exists():
        return accounts[0]
    else:
        account = AccountContainer()
        account.account_type = account_type
        account.bank = None
        account.currency = Attributes.objects.get(short_name=description['currency'], active=True, type='currency')
        account.name = description['account_id'] if description.has_key('account_id') and description['account_id']!=None and not account_type.identifier=='ACC_SECURITY' else (account_type.name + ' ' + description['currency']) 
        account.short_name = description['account_id'] if description.has_key('account_id') and description['account_id']!=None and not account_type.identifier=='ACC_SECURITY' else (account_type.name + ' ' + description['currency'])
        account.status = Attributes.objects.get(identifier='STATUS_ACTIVE')
        account.save()
        container.accounts.add(account)
        container.save()
        return account

def generate_security_movement_label(target, details):
    return details['operation'] + ' ' + details['quantity'] + ' ' + target['security'].name

def generate_security_movement_short_label(target, details):
    return details['operation'] + ' ' + target['security'].short_name

def generate_spot_movement_label(source, target, details):
    return details['operation'] + ' of ' + source['currency'] + ' to ' + target['currency']

def generate_cash_movement_label(source, target):
    if source==None and target!=None:
        return 'Contribution in ' + target['currency']
    elif source!=None and target==None:
        return 'Withdrawal in ' + source['currency']
    else:
        return 'Transfer of ' + source['currency'] + ' to ' + target['currency']


def generate_spot_movement_short_label(source, target, details):
    return source['currency'] + ' -> ' + target['currency']

def generate_cash_movement_short_label(source, target):
    if source==None and target!=None:
        return target['currency'] + ' contribution'
    elif source!=None and target==None:
        return source['currency'] + ' withdrawal'
    else:
        return source['currency'] + ' -> ' + target['currency']

def generate_spot_movement_operation_type(source, target, details):
    return Attributes.objects.get(identifier='OPE_TYPE_SPOT_' + details['operation'], active=True)

def generate_cash_movement_operation_type(source, target, details):
    if source==None and target!=None:
        if details['cashier']:
            return Attributes.objects.get(identifier='OPE_TYPE_CASH_CONTRIBUTION', active=True)
        else:
            return Attributes.objects.get(identifier='OPE_TYPE_CONTRIBUTION', active=True)
    elif source!=None and target==None:
        if details['impact_pnl']:
            return Attributes.objects.get(identifier='OPE_TYPE_FEES', active=True)
        if details['cashier']:
            return Attributes.objects.get(identifier='OPE_TYPE_CASH_WITHDRAWAL', active=True)
        else:
            return Attributes.objects.get(identifier='OPE_TYPE_WITHDRAWAL', active=True)

def compute_accounts(container=None):
    LOGGER.info("Start computing accounts positions")
    spots = {}
    
    if container==None:
        all_operations = FinancialOperation.objects.filter(~Q(operation_type__identifier__in=['OPE_TYPE_BUY_FOP', 'OPE_TYPE_SELL_FOP']), Q(status__identifier__in=['OPE_STATUS_EXECUTED','OPE_STATUS_CONFIRMED'])).order_by('value_date')
    else:
        all_operations = FinancialOperation.objects.filter(Q(repository__in=container.accounts.all()), ~Q(operation_type__identifier__in=['OPE_TYPE_BUY_FOP', 'OPE_TYPE_SELL_FOP']), Q(status__identifier__in=['OPE_STATUS_EXECUTED','OPE_STATUS_CONFIRMED'])).order_by('value_date')
    accounts_history = {}
    previous_date = {}
    for operation in all_operations:
        target_account_used = False
        source_account_used = True
        try:
            portfolio = PortfolioContainer.objects.filter(accounts__id=operation.source.id)
            source_key = str(operation.source.id)
        except:
            source_account_used = False
            portfolio = PortfolioContainer.objects.filter(accounts__id=operation.target.id)
        if portfolio.exists():
            portfolio = portfolio[0]
           
            key_date = str(epoch_time(operation.value_date))
            if operation.target!=None and operation.operation_type.identifier not in ['OPE_TYPE_BUY', 'OPE_TYPE_SELL', 'OPE_TYPE_BUY_FOP', 'OPE_TYPE_SELL_FOP', 'OPE_TYPE_DIVIDEND']:
                target_key = str(operation.target.id)
                if not accounts_history.has_key(target_key):
                    accounts_history[target_key] = {}
                target_account_used = True
                
            if source_account_used:
                if not accounts_history.has_key(source_key):
                    accounts_history[source_key] = {}
                if previous_date.has_key(source_key):
                    accounts_history[source_key][key_date] = copy.deepcopy(accounts_history[source_key][previous_date[source_key]])
                    accounts_history[source_key][key_date]['mvt_pnl'] = 0.0
                    accounts_history[source_key][key_date]['mvt_no_pnl'] = 0.0
                    accounts_history[source_key][key_date]['fx_pnl'] = 0.0
                else:
                    accounts_history[source_key][key_date] = {'assets': 0.0, 'assets_pf': 0.0, 'mvt_pnl': 0.0, 'mvt_no_pnl': 0.0, 'fx_pnl': 0.0}
                spot_pf = 1.0
                wrk_currency = operation.source.currency.short_name
                if wrk_currency!=portfolio.currency.short_name and not spots.has_key(wrk_currency):
                    spot_track = get_exchange_rate(wrk_currency, portfolio.currency.short_name)
                    if not spots.has_key(wrk_currency):
                        spots[wrk_currency] = {}
                    spots[wrk_currency][portfolio.currency.short_name] = spot_track
                if wrk_currency!=portfolio.currency.short_name and spots.has_key(wrk_currency) and spots[wrk_currency].has_key(portfolio.currency.short_name):
                    value = get_closest_value(spots[wrk_currency][portfolio.currency.short_name], operation.value_date)
                    if value!=None:
                        spot_pf = value['value']
                    
                computed_amount = operation.amount * (-1.0 if target_account_used or operation.operation_type.identifier in ['OPE_TYPE_BUY'] else 1.0)
                accounts_history[source_key][key_date]['assets'] += computed_amount
                accounts_history[source_key][key_date]['assets_pf'] += computed_amount * spot_pf
                accounts_history[source_key][key_date]['mvt_pnl' if operation.operation_type.identifier in ['OPE_TYPE_FEES', 'OPE_TYPE_TAX', 'OPE_TYPE_COMMISSION', 'OPE_TYPE_DIVIDEND'] else 'mvt_no_pnl'] += computed_amount
                previous_date[source_key] = key_date
                
            if target_account_used:
                if previous_date.has_key(target_key):
                    accounts_history[target_key][key_date] = copy.deepcopy(accounts_history[target_key][previous_date[target_key]])
                    accounts_history[target_key][key_date]['mvt_pnl'] = 0.0
                    accounts_history[target_key][key_date]['mvt_no_pnl'] = 0.0
                else:
                    accounts_history[target_key][key_date] = {'assets': 0.0, 'assets_pf': 0.0,'mvt_pnl': 0.0, 'mvt_no_pnl': 0.0}
                spot_pf = 1.0
                wrk_currency = operation.target.currency.short_name
                if wrk_currency!=portfolio.currency.short_name and not spots.has_key(wrk_currency):
                    spot_track = get_exchange_rate(wrk_currency, portfolio.currency.short_name)
                    if not spots.has_key(wrk_currency):
                        spots[wrk_currency] = {}
                    spots[wrk_currency][portfolio.currency.short_name] = spot_track
                if wrk_currency!=portfolio.currency.short_name and spots.has_key(wrk_currency) and spots[wrk_currency].has_key(portfolio.currency.short_name):
                    value = get_closest_value(spots[wrk_currency][portfolio.currency.short_name], operation.value_date)
                    if value!=None:
                        spot_pf = value['value']
                computed_amount = operation.amount * (operation.spot if operation.spot!=None else 1.0)
                accounts_history[target_key][key_date]['assets'] += computed_amount
                accounts_history[target_key][key_date]['assets_pf'] += computed_amount * spot_pf
                accounts_history[target_key][key_date]['spot_pf'] = spot_pf
                accounts_history[target_key][key_date]['mvt_pnl' if operation.operation_type.identifier=='OPE_TYPE_FEES' else 'mvt_no_pnl'] += computed_amount
                previous_date[target_key] = key_date
        else:
            LOGGER.error("No portfolio associated to account")
            continue
    LOGGER.info("Completing accounts positions")
    # Complete
    for account_id in accounts_history.keys():
        portfolio = PortfolioContainer.objects.filter(accounts__id=account_id)
        account = AccountContainer.objects.get(id=account_id)
        portfolio = portfolio[0]
        
        start_date = portfolio.inception_date
        if start_date==None:
            start_date = datetime.date(2014,1,1)
        today = datetime.date.today()
        
        movements = sorted(accounts_history[account_id].keys(), reverse=True)
        while start_date<today:
            work_date = dt.combine(start_date, dt.min.time())
            key_date = str(epoch_time(work_date))
            for account_date in movements:
                if key_date>=account_date:
                    break
                account_date = None
            if account_date!=None and key_date!=account_date:
                spot_pf = 1.0
                wrk_currency = account.currency.short_name
                if wrk_currency!=portfolio.currency.short_name and not spots.has_key(wrk_currency):
                    spot_track = get_exchange_rate(wrk_currency, portfolio.currency.short_name)
                    if not spots.has_key(wrk_currency):
                        spots[wrk_currency] = {}
                    spots[wrk_currency][portfolio.currency.short_name] = spot_track
                if wrk_currency!=portfolio.currency.short_name and spots.has_key(wrk_currency) and spots[wrk_currency].has_key(portfolio.currency.short_name):
                    value = get_closest_value(spots[wrk_currency][portfolio.currency.short_name], work_date)
                    if value!=None:
                        spot_pf = value['value']
                accounts_history[account_id][key_date] = copy.deepcopy(accounts_history[account_id][account_date])
                accounts_history[account_id][key_date]['assets_pf'] = accounts_history[account_id][key_date]['assets'] * spot_pf
                accounts_history[account_id][key_date]['spot_pf'] = spot_pf
            start_date = dates.AddDay(start_date, 1)
    LOGGER.info("Accounts positions computed")
    set_accounts_history(accounts_history)
    LOGGER.info("Accounts positions stored")
        
def compute_positions(container=None):
    LOGGER.info("Start computing securities positions")
    if container==None:
        all_operations = FinancialOperation.objects.filter(operation_type__identifier__in=['OPE_TYPE_BUY','OPE_TYPE_SELL','OPE_TYPE_BUY_FOP','OPE_TYPE_SELL_FOP']).order_by('value_date')
    else:
        all_operations = FinancialOperation.objects.filter(repository__in=container.accounts.all(), operation_type__identifier__in=['OPE_TYPE_BUY','OPE_TYPE_SELL','OPE_TYPE_BUY_FOP','OPE_TYPE_SELL_FOP']).order_by('value_date')
        
    tracks = {}
    spots = {}
    
    portfolios = {}
    securities = {}
    previous_date = {}
    for operation in all_operations:
        portfolio = PortfolioContainer.objects.filter(accounts__id=operation.repository.id)
        if portfolio.exists():
            portfolio = portfolio[0]
        else:
            LOGGER.error("No portfolio associated to account")
            continue
        key_date = str(epoch_time(operation.value_date))
        security_id = str(operation.target.id)
        
        portfolio_id = str(portfolio.id)
        if not securities.has_key(security_id):
            securities[security_id] = {}
        if not portfolios.has_key(portfolio_id):
            portfolios[portfolio_id] = {}
        if previous_date.has_key(security_id):
            securities[security_id][key_date] = copy.deepcopy(securities[security_id][previous_date[security_id]])
        if not securities[security_id].has_key(key_date):
            securities[security_id][key_date] = {'total': 0.0, 'name': operation.target.short_name}
        if not portfolios[portfolio_id].has_key(key_date):
            portfolios[portfolio_id][key_date] = {}
        if not securities[security_id][key_date].has_key(portfolio_id):
            securities[security_id][key_date][portfolio_id] = 0.0
        securities[security_id][key_date][portfolio_id] = securities[security_id][key_date][portfolio_id] + (operation.quantity * (1.0 if operation.operation_type.identifier in ['OPE_TYPE_BUY', 'OPE_TYPE_BUY_FOP'] else -1.0))
        securities[security_id][key_date]['total'] = securities[security_id][key_date]['total'] + (operation.quantity * (1.0 if operation.operation_type.identifier in ['OPE_TYPE_BUY', 'OPE_TYPE_BUY_FOP'] else -1.0))
        if previous_date.has_key(portfolio_id):
            portfolios[portfolio_id][key_date] = copy.deepcopy(portfolios[portfolio_id][previous_date[portfolio_id]])
            if previous_date!=key_date:
                if portfolios[portfolio_id][key_date].has_key('increase'):
                    del portfolios[portfolio_id][key_date]['increase']
                if portfolios[portfolio_id][key_date].has_key('decrease'):
                    del portfolios[portfolio_id][key_date]['decrease']
        if not portfolios[portfolio_id][key_date].has_key(security_id):
            portfolios[portfolio_id][key_date][security_id] = {'total': 0.0, 'name': operation.target.short_name, 'price': 0.0, 'price_pf': 0.0, 'price_date': None}
        if not portfolios[portfolio_id][key_date].has_key('increase'):
            portfolios[portfolio_id][key_date]['increase'] = {}
        if not portfolios[portfolio_id][key_date].has_key('decrease'):
            portfolios[portfolio_id][key_date]['decrease'] = {}
        computed_amount = operation.quantity * (1.0 if operation.operation_type.identifier in ['OPE_TYPE_BUY', 'OPE_TYPE_BUY_FOP'] else -1.0)
        portfolios[portfolio_id][key_date][security_id]['total'] += computed_amount
        
        portfolio_movement = portfolios[portfolio_id][key_date]['increase' if operation.operation_type.identifier in ['OPE_TYPE_BUY', 'OPE_TYPE_BUY_FOP'] else 'decrease']
        if not portfolio_movement.has_key(operation.target.currency.short_name):
            portfolio_movement[operation.target.currency.short_name] = 0.0
        portfolio_movement[operation.target.currency.short_name] += operation.amount
        for inner_security in portfolios[portfolio_id][key_date].keys():
            if inner_security not in ['increase', 'decrease']:
                inner_container = SecurityContainer.objects.get(id=inner_security)
                if not tracks.has_key(inner_security):
                    track = get_main_track_content(inner_container)
                    tracks[inner_security] = track
                value = get_closest_value(tracks[inner_security], operation.value_date)
                if value==None:
                    LOGGER.error("No NAV available for " + operation.target.name + " as of " + key_date)
                    break
                portfolios[portfolio_id][key_date][inner_security]['price'] = value['value']
                spot_pf = 1.0
                if inner_container.currency.short_name!=portfolio.currency.short_name and not spots.has_key(inner_container.currency.short_name):
                    spot_track = get_exchange_rate(inner_container.currency.short_name, portfolio.currency.short_name)
                    if not spots.has_key(inner_container.currency.short_name):
                        spots[inner_container.currency.short_name] = {}
                    spots[inner_container.currency.short_name][portfolio.currency.short_name] = spot_track
                if inner_container.currency.short_name!=portfolio.currency.short_name and spots.has_key(inner_container.currency.short_name) and spots[inner_container.currency.short_name].has_key(portfolio.currency.short_name):
                    value = get_closest_value(spots[inner_container.currency.short_name][portfolio.currency.short_name], operation.value_date)
                    if value!=None:
                        spot_pf = value['value']
                portfolios[portfolio_id][key_date][inner_security]['price_pf'] = portfolios[portfolio_id][key_date][inner_security]['price'] * spot_pf
                portfolios[portfolio_id][key_date][inner_security]['price_date'] = value['date'].strftime('%Y-%m-%d')
        previous_date[portfolio_id] = key_date
        previous_date[security_id] = key_date
    LOGGER.info("Completing securities positions")
    # Complete
    for portfolio_id in portfolios:
        movements = sorted(portfolios[portfolio_id].keys(), reverse=True)
        portfolio = PortfolioContainer.objects.get(id=portfolio_id)
        start_date = portfolio.inception_date
        if start_date==None:
            start_date = datetime.date(2014,1,1)
        today = datetime.date.today()
        while start_date<today:
            work_date = dt.combine(start_date, dt.min.time())
            key_date = str(epoch_time(work_date))
            for position_date in movements:
                if key_date>=position_date:
                    break
                position_date = None
            if position_date!=None and key_date!=position_date:
                portfolios[portfolio_id][key_date] = copy.deepcopy(portfolios[portfolio_id][position_date])
                if portfolios[portfolio_id][key_date].has_key('increase'):
                    del portfolios[portfolio_id][key_date]['increase']
                if portfolios[portfolio_id][key_date].has_key('decrease'):
                    del portfolios[portfolio_id][key_date]['decrease']
                for inner_security in portfolios[portfolio_id][key_date].keys():
                    inner_container = SecurityContainer.objects.get(id=inner_security)
                    if not tracks.has_key(inner_security):
                        track = get_main_track_content(inner_container)
                        tracks[inner_security] = track
                    value = get_closest_value(tracks[inner_security], work_date)
                    if value==None:
                        LOGGER.error("No NAV available for " +portfolios[portfolio_id][key_date][inner_security]['name'] + " as of " + key_date)
                        break
                    portfolios[portfolio_id][key_date][inner_security]['price'] = value['value']
                    
                    spot_pf = 1.0
                    if inner_container.currency.short_name!=portfolio.currency.short_name and not spots.has_key(inner_container.currency.short_name):
                        spot_track = get_exchange_rate(inner_container.currency.short_name, portfolio.currency.short_name)
                        if not spots.has_key(inner_container.currency.short_name):
                            spots[inner_container.currency.short_name] = {}
                        spots[inner_container.currency.short_name][portfolio.currency.short_name] = spot_track
                    if inner_container.currency.short_name!=portfolio.currency.short_name and spots.has_key(inner_container.currency.short_name) and spots[inner_container.currency.short_name].has_key(portfolio.currency.short_name):
                        value = get_closest_value(spots[inner_container.currency.short_name][portfolio.currency.short_name], work_date)
                        if value!=None:
                            spot_pf = value['value']
                    portfolios[portfolio_id][key_date][inner_security]['price_pf'] = portfolios[portfolio_id][key_date][inner_security]['price'] * spot_pf
                    portfolios[portfolio_id][key_date][inner_security]['price_date'] = value['date'].strftime('%Y-%m-%d')
            start_date = dates.AddDay(start_date, 1)
            
        portfolios[portfolio_id]
    LOGGER.info("Securities positions computed")
    set_positions_portfolios(portfolios)
    LOGGER.info("Securities positions (portfolio view) stored")
    set_positions_securities(securities)
    LOGGER.info("Securities positions (securities view) stored")