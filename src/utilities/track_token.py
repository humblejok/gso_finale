'''
Created on May 26, 2014

@author: sdejonckheere
'''
from universe.models import TrackContainer, Attributes, CompanyContainer,\
    SecurityContainer
from utilities.track_content import get_track_content_display, get_track_content
import logging
from finale import threaded
from datetime import datetime as dt

LOGGER = logging.getLogger(__name__)

def get_track(security, track_info):
    final_status = Attributes.objects.get(identifier='NUM_STATUS_FINAL', active=True)
    official_type = Attributes.objects.get(identifier='PRICE_TYPE_OFFICIAL', active=True)
    daily_frequency = Attributes.objects.get(identifier='FREQ_DAILY', active=True)
    track_type = Attributes.objects.get(identifier=track_info['track_type'], active=True)
    finale_company = CompanyContainer.objects.get(name='FinaLE Engine')
    if track_info['track_default']:
        provider = security.associated_companies.filter(role__identifier='SCR_DP')
        if provider.exists():
            provider = provider[0].company
        else:
            provider = finale_company
        if security.frequency!=None:
            frequency_id = security.frequency.id
        else:
            frequency_id = daily_frequency.id
        frequency_reference = security.frequency_reference
    else:
        provider = finale_company
        if track_info['track_datasource']!='DATASOURCE_FINALE':
            provider_company = security.associated_companies.filter(role__identifier='SCR_DP')
            if provider_company.exists():
                provider = provider_company[0].company
        frequency_id = Attributes.objects.get(identifier=track_info['track_frequency'], active=True).id
        frequency_reference = None
        
    track = TrackContainer.objects.filter(
            effective_container_id=security.id,
            type__id=track_type.id,
            quality__id=official_type.id,
            source__id=provider.id,
            frequency__id=frequency_id,
            frequency_reference= frequency_reference,
            status__id=final_status.id)
    return track[0] if track.exists() else None

def get_main_track_content(security, ascending = True,  display = False):
    nav_value = Attributes.objects.get(identifier='NUM_TYPE_NAV', active=True)
    final_status = Attributes.objects.get(identifier='NUM_STATUS_FINAL', active=True)
    official_type = Attributes.objects.get(identifier='PRICE_TYPE_OFFICIAL', active=True)
    provider = security.associated_companies.filter(role__identifier='SCR_DP')
    if provider.exists():
        provider = provider[0]
        try:
            track = TrackContainer.objects.get(
                effective_container_id=security.id,
                type__id=nav_value.id,
                quality__id=official_type.id,
                source__id=provider.company.id,
                frequency__id=security.frequency.id,
                frequency_reference=security.frequency_reference,
                status__id=final_status.id)
            return get_track_content_display(track, ascending, False) if display else get_track_content(track, ascending)
        except:
            LOGGER.warn("No track found for container [" + str(security.id) + "]")
    return None

def get_closest_value(track_content, value_date):
    if track_content==None:
        return None
    previous = None
    for token in track_content:
        if token['date']==value_date:
            return token
        elif token['date']>value_date:
            return previous
        previous = token
    return previous

def get_exchange_rate(source_currency, destination_currency):
    currency = SecurityContainer.objects.filter(name__startswith=source_currency + destination_currency)
    if not currency.exists():
        threaded.bloomberg_data_query('NO_NEED', [source_currency + destination_currency + ' Curncy'], True)
    currency = SecurityContainer.objects.filter(name__startswith=source_currency + destination_currency)
    if currency.exists():
        return get_main_track_content(currency[0])
    else:
        return None

def get_exchange_rate_price(source_currency, destination_currency, value_date):
    currency = SecurityContainer.objects.filter(name__startswith=source_currency + destination_currency)
    if not currency.exists():
        threaded.bloomberg_data_query('NO_NEED', [source_currency + destination_currency + ' Curncy'], True)
    currency = SecurityContainer.objects.filter(name__startswith=source_currency + destination_currency)
    if currency.exists():
        value = get_closest_value(get_main_track_content(currency[0]), dt.combine(value_date, dt.min.time()))
        if value==None:
            return 1.0
        else:
            return value['value']