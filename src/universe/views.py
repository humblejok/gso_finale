# Create your views here.
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db.models import Q
from django.http.response import HttpResponse
from django.shortcuts import render, redirect
from finale.threaded import bloomberg_data_query, bloomberg_update_query
from finale.utils import to_bloomberg_code
from reports import universe_reports
from universe.models import Universe, TrackContainer, SecurityContainer, \
    Attributes, FundContainer, IndexContainer, BondContainer, CurrencyContainer, \
    CompanyContainer, BloombergTrackContainerMapping
from utilities.track_content import get_track_content_display
import datetime
import logging
import os
import threading
import uuid
import traceback
from seq_common.utils import dates

LOGGER = logging.getLogger(__name__)


def bloomberg_wizard(request, entity):
    # TODO: Check user
    return render(request, entity + '/bloomberg/wizard.html')

def bloomberg_wizard_execute(request, entity):
    # TODO: Check user
    # TODO: Check Bloomberg method
    entries = [str(entry).strip() for entry in request.POST['bloombergList'].split('\r')]
    try:
        use_terminal = request.POST['bloombergSource']=='True'
    except:
        use_terminal = False
    prepared_entries = [to_bloomberg_code(entry,use_terminal) for entry in entries]

    response_key = uuid.uuid4().get_hex()
    # TODO: Implement CONSTANTS and dynamic choice
    if entity=='financials':
        bb_thread = threading.Thread(None, bloomberg_data_query, response_key, (response_key, prepared_entries, use_terminal))
    bb_thread.start()
    context = {'response_key': response_key}
    return render(request,entity + '/bloomberg/wizard_waiting.html', context)

def bloomberg_update(request):
    # TODO: Check user
    # TODO: Check Bloomberg method (Terminal/DL)
    bloomberg_company = CompanyContainer.objects.get(name='Bloomberg LP')
    bloomberg_fields = {entry[0]: entry[1] for entry in BloombergTrackContainerMapping.objects.values_list('name__name', 'short_name__name')}
    print bloomberg_fields
    try:
        universe_id = request.GET['universe_id']
    except:
        universe_id = None
    if universe_id!=None:
        universe = Universe.objects.filter(Q(id=universe_id), Q(public=True)|Q(owner__id=request.user.id))
        if universe.exists():
            universe = universe[0]
            all_tracks = TrackContainer.objects.filter(effective_container_id__in=universe.members.all().values_list('id', flat=True), source__id=bloomberg_company.id).order_by('end_date')
    else:
        all_tracks = TrackContainer.objects.filter(source__id=bloomberg_company.id).order_by('end_date')
    print all_tracks
    bulk_information = {}
    for track in all_tracks:
        if track.end_date!=None:
            key = dates.AddDay(track.end_date,1)
        else:
            key = 'None'
        if bloomberg_fields.has_key(track.type.name):
            track_field = bloomberg_fields[track.type.name]
            if not bulk_information.has_key(track_field):
                bulk_information[track_field] = {}
            if not bulk_information[track_field].has_key(key):
                bulk_information[track_field][key] = []
            try:
                bulk_information[track_field][key].append(to_bloomberg_code(track.effective_container.aliases.get(alias_type__name='BLOOMBERG').alias_value, True))
            except:
                traceback.print_exc()
                LOGGER.error("No associated BLOOMBERG information for " + str(track.effective_container.name))
    history_key = uuid.uuid4().get_hex()
    update_thread = threading.Thread(None, bloomberg_update_query, history_key, (history_key, bulk_information, True))
    update_thread.start()
    # TODO: Return error message
    return redirect('universes.html')
    
def check_execution(request):
    response_key = request.POST['response_key']
    if cache.get(response_key)==1.0:
        return HttpResponse('{"result": true, "status": 1.0}',"json")
    else:
        return HttpResponse('{"result": false, "status":' + str(cache.get(response_key)) + '}',"json")
    
