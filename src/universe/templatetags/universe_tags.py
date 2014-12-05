'''
Created on 10 mars 2014

@author: humble_jok
'''
from django import template
from json import dumps
from universe.models import Attributes

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

@register.filter()
def get_as_json_string(data):
    return dumps(data)

@register.filter()
def get_field_value(data, field_chain):
    all_fields = field_chain.split('.')
    for field in all_fields:
        if data==None:
            break
        data = getattr(data, field)
    return data if data!=None else 'N/A'

@register.filter()
def get_value(data, field_chain):
    all_fields = field_chain.split('.')
    if data!=None:
        data = getattr(data, all_fields[0])
    if isinstance(data, Attributes):
        return data.identifier
    return data if data!=None else ''