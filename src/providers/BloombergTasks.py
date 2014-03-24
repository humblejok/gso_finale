'''
Created on Aug 19, 2013

@author: sdejonckheere
'''
from django.db.models.aggregates import Max
from providers import bloomberg_pb2
from providers.bloomberg import BloombergRequestSender
from seq_common.decorators import log_start_end_email
from seq_common.utils import dates
import datetime
import logging
import time

from finale import settings
from seq_common.network.soap import RequestsTransport
from xml.sax.saxutils import escape

LOGGER = logging.getLogger(__name__)

DEFAULT_GET_DATA_FIELDS = ['LONG_COMP_NAME','INDUSTRY_SECTOR','INDUSTRY_GROUP','INDUSTRY_SUBGROUP','SECURITY_TYP',
                           'BICS_LEVEL_1_NAME','BICS_LEVEL_2_NAME','BICS_LEVEL_3_NAME','FUND_GEO_FOCUS','FUND_ASSET_CLASS_FOCUS',
                           'FUND_STRATEGY','FUND_MGMT_STYLE','FUND_TYP','FUND_DOMICILE_TYP','REGION_OR_COUNTRY','TICKER','COUNTRY',
                           'MARKET_SECTOR_DES','ISSUER','ID_ISIN','CRNCY','EQY_PRIM_EXCH_SHRT','PRIMARY_EXCHANGE_NAME', 'FUND_INCEPT_DT',
                           'ISSUE_DT','FUND_RTG_CLASS_FOCUS','PX_CLOSE_DT','EQY_FUND_CRNCY','REL_INDEX']

BLOOMBERG_PROGRAMS = (('getData','Static Data'),('getHistory','Historical Data'))

BLOOMBERG_ID_TYPES = (('ISIN','Isin'), ('TICKER', 'Ticker'))


def send_bloomberg_get_history(tickers, fields=['PX_LAST'], ticker_type = 'ISIN'):
    request = bloomberg_pb2.BloombergRequest()
    request.program = 'getHistory'
    request.rawmode = False
    request.tickertype = ticker_type
    request.startdate = dates.epoch_time(datetime.datetime(1972,1,1,0,0,0))
    [request.tickers.append(t) for t in tickers]
    [request.fields.append(f) for f in fields]
    
    sender = BloombergRequestSender(request)
    sender.start()
    time.sleep(1)
    LOGGER.info("Waiting for getHistory response")
    while not sender._stop.isSet():
        None
    return sender.response_object

def send_bloomberg_get_data(tickers, fields=DEFAULT_GET_DATA_FIELDS, ticker_type = 'ISIN'):
    request = bloomberg_pb2.BloombergRequest()
    request.program = 'getData'
    request.rawmode = False
    request.tickertype = ticker_type
    [request.tickers.append(t) for t in tickers]
    [request.fields.append(f) for f in fields]
    
    sender = BloombergRequestSender(request)
    sender.start()
    time.sleep(1)
    LOGGER.info("Waiting for getData response")
    while not sender._stop.isSet():
        None
    return sender.response_object    