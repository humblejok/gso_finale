'''
Created on Dec 15, 2014

@author: sdejonckheere
'''
from utilities.external_content import get_transactions
from utilities import operations

def import_transactions(container):
    all_transactions = get_transactions('guardian', '1.0.40817')
    for transaction in all_transactions:
        if transaction['cod_ope']=='CONTRIBUTION':
            operations.create_cash_movement()
        elif transaction['cod_ope']=='WITHDRAWAL':
            None
        elif transaction['cod_ope']=='SSPOT':
            None
        elif transaction['cod_ope']=='BSPOT':
            None
        elif transaction['cod_ope']=='SELLFOP':
            None
        elif transaction['cod_ope']=='BUYFOP':
            None