'''
Created on May 24, 2014

@author: sdejonckheere
'''
import xlsxwriter

def simple_xlsx_dump(list_of_rows, output_file):
    workbook = xlsxwriter.Workbook(output_file)
    ws = workbook.add_worksheet('Sheet1')
    row_index = 0
    for row in list_of_rows:
        for col_index in range(0, len(row)):
            ws.write(row_index, col_index, row[col_index])
        row_index += 1
    workbook.close()