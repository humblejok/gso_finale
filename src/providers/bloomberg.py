'''
Created on Aug 5, 2013

@author: sdejonckheere
'''
from finale import settings
import pika
import uuid
import logging
from providers import bloomberg_pb2
import threading
from django.db.models import Q
import datetime
from universe.models import Attributes, SecurityContainer,\
    BloombergDataContainerMapping, Alias
from finale.utils import get_bloomberg_provider
import traceback
from utilities.security_content import set_security_information,\
    get_security_provider_information
#
# LOGGING
#
LOGGER = logging.getLogger(__name__)


class BloombergRequestSender(threading.Thread):
    connection = None
    channel = None
    
    request_uid = None
    
    response_queue = None
    response_body = None
    response_object = None
    
    request = None
    
    _stop = None
    
    def __init__(self, request):
        super(BloombergRequestSender, self).__init__()
        LOGGER.info("Initialising new Bloomberg request sender")
        self.connection = pika.BlockingConnection(pika.URLParameters(settings.BLOOMBERG_BROKER_URL))
        LOGGER.info("Connection " + str(self.connection))
        self.channel = self.connection.channel()
        self.response_queue = self.channel.queue_declare(exclusive=True).method.queue 
        self.channel.basic_consume(self.on_bloomberg_response, no_ack=True, queue=self.response_queue)
        LOGGER.info("Response queue:" + self.response_queue)
        self.request = request
        self._stop = threading.Event()
        
    def on_bloomberg_response(self, channel, method, properties, body):
        LOGGER.info("Response received for correlation key [" + properties.correlation_id + "]")
        LOGGER.debug("Connection " + str(self.connection) + " response received")
        if self.request_uid==properties.correlation_id:
            LOGGER.debug("\tMatching correlation key [" + properties.correlation_id + "]")
            if self.request.HasField('responsebuilderclass'):
                LOGGER.info("\tRaw message is assigned")
                self.response_object = body
            else:    
                self.response_object = bloomberg_pb2.BloombergResponse()
                self.response_object.ParseFromString(body)
        LOGGER.debug("Deleting temporary queue")
        try:
            channel.queue_delete(method.queue)
        except:
            LOGGER.warn("Temporary queue already closed?")
        try:
            LOGGER.debug("Closing temporary connection")
            self.connection.close()
        except:
            LOGGER.warn("Temporary channel already closed?")
        LOGGER.debug("Closing thread")
        self.response_body = body
        self._stop.set()

    def run(self):
        self.response_body = None
        self.request_uid = str(uuid.uuid4())
        LOGGER.info("Sending with reply to [" + str(self.response_queue) + "] and correlation key [" + self.request_uid + "]")
        self.channel.basic_publish( exchange='',
                                    routing_key='BLOOMBERG-REQUEST-QUEUE',
                                    body=self.request.SerializeToString(),
                                    properties=pika.BasicProperties(reply_to = self.response_queue, correlation_id=self.request_uid,content_type='application/x-protobuf')
                                   )
        try:
            while not self._stop.is_set():
                self.connection.process_data_events()
        except pika.exceptions.AMQPError,e:
            LOGGER.debug("Connection " + str(self.connection) + " generates an error:" + str(e))
        LOGGER.debug("Connection " + str(self.connection) + " closed")
        self._stop.set()
    
    def send_dictionary(self, dictionnary):
        self.channel.basic_publish( exchange='',
                            routing_key='BLOOMBERG-DICTIONNARY-QUEUE',
                            body=dictionnary.SerializeToString(),
                            properties=pika.BasicProperties(content_type='application/x-protobuf')
                           )
        