def get_execution(request):
    if request.POST.has_key('response_key'):
        response_key = request.POST['response_key']
    else:
        response_key = request.GET['response_key']
    execution_results = cache.get(cache.get('type_' + response_key) + '_' + response_key)
    errors = cache.get('errors_' + response_key)
    universes = Universe.objects.filter(Q(public=True)|Q(owner__id=request.user.id))
    context = {'results': execution_results,'universes': universes, 'errors':errors}
    rendition = render(request, 'rendition/wizard_securities_results.html', context)
    return rendition

def financial_container_get(request):
    # TODO: Check user
    user = User.objects.get(id=request.user.id)
    container_id = request.GET['container_id']
    container = SecurityContainer.objects.get(id=container_id)
    if container.type.identifier=='CONT_FUND':
        container = FundContainer.objects.get(id=container_id)
    elif container.type.identifier=='CONT_INDEX':
        container = IndexContainer.objects.get(id=container_id)
    elif container.type.identifier=='CONT_BOND':
        container = BondContainer.objects.get(id=container_id)
    elif container.type.identifier=='CONT_SPOT':
        container = CurrencyContainer.objects.get(id=container_id)
    elif container.type.identifier=='CONT_FORWARD':
        container = CurrencyContainer.objects.get(id=container_id)
    tracks = TrackContainer.objects.filter(effective_container_id=container_id).order_by('source','type','quality','frequency','id')
    context = {'container': container, 'tracks': tracks}
    return render(request,'container/' + container.type.identifier + '.html', context)

def track_get(request):
    # TODO: Check user
    user = User.objects.get(id=request.user.id)
    try:
        track_id = request.POST['track_id']
    except:
        track_id = request.GET['track_id']
    track = TrackContainer.objects.get(id=track_id)
    track_content = get_track_content_display(track, True)
    return HttpResponse(str(track_content).replace("'",'"'),"json")

def universes(request):
    # TODO: Check user
    universes = Universe.objects.filter(Q(public=True)|Q(owner__id=request.user.id))
    context = {'universes': universes}
    return render(request, 'universes.html', context)

def universe_backtest_wizard(request):
    source_id = request.GET['universe_id']
    # TODO: Check user
    user = User.objects.get(id=request.user.id)
    try:
        source = Universe.objects.get(Q(id=source_id),Q(public=True)|Q(owner__id=request.user.id))
    except:
        # TODO: Return error message
        return redirect('universes')
    context = {'universe': source}
    return render(request, 'financials/backtest/wizard.html', context)
    

def universe_report(request):
    source_id = request.GET['universe_id']
    # TODO: Check user
    user = User.objects.get(id=request.user.id)
    
    weekly = Attributes.objects.get(identifier='FREQ_WEEKLY', active=True)
    reference = Attributes.objects.get(identifier='DT_REF_FRIDAY')
    try:
        source = Universe.objects.get(Q(id=source_id),Q(public=True)|Q(owner__id=request.user.id))
    except:
        # TODO: Return error message
        return redirect('universes')
    result, path = universe_reports.simple_price_report(user, source, weekly, reference, datetime.datetime(2014,4,25,0,0), 90)
    xlsx_mime = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    if not result:
        return redirect('universes')
    else:
        with open(path,'rb') as f:
            content = f.read()
        response = HttpResponse(content,xlsx_mime)
        split_path = os.path.split(path)
        response['Content-Disposition'] = 'attachement; filename="' + split_path[len(split_path)-1] + '"'
        return response 

def universe_create(request):
    # TODO: Check user
    user = User.objects.get(id=request.user.id)
    
    universe_name = request.POST['universe_name']
    universe_short_name = request.POST['universe_short_name']
    universe_description = request.POST['universe_description']
    universe_securities = [long(security_id) for security_id in request.POST['universe_securities'].split(',')]
    try:
        universe = Universe()
        universe.name = universe_name
        universe.short_name = universe_short_name
        universe.type = Attributes.objects.get(identifier='CONT_UNIVERSE')
        universe.inception_date = datetime.date.today()
        universe.closed_date = None
        universe.status = Attributes.objects.get(identifier='STATUS_ACTIVE')
        universe.public = False
        universe.owner = user
        universe.description = universe_description
        universe.save()
        for security_id in universe_securities:
            universe.members.add(SecurityContainer.objects.get(id=security_id))
        universe.save()
    except:
        return HttpResponse('{"result": false, "status": "Error during universe creation."}',"json")
    
    return HttpResponse('{"result": true, "status": "Universe updated", "universe_id": ' + str(universe.id) + '}',"json")

