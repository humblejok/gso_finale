# Create your views here.
import datetime
import importlib
import logging
import os
import threading
import traceback
import uuid

from django.contrib.auth.models import User
from django.core.cache import cache
from django.db.models import Q
from django.http.response import HttpResponse
from django.shortcuts import render, redirect
from seq_common.utils import dates, classes

from finale.threaded import bloomberg_data_query, bloomberg_update_query
from finale.utils import to_bloomberg_code, get_static_fields
from reports import universe_reports
from universe.models import Universe, TrackContainer, SecurityContainer, \
    Attributes, CompanyContainer, BloombergTrackContainerMapping, BacktestContainer, \
    Container, RelatedCompany, PortfolioContainer, FinancialContainer, \
    PersonContainer
from utilities.external_content import import_external_data, \
    import_external_grouped_data, import_external_tracks
from utilities.track_content import get_track_content_display
from utilities.track_token import get_main_track
from utilities import setup_content, external_content
from bson.json_util import dumps
import json
from django.template.context import Context
from django.template import loader
from finale.settings import STATICS_PATH, STATICS_GLOBAL_PATH
from django.db.models.fields import FieldDoesNotExist
from django.forms.models import model_to_dict


LOGGER = logging.getLogger(__name__)

def call_external(request):
    context = {}
    provider = request.GET['provider']
    action = request.GET['action']
    step = request.GET['step']
    if step=='execute':
        getattr(importlib.import_module('external.' + provider), action)(request.POST)
    return render(request, 'external/' + provider + '/' + action + '/' + step + '.html', context)

def get_attributes(request):
    user = User.objects.get(id=request.user.id)
    attributes_type = request.POST['attributes_type']
    attributes = Attributes.objects.filter(type=attributes_type, active=True)
    attributes = [attribute.get_short_json() for attribute in attributes]
    return HttpResponse('{"result": ' + dumps(attributes) + ', "attribute_type":"' + attributes_type + '""status_message": "Loaded"}',"json")

def get_filtering_entry(request):
    user = User.objects.get(id=request.user.id)
    # TODO: Check user
    container_type = request.POST['container_type']
    filtered_field = request.POST['filtered_field']
    filtering_field = request.POST['filtering_field']
    
    container_class = container_type + '_CLASS'
    # TODO: Handle error
    effective_class_name = Attributes.objects.get(identifier=container_class, active=True).name
    effective_class = classes.my_class_import(effective_class_name)
    target_class = effective_class._meta.get_field(filtered_field).rel.to
    limit = dict(target_class._meta.get_field(str(filtering_field)).rel.limit_choices_to)
    limit['active'] = True
    results = dumps([model_to_dict(item) for item in target_class._meta.get_field(filtering_field).rel.to.objects.filter(**limit)])
    return HttpResponse('{"result": ' + results + ', "status_message": "Saved"}',"json")

def backtest_wizard_execute(request):
    # TODO: Check user
    # TODO: Check parameters
    user = User.objects.get(id=request.user.id)
    backtest_name = request.POST['backtestName']
    pm_role = Attributes.objects.get(identifier='TPR_PM')
    backtest_container = Attributes.objects.get(identifier='CONT_BACKTEST')
    active_status = Attributes.objects.get(identifier='STATUS_ACTIVE')
    try:
        backtest = BacktestContainer.objects.get(name=backtest_name, owner=user)
    except:
        backtest = BacktestContainer()
    backtest.name = backtest_name
    backtest.short_name = 'To define'
    backtest.type = backtest_container
    
    backtest.inception_date = request.POST['fromDate']
    if request.POST.has_key('toDate'):
        backtest.closed_date = request.POST['toDate']
    backtest.short_description = 'A backtest by ' + str(user.last_name) + ' ' + str(user.first_name)
    backtest.status = active_status
    backtest.currency = Attributes.objects.get(identifier=request.POST['currency'], type='currency')
    backtest.owner_role = None
    backtest.owner = None
    backtest.frequency = Attributes.objects.get(identifier=request.POST['frequency'], type='frequency')
    backtest.frequency_reference = None
    backtest.universe = Universe.objects.get(id=request.POST['universeId'])
    backtest.public = False
    backtest.publisher = user
    backtest.reweight = request.POST.has_key('reweight')
    if request.POST.has_key('reweight'):
        backtest.organic_date = request.POST['organicDate']
    else:
        backtest.organic_date = None
    backtest.hedging = Attributes.objects.get(identifier=request.POST['hedgingMethod'], type='hedging_method')
    backtest.fees = Attributes.objects.get(identifier=request.POST['feesScheme'], type='fees_scheme')
    backtest.leverage = Attributes.objects.get(identifier=request.POST['leverage'], type='leverage')
    if request.POST['leverage']!='LEVERAGE_NONE':
        backtest.leverage_level = request.POST['leverageLevel']
    else:
        backtest.leverage_level = None
    backtest.history = Attributes.objects.get(identifier=request.POST['historyCompletion'], type='history_completion')
    backtest.initial_aum = request.POST['initialAUM']
    backtest.save()
    redirect('/universe_backtest_wizard.html?universe_id=' + str(request.POST['universeId']))

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
        return HttpResponse('{"result": true, "status_message": 1.0}',"json")
    else:
        return HttpResponse('{"result": false, "status_message":' + str(cache.get(response_key)) + '}',"json")

