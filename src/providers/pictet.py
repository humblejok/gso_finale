'''
Created on May 24, 2014

@author: sdejonckheere
'''
from utilities import xls_loader
from utilities.xls_writer import simple_xlsx_dump
import logging
from universe.models import SecurityContainer
from finale import threaded
from datetime import datetime as dt
from utilities.track_token import get_main_track, get_closest_value

LOGGER = logging.getLogger(__name__)

def load_pictet_operations(file_path):
    return xls_loader.load_xlsx("Pictet",file_path,[u'No ordre'])

def get_guardian_account_code(accounts, pictet_code, currency, fiduciary = None):
    for account in accounts[pictet_code][currency]:
        if fiduciary==account[u'fiduciary_name']:
            return account[u'account_code'].strip()

def get_security_price(isin_code,bloomberg_code, value_date):
    securities = []
    if isin_code!=None and isin_code!='':
        securities = SecurityContainer.objects.filter(aliases__alias_type__name='ISIN', aliases__alias_value=isin_code)
    elif bloomberg_code!=None and bloomberg_code!='':
        securities = SecurityContainer.objects.filter(aliases__alias_type__name='BLOOMBERG', aliases__alias_value=bloomberg_code)
    if len(securities)==0 and ((bloomberg_code!=None and bloomberg_code!='') or (isin_code!=None and isin_code!='')):
        threaded.bloomberg_data_query('NO_NEED', [isin_code if bloomberg_code==None or bloomberg_code=='' else bloomberg_code], True)
        if isin_code!=None and isin_code!='':
            securities = SecurityContainer.objects.filter(aliases__alias_type__name='ISIN', aliases__alias_value=isin_code)
        elif bloomberg_code!=None and bloomberg_code!='':
            securities = SecurityContainer.objects.filter(aliases__alias_type__name='BLOOMBERG', aliases__alias_value=bloomberg_code)
    if len(securities)==0:
        LOGGER.warn("Security cannot be found:" + str(isin_code) + "/" + str(bloomberg_code))
        return 1.0
    else:
        value = get_closest_value(get_main_track(securities[0]), dt.combine(value_date, dt.min.time()))
        if value==None:
            return 1.0
        else:
            return value['value']

def default_operation(entry, account_code, pictet_code, accounts, code_operation, type_operation, guardian_cash, guardian_operation):
    isin_code = entry[u'ISIN']
    bloomberg_code = entry[u'Ticker Bloomberg (Code g\xe9n\xe9rique)']
    
    if entry[u'Monnaie du compte courant']!=u'':
        amount = entry[u'Montant brut (monnaie op.)'] if entry[u'Montant brut (monnaie op.)']!=None and entry[u'Montant brut (monnaie op.)']!='' else entry[u'Montant net (monnaie compte courant)']
        target_amount_gross = amount/(entry[u'Taux de change'] if entry[u'Taux de change']!=None and entry[u'Taux de change']!=u'' else 1.0)
        target_fees = (entry[u'Total frais (monnaie op.)'] if entry[u'Total frais (monnaie op.)']!=None and entry[u'Total frais (monnaie op.)']!='' else 0.0)/(entry[u'Taux de change'] if entry[u'Taux de change']!=None and entry[u'Taux de change']!=u'' else 1.0)
    else:
        target_amount_gross = ''
        target_fees = ''
    
    return ['','','','','','','',
           entry[u'Date op\xe9ration'],
           entry[u'Date op\xe9ration'],
           '',
           entry[u'Date comptable'],
           guardian_operation,
           account_code,
           '' if guardian_operation in ['A', 'V', 'CARICO', 'SCARICO','DIVIDENDO'] else entry[u'Monnaie de r\xe9f\xe9rence'],
           entry[u'Monnaie titre'],
           isin_code if guardian_operation in ['A', 'V', 'CARICO', 'SCARICO','DIVIDENDO'] else '',
           bloomberg_code if (isin_code==None or isin_code=='') and guardian_operation in ['A', 'V', 'CARICO', 'SCARICO','DIVIDENDO'] else '',
           '',
           entry[u'Quantit\xe9'] if guardian_operation!='ACCREDITO' else entry[u'Montant brut (monnaie op.)'],
           get_security_price(isin_code,bloomberg_code, entry[u'Date valeur']) if guardian_operation in ['CARICO', 'SCARICO'] else entry[u'Prix march\xe9'] if guardian_operation in ['A', 'V', 'DIVIDENDO'] else '',
           '',
           '',
           entry[u'Taux de change'] if entry[u'Taux de change']!=None and entry[u'Taux de change']!=1.0 else '',
           'PIC',
           'DEPTIT' if guardian_operation in ['A', 'V', 'CARICO', 'SCARICO','DIVIDENDO'] else '',
           get_guardian_account_code(accounts, pictet_code, entry[u"Monnaie d'op\xe9ration"] if entry[u"Monnaie d'op\xe9ration"]!='' and entry[u"Monnaie d'op\xe9ration"]!=None else entry[u"Monnaie titre"], None),
           get_guardian_account_code(accounts, pictet_code, entry[u'Monnaie du compte courant'], None) if entry[u'Monnaie du compte courant']!=entry[u'Monnaie titre'] and entry[u'Monnaie du compte courant']!=u'' else '',
           entry[u'Monnaie titre'],
           entry[u'Montant brut (monnaie op.)'] * (-1.0 if entry[u'Montant brut (monnaie op.)']>0.0 and guardian_operation=='GIROCONTO' else 1.0),'','','','','','','',entry[u'Montant brut (monnaie op.)'] * (-1.0 if entry[u'Montant brut (monnaie op.)']>0.0  and guardian_operation=='GIROCONTO' else 1.0),'',                       
           target_amount_gross * (-1.0 if target_amount_gross<0.0 and guardian_operation=='GIROCONTO' else 1.0),'','','','','',target_fees,'',entry[u'Montant net (monnaie compte courant)'] * (-1.0 if entry[u'Montant net (monnaie compte courant)'] and guardian_operation=='GIROCONTO' else 1.0),
           entry[u'Description'],'','','','','','','','','','','','','',
           guardian_cash
           ]
    