def universe_change_members(request):
    universe_id = request.POST['universe_id']
    universe_clean = request.POST['universe_clean']=='true'
    universe_securities = [long(security_id) for security_id in request.POST['universe_securities'].split(',')]
    # TODO: Check user
    user = User.objects.get(id=request.user.id)
    try:
        source = Universe.objects.get(Q(id=universe_id),Q(owner__id=request.user.id))
    except:
        # TODO: Return error message
        return HttpResponse('{"result": false, "status": "You are not allowed to edit that universe."}',"json")
    if universe_clean:
        source.members.clear()
        source.save()
    for security_id in universe_securities:
        source.members.add(SecurityContainer.objects.get(id=security_id))
    source.save()
    return HttpResponse('{"result": true, "status": "Universe ' + source.name + 'updated", "universe_id": ' + str(source.id) + '}',"json")

def universe_duplicate(request):
    source_id = request.GET['universe_id']
    # TODO: Check user
    user = User.objects.get(id=request.user.id)
    try:
        source = Universe.objects.get(Q(id=source_id),Q(public=True)|Q(owner__id=request.user.id))
    except:
        # TODO: Return error message
        return redirect('universes.html')
    destination = source.clone(Universe)
    destination.name = destination.name + ' (copy)'
    destination.owner = user
    destination.save()
    for member in source.members.all():
        destination.members.add(member)
    destination.save()
    # TODO: Return success message
    return redirect('universes.html')

def universe_delete(request):
    source_id = request.GET['universe_id']
    # TODO: Check user
    user = User.objects.get(id=request.user.id)
    try:
        source = Universe.objects.get(Q(id=source_id),Q(public=True)|Q(owner__id=request.user.id))
    except:
        # TODO: Return error message
        return redirect('universes.html')
    source.delete()
    # TODO: Return success message
    return redirect('universes.html')

def universe_base_edit(request):
    universe_id = request.POST['universe_id']
    # TODO: Check user
    user = User.objects.get(id=request.user.id)
    try:
        source = Universe.objects.get(Q(id=universe_id),Q(owner__id=request.user.id))
    except:
        # TODO: Return error message
        return redirect('universes.html')
    source.name = request.POST['name']
    source.short_name = request.POST['short_name']
    if request.POST.has_key('public'):
        source.public = True
    else:
        source.public = False
    source.save()
    # TODO: Return success message
    return redirect('/universe_details_edit.html?universe_id=' + str(universe_id))

def universe_description_edit(request):
    universe_id = request.POST['universe_id']
    # TODO: Check user
    user = User.objects.get(id=request.user.id)
    try:
        source = Universe.objects.get(Q(id=universe_id),Q(owner__id=request.user.id))
    except:
        # TODO: Return error message
        return redirect('universes')
    source.description = request.POST['universe_description']
    source.save()
    # TODO: Return success message
    return HttpResponse('{"result": true, "status": "Description changed", "member_id": ' + universe_id + '}',"json")

def universe_get_writable(request):
    # TODO: Check user
    user = User.objects.get(id=request.user.id)
    universes = Universe.objects.filter(Q(public=True)|Q(owner__id=request.user.id))
    context = {'universes': universes}
    return render(request, 'rendition/universes/universes_list.json', context)

