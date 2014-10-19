import datetime
from utilities.external_content import get_positions
import logging
import sys
from universe.models import Universe, Alias, Attributes, SecurityContainer,\
    TrackContainer, CompanyContainer
from utilities.track_content import get_track_content
from seq_common.utils import dates
import traceback
import os
from finale.settings import WORKING_PATH
from openpyxl.workbook import Workbook
from external.sequoia_data import ROLE_MAPS_TEMPLATE, SEQUOIA_STYLES
from openpyxl.worksheet.dimensions import RowDimension

LOGGER = logging.getLogger(__name__)

def define_xslx_header(sheet, headers):
    row_index = 1
    col_index = 1
    for row in headers:
        for column in row:
            sheet.cell(row=row_index, column=col_index).value = column
            col_index += 1
        row_index += 1
        col_index = 1
    return row_index

def get_name_from_identifier(identifier):
    return Attributes.objects.get(identifier=identifier, active=True).name

def get_details(data, target, fees_type, index):
    if index<len(data[fees_type][target]):
        data[fees_type][target][index]['rate'] /= 100.0
        return data[fees_type][target][index]
    else:
        return {'bud': None, 'rate': None}

def execute_row_command(ws, row, row_index, container, data_map, query_date):
    hide = False
    if row!=None:
        LOGGER.debug("Row:" + str(row_index) + ' - ' + str(row))
        for col_index in row.keys():
            if row[col_index].has_key('text'):
                value = row[col_index]['text']
                if not isinstance(row[col_index]['text'], basestring):
                    # value = [ row[col_index]['text'][i] if i%2==1 else all_formats[row[col_index]['text'][i]] for i in range(0, len(row[col_index]['text']))]
                    value = 'TO BE IMPLEMENTED'
            elif row[col_index].has_key('value'):
                try:
                    value = eval(row[col_index]['value'])
                except:
                    value = row[col_index]['default']
                    hide = hide or (row[col_index]['on_default_hide'] if row[col_index].has_key('on_default_hide') else False)
                if row[col_index].has_key('field'):
                    if value!=None and isinstance(value, dict):
                        value = value[row[col_index]['field']]
                    else:
                        value = '' if row[col_index]['default']==None else row[col_index]['default']
                    hide = hide or (row[col_index]['on_default_hide'] if row[col_index].has_key('on_default_hide') else False)
            elif row[col_index].has_key('formula'):
                # Same as value for the time being, may change in the future
                value = row[col_index]['formula']
            ws.cell(row=row_index, column=col_index).value = value
            if row[col_index].has_key('merge'):
                row_span = row[col_index]['merge']['row_span'] if row[col_index]['merge'].has_key('row_span') else 0
                ws.merge_cells(start_row=row_index, start_column=row[col_index]['merge']['start'], end_row=row_index + row_span,end_column=row[col_index]['merge']['end'])
                for merge_index in range(row[col_index]['merge']['start'], row[col_index]['merge']['end'] + 1):
                    ws.cell(row=row_index, column=merge_index).style = SEQUOIA_STYLES['SWM'][row[col_index]['format']]
            else:
                ws.cell(row=row_index, column=col_index).style = SEQUOIA_STYLES['SWM'][row[col_index]['format']]
                # ws.write(row_index, col_index, value, all_formats[row[col_index]['format']])
    else:
        ws.cell(row=row_index, column=1).value = ''
    return hide

