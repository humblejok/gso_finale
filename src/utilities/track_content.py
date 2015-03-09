'''
Created on 6 mai 2014

@author: humble_jok
'''
from pymongo.mongo_client import MongoClient
from finale.settings import MONGO_URL
from seq_common.utils.dates import epoch_time, from_epoch
import logging

LOGGER = logging.getLogger(__name__)

client = MongoClient(MONGO_URL)

def get_track_content(track, ascending = True):
    LOGGER.info('Loading track content')
    container_id = 'trackscontainer_' + str(track.effective_container_id)
    track_id = 'track_' + str(track.id)
    raw_values = client[container_id][track_id].find().sort('_id',1 if ascending else -1)
    LOGGER.info('Track content loaded from ' + container_id + '.' + track_id + ' with ' + str(client[container_id][track_id].count()) + ' elements.')
    return [{'date':from_epoch(value[u'_id']), 'value': value[u'value']} for value in raw_values]

def get_track_content_display(track, ascending = True, intraday = False):
    content = get_track_content(track, ascending)
    return [{'date':value['date'].strftime('%Y-%m-%d %H:%M:%S' if intraday else '%Y-%m-%d'), 'value':value['value']} for value in content]


def update_end_date(track, intraday):
    container_id = 'trackscontainer_' + str(track.effective_container_id)
    track_id = 'track_' + str(track.id)
    last_value = client[container_id][track_id].find_one({},{'_id': -1})
    if last_value!=None:
        track.end_date = from_epoch(last_value['_id'])
        track.save()

def set_track_content(track, values, clean):
    LOGGER.info('Storing track content')
    if len(values)>0:
        container_id = 'trackscontainer_' + str(track.effective_container_id)
        track_id = 'track_' + str(track.id)
        proper_values = [{'_id': epoch_time(value['date']), 'value': value['value']} for value in values]
        if clean:
            client[container_id][track_id].drop()
            client[container_id][track_id].insert(proper_values)
        else:
            for value in proper_values:
                client[container_id][track_id].update({'_id': value['_id']}, value, True)
        LOGGER.info('Track content stored as ' + container_id + '.' + track_id + ' with ' + str(client[container_id][track_id].count()) + ' elements.')
        if len(values)>0:
            track.start_date = values[0]['date']
            track.end_date = values[len(values)-1]['date']
            track.save()
    else:
        LOGGER.warn('Cannot store empty tracks into MongoDB')
        