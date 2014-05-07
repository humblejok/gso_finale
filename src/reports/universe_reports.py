'''
Created on May 6, 2014

@author: sdejonckheere
'''
from finale.settings import WORKING_PATH
import datetime
import os
import xlsxwriter
from universe.models import Attributes, TrackContainer
from seq_common.utils import dates
import logging

LOGGER = logging.getLogger(__name__)


def define_formats(workbook):
    
    bold = workbook.add_format()
    bold.set_font_name('Arial')
    bold.set_font_color('#C00000')
    bold.set_align('top')
    bold.set_bold(True)
    bold.set_text_wrap()
    bold.set_border(2)
    
    normal = workbook.add_format()
    normal.set_font_name('Arial')
    normal.set_font_color('#C00000')
    normal.set_bold(False)
    normal.set_align('top')
    normal.set_text_wrap()
    normal.set_border(2)
    
    main_format = workbook.add_format()
    main_format.set_font_name('Arial')
    main_format.set_align('center')
    main_format.set_align('vcenter')
    main_format.set_bold(True)
    main_format.set_border(2)
    
    main_format_normal = workbook.add_format()
    main_format_normal.set_font_name('Arial')
    main_format_normal.set_align('center')
    main_format_normal.set_align('vcenter')
    main_format_normal.set_bold(False)
    main_format_normal.set_border(2)
    main_format_normal.set_text_wrap()

    main_format_amount = workbook.add_format()
    main_format_amount.set_font_name('Arial')
    main_format_amount.set_align('center')
    main_format_amount.set_align('vcenter')
    main_format_amount.set_bold(False)
    main_format_amount.set_border(2)    
    main_format_amount.set_num_format("#,##0.-")
    
    main_format_percent = workbook.add_format()
    main_format_percent.set_font_name('Arial')
    main_format_percent.set_align('center')
    main_format_percent.set_align('vcenter')
    main_format_percent.set_bold(False)
    main_format_percent.set_border(2)
    main_format_percent.set_num_format('0.00%')
    
    green_format_percent = workbook.add_format()
    green_format_percent.set_font_name('Arial')
    green_format_percent.set_align('center')
    green_format_percent.set_align('vcenter')
    green_format_percent.set_font_color('#006100')
    green_format_percent.set_bg_color('#C6EFD0')
    green_format_percent.set_bold(True)
    green_format_percent.set_border(2)
    green_format_percent.set_num_format('0.00%')
        
    main_format_borderless = workbook.add_format()
    main_format_borderless.set_font_name('Arial')
    main_format_borderless.set_align('left')
    main_format_borderless.set_align('vcenter')
    main_format_borderless.set_bold(True)
    
    note_format_borderless = workbook.add_format()
    note_format_borderless.set_font_name('Arial')
    note_format_borderless.set_align('left')
    note_format_borderless.set_align('vcenter')
    note_format_borderless.set_font_size(9)
    note_format_borderless.set_bold(True)
    
    title_format = workbook.add_format()
    title_format.set_font_name('Arial')
    title_format.set_align('center')
    title_format.set_align('vcenter')
    title_format.set_font_size(16)
    title_format.set_bold(True)
    title_format.set_underline(True)
    
    wrapped_format = workbook.add_format()
    wrapped_format.set_font_name('Arial')
    wrapped_format.set_text_wrap()
    wrapped_format.set_align('center')
    wrapped_format.set_align('top')
    wrapped_format.set_bold(True)
    wrapped_format.set_border(2)
    
    return {'bold': bold, 'normal': normal, 'main_format': main_format, 'main_format_normal': main_format_normal, 'main_format_amount': main_format_amount, 'main_format_percent': main_format_percent, 'main_format_borderless': main_format_borderless, 'note_format_borderless': note_format_borderless, 'title_format': title_format, 'wrapped_format': wrapped_format, 'green_format_percent': green_format_percent}