def custom_edit(request):
    # TODO: Check user
    container_id = request.GET['container_id']
    custom_id = request.GET['custom']
    target = request.GET['target']
    container = FinancialContainer.objects.get(id=container_id)
    if container.type.id==Attributes.objects.get(identifier='CONT_PORTFOLIO').id:
        container = PortfolioContainer.objects.get(id=container_id)
    else:
        container = SecurityContainer.objects.get(id=container_id)
    tracks = TrackContainer.objects.filter(effective_container_id=container_id).order_by('source','type','quality','frequency','id')
    context = {'container': container, 'tracks': tracks, 'all_types': {}}
    all_types = Attributes.objects.filter(type__startswith=custom_id).order_by('type').distinct('type')
    all_types_json = {}
    for a_type in all_types:
        all_types_json[a_type.type] = [attribute.get_short_json() for attribute in Attributes.objects.filter(type=a_type.type, active=True).order_by('identifier')]
    context['all_types_json'] = dumps(all_types_json);
    content = getattr(external_content, 'get_' + custom_id + "_" + target)()
    context['custom_data'] = content[container_id] if content.has_key(container_id) else getattr(external_content,'create_' + custom_id + '_' + target + '_entry')(container)
    context['custom_data_json'] = dumps(context['custom_data'])
    return render(request, 'external/' + custom_id + '/' + target +'/edit.html', context)

def custom_save(request):
    # TODO: Check user
    container_id = request.POST['container_id']
    custom_id = request.POST['custom']
    target = request.POST['target']
    custom_data = request.POST['new_data']
    custom_data = json.loads(custom_data)
    content = getattr(external_content, 'get_' + custom_id + "_" + target)()
    content[container_id] = custom_data
    getattr(external_content, 'set_' + custom_id + "_" + target)(content)
    return HttpResponse('{"result": true, "status_message": "Saved"}',"json")

def custom_view(request):
    # TODO: Check user
    container_id = request.GET['container_id']
    custom_id = request.GET['custom']
    target = request.GET['target']
    container = FinancialContainer.objects.get(id=container_id)
    if container.type.id==Attributes.objects.get(identifier='CONT_PORTFOLIO').id:
        container = PortfolioContainer.objects.get(id=container_id)
    else:
        container = SecurityContainer.objects.get(id=container_id)
    tracks = TrackContainer.objects.filter(effective_container_id=container_id).order_by('source','type','quality','frequency','id')
    context = {'container': container, 'tracks': tracks}
    return render(request, 'external/' + custom_id + '/' + target +'/view.html', context)

def setup(request):
    # TODO: Check user
    item = request.GET['item']
    item_view_type = request.GET['type']
    all_data = getattr(setup_content, 'get_' + item + '_' + item_view_type)()
    print all_data
    context = {'data_set': Attributes.objects.filter(type=item), 'selection_template': 'statics/' + item + '_en.html','global': dumps(all_data) if not all_data.has_key('global') else dumps(all_data['global']), 'user': {} if not all_data.has_key('user') else dumps(all_data['user'])}
    return render(request, 'rendition/' + item + '/' + item_view_type + '/setup.html', context)


def object_fields_get(request):
    # TODO: Check user
    user = User.objects.get(id=request.user.id)
    container_class = request.POST['container_type'] + '_CLASS'
    # TODO: Handle error
    effective_class_name = Attributes.objects.get(identifier=container_class, active=True).name
    effective_class = classes.my_class_import(effective_class_name)
    object_static_fields = get_static_fields(effective_class)
    return HttpResponse('{"result": ' + dumps(object_static_fields) + ', "status_message": "Found"}',"json")

def object_base_edit(request):
    # TODO: Check user
    user = User.objects.get(id=request.user.id)
    name = request.POST['name']
    new_type = request.POST['newObjectType']
    all_data = setup_content.get_object_type_fields()
    if not all_data.has_key(new_type) or not isinstance(all_data[new_type], list):
        all_data[new_type] = []
    all_data[new_type].append({'name': name, 'fields':[]})
    setup_content.set_object_type_fields(all_data)
    return redirect(request.META.get('HTTP_REFERER') + '&name=' + name + '&newObjectType=' + new_type)

def object_delete(request):
    # TODO: Check user
    user = User.objects.get(id=request.user.id)
    object_type = request.POST['object_type']
    object_name = request.POST['object_name']
    all_data = setup_content.get_object_type_fields()
    new_list = []
    # TODO Pythonize this
    for element in all_data[object_type]:
        if element['name']==object_name:
            None
        else:
            new_list.append(element)
    all_data[object_type] = new_list
    setup_content.set_object_type_fields(all_data)
    return HttpResponse('{"result": true, "status_message": "Deleted"}',"json")
    
