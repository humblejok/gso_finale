from universe.models import FinancialOperation, Attributes, AccountContainer,\
    PortfolioContainer, SecurityContainer
from seq_common.utils.dates import epoch_time, from_epoch
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
from utilities.security_content import get_price_divisor
from finale.utils import get_effective_instance

LOGGER = logging.getLogger(__name__)

def create_forward_operation(container, source, target, details, label):
    current_account_type = Attributes.objects.get(identifier='ACC_CURRENT', active=True)
    forward_account_type = Attributes.objects.get(identifier='ACC_FORWARD', active=True)
    
    open_operation = FinancialOperation()
    open_operation.name = "[OPEN] " + label if label!=None else generate_forward_open_label(source, target, details)
    open_operation.short_name = generate_forward_open_short_label(source, target, details)
    open_operation.status = Attributes.objects.get(identifier='OPE_STATUS_EXECUTED', active=True) if not details.has_key('status') else details['status']
    open_operation.operation_type = generate_spot_movement_operation_type(source, target, details)
    open_operation.creation_date = details['operation_date']
    open_operation.operator = None
    open_operation.validator = None
    open_operation.source = get_account(container, source, forward_account_type)
    open_operation.target = get_account(container, target, forward_account_type)
    open_operation.spot = details['spot_rate']
    open_operation.repository = None
    open_operation.quantity = None
    open_operation.amount = get_forward_amount(source, details)
    open_operation.price = None
    open_operation.operation_date = details['trade_date']
    open_operation.operation_pnl = 0.0
    open_operation.value_date = details['trade_date']
    open_operation.termination_date = details['trade_date']
    open_operation.associated_operation = None
    open_operation.save()
    create_expenses(open_operation, open_operation.source, details['source_expenses'])
    create_expenses(open_operation, open_operation.target, details['target_expenses'])
    
    close_operation = FinancialOperation()
    close_operation.name = "[CLOSE] " + label if label!=None else generate_forward_close_label(source, target, details)
    close_operation.short_name = generate_forward_close_short_label(source, target, details)
    close_operation.status = Attributes.objects.get(identifier='OPE_STATUS_EXECUTED', active=True) if not details.has_key('status') else details['status']
    close_operation.operation_type = generate_spot_movement_operation_type(target, source, details)
    close_operation.creation_date = details['operation_date']
    close_operation.operator = None
    close_operation.validator = None
    close_operation.source = get_account(container, source, forward_account_type)
    close_operation.target = get_account(container, target, forward_account_type)
    close_operation.spot = details['spot_rate']
    close_operation.repository = None
    close_operation.quantity = None
    close_operation.amount = -get_forward_amount(source, details)
    close_operation.price = None
    close_operation.operation_date = details['value_date']
    close_operation.operation_pnl = 0.0
    close_operation.value_date = details['value_date']
    close_operation.termination_date = details['value_date']
    close_operation.associated_operation = None
    close_operation.save()
    
    spot_operation = FinancialOperation()
    spot_operation.name = "[FWD EXEC] " + label if label!=None else generate_forward_open_label(source, target, details)
    spot_operation.short_name = generate_forward_open_short_label(source, target, details)
    spot_operation.status = Attributes.objects.get(identifier='OPE_STATUS_EXECUTED', active=True) if not details.has_key('status') else details['status']
    spot_operation.operation_type = generate_spot_movement_operation_type(source, target, details)
    spot_operation.creation_date = details['operation_date']
    spot_operation.operator = None
    spot_operation.validator = None
    # Clean account ids
    source['account_id'] = None
    target['account_id'] = None 
    spot_operation.source = get_account(container, source, current_account_type)
    spot_operation.target = get_account(container, target, current_account_type)
    spot_operation.spot = details['spot_rate'] if details['operation']=='BUY' else 1.0/details['spot_rate']
    spot_operation.repository = None
    spot_operation.quantity = None
    spot_operation.amount = -get_forward_amount(source, details)
    spot_operation.price = None
    spot_operation.operation_date = details['trade_date']
    spot_operation.operation_pnl = 0.0
    spot_operation.value_date = details['value_date']
    spot_operation.termination_date = details['value_date']
    spot_operation.associated_operation = None
    spot_operation.save()
    
    
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
    operation.source = get_account(container, details, current_account_type) if details['impact_pnl'] else None
    operation.target = target['security']
    if operation.target.status.identifer!='STATUS_ACTIVE':
        # Status cannot be executed on a pending security
        operation.status = Attributes.objects.get(identifier='OPE_STATUS_PENDING', active=True) if not details.has_key('status') else details['status']
    operation.spot = details['spot_rate']
    operation.repository = get_account(container, details, security_account_type)
    operation.quantity = target['quantity']
    used_price = target['price']
    if not details['impact_pnl'] and (used_price==None or used_price==0.0):
        track = get_main_track_content(target['security'])
        value = get_closest_value(track, dt.strptime(details['trade_date'], '%Y-%m-%d'))
        if value==None:
            LOGGER.warn(target['security'].name + " - Transaction does not have a correct price but no valid price could be found.")
            used_price = 0.0
        else:
            LOGGER.warn(target['security'].name + " - Transaction does not have a correct price but a valid price could be found.")
            used_price = value['value']
    divisor = get_price_divisor(target['security'])
    operation.amount = (target['quantity'] * used_price * details['spot_rate']) / divisor
    operation.price = target['price']
    operation.operation_date = details['trade_date']
    operation.operation_pnl = 0.0
    operation.value_date = details['value_date']
    operation.termination_date = details['value_date']
    operation.associated_operation = None
    operation.save()
    if details['impact_pnl']:
        create_expenses(operation, operation.source, details['source_expenses'])
        create_expenses(operation, operation.source, details['target_expenses'])
    if details.has_key('accrued_interest'):
        if details['accrued_interest'].has_key('source') and details['accrued_interest']['source']!=None and details['accrued_interest']['source']!=0.0:
            create_accrued(operation, operation.source, details['accrued_interest']['source'])
        if details['accrued_interest'].has_key('target') and details['accrued_interest']['target']!=None and details['accrued_interest']['target']!=0.0:
            create_accrued(operation, operation.source, details['accrued_interest']['target'])
    return operation

