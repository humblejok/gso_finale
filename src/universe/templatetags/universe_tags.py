'''
Created on 10 mars 2014

@author: humble_jok
'''
from django import template

register = template.Library()

@register.filter()
def track_identifier(track_id):
    return 'track_' + str(track_id)

@register.filter()
def track_content(tracks, track_id):
    return tracks['track_' + str(track_id)]