def object_save(request):
    # TODO: Check user
    user = User.objects.get(id=request.user.id)
    object_type = request.POST['object_type']
    object_name = request.POST['object_name']
    object_fields = request.POST['object_fields']
    object_fields = json.loads(object_fields)
    all_data = setup_content.get_object_type_fields()
    for element in all_data[object_type]:
        if element['name']==object_name:
            element['fields'] = object_fields
            context = Context({"element": element})
            template = loader.get_template('rendition/object_simple_wizard.html')
            rendition = template.render(context)
            # TODO Implement multi-langage
            outfile = os.path.join(STATICS_GLOBAL_PATH, element['name'] + '_en.html')
            with open(outfile,'w') as o:
                o.write(rendition.encode('utf-8'))
    setup_content.set_object_type_fields(all_data)
    return HttpResponse('{"result": true, "status_message": "Saved"}',"json")


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
    
def external_import(request):
    provider = request.POST['provider']
    data_type = request.POST['data_type']
    if data_type=='tracks':
        import_external_tracks(provider)
    elif request.POST.has_key('grouped'):
        import_external_grouped_data(provider, data_type)
    else:
        import_external_data(provider, data_type)
    return HttpResponse('{"result": true, "status_message": "Job done."}',"json")

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
    export_formats = Attributes.objects.filter(type='export_to', active=True).order_by('id')
    context = {'universes': universes, 'export_formats':export_formats}
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

def universe_export(request):
    source_id = request.GET['universe_id']
    export_to = request.GET['export_to']
    export_type = request.GET['export_type']
    # TODO: Check user
    user = User.objects.get(id=request.user.id)
    try:
        source = Universe.objects.get(Q(id=source_id),Q(public=True)|Q(owner__id=request.user.id))
    except:
        # TODO: Return error message
        return HttpResponse('{"result": false, "status_message": "You are not allowed to view that universe."}',"json")
    try:
        if export_type=='securities':
            path = universe_reports.export_universe(source, export_to)
        elif export_type=='history':
            path = universe_reports.export_universe_history(source, export_to)
        else:
            # Redirect with error message
            return redirect('universes.html')
        xlsx_mime = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        with open(path,'rb') as f:
            content = f.read()
        response = HttpResponse(content,xlsx_mime)
        split_path = os.path.split(path)
        response['Content-Disposition'] = 'attachement; filename="' + split_path[len(split_path)-1] + '"'
        return response
    except:
        traceback.print_exc()
        return redirect('universes.html')

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
        return redirect('universes.html')
    result, path = universe_reports.simple_price_report(user, source, weekly, reference, datetime.datetime(2014,4,25,0,0), 90)
    xlsx_mime = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    if not result:
        return redirect('universes.html')
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
        return HttpResponse('{"result": false, "status_message": "Error during universe creation."}',"json")
    
    return HttpResponse('{"result": true, "status_message": "Universe updated", "universe_id": ' + str(universe.id) + '}',"json")

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
        return HttpResponse('{"result": false, "status_message": "You are not allowed to edit that universe."}',"json")
    if universe_clean:
        source.members.clear()
        source.save()
    for security_id in universe_securities:
        source.members.add(SecurityContainer.objects.get(id=security_id))
    source.save()
    return HttpResponse('{"result": true, "status_message": "Universe ' + source.name + 'updated", "universe_id": ' + str(source.id) + '}',"json")

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

def universe_add_security(request):
    # TODO: Check user
    user = User.objects.get(id=request.user.id)
    universe_id = request.POST['universe_id']
    security_id = request.POST['security_id']
    source = Universe.objects.get(Q(id=universe_id),Q(owner__id=request.user.id))
    security = SecurityContainer.objects.get(id=security_id)
    if not source.members.filter(id=security_id).exists():
        source.members.add(security)
        source.save()
    return HttpResponse('{"result": true, "status_message": "Universe ' + source.name + 'updated", "universe_id": ' + str(source.id) + '}',"json")

def universe_base_edit(request):
    # TODO: Check user
    user = User.objects.get(id=request.user.id)
    
    if request.POST.has_key('universe_id'):
        universe_id = request.POST['universe_id']
        try:
            source = Universe.objects.get(Q(id=universe_id),Q(owner__id=request.user.id))
        except:
            # TODO: Return error message
            return redirect('universes.html')
    else:
        source = Universe()
        source.owner = user
         
    source.name = request.POST['name']
    source.short_name = request.POST['short_name']

    if request.POST.has_key('public'):
        source.public = True
    else:
        source.public = False
    source.save()
    # TODO: Return success message
    return redirect('/universe_details_edit.html?universe_id=' + str(source.id))

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
    return HttpResponse('{"result": true, "status_message": "Description changed", "member_id": ' + universe_id + '}',"json")

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
 
    for member in source.members.all():
        content = get_main_track(member, True, True)
        if content!=None:
            context['tracks']['track_' + str(member.id)] = content
        else:
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
        return HttpResponse('{"result": false, "status_message": "Could not remove member!"}',"json")
    # TODO: Return success message
    return HttpResponse('{"result": true, "status_message": "Member removed", "member_id": ' + member_id + '}',"json")