'''
Created on Dec 15, 2014

@author: sdejonckheere
'''
from django.db.models import Q
from universe.models import Attributes, FinancialOperation, Alias,\
    SecurityContainer
from utilities.external_content import get_transactions, get_portfolios
from utilities import operations
from utilities.operations import compute_positions, compute_accounts

import logging

LOGGER = logging.getLogger(__name__)

def import_portfolio(container):
    guardian_alias = Attributes.objects.get(type='alias_type', short_name='GUARDIAN')
    portfolios = get_portfolios('guardian')
    for portfolio in portfolios:
        if container.name==portfolio['values'][0]['des_rap']:
            if container.aliases.filter(alias_type=guardian_alias).exists():
                alias = container.aliases.get(alias_type=guardian_alias)
            else:
                alias = Alias()
                alias.alias_type = guardian_alias
                alias.save()
                container.aliases.add(alias)
                container.save()
            alias.alias_value = portfolio['values'][0]['cod_rap']
            alias.save()

def import_transactions(container):
    for account in container.accounts.all():
        FinancialOperation.objects.filter(Q(source=account) | Q(target=account) | Q(repository=account)).delete()
        container.accounts.remove(account)
        account.delete()
        container.save()

    operation_status = Attributes.objects.get(identifier='OPE_STATUS_EXECUTED', active=True)
    guardian_alias = Attributes.objects.get(type='alias_type', short_name='GUARDIAN')
    
    if container.aliases.filter(alias_type=guardian_alias).exists():
        all_transactions = get_transactions('guardian', container.aliases.get(alias_type=guardian_alias).alias_value)
        print len(all_transactions)
        for transaction in all_transactions:
            if transaction['cod_ope']=='CONTRIBUTION':
                source = None
                target = {'currency': transaction['cod_div_reg'], 'initial_amount': transaction['ctv_tot_dn'], 'amount': transaction['ctv_tot_dr'], 'account_id': transaction['cod_dep_liq']}
                details = {'impact_pnl': False, 'operation_date': transaction['data_ins'], 'trade_date': transaction['data_ope'], 'amount': transaction['ctv_tot_dr'], 'value_date': transaction['data_val'], 'status': operation_status, 'cashier': transaction['cash']=='S'}
                operations.create_cash_movement(container, source, target, details, transaction['des_mov'])
            elif transaction['cod_ope']=='WITHDRAWAL':
                source = {'currency': transaction['cod_div_reg'], 'initial_amount': transaction['ctv_tot_dn'], 'amount': transaction['ctv_tot_dr'], 'account_id': transaction['cod_dep_liq']}
                target = None
                details = {'impact_pnl': False, 'operation_date': transaction['data_ins'], 'trade_date': transaction['data_ope'], 'amount': transaction['ctv_tot_dr'], 'value_date': transaction['data_val'], 'status': operation_status, 'cashier': transaction['cash']=='S'}
                operations.create_cash_movement(container, source, target, details, transaction['des_mov'])
            elif transaction['cod_ope']=='DEBIT':
                source = {'currency': transaction['cod_div_reg'], 'initial_amount': transaction['ctv_tot_dn'], 'amount': transaction['ctv_tot_dr'], 'account_id': transaction['cod_dep_liq']}
                target = None
                details = {'impact_pnl': True, 'operation_date': transaction['data_ins'], 'trade_date': transaction['data_ope'], 'amount': transaction['ctv_tot_dr'], 'value_date': transaction['data_val'], 'status': operation_status, 'cashier': transaction['cash']=='S'}
                operations.create_cash_movement(container, source, target, details, transaction['des_mov'])            
            elif transaction['cod_ope']=='CREDIT':
                source = None
                target = {'currency': transaction['cod_div_reg'], 'initial_amount': transaction['ctv_tot_dn'], 'amount': transaction['ctv_tot_dr'], 'account_id': transaction['cod_dep_liq']}
                details = {'impact_pnl': True, 'operation_date': transaction['data_ins'], 'trade_date': transaction['data_ope'], 'amount': transaction['ctv_tot_dr'], 'value_date': transaction['data_val'], 'status': operation_status, 'cashier': transaction['cash']=='S'}
                operations.create_cash_movement(container, source, target, details, transaction['des_mov'])
            elif transaction['cod_ope']=='BSPOT':
                source = {'currency': transaction['cod_div_reg'], 'initial_amount': transaction['ctv_tit_dr'], 'amount': transaction['ctv_tot_dr'], 'account_id': transaction['cod_dep_liq']}
                target = {'currency': transaction['cod_div_tit'], 'initial_amount': transaction['ctv_tit_dn'], 'amount': transaction['ctv_tot_dn'], 'account_id': transaction['cod_dep_liq2']}
                details = {'operation': 'BUY', 'spot_rate': transaction['cambiod'] if transaction.has_key('cambiod') and transaction['cambiod']!=None else (1.0/transaction['cambiom']), 'operation_date': transaction['data_ins'], 'trade_date': transaction['data_ope'], 'amount': transaction['ctv_tot_dr'], 'value_date': transaction['data_val'], 'status': operation_status, 'cashier': transaction['cash']=='S'}
                operations.create_spot_movement(container, source, target, details, transaction['des_mov'])
            elif transaction['cod_ope']=='SSPOT':
                source = {'currency': transaction['cod_div_tit'], 'initial_amount': transaction['ctv_tit_dn'], 'amount': transaction['ctv_tot_dn'], 'account_id': transaction['cod_dep_liq2']}
                target = {'currency': transaction['cod_div_reg'], 'initial_amount': transaction['ctv_tit_dr'], 'amount': transaction['ctv_tot_dr'], 'account_id': transaction['cod_dep_liq']}
                details = {'operation': 'SELL', 'spot_rate': transaction['cambiom'] if transaction.has_key('cambiom') and transaction['cambiom']!=None else (1.0/transaction['cambiod']), 'operation_date': transaction['data_ins'], 'trade_date': transaction['data_ope'], 'amount': transaction['ctv_tot_dr'], 'value_date': transaction['data_val'], 'status': operation_status, 'cashier': transaction['cash']=='S'}
                operations.create_spot_movement(container, source, target, details, transaction['des_mov'])
            elif transaction['cod_ope']=='B' or transaction['cod_ope']=='BUYFOP':
                security = SecurityContainer.objects.filter(aliases__alias_type=guardian_alias, aliases__alias_value=transaction['cod_tit'])
                if security.exists():
                    source = None
                    target = {'security': security[0], 'quantity': transaction['qta'], 'price': transaction['prezzo']}
                    details = {'operation_date': transaction['data_ins'], 'trade_date': transaction['data_ope'], 'value_date': transaction['data_val'],
                               'spot_rate': transaction['cambiom'] if transaction.has_key('cambiom') and transaction['cambiom']!=None else ((1.0/transaction['cambiod']) if transaction.has_key('cambiod') and transaction['cambiod']!=None else 1.0),
                               'operation': 'BUY', 'impact_pnl': transaction['cod_ope']=='B', 'currency': transaction['cod_div_reg'], 'account_id': transaction['cod_dep_liq']
                               }
                    operations.create_security_movement(container, source, target, details, transaction['des_mov'])
                else:
                    LOGGER.warn('Security with Guardian alias [' + transaction['cod_tit'] + '] could not be found.')
            elif transaction['cod_ope']=='S' or transaction['cod_ope']=='SELLFOP':
                security = SecurityContainer.objects.filter(aliases__alias_type=guardian_alias, aliases__alias_value=transaction['cod_tit'])
                if security.exists():
                    source = None
                    target = {'security': security[0], 'quantity': -1.0 * transaction['qta'], 'price': transaction['prezzo']}
                    details = {'operation_date': transaction['data_ins'], 'trade_date': transaction['data_ope'], 'value_date': transaction['data_val'],
                               'spot_rate': transaction['cambiom'] if transaction.has_key('cambiom') and transaction['cambiom']!=None else ((1.0/transaction['cambiod']) if transaction.has_key('cambiod') and transaction['cambiod']!=None else 1.0),
                               'operation': 'SELL', 'impact_pnl': transaction['cod_ope']=='S', 'currency': transaction['cod_div_reg'], 'account_id': transaction['cod_dep_liq']
                               }
                    operations.create_security_movement(container, source, target, details, transaction['des_mov'])
                else:
                    LOGGER.warn('Security with Guardian alias [' + transaction['cod_tit'] + '] could not be found.')
            elif transaction['cod_ope']=='BUYFOP':
                None
            elif transaction['cod_ope']=='SELLFOP':
                None
        compute_accounts()
        compute_positions()