def switch_operation(entry, account_code, pictet_code, accounts, guardian_cash, guardian_operation):
    isin_code = entry[u'ISIN']
    bloomberg_code = entry[u'Ticker Bloomberg (Code g\xe9n\xe9rique)']
    quantity = entry[u'Quantit\xe9']
    return ['','','','','','','',
           entry[u'Date op\xe9ration'],
           entry[u'Date op\xe9ration'],
           '',
           entry[u'Date valeur'],
           'SCARICO' if quantity<0.0 else 'CARICO',
           account_code,
           '',
           entry[u'Monnaie titre'],
           isin_code,
           bloomberg_code if isin_code==None or isin_code=='' else '',
           '',
           quantity,
           get_security_price(isin_code,bloomberg_code, entry[u'Date valeur']), # Price
           '',
           '',
           '', # Div spot rate
           'PIC',
           'DEPTIT' if guardian_operation in ['A', 'V'] else '',
           get_guardian_account_code(accounts, pictet_code, entry[u'Monnaie titre'], None),
           '',
           entry[u'Monnaie titre'],
           '','','','','','','','','','',
           '','','','','','','','','',
           entry[u'Description'],'','','','','','','','','','','','','',
           guardian_cash
           ]

def default_multi_operation(entry, account_code, pictet_code, accounts, guardian_cash, guardian_operation, source_currency, source_quantity, target_currency, target_quantity):
    isin_code = entry[u'ISIN']
    bloomberg_code = entry[u'Ticker Bloomberg (Code g\xe9n\xe9rique)']
    return ['','','','','','','',
               entry[u'Date op\xe9ration'],
               entry[u'Date op\xe9ration'],
               '',
               entry[u'Date valeur'],
               guardian_operation,
               account_code,
               '' if guardian_operation in ['A', 'V', 'CARICO', 'SCARICO'] else source_currency,
               source_currency,
               isin_code,
               bloomberg_code if isin_code==None or isin_code=='' else '',
               '',
               source_quantity,
               get_security_price(isin_code,bloomberg_code, entry[u'Date valeur']) if guardian_operation in ['A', 'V', 'CARICO', 'SCARICO'] else '', # Price
               '',
               '',
               abs(source_quantity/target_quantity) if source_currency!=target_currency else '', # Div spot rate
               'PIC',
               'DEPTIT' if guardian_operation in ['A','V'] else '',
               get_guardian_account_code(accounts, pictet_code, target_currency, None) if source_currency!=target_currency else '',
               get_guardian_account_code(accounts, pictet_code, source_currency, None),
               target_currency,
               source_quantity * (-1.0 if source_quantity>0.0 and guardian_operation=='GIROCONTO' else 1.0),'','','','','','','',source_quantity * (-1.0 if source_quantity>0.0 and guardian_operation=='GIROCONTO' else 1.0),'',
               target_quantity * (-1.0 if target_quantity<0.0 and guardian_operation=='GIROCONTO' else 1.0),'','','','','','','',target_quantity * (-1.0 if target_quantity<0.0 and guardian_operation=='GIROCONTO' else 1.0),
               entry[u'Description'],'','','','','','','','','','','','','',
               guardian_cash
               ]
        