def create_security_credit(container, source, target, details, label, is_dividend=True):
    current_account_type = Attributes.objects.get(identifier='ACC_CURRENT', active=True)
    operation_type = Attributes.objects.get(identifier='OPE_TYPE_DIVIDEND' if is_dividend else 'OPE_TYPE_COUPON', active=True)
    
    operation = FinancialOperation()
    operation.name = ('Dividends' if operation_type.identifier=='OPE_TYPE_DIVIDEND'  else 'Coupon') + ' on security ' + target['security'].name + ' of ' + str(target['price']) + ' per share'
    operation.short_name =('Dividends' if operation_type.identifier=='OPE_TYPE_DIVIDEND'  else 'Coupon') + ' on security ' + target['security'].name
    operation.status = Attributes.objects.get(identifier='OPE_STATUS_EXECUTED', active=True) if not details.has_key('status') else details['status']
    operation.operation_type = operation_type
    operation.creation_date = details['operation_date']
    operation.operator = None
    operation.validator = None
    operation.source = get_account(container, details, current_account_type)
    operation.target = target['security']
    operation.spot = details['spot_rate']
    operation.repository = None
    
    divisor = get_price_divisor(target['security'])

    operation.quantity = target['quantity']
    operation.amount = target['quantity'] * target['price'] * details['spot_rate'] / divisor
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

def create_investment(container, source, target, details, label):
    current_account_type = Attributes.objects.get(identifier='ACC_CURRENT', active=True)
    
    operation = FinancialOperation()
    operation.name = label if label!=None else generate_investment_label(target, details)
    operation.short_name = generate_investment_short_label(target, details)
    operation.status = Attributes.objects.get(identifier='OPE_STATUS_EXECUTED', active=True) if not details.has_key('status') else details['status']
    operation.operation_type = generate_investment_type(source, target, details)
    operation.creation_date = details['operation_date']
    operation.operator = None
    operation.validator = None
    operation.source = None
    operation.target = get_account(container, target, current_account_type) if target!=None else None
    operation.spot = None
    operation.repository = None
    operation.quantity = None
    operation.amount = target['quantity'] * target['price'] * (1.0 if details['operation']=='BUY' else -1.0)
    operation.price = None
    operation.operation_date = details['trade_date']
    operation.operation_pnl = 0.0
    operation.value_date = details['value_date']
    operation.termination_date = details['value_date']
    operation.associated_operation = None
    operation.save()
    create_expenses(operation, operation.target, details['target_expenses'])
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

