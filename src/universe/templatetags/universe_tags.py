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

@register.filter()
def as_identifier(name):
    return name.lower().replace(' ','_')

@register.filter()
def get_dict_key(d, key):
    if d.has_key(key):
        return d[key]
    elif d.has_key(str(key)):
        return d[str(key)]
    elif d.has_key(unicode(key)):
        return d[unicode(key)]
    else:
        return None