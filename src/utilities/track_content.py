'''
Created on 6 mai 2014

@author: humble_jok
'''
from pymongo.mongo_client import MongoClient
from finale.settings import MONGO_URL
from seq_common.utils.dates import epoch_time

client = MongoClient(MONGO_URL)
tracks = client.tracks

def get_track_content(track, ascending = True):
    return tracks[track.effective_container_id][track.id].find().sort()

def set_track_content(track, values):
    proper_values = [{'date': epoch_time(value['date']), 'value': value['value']} for value in values]
    tracks[track.effective_container_id][track.id].insert(proper_values)