def fiduciary_transfer(entry, account_code, pictet_code, accounts, code_operation, type_operation, guardian_cash, guardian_operation):
    return ['','','','','','','',
                       entry[u'Date op\xe9ration'],
                       entry[u'Date op\xe9ration'],
                       '',
                       entry[u'Date comptable'],
                       'GIROCONTO',
                       account_code,
                       entry[u'Monnaie de r\xe9f\xe9rence'],
                       '',
                       '',
                       '',
                       '',
                       entry[u'Quantit\xe9'] * -1.0,
                       '',
                       '',
                       '',
                       '',
                       'PIC',
                       '',
                       get_guardian_account_code(accounts, pictet_code, entry[u'Monnaie titre'], None) if code_operation=='Decrease' or code_operation=='Close' else get_guardian_account_code(accounts, pictet_code, entry[u'Monnaie titre'], entry[u'Nom titre']),
                       get_guardian_account_code(accounts, pictet_code, entry[u'Monnaie titre'], entry[u'Nom titre']) if code_operation=='Decrease' or code_operation=='Close' else get_guardian_account_code(accounts, pictet_code, entry[u'Monnaie titre'], None),
                       entry[u'Monnaie titre'],
                       entry[u'Montant brut (monnaie op.)'] * (-1.0 if entry[u'Montant brut (monnaie op.)']>0.0 else 1.0),'','','','','','','',entry[u'Montant brut (monnaie op.)'] * (-1.0 if entry[u'Montant brut (monnaie op.)']>0.0 else 1.0),'',                       
                       entry[u'Montant brut (monnaie op.)'] * (1.0 if entry[u'Montant brut (monnaie op.)']>0.0 else -1.0),'','','','','','','',entry[u'Montant brut (monnaie op.)'] * (1.0 if entry[u'Montant brut (monnaie op.)']>0.0 else -1.0),
                       entry[u'Description'],'','','','','','','','','','','','','',
                       guardian_cash
                       ]

def get_guardian_operation(pictet_entries, account_code, pictet_code, guardian, accounts):
    guardian_operation = None
    source_currency = ''
    source_quantity = None
    target_currency = ''
    target_quantity = None
    for entry in pictet_entries:
        if guardian_operation==None:
            code_operation = entry[u'Code op\xe9ration']
            type_operation = entry[u'Type op\xe9ration']
            guardian_operation = guardian[type_operation][code_operation][0][u'GUARDIAN']
            if guardian_operation==None or guardian_operation==u'':
                guardian_operation = guardian[type_operation][code_operation][0][u'ADVANCED']
            guardian_cash = 'S' if guardian[type_operation][code_operation][0][u'CASH']==1 else ''
        LOGGER.info("Pictet=" + type_operation + "/" + code_operation)
        LOGGER.info("Guard.=" + str(guardian_operation))
        if entry[u'Quantit\xe9']<0:
            source_currency = entry[u'Monnaie titre']
            source_quantity = entry[u'Quantit\xe9']
        else:
            target_currency = entry[u'Monnaie titre']
            target_quantity = entry[u'Quantit\xe9']
    if guardian_operation=='DIVIDENDO':
        rows = []
        for entry in pictet_entries:
            code_operation = entry[u'Code op\xe9ration']
            type_operation = entry[u'Type op\xe9ration']
            row = default_operation(entry, account_code, pictet_code, accounts, code_operation, type_operation, guardian_cash, guardian_operation)
            rows.append(row)
        return rows
    elif guardian_operation=='STOCKDIVIDEND':
        rows = []
        for entry in pictet_entries:
            code_operation = entry[u'Code op\xe9ration']
            type_operation = entry[u'Type op\xe9ration']
            if entry[u'Montant net (monnaie op.)']==None or entry[u'Montant net (monnaie op.)']=='':
                rows.append(switch_operation(entry, account_code, pictet_code, accounts, guardian_cash, 'CARICO'))
            else:
                rows.append(default_operation(entry, account_code, pictet_code, accounts, code_operation, type_operation, 'N', 'ACCREDITO'))
        return rows
    elif guardian_operation!=None and guardian_operation!=u'SPLIT' and guardian_operation!=u'SWITCH' and guardian_operation!=u'EQUAL':
        if guardian_operation=='GIROCONTO':
            row = default_multi_operation(entry, account_code, pictet_code, accounts, guardian_cash, guardian_operation, source_currency, source_quantity, target_currency, target_quantity)
            return [row]
        else:
            rows = []
            for entry in pictet_entries:
                code_operation = entry[u'Code op\xe9ration']
                type_operation = entry[u'Type op\xe9ration']
                guardian_operation = guardian[type_operation][code_operation][0][u'GUARDIAN']
                row = default_operation(entry, account_code, pictet_code, accounts, code_operation, type_operation, guardian_cash, guardian_operation)
                rows.append(row)
            return rows
    elif guardian_operation==u'SWITCH' or guardian_operation==u'SPLIT':
        rows = []
        for entry in pictet_entries:
            row = switch_operation(entry, account_code, pictet_code, accounts, guardian_cash, guardian_operation)
            rows.append(row)
        return rows
    else:
        None
        
