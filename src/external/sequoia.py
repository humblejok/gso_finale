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