def create_transfer(container, source, target, details, label):
    current_account_type = Attributes.objects.get(identifier='ACC_CURRENT', active=True)
    operation = FinancialOperation()
    operation.name = label if label!=None else generate_spot_movement_label(source, target, details)
    operation.short_name = generate_spot_movement_short_label(source, target, details)
    operation.status = Attributes.objects.get(identifier='OPE_STATUS_EXECUTED', active=True) if not details.has_key('status') else details['status']
    operation.operation_type = Attributes.objects.get(identifier='OPE_TYPE_INTERNAL_TRANSFER')
    operation.creation_date = details['operation_date']
    operation.operator = None
    operation.validator = None
    operation.source = get_account(container, source, current_account_type)
    operation.target = get_account(container, target, current_account_type)
    operation.spot = None
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


def create_accrued(parent_operation, account, information):
    operation = FinancialOperation()

    operation.name = parent_operation.name + ' (interest re-payment)'
    operation.short_name = parent_operation.name + ' (interest re-payment)'
    operation.status = parent_operation.status
    operation.operation_type = Attributes.objects.get(identifier='OPE_TYPE_ACCRUED_PAYMENT', active=True)
    operation.creation_date = parent_operation.creation_date
    operation.operator = None
    operation.validator = None
    operation.source = account
    operation.target = None
    operation.spot = 1.0
    operation.repository = None
    operation.quantity = None
    operation.amount = information
    operation.price = None
    operation.operation_date = parent_operation.operation_date
    operation.operation_pnl = 0.0
    operation.value_date = parent_operation.value_date
    operation.termination_date = parent_operation.termination_date
    operation.associated_operation = operation

    operation.save()

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

def get_forward_amount(information, details): 
    return information['amount']
    
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
    account_attribute = Attributes.objects.get(active=True, identifier='CONT_ACCOUNT')
    if description.has_key('account_id') and description['account_id']!=None and account_type.identifier not in ['ACC_SECURITY','ACC_FORWARD']:
        if isinstance(description['account_id'], int):
            accounts = container.accounts.filter(id=description['account_id'])
        else:
            accounts = container.accounts.filter(name=description['account_id'])
    else:
        accounts = container.accounts.filter(currency__short_name=description['currency'], account_type=account_type)
    if accounts.exists():
        return accounts[0]
    else:
        account = AccountContainer()
        account.type = account_attribute
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

def generate_forward_open_label(source, target, details):
    return 'Forward opening ' + details['operation'] + ' of ' + source['currency'] + ' to ' + target['currency']

def generate_forward_open_short_label(source, target, details):
    return 'Open fwd ' + details['operation'] + ' ' + source['currency'] + ' -> ' + target['currency']

def generate_forward_close_label(source, target, details):
    return 'Forward closing ' + details['operation'] + ' of ' + source['currency'] + ' to ' + target['currency']

def generate_forward_close_short_label(source, target, details):
    return 'Close fwd' + details['operation'] + ' ' + source['currency'] + ' -> ' + target['currency']

def generate_security_movement_label(target, details):
    return details['operation'] + ' ' + str(target['quantity']) + ' ' + target['security'].name

def generate_security_movement_short_label(target, details):
    return details['operation'] + ' ' + target['security'].short_name

def generate_spot_movement_label(source, target, details):
    return details['operation'] + ' of ' + source['currency'] + ' to ' + target['currency']

def generate_investment_label(target, details):
    if details['operation']=='BUY':
        return 'Subscription of ' + str(target['quantity']) + ' @ ' + str(target['price'])
    else:
        return 'Redemption of ' + str(target['quantity']) + ' @ ' + str(target['price'])

def generate_investment_short_label(target, details):
    if details['operation']=='BUY':
        return 'Sub. ' + str(target['quantity']) + ' @ ' + str(target['price'])
    else:
        return 'Red. ' + str(target['quantity']) + ' @ ' + str(target['price'])

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

