'''
Created on May 26, 2014

@author: sdejonckheere
'''
from universe.models import TrackContainer, Attributes
from utilities.track_content import get_track_content_display, get_track_content
import logging

LOGGER = logging.getLogger(__name__)

def get_main_track(security, ascending = True,  display = False):
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