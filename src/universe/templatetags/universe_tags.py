'''
Created on 10 mars 2014

@author: humble_jok
'''
from django import template
from json import dumps
from universe.models import Attributes, CoreModel
import datetime
from utilities.compute.valuations import get_work_date
from django.forms.models import model_to_dict
from finale.utils import dict_to_json_compliance

PERF_MAPPING = { 'FREQ_DAILY': ['day', 'wtd', 'mtd', 'qtd', 'std', 'ytd', 'si'],
                 'FREQ_WEEKLY': ['wtd', 'mtd', 'qtd', 'std', 'ytd', 'si'],
                 'FREQ_MONTHLY': ['mtd', 'qtd', 'std', 'ytd', 'si'],
                 'FREQ_QUARTERLY': ['qtd', 'std', 'ytd', 'si'],
                 'FREQ_SEMESTERLY': ['std', 'ytd', 'si'],
                 'FREQ_ANNUALLY': ['ytd', 'si']
                }

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
    if type(d) is dict:
        if d.has_key(key):
            return d[key]
        elif d.has_key(str(key)):
            return d[str(key)]
        elif d.has_key(unicode(key)):
            return d[unicode(key)]
    return None

@register.filter()
def get_as_json_string(data):
    if isinstance(data, CoreModel):
        return dumps(dict_to_json_compliance(model_to_dict(data), data.__class__))
    else:
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

@register.filter()
def get_jquery_id(identity):
    return identity.replace('.', '\\\\.')

@register.filter()
def match_frequency(date_value, frequency):
    if isinstance(date_value,basestring):
        wrk_date = datetime.datetime.strptime(date_value,'%Y-%m-%d')
    else:
        wrk_date = date_value
    return get_work_date(wrk_date, frequency)==wrk_date

@register.filter()
def get_frequency_perfs(frequency):
    return PERF_MAPPING[frequency.identifier]