def universe_details(request):
    if request.POST.has_key('universe_id'):
        universe_id = request.POST['universe_id']
    else:
        universe_id = request.GET['universe_id']
    # TODO: Check user
    user = User.objects.get(id=request.user.id)
    try:
        source = Universe.objects.get(Q(id=universe_id),Q(public=True)|Q(owner__id=request.user.id))
    except:
        # TODO: Return error message
        return redirect('universes.html')
    context = {'universe': source, 'tracks': {}}
    
    nav_value = Attributes.objects.get(identifier='NUM_TYPE_NAV', active=True)
    final_status = Attributes.objects.get(identifier='NUM_STATUS_FINAL', active=True)
    official_type = Attributes.objects.get(identifier='PRICE_TYPE_OFFICIAL', active=True)
    monthly = Attributes.objects.get(identifier='FREQ_MONTHLY', active=True)
    
    for member in source.members.all():
        provider = member.associated_companies.filter(role__identifier='SCR_DP')
        if provider.exists():
            provider = provider[0]
            try:
                track = TrackContainer.objects.get(
                    effective_container_id=member.id,
                    type__id=nav_value.id,
                    quality__id=official_type.id,
                    source__id=provider.company.id,
                    frequency__id=monthly.id,
                    status__id=final_status.id)
                context['tracks']['track_' + str(member.id)] = get_track_content_display(track)
            except:
                LOGGER.warn("No track found for container [" + str(member.id) + "]")
                context['tracks']['track_' + str(member.id)] = []
    return render(request, 'universe_details.html', context)

def universe_details_edit(request):
    if request.POST.has_key('universe_id'):
        universe_id = request.POST['universe_id']
    else:
        universe_id = request.GET['universe_id']
    # TODO: Check user
    user = User.objects.get(id=request.user.id)
    try:
        source = Universe.objects.get(Q(id=universe_id),Q(public=True)|Q(owner__id=request.user.id))
    except:
        # TODO: Return error message
        return redirect('universes.html')
    context = {'universe': source, 'tracks': {}}
    
    nav_value = Attributes.objects.get(identifier='NUM_TYPE_NAV', active=True)
    final_status = Attributes.objects.get(identifier='NUM_STATUS_FINAL', active=True)
    official_type = Attributes.objects.get(identifier='PRICE_TYPE_OFFICIAL', active=True)
    monthly = Attributes.objects.get(identifier='FREQ_MONTHLY', active=True)
    
    for member in source.members.all():
        provider = member.associated_companies.filter(role__identifier='SCR_DP')
        if provider.exists():
            provider = provider[0]
            try:
                track = TrackContainer.objects.get(
                    effective_container_id=member.id,
                    type__id=nav_value.id,
                    quality__id=official_type.id,
                    source__id=provider.company.id,
                    frequency__id=monthly.id,
                    status__id=final_status.id)
                context['tracks']['track_' + str(member.id)] = get_track_content_display(track)
            except:
                LOGGER.warn("No track found for container [" + str(member.id) + "]")
                context['tracks']['track_' + str(member.id)] = []
    return render(request, 'universe_details_edit.html', context)

def universe_member_delete(request):
    try:
        universe_id = request.GET['universe_id']
        member_id = request.GET['member_id']
        # TODO: Check user
        user = User.objects.get(id=request.user.id)
        source = Universe.objects.get(Q(id=universe_id),Q(public=True)|Q(owner__id=request.user.id))
        member = SecurityContainer.objects.get(id=member_id)
        source.members.remove(member)
        source.save()
    except:
        # TODO: Return error message
        return HttpResponse('{"result": false, "status": "Could not remove member!"}',"json")
    # TODO: Return success message
    return HttpResponse('{"result": true, "status": "Member removed", "member_id": ' + member_id + '}',"json")

def security_search(request):
    try:
        searching = request.POST['searching']
        # TODO: Check user
        user = User.objects.get(id=request.user.id)
        results = SecurityContainer.objects.filter(Q(name__icontains=searching) | Q(short_name__icontains=searching) | Q(aliases__alias_value__icontains=searching))
        
    except:
        return HttpResponse('{"result": false, "status": "Error while querying for:"' + searching + '}',"json")