def export_map(container, data, workbook = None):
    if workbook==None:
        workbook = Workbook()
        sheet = workbook.active
    else:
        sheet = workbook.create_sheet()
    sheet.title = container.short_name
    xlsx_rows_setup = ROLE_MAPS_TEMPLATE['SWM']
    row_index = 1
    for row in xlsx_rows_setup:
        hide = execute_row_command(sheet, row, row_index, container, data, datetime.date.today() )
        print str(row_index) + ' - ' + str(hide)
        if row_index==1:
            sheet.row_dimensions[row_index].height = 33.75
        elif row_index==2:
            sheet.row_dimensions[row_index].height = 32.25
        elif row_index>74:
            sheet.row_dimensions[row_index].height = 19.5
        else:
            if hide:
                sheet.row_dimensions[row_index] = RowDimension(hidden=True)
            else:
                sheet.row_dimensions[row_index].height=27.0
        row_index = row_index + 1
    for col in range(1,10):
        sheet.cell(row=row_index, column=col).value = ''
    sheet.column_dimensions['A'].width = 35.71
    sheet.column_dimensions['B'].width = 10
    sheet.column_dimensions['C'].width = 47.71
    sheet.column_dimensions['D'].width = 12
    sheet.column_dimensions['E'].width = 8.43
    sheet.column_dimensions['F'].width = 5.29
    sheet.column_dimensions['G'].width = 10
    sheet.column_dimensions['H'].width = 8.43
    sheet.column_dimensions['I'].width = 8.43
    return workbook

