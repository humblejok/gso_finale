'''
Created on May 24, 2014

@author: sdejonckheere
'''
from utilities import xls_loader
from utilities.xls_writer import simple_xlsx_dump
import logging

LOGGER = logging.getLogger(__name__)

def load_pictet_operations(file_path):
    return xls_loader.load_xlsx("Pictet",file_path,[u'No ordre'])

def convert_pictet_operations_guardian(pictet_file, guardian_file, export_file):
    export_header = ['progr','rif','simulazione','spuntato','storicizzato','storno','annullato','data_ins','data_ope','ora_ope','data_val',
                     'cod_ope','cod_rap','cod_tit','cod_div_tit','cod_isin','cod_bloomberg','cod_esterno','qta','prezzo','rateo','cambiom',
                     'cambiod','cod_ctp','cod_dep_tit','cod_dep_liq','cod_dep_liq2','cod_div_reg','ctv_tit_dn','ctv_rat_dn','comp_dep_dn',
                     'coma_dep_dn','comp_alt_dn','coma_alt_dn','spese_dn','imposte_dn','ctv_tot_dn','margini_dn','ctv_tit_dr','ctv_rat_dr',
                     'omp_dep_dr','coma_dep_dr','comp_alt_dr','coma_alt_dr','spese_dr','imposte_dr','ctv_tot_dr','des_mov','rif_est',
                     'coordinate1','coordinate2','data_sto','progr_sto','prezzo_car','cod_div_ds','cambiom_ds','cambiod_ds','ctv_tot_ds',
                     'cod_mer','tipo_prezzo','tipo_tempo','cash']

    data = load_pictet_operations(pictet_file)
    guardian = xls_loader.load_xlsx("Guardian",guardian_file,[u'PICTET 1',u'PICTET 2'])
    
    full_content = [export_header]
    line_index = 1
    for order in data.keys():
        LOGGER.info("Working on row " + str(line_index) + " with operation code " + str(order))
        if len(data[order])==1:
            # Simple case
            code_operation = data[order][0][u'Code op\xe9ration']
            type_operation = data[order][0][u'Type op\xe9ration']
            guardian_operation = guardian[type_operation][code_operation][0][u'GUARDIAN']
            guardian_cash = 'S' if guardian[type_operation][code_operation][0][u'CASH']==1 else ''
            if guardian_operation!=None and guardian_operation!='':
                isin_code = data[order][0][u'ISIN']
                bloomberg_code = data[order][0][u'Ticker Bloomberg (Code g\xe9n\xe9rique)']
                row = ['','','','','','','',
                       data[order][0][u'Date op\xe9ration'],
                       data[order][0][u'Date op\xe9ration'],
                       '',
                       data[order][0][u'Date valeur'],
                       guardian_operation,
                       data[order][0][u'No du compte'],
                       data[order][0][u'Monnaie de r\xe9f\xe9rence'],
                       data[order][0][u'Monnaie titre'],
                       isin_code if bloomberg_code==None or bloomberg_code=='' else '',
                       bloomberg_code,
                       '',
                       data[order][0][u'Quantit\xe9'],
                       data[order][0][u'Prix march\xe9'],
                       '',
                       '',
                       data[order][0][u'Taux de change'] if data[order][0][u'Taux de change']!=None and data[order][0][u'Taux de change']!=1.0 else '',
                       'PIC',
                       'DEPTIT' if guardian_operation=='A' or guardian_operation=='V' else '',
                       'HERE COMES THE SOURCE ACCOUNT',
                       'HERE COMES THE TARGET ACCOUNT',
                       data[order][0][u'Monnaie du compte courant'],
                       data[order][0][u'Montant brut (monnaie op.)'],'','','','','','','',data[order][0][u'Montant brut (monnaie op.)'],'',
                       data[order][0][u'Montant brut (monnaie op.)']/(data[order][0][u'Taux de change'] if data[order][0][u'Taux de change']!=None else 1.0),'','','','','',(data[order][0][u'Total frais (monnaie op.)'] if data[order][0][u'Total frais (monnaie op.)']!=None and data[order][0][u'Total frais (monnaie op.)']!='' else 0.0)/(data[order][0][u'Taux de change'] if data[order][0][u'Taux de change']!=None else 1.0),'',data[order][0][u'Montant net (monnaie compte courant)'],
                       data[order][0][u'Description'],'','','','','','','','','','','','','',
                       guardian_cash
                       ]
                full_content.append(row)
                line_index += 1
        else:
            # Complex: Cancellation, transfer
            line_index += 1
    simple_xlsx_dump(full_content, export_file)