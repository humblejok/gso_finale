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