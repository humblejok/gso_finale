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
tracks = client.tracks

def get_track_content(track, ascending = True):
    LOGGER.info('Loading track content')
    container_id = 'container_' + str(track.effective_container_id)
    track_id = 'track_' + str(track.id)
    raw_values = tracks[container_id][track_id].find().sort('_id',1 if ascending else -1)
    LOGGER.info('Track content loaded from ' + container_id + '.' + track_id + ' with ' + str(tracks[container_id][track_id].count()) + ' elements.')
    return [{'date':from_epoch(value[u'_id']), 'value': value[u'value']} for value in raw_values]

def get_track_content_display(track, ascending = True, intraday = False):
    content = get_track_content(track, ascending)
    return [{'date':value['date'].strftime('%Y-%m-%d %H:%M:%S' if intraday else '%Y-%m-%d'), 'value':value['value']} for value in content]

def set_track_content(track, values, clean):
    LOGGER.info('Storing track content')
    if len(values)>0:
        container_id = 'container_' + str(track.effective_container_id)
        track_id = 'track_' + str(track.id)
        proper_values = [{'_id': epoch_time(value['date']), 'value': value['value']} for value in values]
        if clean:
            tracks[container_id][track_id].drop()
        tracks[container_id][track_id].insert(proper_values)
        LOGGER.info('Track content stored as ' + container_id + '.' + track_id + ' with ' + str(tracks[container_id][track_id].count()) + ' elements.')
        if len(values)>0:
            track.start_date = values[0]['date']
            track.end_date = values[len(values)-1]['date']
            track.save()
    else:
        LOGGER.warn('Cannot store empty tracks into MongoDB')