def generate_investment_type(source, target, details):
    if details['operation']=='BUY':
        return Attributes.objects.get(identifier='OPE_TYPE_SUB', active=True)
    else:
        return Attributes.objects.get(identifier='OPE_TYPE_RED', active=True)

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

def compute_account_details(portfolio, operation, spots, accounts_history, current_account_key,
                            previous_date, key_date, is_source, target_used):
    if not accounts_history.has_key(current_account_key):
        accounts_history[current_account_key] = {}
    if previous_date.has_key(current_account_key):
        accounts_history[current_account_key][key_date] = copy.deepcopy(accounts_history[current_account_key][previous_date[current_account_key]])
        if key_date!=previous_date[current_account_key]:
            accounts_history[current_account_key][key_date]['fx_pnl'] = 0.0
            accounts_history[current_account_key][key_date]['mvt_pnl'] = 0.0
            accounts_history[current_account_key][key_date]['mvt_no_pnl'] = 0.0
            accounts_history[current_account_key][key_date]['mvt_pnl_pf'] = 0.0
            accounts_history[current_account_key][key_date]['mvt_no_pnl_pf'] = 0.0
    else:
        accounts_history[current_account_key][key_date] = {'assets': 0.0, 'assets_pf': 0.0,'mvt_pnl': 0.0, 'mvt_no_pnl': 0.0, 'mvt_pnl_pf': 0.0, 'mvt_no_pnl_pf': 0.0}
    spot_pf = 1.0
    if is_source:
        wrk_currency = operation.source.currency.short_name
    else:
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
    if is_source:
        multiplier = -1.0 if target_used or operation.operation_type.identifier in ['OPE_TYPE_BUY', 'OPE_TYPE_BUY_FOP'] else 1.0
    else:
        multiplier = operation.spot if operation.spot!=None else 1.0
    computed_amount = operation.amount * multiplier
    accounts_history[current_account_key][key_date]['assets'] += computed_amount
    accounts_history[current_account_key][key_date]['assets_pf'] = accounts_history[current_account_key][key_date]['assets'] * spot_pf
    accounts_history[current_account_key][key_date]['spot_pf'] = spot_pf
    if operation.operation_type.identifier not in ['OPE_TYPE_BUY', 'OPE_TYPE_SELL', 'OPE_TYPE_BUY_FOP', 'OPE_TYPE_SELL_FOP']:
        operation.source = get_effective_instance(operation.source)
        operation.target = get_effective_instance(operation.target)
        if (operation.source==None or (operation.source.type.identifier=='CONT_ACCOUNT' and not operation.source.account_type.identifier=='ACC_FORWARD')) and (operation.target==None or (operation.target.type.identifier=='CONT_ACCOUNT' and not operation.target.account_type.identifier=='ACC_FORWARD')):
            accounts_history[current_account_key][key_date]['mvt_pnl' if operation.operation_type.identifier in ['OPE_TYPE_FEES','OPE_TYPE_ACCRUED_PAYMENT','OPE_TYPE_COUPON', 'OPE_TYPE_DIVIDEND'] else 'mvt_no_pnl'] += computed_amount
            accounts_history[current_account_key][key_date]['mvt_pnl_pf' if operation.operation_type.identifier in ['OPE_TYPE_FEES','OPE_TYPE_ACCRUED_PAYMENT','OPE_TYPE_COUPON', 'OPE_TYPE_DIVIDEND'] else 'mvt_no_pnl_pf'] += computed_amount * spot_pf
    previous_date[current_account_key] = key_date
    previous_date[current_account_key] = key_date