def simple_price_report(user, universe, frequency, reference = None, start_date = None, rolling = None):
    # WORKING VARIABLES
    LOGGER.info("Simple price report for " + universe.name)
    today = datetime.date.today()
    nav_value = Attributes.objects.get(identifier='NUM_TYPE_NAV', active=True)
    perf_value = Attributes.objects.get(identifier='NUM_TYPE_PERF', active=True)
    final_status = Attributes.objects.get(identifier='NUM_STATUS_FINAL', active=True)
    official_type = Attributes.objects.get(identifier='PRICE_TYPE_OFFICIAL', active=True)
    monthly = Attributes.objects.get(identifier='FREQ_MONTHLY', active=True)
    
    save_path = os.path.join(WORKING_PATH,universe.name + '_' + str(user.id) + '_PRICES_REPORT_' + str(today) + '.xlsx')
    
    if rolling!=None:
        if start_date==None:
            start_date = dates.AddDay(today, -rolling)
        else:
            effective_start_date = dates.AddDay(today, -rolling)
            if effective_start_date>start_date:
                start_date = effective_start_date
        LOGGER.debug("Rolling enabled - Start date = " + str(start_date))        

    if reference==None:
        all_dates = TrackContainer.objects.filter(day__gte=start_date, effective_container_id__in=[member.id for member in universe.members.all()], type__id=nav_value.id,quality__id=official_type.id, frequency__id=frequency.id, status__id=final_status.id, time__isnull=True).distinct('day').order_by('day').values_list('day', flat=True)
    else:
        all_dates = TrackContainer.objects.filter(day__gte=start_date, frequency_reference=reference, effective_container_id__in=[member.id for member in universe.members.all()], type__id=nav_value.id,quality__id=official_type.id, frequency__id=frequency.id, status__id=final_status.id, time__isnull=True).distinct('day').order_by('day').values_list('day', flat=True)
    if len(all_dates)==0:
        LOGGER.warn("Universe members do not have track content")
        return False, None
    LOGGER.info("Will produce " + str(len(all_dates)) + " columns groups")
    
    if start_date==None:
        start_date = all_dates[0]
        LOGGER.info("Full content - Start date = " + str(start_date))
    
    workbook = xlsxwriter.Workbook(save_path)
    formats = define_formats(workbook)
    
    ws = workbook.add_worksheet('Prices')
    ws.set_column(0,0,30)

    col_index = 1
    
    all_data = {}
    first = True    
    for day in all_dates:
        row_index = 0
        ws.write(row_index, col_index, 'Closing price on the ' + str(day), formats['main_format_normal'])
        ws.write(row_index, col_index + 1, 'WTD on the ' + str(day), formats['main_format_normal'])
        ws.write(row_index, col_index + 2, 'MTD on the ' + str(day), formats['main_format_normal'])
        ws.write(row_index, col_index + 3, 'YTD on the ' + str(day), formats['main_format_normal'])
        ws.set_column(col_index,col_index+3,15)
        eom = dates.AddDay(dates.GetStartOfMonth(day),-1)
        eoy = datetime.date(day.year-1,12,31)
        row_index += 1
        # CONTENT
        for member in universe.members.all():
            LOGGER.info("Working with " + member.name + " as of " + str(day))
            if first:
                ws.write(row_index, 0, member.short_name, formats['main_format_normal'])
            if not all_data.has_key(member.id):
                all_data[member.id] = {}
                provider = member.associated_companies.filter(role__identifier='SCR_DP')
                if provider.exists():
                    provider = provider[0]
                    monthlies = all_values = dict(TrackContainer.objects.filter(effective_container_id=member.id, type__id=nav_value.id,quality__id=official_type.id, source__id=provider.company.id, frequency__id=monthly.id, status__id=final_status.id, time__isnull=True).values_list('day','value'))
                    if start_date==None:
                        if reference==None:
                            all_values = dict(TrackContainer.objects.filter(effective_container_id=member.id, type__id=nav_value.id,quality__id=official_type.id, source__id=provider.company.id, frequency__id=frequency.id, status__id=final_status.id, time__isnull=True).values_list('day','value'))
                            all_performances = dict(TrackContainer.objects.filter(effective_container_id=member.id, type__id=perf_value.id,quality__id=official_type.id, source__id=provider.company.id, frequency__id=frequency.id, status__id=final_status.id, time__isnull=True).values_list('day','value'))
                        else:
                            all_values = dict(TrackContainer.objects.filter(frequency_reference=reference, effective_container_id=member.id, type__id=nav_value.id,quality__id=official_type.id, source__id=provider.company.id, frequency__id=frequency.id, status__id=final_status.id, time__isnull=True).values_list('day','value'))
                            all_performances = dict(TrackContainer.objects.filter(frequency_reference=reference, effective_container_id=member.id, type__id=perf_value.id,quality__id=official_type.id, source__id=provider.company.id, frequency__id=frequency.id, status__id=final_status.id, time__isnull=True).values_list('day','value'))
                    else:
                        if reference==None:
                            all_values = dict(TrackContainer.objects.filter(day__gte=start_date, effective_container_id=member.id, type__id=nav_value.id,quality__id=official_type.id, source__id=provider.company.id, frequency__id=frequency.id, status__id=final_status.id, time__isnull=True).values_list('day','value'))
                            all_performances = dict(TrackContainer.objects.filter(day__gte=start_date, effective_container_id=member.id, type__id=perf_value.id,quality__id=official_type.id, source__id=provider.company.id, frequency__id=frequency.id, status__id=final_status.id, time__isnull=True).values_list('day','value'))
                        else:
                            all_values = dict(TrackContainer.objects.filter(day__gte=start_date, frequency_reference=reference, effective_container_id=member.id, type__id=nav_value.id,quality__id=official_type.id, source__id=provider.company.id, frequency__id=frequency.id, status__id=final_status.id, time__isnull=True).values_list('day','value'))
                            all_performances = dict(TrackContainer.objects.filter(day__gte=start_date, frequency_reference=reference, effective_container_id=member.id, type__id=perf_value.id,quality__id=official_type.id, source__id=provider.company.id, frequency__id=frequency.id, status__id=final_status.id, time__isnull=True).values_list('day','value'))
                    all_data[member.id]['VALUES'] = all_values
                    all_data[member.id]['PERFORMANCES'] = all_performances
                    all_data[member.id]['MONTHLY'] = monthlies
            if all_values.has_key(day):
                ws.write(row_index, col_index, all_data[member.id]['VALUES'][day], formats['main_format_normal'])
                ws.write(row_index, col_index + 1, all_data[member.id]['PERFORMANCES'][day], formats['main_format_percent'])
                if all_data[member.id]['MONTHLY'].has_key(eom):
                    LOGGER.info("PREVIOUS EOM:" + str(all_data[member.id]['MONTHLY'][eom]))
                    ws.write(row_index, col_index + 2, (all_data[member.id]['VALUES'][day]/all_data[member.id]['MONTHLY'][eom]) - 1.0, formats['main_format_percent'])
                else:
                    ws.write(row_index, col_index + 2, '', formats['main_format_normal'])
                if all_data[member.id]['MONTHLY'].has_key(eoy):
                    LOGGER.info("PREVIOUS EOY:" + str(all_data[member.id]['MONTHLY'][eoy]))
                    ws.write(row_index, col_index + 3, (all_data[member.id]['VALUES'][day]/all_data[member.id]['MONTHLY'][eoy]) - 1.0, formats['main_format_percent'])
                else:
                    ws.write(row_index, col_index + 3, '', formats['main_format_normal'])
            row_index += 1
        first = False
        col_index += 4
    workbook.close()
    return True, save_path