'''
Created on Jun 3, 2014

@author: sdejonckheere
'''
from utilities.xls_writer import simple_xlsx_dump
import os
from finale.settings import WORKING_PATH
import datetime
import logging
from utilities import external_content
from utilities.track_token import get_main_track

LOGGER = logging.getLogger(__name__)

GUARDIAN_SECURITY_HEADER = ['cod_tit','des_tit','cod_div','cod_isin','cod_bloomberg','cod_reuters','cod_esterno','cod_esterno2','des_esterna','data_emi','data_rim','liquidita',
'senza_prezzo','azione','obbligazione','opzione','fondo','fondo_azi','fondo_obb','fondo_bil','fondo_mon','cfd','cedola','dividendo','forward',
'coeff_indice','tasso_cedola','rating_sp','rating_mo','rating_fi','risk_class','qta_min','qta_mul','divisore','moltiplicatore','leva','cod_mer',
'cod_catmer','cod_comneg','cod_tiptit','sigla_paese','gg_valuta','qta_margar','estinto','con_scadenza','titolo_stato_ue','link_prezzi','link_offline',
'focus','style','issuer_industry','industry_sector','industry_group','industry_subgroup','massa_amm','massa_amm_tot','note','coeff_rival','prezzo_ult',
'rateo_ult','data_ult','new_entry']

GUARDIAN_HISTORY_HEADER = ['data_ins','cod_tit','cod_div_tit','cod_isin','cod_bloomberg','cod_esterno','prezzo','variazione']

GUARDIAN_DATASOURCE = 'guardian'

def export_universe(universe):
    LOGGER.info("Exporting " + str(universe.name) + " as GUARDIAN")
    rows = [GUARDIAN_SECURITY_HEADER]
    for member in universe.members.all():
        data = []
        data.append('')
        data.append(member.name)
        data.append(member.currency.short_name)
        isin = member.aliases.filter(alias_type__name='ISIN')
        if isin.exists():
            data.append(isin[0].alias_value)
        else:
            data.append('')
        bloomberg = member.aliases.filter(alias_type__name='BLOOMBERG')
        if bloomberg.exists():
            data.append(bloomberg[0].alias_value)
        else:
            data.append('')
        data.append('')
        data.append('')
        data.append('')
        data.append('')
        data.append('')
        data.append('')
        data.append('')
        data.append('')
        stock = bond = option = fund = ucits = bond_fund = cfd = coupon = dividend = forward = 'N'
        minimal_quantity = divisor = 1.0
        
        if member.type.identifier=='CONT_BOND':
            bond = 'S'
            coupon = 'S'
            divisor = 100.0
        elif member.type.identifier=='CONT_STOCK':
            stock='S'
            dividend = 'S'
        elif member.type.identifier=='CONT_FUND':
            fund = 'S'
            minimal_quantity = 0.00001
        elif member.type.identifier=='CONT_FORWARD':
            forward = 'S'
        elif member.type.identifier in('CONT_PUT','CONT_CALL'):
            option = 'S'
        data.append(stock)
        data.append(bond)
        data.append(option)
        data.append(fund)
        data.append(ucits)
        data.append(bond_fund)
        data.append('N')
        data.append('N')
        data.append(cfd)
        data.append(coupon)
        data.append(dividend)
        data.append(forward)
        data.append('')
        data.append('') # Coupon rate
        data.append('')
        data.append('')
        data.append('')
        data.append('')
        data.append(minimal_quantity)
        data.append('S')
        data.append(divisor)
        data.append('')
        data.append('')
        data.append('')
        data.append('')
        data.append('')
        data.append('')
        data.append('')
        data.append('')
        data.append('')
        data.append('')
        data.append('')
        data.append('')
        data.append('S') # Price link
        data.append('')
        data.append('')
        data.append('')
        data.append('')
        data.append('')
        data.append('')
        data.append('')
        data.append('')
        data.append('')
        data.append('')
        data.append('')
        data.append('')
        data.append('')
        data.append('')
        data.append('S')
        rows.append(data)
        
    save_path = os.path.join(WORKING_PATH,universe.name + '_SECURITIES_' + str(datetime.date.today()) + '.xlsx')
    simple_xlsx_dump(rows, save_path)
    return save_path

def export_universe_history(universe):
    rows = [GUARDIAN_HISTORY_HEADER]
    for security in universe.members.all():
        rows = rows + export_security_history(security, rows)
    save_path = os.path.join(WORKING_PATH,universe.name + '_HISTORY_' + str(datetime.date.today()) + '.xlsx')
    simple_xlsx_dump(rows, save_path)
    return save_path

def export_security_history(security, global_rows=None):
    if global_rows==None:
        rows = [GUARDIAN_HISTORY_HEADER]
    else:
        rows = []
    isin = security.aliases.filter(alias_type__name='ISIN')
    if isin.exists():
        isin = isin[0].alias_value
    else:
        isin = None
    bloomberg = security.aliases.filter(alias_type__name='BLOOMBERG')
    if bloomberg.exists():
        bloomberg = bloomberg[0].alias_value
    else:
        bloomberg = None
    external_information = external_content.get_security_information(GUARDIAN_DATASOURCE,isin=isin, bloomberg=bloomberg)
    if external_information!=None:
        content = get_main_track(security, True, False)
        if content!=None:
            for token in content:
                row = []
                row.append(token['date'])
                row.append(external_information['cod_tit'])
                row.append(None)
                row.append(None)
                row.append(None)
                row.append(None)
                row.append(token['value'])
                row.append(None)
                rows.append(row)
    else:
        LOGGER.warn("Security " + str(security.name) + " could not be found with [BLOOMBERG=" + str(bloomberg) + ", ISIN=" + str(isin) + "]")
    if global_rows==None:
        save_path = os.path.join(WORKING_PATH,security.name + '_HISTORY_' + str(datetime.date.today()) + '.xlsx')
        simple_xlsx_dump(rows, save_path)
        return save_path
    else:
        return rows
    