def compute_accounts(container=None):
    LOGGER.info("Start computing accounts positions")
    spots = {}
    if container==None:
        all_operations = FinancialOperation.objects.filter(~Q(operation_type__identifier__in=['OPE_TYPE_BUY_FOP', 'OPE_TYPE_SELL_FOP']), Q(status__identifier__in=['OPE_STATUS_EXECUTED','OPE_STATUS_CONFIRMED'])).order_by('value_date')
    else:
        accounts = container.accounts.all()
        accounts_ids = [account.id for account in accounts]
        all_operations = FinancialOperation.objects.filter(~Q(operation_type__identifier__in=['OPE_TYPE_BUY_FOP', 'OPE_TYPE_SELL_FOP']), Q(repository__id__in=accounts_ids) | Q(source__id__in=accounts_ids) | Q(target__id__in=accounts_ids), Q(status__identifier__in=['OPE_STATUS_EXECUTED','OPE_STATUS_CONFIRMED'])).order_by('value_date')
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
            if operation.target!=None and operation.operation_type.identifier not in ['OPE_TYPE_BUY', 'OPE_TYPE_SELL', 'OPE_TYPE_BUY_FOP', 'OPE_TYPE_SELL_FOP', 'OPE_TYPE_DIVIDEND', 'OPE_TYPE_COUPON']:
                target_key = str(operation.target.id)
                if not accounts_history.has_key(target_key):
                    accounts_history[target_key] = {}
                target_account_used = True
                
            if source_account_used:
                compute_account_details(portfolio, operation, spots, accounts_history, source_key, previous_date, key_date, True, target_account_used)
                
            if target_account_used:
                compute_account_details(portfolio, operation, spots, accounts_history, target_key, previous_date, key_date, False, target_account_used)
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
                accounts_history[account_id][key_date]['mvt_no_pnl_pf'] = 0.0
                accounts_history[account_id][key_date]['mvt_pnl_pf'] = 0.0
                accounts_history[account_id][key_date]['mvt_no_pnl'] = 0.0
                accounts_history[account_id][key_date]['mvt_pnl'] = 0.0
                accounts_history[account_id][key_date]['spot_pf'] = spot_pf
            start_date = dates.AddDay(start_date, 1)
    LOGGER.info("Accounts positions computed")
    set_accounts_history(accounts_history)
    LOGGER.info("Accounts positions stored")
        
        
def compute_underlying_security(portfolios, tracks, spots, portfolio, operation, inner_security, key_date, work_date=None):
    portfolio_id = str(portfolio.id)
    inner_container = SecurityContainer.objects.get(id=inner_security)
    if not tracks.has_key(inner_security):
        track = get_main_track_content(inner_container)
        tracks[inner_security] = track
    value = get_closest_value(tracks[inner_security], operation.value_date if work_date==None else work_date)
    if value==None:
        LOGGER.error("No NAV available for " + inner_container.name + " as of " + str(from_epoch(long(key_date))))
        return None
    divisor = get_price_divisor(inner_container)
    portfolios[portfolio_id][key_date][inner_security]['price'] = value['value']
    portfolios[portfolio_id][key_date][inner_security]['price_divisor'] = divisor
    spot_pf = 1.0
    if inner_container.currency.short_name!=portfolio.currency.short_name and (not spots.has_key(inner_container.currency.short_name) or not spots[inner_container.currency.short_name].has_key(portfolio.currency.short_name)):
        spot_track = get_exchange_rate(inner_container.currency.short_name, portfolio.currency.short_name)
        if not spots.has_key(inner_container.currency.short_name):
            spots[inner_container.currency.short_name] = {}
        spots[inner_container.currency.short_name][portfolio.currency.short_name] = spot_track
    if inner_container.currency.short_name!=portfolio.currency.short_name and spots.has_key(inner_container.currency.short_name) and spots[inner_container.currency.short_name].has_key(portfolio.currency.short_name):
        value = get_closest_value(spots[inner_container.currency.short_name][portfolio.currency.short_name], operation.value_date if work_date==None else work_date)
        if value!=None:
            spot_pf = value['value']
        else:
            LOGGER.error("No SPOT available for " + inner_container.currency.short_name + '/' + portfolio.currency.short_name + " as of " + str(from_epoch(long(key_date))))
            return None
    portfolios[portfolio_id][key_date][inner_security]['price_pf'] = portfolios[portfolio_id][key_date][inner_security]['price'] * spot_pf
    portfolios[portfolio_id][key_date][inner_security]['price_pf_divisor'] = portfolios[portfolio_id][key_date][inner_security]['price'] * spot_pf / divisor
    portfolios[portfolio_id][key_date][inner_security]['spot_pf'] = spot_pf
    portfolios[portfolio_id][key_date][inner_security]['price_date'] = value['date'].strftime('%Y-%m-%d')