def populate_security_from_bloomberg_protobuf(data):    
    bloomberg_alias = Attributes.objects.get(identifier='ALIAS_BLOOMBERG')
    daily = Attributes.objects.get(identifier='FREQ_DAILY', active=True)
    bloomberg_provider = get_bloomberg_provider()
    
    securities = {}
    with_errors = []
    
    for row in data.rows:
        if row.errorCode==0:
            if row.field=='SECURITY_TYP':
                try:
                    LOGGER.debug('Entity identified by [' + row.ticker + ',' + row.valueString + '] will be created')
                    sec_type_name = Attributes.objects.get(type='bloomberg_security_type', name=row.valueString).short_name
                    cont_type_name = Attributes.objects.get(type='bloomberg_container_type', name=row.valueString).short_name
                    container_type = Attributes.objects.get(identifier=cont_type_name)
                    security_type = Attributes.objects.get(type='security_type', identifier=sec_type_name)
                    if not securities.has_key(row.ticker):
                        LOGGER.info('Creating new security for ticker ' + str(row.ticker))
                        securities[row.ticker] = SecurityContainer.create()
                    securities[row.ticker].type = container_type
                    securities[row.ticker].security_type = security_type
                except:
                    traceback.print_exc()
                    LOGGER.warn('Entity identified by [' + row.ticker  + ',' + row.valueString + ',' + sec_type_name + '] will be treated as a simple security')
                    securities[row.ticker] = SecurityContainer.create()
        else:
            with_errors.append(row.ticker)
            
    for row in data.rows:
        if row.errorCode==0:
            field_info = BloombergDataContainerMapping.objects.filter(Q(short_name__code=row.field), Q(container__short_name=container_type.short_name) | Q(container__short_name='Security') , Q(active=True))
            if field_info.exists():
                field_info = BloombergDataContainerMapping.objects.get(short_name__code=row.field, active=True)
                set_security_information(securities[row.ticker], field_info.name , row.valueString, 'bloomberg')
                securities[row.ticker].save()
                if field_info.model_link!=None and field_info.model_link!='':
                    info = Attributes()
                    info.name = row.field
                    info.short_name = field_info.model_link
                    securities[row.ticker].set_attribute('bloomberg', info, row.valueString)
            else:
                LOGGER.debug("Cannot find matching field for " + row.field)
    for security in securities.values():
        security.finalize()
    #[security.finalize() for security in securities.values()]
    [security.associated_companies.add(bloomberg_provider) for security in securities.values() if len(security.associated_companies.all())==0]
    [setattr(security,'frequency',daily) for security in securities.values()]
    [security.save() for security in securities.values()]
    final_tickers = []
    for ticker in securities:
        securities[ticker].status = Attributes.objects.get(identifier='STATUS_TO_BE_VALIDATED')
        ticker_value = securities[ticker].aliases.filter(alias_type__name='BLOOMBERG')
        if ticker_value.exists() and securities[ticker].market_sector!=None:
            LOGGER.info("Using Bloomberg information for ticker and exchange")
            ticker_value = ticker_value[0]
            if not ticker_value.alias_value.endswith(securities[ticker].market_sector):
                new_full_ticker = ticker_value.alias_value + ' ' + securities[ticker].market_sector
                ticker_value.alias_value = new_full_ticker
                final_tickers.append(new_full_ticker)
                ticker_value.save()
        else:
            LOGGER.info("Using user information for ticker and exchange")
            ticker_value = Alias()
            ticker_value.alias_type = bloomberg_alias
            ticker_value.alias_value = ticker
            ticker_value.save()
            final_tickers.append(ticker)
            securities[ticker].aliases.add(ticker_value)
    [security.save() for security in securities.values()]
    
    for security in securities.values():
        if security.type!=None:
            if security.type.identifier=='CONT_BOND':
                data = get_security_provider_information(security, 'bloomberg')
                if data.has_key('coupon_rate') and data.has_key('maturity_date'):
                    security.name = data['short_name'] + ' ' + data['coupon_rate'] + '% ' + data['maturity_date']
                    security.save()
                else:
                    LOGGER.error(u"The following security has incomplete data [" + unicode(security.name) + u"," + unicode(security.id) +  u"]")
        else:
            LOGGER.error(u"The following security is wrongly categorized [" + unicode(security.name) + u"," + unicode(security.id) +  u"]")
    return securities, final_tickers, with_errors