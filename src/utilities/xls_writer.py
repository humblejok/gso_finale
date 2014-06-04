'''
Created on May 24, 2014

@author: sdejonckheere
'''
import xlsxwriter
import datetime

def date_format(workbook):
    return workbook.add_format({'num_format': 'mm/dd/yy'})

def simple_xlsx_dump(list_of_rows, output_file):
    workbook = xlsxwriter.Workbook(output_file)
    ws = workbook.add_worksheet('Sheet1')
    row_index = 0
    for row in list_of_rows:
        for col_index in range(0, len(row)):
            if isinstance(row[col_index],(datetime.date, datetime.datetime)):
                ws.write(row_index, col_index, row[col_index], date_format(workbook))
            else:
                ws.write(row_index, col_index, row[col_index])
        row_index += 1
    workbook.close()