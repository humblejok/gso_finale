from universe.models import FinancialOperation, Attributes, AccountContainer,\
    PortfolioContainer
from seq_common.utils.dates import epoch_time
import logging
from utilities.valuation_content import set_accounts_history,\
    set_positions_portfolios, set_positions_securities
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
    return operation

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
    if container==None:
        all_operations = FinancialOperation.objects.all().order_by('value_date')
    else:
        all_operations = FinancialOperation.objects.filter(repository__in=container.accounts.all()).order_by('value_date')
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
            if operation.target!=None and operation.operation_type.identifier not in ['OPE_TYPE_BUY', 'OPE_TYPE_SELL', 'OPE_TYPE_BUY_FOP', 'OPE_TYPE_SELL_FOP']:
                target_key = str(operation.target.id)
                if not accounts_history.has_key(target_key):
                    accounts_history[target_key] = {}
                target_account_used = True
                
            if source_account_used:
                if not accounts_history.has_key(source_key):
                    accounts_history[source_key] = {}
                if previous_date.has_key(source_key):
                    accounts_history[source_key][key_date] = accounts_history[source_key][previous_date[source_key]]
                else:
                    accounts_history[source_key][key_date] = {'assets': 0.0, 'mvt_pnl': 0.0, 'mvt_no_pnl': 0.0}
                accounts_history[source_key][key_date]['assets'] += (operation.amount * (-1.0 if target_account_used else 1.0))
                accounts_history[source_key][key_date]['mvt_pnl' if operation.operation_type.identifier=='OPE_TYPE_FEES' else 'mvt_no_pnl'] += (operation.amount * (-1.0 if target_account_used else 1.0))
                previous_date[source_key] = key_date
                
            if target_account_used:
                if previous_date.has_key(target_key):
                    accounts_history[target_key][key_date] = accounts_history[target_key][previous_date[target_key]]
                else:
                    accounts_history[target_key][key_date] = {'assets': 0.0, 'mvt_pnl': 0.0, 'mvt_no_pnl': 0.0}
                accounts_history[target_key][key_date]['assets'] += operation.amount
                accounts_history[target_key][key_date]['mvt_pnl' if operation.operation_type.identifier=='OPE_TYPE_FEES' else 'mvt_no_pnl'] += operation.amount
                previous_date[target_key] = key_date
        else:
            LOGGER.error("No portfolio associated to account")
            continue
    set_accounts_history(accounts_history)
        
def compute_positions(container=None):
    if container==None:
        all_operations = FinancialOperation.objects.filter(operation_type__identifier__in=['OPE_TYPE_BUY','OPE_TYPE_SELL','OPE_TYPE_BUY_FOP','OPE_TYPE_SELL_FOP']).order_by('value_date')
    else:
        all_operations = FinancialOperation.objects.filter(repository__in=container.accounts.all(), operation_type__identifier__in=['OPE_TYPE_BUY','OPE_TYPE_SELL','OPE_TYPE_BUY_FOP','OPE_TYPE_SELL_FOP']).order_by('value_date')
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
        if not securities[security_id].has_key(key_date):
            securities[security_id][key_date] = {'total': 0.0, 'name': operation.target.short_name}
        if not portfolios[portfolio_id].has_key(key_date):
            portfolios[portfolio_id][key_date] = {}
        if not securities[security_id][key_date].has_key(portfolio_id):
            securities[security_id][key_date][portfolio_id] = 0.0
        securities[security_id][key_date][portfolio_id] = securities[security_id][key_date][portfolio_id] + (operation.quantity * (1.0 if operation.operation_type.identifier in ['OPE_TYPE_BUY', 'OPE_TYPE_BUY_FOP'] else -1.0))
        securities[security_id][key_date]['total'] = securities[security_id][key_date]['total'] + (operation.quantity * (1.0 if operation.operation_type.identifier in ['OPE_TYPE_BUY', 'OPE_TYPE_BUY_FOP'] else -1.0))
        if previous_date.has_key(portfolio_id):
            portfolios[portfolio_id][key_date] = { key: portfolios[portfolio_id][previous_date[portfolio_id]][key] for key in portfolios[portfolio_id][previous_date[portfolio_id]]}
        if not portfolios[portfolio_id][key_date].has_key(security_id):
            portfolios[portfolio_id][key_date][security_id] = {'total': 0.0, 'name': operation.target.short_name}
        portfolios[portfolio_id][key_date][security_id]['total'] = portfolios[portfolio_id][key_date][security_id]['total'] + (operation.quantity * (1.0 if operation.operation_type.identifier in ['OPE_TYPE_BUY', 'OPE_TYPE_BUY_FOP'] else -1.0))
        previous_date[portfolio_id] = key_date
    set_positions_portfolios(portfolios)
    set_positions_securities(securities)