def export(parameters):
    working_date = parameters['workingDate']
    export_type = parameters['exportType']
    
    sequoia_universe = Universe.objects.get(name='Sequoia Products')
    guardian_alias = Attributes.objects.get(type='alias_type', short_name='GUARDIAN')
    bloomberg_alias = Attributes.objects.get(identifier='ALIAS_BLOOMBERG')
    
    nav_value = Attributes.objects.get(identifier='NUM_TYPE_NAV', active=True)
    final_status = Attributes.objects.get(identifier='NUM_STATUS_FINAL', active=True)
    official_type = Attributes.objects.get(identifier='PRICE_TYPE_OFFICIAL', active=True)
    monthly = Attributes.objects.get(identifier='FREQ_MONTHLY', active=True)
    computing_company = CompanyContainer.objects.get(name='FinaLE Engine')
    
    if not isinstance(working_date, basestring):
        working_date = working_date[0]
    end_date = datetime.datetime.strptime(working_date,'%Y-%m-%d')
    begin_date = dates.GetStartOfMonth(end_date)
    all_portfolios = get_positions('guardian', end_date)
    
    all_products = {}
    all_groups = {}
    all_navs = {}
    all_spots = {'CHF': 1.0}
    
    for portfolio_code in all_portfolios['values']:
        portfolio_name = portfolio_code.replace('___','.')
        LOGGER.info("Working on " + portfolio_name)
        
        all_positions = all_portfolios['values'][portfolio_code]
        for position in all_positions:
            group = position['cod_gru']
            printable_name = position['des_tit'].encode(sys.stdout.encoding, errors='replace')
            target_currency = position['cod_div_tit']

            if not all_groups.has_key(group):
                all_groups[group] = {}
                
            if not all_groups[group].has_key(portfolio_name):
                all_groups[group][portfolio_name] = {'AUM': 0.0}
                
            security = SecurityContainer.objects.filter(aliases__alias_type=guardian_alias, aliases__alias_value=position['cod_tit'])
            if security.exists():
                security = security[0]
                if target_currency==None and target_currency.currency!=None:
                    target_currency = security.currency.short_name
            else:
                security = None
            print "SECURITY:" + printable_name               
            if security!=None:
                sequoia = sequoia_universe.members.filter(id=security.id).exists()
                if sequoia:
                    LOGGER.info("\tFound " + printable_name)
                    if not all_groups[group][portfolio_name].has_key('SEQUOIA'):
                        all_groups[group][portfolio_name]['SEQUOIA'] = {}
                    if not all_products.has_key(security.name):
                        all_products[security.name] = {}
                if not all_navs.has_key(position['des_tit']):
                    try:
                        monthly_track = TrackContainer.objects.get(effective_container_id=security.id, type__id=nav_value.id,quality__id=official_type.id, source__id=computing_company.id, frequency__id=monthly.id, status__id=final_status.id)
                        monthlies = {token['date']:token['value'] for token in get_track_content(monthly_track)}
                        backdated_day = end_date
                        while not monthlies.has_key(backdated_day):
                            backdated_day = dates.AddDay(backdated_day, -1)
                        nav = monthlies[backdated_day]
                        all_navs[position['des_tit']] = nav
                    except:
                        LOGGER.warn("\tNo price nor track for " + printable_name)
                        all_navs[position['des_tit']] = 1.0
                if not all_spots.has_key(target_currency):
                    spot_container = SecurityContainer.objects.filter(aliases__alias_type=bloomberg_alias, aliases__alias_value= target_currency + 'CHF Curncy')
                    if spot_container.exists():
                        spot_container = spot_container[0]
                        try:
                            monthly_track = TrackContainer.objects.get(effective_container_id=spot_container.id, type__id=nav_value.id,quality__id=official_type.id, source__id=computing_company.id, frequency__id=monthly.id, status__id=final_status.id)
                            monthlies = {token['date']:token['value'] for token in get_track_content(monthly_track)}
                            backdated_day = end_date
                            while not monthlies.has_key(backdated_day):
                                backdated_day = dates.AddDay(backdated_day, -1)
                            spot = monthlies[backdated_day]
                            all_spots[target_currency] = spot
                        except:
                            traceback.print_exc()
                            LOGGER.warn("\tNo price nor track for " + target_currency + "/CHF SPOT")
                            all_spots[target_currency] = 1.0
                    else:
                        LOGGER.warn("\tNo security for " + target_currency + "/CHF SPOT")
                        all_spots[target_currency] = 1.0
                chf_value = position['qta'] * all_navs[position['des_tit']] * all_spots[target_currency]
                if sequoia:
                    all_products[security.name][portfolio_name] = chf_value
                    all_groups[group][portfolio_name]['SEQUOIA'][position['des_tit']] = chf_value
                all_groups[group][portfolio_name]['AUM'] += chf_value
            else:
                if not all_spots.has_key(target_currency):
                    spot_container = SecurityContainer.objects.filter(aliases__alias_type=bloomberg_alias, aliases__alias_value= target_currency + 'CHF Curncy')
                    if spot_container.exists():
                        spot_container = spot_container[0]
                        try:
                            monthly_track = TrackContainer.objects.get(effective_container_id=spot_container.id, type__id=nav_value.id,quality__id=official_type.id, source__id=computing_company.id, frequency__id=monthly.id, status__id=final_status.id)
                            monthlies = {token['date']:token['value'] for token in get_track_content(monthly_track)}
                            backdated_day = end_date
                            while not monthlies.has_key(backdated_day):
                                backdated_day = dates.AddDay(backdated_day, -1)
                            spot = monthlies[backdated_day]
                            all_spots[target_currency] = spot
                        except:
                            traceback.print_exc()
                            LOGGER.warn("\tNo price nor track for " + target_currency + "/CHF SPOT")
                            all_spots[target_currency] = 1.0
                    else:
                        LOGGER.warn("\tNo security for " + target_currency + "/CHF SPOT")
                        all_spots[target_currency] = 1.0
                chf_value = position['qta'] * all_spots[target_currency]
                all_groups[group][portfolio_name]['AUM'] += chf_value
    # OUTPUT of SWM file
    out_file_name = os.path.join(WORKING_PATH,'_SWM_' + str(working_date) + '.xlsx')
    wb = Workbook()
    ws = wb.get_active_sheet()
    ws.title = "Import"
    headers = [['','','','Allocation',''],['Code Fond / Banque',u'Date d\xe9but','Date fin','Code Client','Montant CHF'],]
    row_index = define_xslx_header(ws, headers)
    for product in sorted(all_products.keys()):
        first = True
        for client in all_products[product].keys():
            if not first:
                ws.cell(row=row_index, column=1).value = ''
            else:
                ws.cell(row=row_index, column=1).value = product
            ws.cell(row=row_index, column=2).value = begin_date
            ws.cell(row=row_index, column=3).value = working_date
            ws.cell(row=row_index, column=4).value = client if client!='NEW FRONTIER' else 'NF'
            ws.cell(row=row_index, column=5).value = all_products[product][client]
            row_index += 1
            first = False
    wb.save(out_file_name)