def compute_positions(container=None):
    LOGGER.info("Start computing securities positions")
    if container==None:
        all_operations = FinancialOperation.objects.filter(operation_type__identifier__in=['OPE_TYPE_BUY','OPE_TYPE_SELL','OPE_TYPE_BUY_FOP','OPE_TYPE_SELL_FOP']).order_by('value_date')
    else:
        accounts = container.accounts.all()
        accounts_ids = [account.id for account in accounts]
        all_operations = FinancialOperation.objects.filter(Q(repository__id__in=accounts_ids) | Q(source__id__in=accounts_ids) | Q(target__id__in=accounts_ids), operation_type__identifier__in=['OPE_TYPE_BUY','OPE_TYPE_SELL','OPE_TYPE_BUY_FOP','OPE_TYPE_SELL_FOP']).order_by('value_date')
        
    tracks = {}
    spots = {}
    
    portfolios = {}
    securities = {}
    previous_date = {}
    for operation in all_operations:
        LOGGER.info(operation.name)
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
            securities[security_id][key_date] = {'total': 0.0, 'name': operation.target.short_name, 'id': operation.target.id, 'type': operation.target.type.identifier}
        if not portfolios[portfolio_id].has_key(key_date):
            portfolios[portfolio_id][key_date] = {}
        if not securities[security_id][key_date].has_key(portfolio_id):
            securities[security_id][key_date][portfolio_id] = 0.0
        securities[security_id][key_date][portfolio_id] = securities[security_id][key_date][portfolio_id] + (operation.quantity * (1.0 if operation.operation_type.identifier in ['OPE_TYPE_BUY', 'OPE_TYPE_BUY_FOP'] else -1.0))
        securities[security_id][key_date]['total'] = securities[security_id][key_date]['total'] + (operation.quantity * (1.0 if operation.operation_type.identifier in ['OPE_TYPE_BUY', 'OPE_TYPE_BUY_FOP'] else -1.0))
        if previous_date.has_key(portfolio_id):
            portfolios[portfolio_id][key_date] = copy.deepcopy(portfolios[portfolio_id][previous_date[portfolio_id]])
            if previous_date[portfolio_id]!=key_date:
                if portfolios[portfolio_id][key_date].has_key('increase'):
                    del portfolios[portfolio_id][key_date]['increase']
                if portfolios[portfolio_id][key_date].has_key('decrease'):
                    del portfolios[portfolio_id][key_date]['decrease']
                if portfolios[portfolio_id][key_date].has_key('increase_fop'):
                    del portfolios[portfolio_id][key_date]['increase_fop']
                if portfolios[portfolio_id][key_date].has_key('decrease_fop'):
                    del portfolios[portfolio_id][key_date]['decrease_fop']
        if not portfolios[portfolio_id][key_date].has_key(security_id):
            portfolios[portfolio_id][key_date][security_id] = {'total': 0.0, 'name': operation.target.short_name, 'id': operation.target.id, 'type': operation.target.type.identifier, 'price': 0.0, 'price_pf': 0.0, 'price_date': None, 'buy_price': 0.0, 'buy_spot': 1.0}
        if not portfolios[portfolio_id][key_date].has_key('increase'):
            portfolios[portfolio_id][key_date]['increase'] = {'portfolio': 0.0}
        if not portfolios[portfolio_id][key_date].has_key('decrease'):
            portfolios[portfolio_id][key_date]['decrease'] = {'portfolio': 0.0}
        if not portfolios[portfolio_id][key_date].has_key('increase_fop'):
            portfolios[portfolio_id][key_date]['increase_fop'] = {'portfolio': 0.0}
        if not portfolios[portfolio_id][key_date].has_key('decrease_fop'):
            portfolios[portfolio_id][key_date]['decrease_fop'] = {'portfolio': 0.0}
        computed_amount = operation.quantity * (1.0 if operation.operation_type.identifier in ['OPE_TYPE_BUY', 'OPE_TYPE_BUY_FOP'] else -1.0)
        if (portfolios[portfolio_id][key_date][security_id]['total'] + computed_amount)!=0.0:
            portfolios[portfolio_id][key_date][security_id]['buy_price'] = computed_amount * (operation.price if operation.price!=None else 0.0) + portfolios[portfolio_id][key_date][security_id]['buy_price'] * portfolios[portfolio_id][key_date][security_id]['total']
            portfolios[portfolio_id][key_date][security_id]['buy_price'] = portfolios[portfolio_id][key_date][security_id]['buy_price']/(portfolios[portfolio_id][key_date][security_id]['total'] + computed_amount)
            portfolios[portfolio_id][key_date][security_id]['buy_spot'] = operation.spot if operation.spot!=None else 1.0
            
        portfolios[portfolio_id][key_date][security_id]['total'] += computed_amount
        
        portfolio_movement = portfolios[portfolio_id][key_date]['increase' if operation.operation_type.identifier in ['OPE_TYPE_BUY', 'OPE_TYPE_BUY_FOP'] else 'decrease']
        portfolio_movement_fop = portfolios[portfolio_id][key_date]['increase_fop' if operation.operation_type.identifier in ['OPE_TYPE_BUY', 'OPE_TYPE_BUY_FOP'] else 'decrease_fop']
        if not portfolio_movement.has_key(operation.target.currency.short_name):
            portfolio_movement[operation.target.currency.short_name] = 0.0
        if not portfolio_movement_fop.has_key(operation.target.currency.short_name):
            portfolio_movement_fop[operation.target.currency.short_name] = 0.0
        spot_pf = 1.0
        if operation.target.currency.short_name!=portfolio.currency.short_name and (not spots.has_key(operation.target.currency.short_name) or not spots[operation.target.currency.short_name].has_key(portfolio.currency.short_name)):
            spot_track = get_exchange_rate(operation.target.currency.short_name, portfolio.currency.short_name)
            if not spots.has_key(operation.target.currency.short_name):
                spots[operation.target.currency.short_name] = {}
            spots[operation.target.currency.short_name][portfolio.currency.short_name] = spot_track
        if operation.target.currency.short_name!=portfolio.currency.short_name and spots.has_key(operation.target.currency.short_name) and spots[operation.target.currency.short_name].has_key(portfolio.currency.short_name):
            value = get_closest_value(spots[operation.target.currency.short_name][portfolio.currency.short_name], operation.value_date)
            if value!=None:
                spot_pf = value['value']
        portfolios[portfolio_id][key_date][security_id]['buy_spot'] = spot_pf
        portfolio_movement[operation.target.currency.short_name] += operation.amount
        portfolio_movement['portfolio'] += operation.amount * spot_pf
        portfolio_movement_fop[operation.target.currency.short_name] += operation.amount if operation.operation_type.identifier in ['OPE_TYPE_SELL_FOP', 'OPE_TYPE_BUY_FOP'] else 0.0
        portfolio_movement_fop['portfolio'] += (operation.amount if operation.operation_type.identifier in ['OPE_TYPE_SELL_FOP', 'OPE_TYPE_BUY_FOP'] else 0.0) * spot_pf
        for inner_security in portfolios[portfolio_id][key_date].keys():
            if inner_security not in ['increase', 'decrease', 'increase_fop', 'decrease_fop']:
                compute_underlying_security(portfolios, tracks, spots, portfolio, operation, inner_security, key_date)
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
                if portfolios[portfolio_id][key_date].has_key('increase_fop'):
                    del portfolios[portfolio_id][key_date]['increase_fop']
                if portfolios[portfolio_id][key_date].has_key('decrease_fop'):
                    del portfolios[portfolio_id][key_date]['decrease_fop']
                for inner_security in portfolios[portfolio_id][key_date].keys():
                    if portfolios[portfolio_id][key_date][inner_security]['total']!=0.0:
                        compute_underlying_security(portfolios, tracks, spots, portfolio, operation, inner_security, key_date, work_date)
                    else:
                        del portfolios[portfolio_id][key_date][inner_security]
            start_date = dates.AddDay(start_date, 1)
            
    LOGGER.info("Securities positions computed")
    set_positions_portfolios(portfolios)
    LOGGER.info("Securities positions (portfolio view) stored")
    set_positions_securities(securities)
    LOGGER.info("Securities positions (securities view) stored")