def convert_pictet_operations_guardian(pictet_file, guardian_file, accounts_file, export_file):
    export_header = ['progr','rif','simulazione','spuntato','storicizzato','storno','annullato','data_ins','data_ope','ora_ope','data_val',
                     'cod_ope','cod_rap','cod_tit','cod_div_tit','cod_isin','cod_bloomberg','cod_esterno','qta','prezzo','rateo','cambiom',
                     'cambiod','cod_ctp','cod_dep_tit','cod_dep_liq','cod_dep_liq2','cod_div_reg','ctv_tit_dn','ctv_rat_dn','comp_dep_dn',
                     'coma_dep_dn','comp_alt_dn','coma_alt_dn','spese_dn','imposte_dn','ctv_tot_dn','margini_dn','ctv_tit_dr','ctv_rat_dr',
                     'omp_dep_dr','coma_dep_dr','comp_alt_dr','coma_alt_dr','spese_dr','imposte_dr','ctv_tot_dr','des_mov','rif_est',
                     'coordinate1','coordinate2','data_sto','progr_sto','prezzo_car','cod_div_ds','cambiom_ds','cambiod_ds','ctv_tot_ds',
                     'cod_mer','tipo_prezzo','tipo_tempo','cash']

    data = load_pictet_operations(pictet_file)
    guardian = xls_loader.load_xlsx("Guardian",guardian_file,[u'PICTET 1',u'PICTET 2'])
    accounts = xls_loader.load_xlsx("GUARDIAN_ACCOUNTS", accounts_file, [u'pictet_code',u'account_currency'])
    full_content = [export_header]
    line_index = 1
    account_code = None
    
    for order in data.keys():
        LOGGER.info("Working on row " + str(line_index) + " with operation code " + str(order))
        code_operation = data[order][0][u'Code op\xe9ration']
        type_operation = data[order][0][u'Type op\xe9ration']
        try:
            account_code = accounts[data[order][0][u'No du compte']][data[order][0][u'Monnaie de r\xe9f\xe9rence']][0][u'portfolio_code']
            pictet_code = data[order][0][u'No du compte']
        except:
            continue
        if len(data[order])==1:
            # Simple case
            guardian_operation = guardian[type_operation][code_operation][0][u'GUARDIAN']
            LOGGER.info("Pictet=" + type_operation + "/" + code_operation)
            LOGGER.info("Guard.=" + str(guardian_operation))
            if guardian_operation!=None and guardian_operation!='':
                if guardian_operation=='GIROCONTO' and type_operation!='Fiduciary deposit':
                    guardian_operation = 'PRELEVAMENTO'
                guardian_cash = 'S' if guardian[type_operation][code_operation][0][u'CASH']==1 else ''
                if guardian_operation!=None and guardian_operation!='' and guardian_operation!='GIROCONTO':
                    row = default_operation(data[order][0], account_code, pictet_code, accounts, code_operation, type_operation, guardian_cash, guardian_operation)
                    full_content.append(row)
                    LOGGER.info("Size:" + str(len(full_content)))
                elif guardian_operation=='GIROCONTO':
                    row = fiduciary_transfer(data[order][0], account_code, pictet_code, accounts, code_operation, type_operation, guardian_cash, guardian_operation) 
                    full_content.append(row)
                    LOGGER.info("Size:" + str(len(full_content)))
                else:
                    LOGGER.warn('\tSkipping')
            elif guardian[type_operation][code_operation][0][u'ADVANCED']=='STOCKDIVIDEND':
                row = switch_operation(data[order][0], account_code, pictet_code, accounts, '', 'CARICO')
                full_content.append(row)
                LOGGER.info("Size:" + str(len(full_content)))
            line_index += 1
        else:
            # Complex: Cancellation, transfer
            rows = get_guardian_operation(data[order], account_code, pictet_code, guardian, accounts)
            if rows!=None:
                [full_content.append(row) for row in rows]
                LOGGER.info("Size:" + str(len(full_content)))
            else:
                LOGGER.warn('\tSkipping')
            line_index += 1
    simple_xlsx_dump(full_content, export_file)