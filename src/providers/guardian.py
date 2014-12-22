'''
Created on Dec 15, 2014

@author: sdejonckheere
'''
from django.db.models import Q

from universe.models import Attributes, FinancialOperation

from utilities.external_content import get_transactions
from utilities import operations

def import_transactions(container):
    for account in container.accounts.all():
        FinancialOperation.objects.filter(Q(source=account) | Q(target=account) | Q(repository=account)).delete()
    operation_status = Attributes.objects.get(identifier='OPE_STATUS_EXECUTED', active=True)
    all_transactions = get_transactions('guardian', '1.0.40817')
    for transaction in all_transactions:
        if transaction['cod_ope']=='CONTRIBUTION':
            source = None
            target = {'currency': transaction['cod_div_reg'],'initial_amount': transaction['ctv_tot_dn'], 'amount': transaction['ctv_tot_dr'], 'account_id': transaction['cod_dep_liq']}
            details = {'impact_pnl': False, 'operation_date': transaction['data_ins'], 'trade_date': transaction['data_ope'], 'amount': transaction['ctv_tot_dr'], 'value_date': transaction['data_val'], 'status': operation_status, 'cashier': transaction['cash']=='S'}
            operations.create_cash_movement(container, source, target, details, transaction['des_mov'])
        elif transaction['cod_ope']=='WITHDRAWAL':
            source = {'currency': transaction['cod_div_reg'],'initial_amount': transaction['ctv_tot_dn'], 'amount': transaction['ctv_tot_dr'], 'account_id': transaction['cod_dep_liq']}
            target = None
            details = {'impact_pnl': False, 'operation_date': transaction['data_ins'], 'trade_date': transaction['data_ope'], 'amount': transaction['ctv_tot_dr'], 'value_date': transaction['data_val'], 'status': operation_status, 'cashier': transaction['cash']=='S'}
            operations.create_cash_movement(container, source, target, details, transaction['des_mov'])
        elif transaction['cod_ope']=='DEBIT':
            source = {'currency': transaction['cod_div_reg'],'initial_amount': transaction['ctv_tot_dn'], 'amount': transaction['ctv_tot_dr'], 'account_id': transaction['cod_dep_liq']}
            target = None
            details = {'impact_pnl': True, 'operation_date': transaction['data_ins'], 'trade_date': transaction['data_ope'], 'amount': transaction['ctv_tot_dr'], 'value_date': transaction['data_val'], 'status': operation_status, 'cashier': transaction['cash']=='S'}
            operations.create_cash_movement(container, source, target, details, transaction['des_mov'])            
        elif transaction['cod_ope']=='BSPOT':
            source = {'currency': transaction['cod_div_reg'],'initial_amount': transaction['ctv_tit_dr'], 'amount': transaction['ctv_tot_dr'], 'account_id': transaction['cod_dep_liq']}
            target = {'currency': transaction['cod_div_tit'],'initial_amount': transaction['ctv_tit_dn'], 'amount': transaction['ctv_tot_dn'], 'account_id': transaction['cod_dep_liq2']}
            details = {'operation': 'BUY', 'spot_rate': transaction['cambiod'] if transaction.has_key('cambiod') and transaction['cambiod']!=None else (1.0/transaction['cambiom']), 'operation_date': transaction['data_ins'], 'trade_date': transaction['data_ope'], 'amount': transaction['ctv_tot_dr'], 'value_date': transaction['data_val'], 'status': operation_status, 'cashier': transaction['cash']=='S'}
            operations.create_spot_movement(container, source, target, details, transaction['des_mov'])
        elif transaction['cod_ope']=='SSPOT':
            source = {'currency': transaction['cod_div_tit'],'initial_amount': transaction['ctv_tit_dn'], 'amount': transaction['ctv_tot_dn'], 'account_id': transaction['cod_dep_liq2']}
            target = {'currency': transaction['cod_div_reg'],'initial_amount': transaction['ctv_tit_dr'], 'amount': transaction['ctv_tot_dr'], 'account_id': transaction['cod_dep_liq']}
            details = {'operation': 'SELL', 'spot_rate': transaction['cambiom'] if transaction.has_key('cambiom') and transaction['cambiom']!=None else (1.0/transaction['cambiod']), 'operation_date': transaction['data_ins'], 'trade_date': transaction['data_ope'], 'amount': transaction['ctv_tot_dr'], 'value_date': transaction['data_val'], 'status': operation_status, 'cashier': transaction['cash']=='S'}
            operations.create_spot_movement(container, source, target, details, transaction['des_mov'])
        elif transaction['cod_ope']=='SELLFOP':
            None
        elif transaction['cod_ope']=='BUYFOP':
            None