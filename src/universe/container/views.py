'''
Created on Oct 3, 2014

@author: sdejonckheere
'''
import json
import logging
import os

from universe.models import Attributes, TrackContainer, FieldLabel,\
    PortfolioContainer, MenuEntries, SecurityContainer, AccountContainer,\
    FinancialOperation
from seq_common.utils import classes
from django.shortcuts import render, redirect, render_to_response
from django.contrib.auth.models import User
from utilities import setup_content
from django.template.context import Context
from django.template import loader
from django.db.models import Q
from finale.settings import STATICS_PATH

from django.http.response import HttpResponse
from finale.utils import complete_fields_information, dict_to_json_compliance,\
    get_model_foreign_field_class
from django.forms.models import model_to_dict
from json import dumps
from bson import json_util
import itertools
from utilities.track_token import get_track
from utilities.compute.valuations import NativeValuationsComputer
from utilities.valuation_content import get_portfolio_valuations,\
    get_valuation_content_display, get_positions_portfolio, get_closest_value,\
    get_closest_date, get_account_history
import datetime
from utilities.computing import get_previous_date
from utilities.track_content import get_track_content, set_track_content


LOGGER = logging.getLogger(__name__)

def lists(request):
    # TODO: Check user
    container_type = request.GET['item']
    container_class = container_type + '_CLASS'
    # TODO: Handle error
    effective_class_name = Attributes.objects.get(identifier=container_class, active=True).name
    effective_class = classes.my_class_import(effective_class_name)
    results = effective_class.objects.all().order_by('name')
    context = {'containers': results, 'container_type': container_type, 'container_label': Attributes.objects.get(identifier=container_type).name}
    return render(request, 'statics/' + container_type + '_results_lists_en.html', context)

def setup_save(request):
    # TODO: Check user
    user = User.objects.get(id=request.user.id)
    
    container_setup = request.POST['container_setup']
    container_setup = json.loads(container_setup)
    
    item = request.POST['item']
    item_view_type = request.POST['type']
    item_render_name = request.POST['render_name']
    
    container_class = container_setup["type"] + '_CLASS'
    # TODO: Handle error
    effective_class_name = Attributes.objects.get(identifier=container_class, active=True).name
    effective_class = classes.my_class_import(effective_class_name)
    
    all_data = getattr(setup_content, 'get_' + item + '_' + item_view_type)()
    all_data[container_setup["type"]] = container_setup['data']
    getattr(setup_content, 'set_' + item + '_' + item_view_type)(all_data)
    if item_view_type=='fields':
        data_as_dict = container_setup["data"]
        # TODO Clean the mess
        if isinstance(container_setup["data"], list):
            data_as_dict = {}
            for field in container_setup["data"]:
                if '.' not in field:
                    data_as_dict[field] = {'name': field}
        context = Context({"fields":container_setup['fields'], "complete_fields": complete_fields_information(effective_class,  data_as_dict), "container" : container_setup["type"]})
        template = loader.get_template('rendition/' + item + '/' + item_view_type + '/' + item_render_name + '.html')
        rendition = template.render(context)
        # TODO Implement multi-langage
        outfile = os.path.join(STATICS_PATH, container_setup["type"] + '_' + item_render_name + '_' + item_view_type + '_en.html')
        with open(outfile,'w') as o:
            o.write(rendition.encode('utf-8'))
    elif item_view_type=='menus':
        headers = Attributes.objects.filter(active=True, type='container_menu_target').order_by('name')
        print headers
        entries = {}
        for entry in container_setup['data']:
            if entry['entry_id']!=None:
                if not entries.has_key(entry['menu_target']):
                    entries[entry['menu_target']] = []
                entries[entry['menu_target']].append(MenuEntries.objects.get(id=entry['entry_id']))
        context = Context({'entries': entries, 'headers': headers})
        template = loader.get_template('rendition/' + item + '/' + item_view_type + '/' + item_render_name + '.html')
        rendition = template.render(context)
        # TODO Implement multi-langage
        outfile = os.path.join(STATICS_PATH, container_setup["type"] + '_' + item_render_name + '_' + item_view_type + '_en.html')
        with open(outfile,'w') as o:
            o.write(rendition.encode('utf-8'))
    elif item_view_type!='details':
        data_as_dict = container_setup["data"]
        # TODO Clean the mess
        if isinstance(container_setup["data"], list):
            data_as_dict = {}
            for field in container_setup["data"]:
                if '.' not in field:
                    data_as_dict[field] = {'name': field}
        context = Context({"fields":container_setup['data'], "complete_fields": complete_fields_information(effective_class,  data_as_dict), "container" : container_setup["type"]})
        template = loader.get_template('rendition/' + item + '/' + item_view_type + '/' + item_render_name + '.html')
        rendition = template.render(context)
        # TODO Implement multi-langage
        outfile = os.path.join(STATICS_PATH, container_setup["type"] + '_' + item_render_name + '_' + item_view_type + '_en.html')
        with open(outfile,'w') as o:
            o.write(rendition.encode('utf-8'))
    return HttpResponse('{"result": true, "status_message": "Saved"}',"json")


def definition_save(request):
    # TODO: Check user
    user = User.objects.get(id=request.user.id)
    container = request.POST['container']
    definitions = request.POST['definitions']
    definitions = json.loads(definitions)
    all_data = setup_content.get_container_type_fields()
    all_data[container] = definitions
    setup_content.set_container_type_fields(all_data)
    return HttpResponse('{"result": true, "status_message": "Saved"}',"json")

def base_edit(request):
    # TODO: Check user
    container_type = request.POST['container_type']
    container_class = container_type + '_CLASS'
    # TODO: Handle error
    effective_class_name = Attributes.objects.get(identifier=container_class, active=True).name
    effective_class = classes.my_class_import(effective_class_name)

    active_status = Attributes.objects.get(identifier='STATUS_ACTIVE')
    container_attribute = Attributes.objects.get(identifier=container_type)
    if request.POST.has_key('container_id'):
        portfolio_id = request.POST['container_id']
        try:
            source = effective_class.objects.get(Q(id=portfolio_id))
        except:
            # TODO: Return error message
            return redirect('/containers.html?item=' + container_type)
    else:
        source = effective_class()
    # Initial setup
    # TODO: Check if name already exists for that container type
    source.type = container_attribute
    source.name = request.POST['name']
    source.short_name = request.POST['short_name']
    source.status = active_status
    source.save()
    # Working on creations mandatory fields
    creation_data = setup_content.get_container_type_creations()
    if creation_data.has_key(container_type):
        creation_data = creation_data[container_type]
    else:
        creation_data = {}
    creation_data = complete_fields_information(effective_class,  creation_data)
    for field in creation_data.keys():
        if creation_data[field]['type'] in ['ForeignKey', 'ManyToManyField']:
            if creation_data[field]['type']=='ForeignKey':
                # TODO: Implement not attribute
                setattr(source, field, Attributes.objects.get(identifier=request.POST[field], active=True))
                source.save()
            else:
                target_class = classes.my_class_import(creation_data[field]['target_class'])
                new_instance = target_class.retrieve_or_create(source, 'FinaLE', request.POST[field + '-' + creation_data[field]['filter']], request.POST[field])
                setattr(source, field,[new_instance])
                source.save()
        else:
            setattr(source, field, request.POST[field])
    return redirect('/containers.html?item=' + container_type)

def delete(request):
    # TODO: Check user
    user = User.objects.get(id=request.user.id)
    container_id = request.GET['container_id']
    container_type = request.GET['container_type']
    container_class = container_type + '_CLASS'
    # TODO: Handle error
    effective_class_name = Attributes.objects.get(identifier=container_class, active=True).name
    effective_class = classes.my_class_import(effective_class_name)
    
    effective_class.objects.get(id=container_id).delete()
    return HttpResponse('{"result": true, "status_message": "Deleted"}',"json")

def external_import(request):
    # TODO: Check user
    user = User.objects.get(id=request.user.id)
    external_provider = request.GET['external']
    data_type = request.GET['target']
    container_id = request.GET['container_id']
    container_type = request.GET['container_type']
    container_class = container_type + '_CLASS'
    # TODO: Handle error
    effective_class_name = Attributes.objects.get(identifier=container_class, active=True).name
    effective_class = classes.my_class_import(effective_class_name)
    container = effective_class.objects.get(id=container_id)
    
    external = classes.my_import('providers.' + external_provider)
    getattr(external, 'import_' + data_type)(container)
    return HttpResponse('{"result": true, "status_message": "Executed"}',"json")

def get(request):
    # TODO: Check user
    user = User.objects.get(id=request.user.id)
    container_id = request.GET['container_id']
    container_type = request.GET['container_type']
    container_class = container_type + '_CLASS'
    # TODO: Handle error
    effective_class_name = Attributes.objects.get(identifier=container_class, active=True).name
    effective_class = classes.my_class_import(effective_class_name)
    
    container = effective_class.objects.get(id=container_id)
    filtering = lambda d, k: d[k]['data']
    fields = list(itertools.chain(*[filtering(setup_content.get_container_type_details()[container_type]['data'], k) for k in setup_content.get_container_type_details()[container_type]['data'].keys()]))
    # TODO: Handle other langage and factorize with other views
    labels = dict_to_json_compliance({label.identifier: label.field_label for label in FieldLabel.objects.filter(identifier__in=fields, langage='en')})
    context = {'complete_fields': complete_fields_information(effective_class,  {field:{} for field in fields}), 'container': container, 'container_json': dumps(dict_to_json_compliance(model_to_dict(container), effective_class)), 'container_type': container_type, 'layout': setup_content.get_container_type_details()[container_type], 'labels': labels}
    return render(request,'rendition/container_type/details/view.html', context)

def render_history_chart(request):
    # TODO: Check user
    user = User.objects.get(id=request.user.id)
    container_id = request.POST['container_id'][0] if isinstance(request.POST['container_id'], list) else request.POST['container_id']
    container_type = request.POST['container_type'][0] if isinstance(request.POST['container_type'], list) else request.POST['container_type']
    container_class = container_type + '_CLASS'
    widget_index = request.POST['widget_index'][0] if isinstance(request.POST['widget_index'], list) else request.POST['widget_index']
    widget_title = request.POST['widget_title'][0] if isinstance(request.POST['widget_title'], list) else request.POST['widget_title']
    track_info = request.POST['track_info'][0] if isinstance(request.POST['track_info'], list) else request.POST['track_info']
    track_info = json.loads(track_info)
    # TODO: Handle error
    effective_class_name = Attributes.objects.get(identifier=container_class, active=True).name
    effective_class = classes.my_class_import(effective_class_name)
    container = effective_class.objects.get(id=container_id)
    track = get_track(container, track_info)    
    context = {'title': widget_title, 'index':widget_index, 'container': container, 'track_id': track.id if track!=None else None}
    return render(request, 'container/view/history_chart.html', context)

def render_singles_list(request):
    # TODO: Check user
    user = User.objects.get(id=request.user.id)
    container_id = request.POST['container_id'][0] if isinstance(request.POST['container_id'], list) else request.POST['container_id']
    container_type = request.POST['container_type'][0] if isinstance(request.POST['container_type'], list) else request.POST['container_type']
    container_class = container_type + '_CLASS'
    container_fields = eval(request.POST['container_fields'])
    widget_index = request.POST['widget_index'][0] if isinstance(request.POST['widget_index'], list) else request.POST['widget_index']
    widget_title = request.POST['widget_title'][0] if isinstance(request.POST['widget_title'], list) else request.POST['widget_title']
    # TODO: Handle error
    effective_class_name = Attributes.objects.get(identifier=container_class, active=True).name
    effective_class = classes.my_class_import(effective_class_name)

    container = effective_class.objects.get(id=container_id)
    context = {'title': widget_title, 'index':widget_index, 'container': container, 'fields': container_fields, 'labels': {label.identifier: label.field_label for label in FieldLabel.objects.filter(identifier__in=container_fields, langage='en')}}
    return render(request, 'container/view/simple_fields_list.html', context)

def render_many_to_many(request):
    # TODO: Check user
    user = User.objects.get(id=request.user.id)
    container_id = request.POST['container_id'][0] if isinstance(request.POST['container_id'], list) else request.POST['container_id']
    container_type = request.POST['container_type'][0] if isinstance(request.POST['container_type'], list) else request.POST['container_type']
    container_class = container_type + '_CLASS'
    container_field = request.POST['container_field'][0] if isinstance(request.POST['container_field'], list) else request.POST['container_field']
    rendition_witdh = request.POST['rendition_width'][0] if isinstance(request.POST['rendition_width'], list) else request.POST['rendition_width']
    widget_index = request.POST['widget_index'][0] if isinstance(request.POST['widget_index'], list) else request.POST['widget_index']
    widget_title = request.POST['widget_title'][0] if isinstance(request.POST['widget_title'], list) else request.POST['widget_title']
    # TODO: Handle error
    effective_class_name = Attributes.objects.get(identifier=container_class, active=True).name
    effective_class = classes.my_class_import(effective_class_name)

    foreign_class = effective_class._meta.get_field(container_field).rel.to

    container = effective_class.objects.get(id=container_id)
    context = {'title': widget_title,
               'container_id': container_id, 'container_type': container_type, 'container_field': container_field,
               'index':widget_index,
               'data': getattr(container,container_field),
               'fields': foreign_class.get_displayed_fields(rendition_witdh),
               'labels': {label.identifier: label.field_label for label in FieldLabel.objects.filter(identifier__in=foreign_class.get_displayed_fields(rendition_witdh), langage='en')}}
    return render(request, 'container/view/many_to_many_field.html', context)

def filters(request):
    user = User.objects.get(id=request.user.id)
    if request.GET.has_key('container_type'):
        container_type = request.GET['container_type']
        container_class = container_type + '_CLASS'
        effective_class_name = Attributes.objects.get(identifier=container_class, active=True).name
    else:
        effective_class_name = request.GET['container_class']
    effective_class = classes.my_class_import(effective_class_name)
    if getattr(effective_class,'get_querying_class', None)!=None:
        effective_class = effective_class.get_querying_class()
    searching = request.GET['term']
    query_filter = None
    for field in effective_class.get_querying_fields():
        query_dict = {}
        field = field.replace('.','__') + '__icontains'
        query_dict[field] = searching
        if query_filter==None:
            query_filter = Q(**query_dict)
        else:
            query_filter = query_filter | Q(**query_dict)
    results = effective_class.objects.filter(query_filter).distinct()
    results = dumps([dict_to_json_compliance(model_to_dict(item)) for item in results], default=json_util.default)
    return HttpResponse('{"result": ' + results + ', "status_message": "Deleted"}',"json")

def valuations_compute(request):
    # TODO: Check user
    user = User.objects.get(id=request.user.id)
    container_id = request.GET['container_id']
    container_type = request.GET['container_type']
    container_class = container_type + '_CLASS'
    # TODO: Handle error
    effective_class_name = Attributes.objects.get(identifier=container_class, active=True).name
    effective_class = classes.my_class_import(effective_class_name)
    
    container = effective_class.objects.get(id=container_id)
    computer = NativeValuationsComputer()
    #computer.compute_daily_valuation(container)
    computer.compute_valuation(container, Attributes.objects.get(identifier='FREQ_DAILY', active=True))
    return HttpResponse('{"result": true, "status_message": "Computed"}',"json")


def partial_delete(request):
    # TODO: Check user
    user = User.objects.get(id=request.user.id)
    container_id = request.POST['container_id']
    container_type = request.POST['container_type']
    container_class = container_type + '_CLASS'
    container_field = request.POST['container_field']
    item_id = request.POST['item_id']
    # TODO: Handle error
    effective_class_name = Attributes.objects.get(identifier=container_class, active=True).name
    effective_class = classes.my_class_import(effective_class_name)
    container = effective_class.objects.get(id=container_id)
    foreign = get_model_foreign_field_class(effective_class, container_field)
    if foreign!=None:
        entry = foreign.objects.get(id=item_id)
        getattr(container, container_field).remove(entry)
        container.save()
        entry.delete()
    return HttpResponse('{"result": "Finished", "status_message": "Saved"}',"json")

def add_price(request):
    # TODO: Check user
    user = User.objects.get(id=request.user.id)
    container_id = request.POST['container_id']
    container_type = request.POST['container_type']
    container_class = container_type + '_CLASS'
    
    price_date = datetime.datetime.strptime(request.POST['price_date'], '%Y-%m-%d')
    price_value = float(request.POST['price_value'])
    # TODO: Handle error
    effective_class_name = Attributes.objects.get(identifier=container_class, active=True).name
    effective_class = classes.my_class_import(effective_class_name)
    container = effective_class.objects.get(id=container_id)
    track = get_track(container, {'track_default': True, 'track_type': 'NUM_TYPE_NAV'})
    if track==None:
        return HttpResponse('{"result": "No valid track", "status_message": "Not saved"}',"json")
    all_tokens = get_track_content(track)
    if all_tokens==None:
        all_tokens = []
    found = False
    for token in all_tokens:
        if token['date']==price_date:
            found = True
            token['value'] = price_value
    if not found:
        all_tokens.append({'date': price_date, 'value': price_value})

    set_track_content(track, all_tokens, True)
    
    return HttpResponse('{"result": "Token added", "status_message": "Saved"}',"json")

def partial_save(request):
    # TODO: Check user
    user = User.objects.get(id=request.user.id)
    container_id = request.POST['container_id']
    container_data = request.POST['container_data']
    container_data = json.loads(container_data)
    container_type = request.POST['container_type']
    container_class = container_type + '_CLASS'
    # TODO: Handle error
    effective_class_name = Attributes.objects.get(identifier=container_class, active=True).name
    effective_class = classes.my_class_import(effective_class_name)
    container = effective_class.objects.get(id=container_id)
    if container_data.has_key('many-to-many'):
        foreign = get_model_foreign_field_class(effective_class, container_data['many-to-many'])
        if foreign!=None:
            entry = foreign.retrieve_or_create('web', None, None, container_data)
            getattr(container, container_data['many-to-many']).add(entry)
            container.save()
    else:
        for field_key in container_data.keys():
            #TODO Handle relation
            field_info = Attributes()
            field_info.short_name = field_key.split('.')[0]
            field_info.name = field_key.split('.')[0]
            container.set_attribute('web', field_info, container_data[field_key])
    container.save()
    return HttpResponse('{"result": "Finished", "status_message": "Saved"}',"json")

def search(request):
    context = {}
    try:
        searching = request.POST[u'searching']
        
        if not isinstance(searching, basestring):
            searching = searching[0]
        action = request.POST['action']
        print action
        # TODO: Check user
        user = User.objects.get(id=request.user.id)
        container_id = request.GET['container_id']
        container_type = request.GET['container_type']
        container_class = container_type + '_CLASS'
        # TODO: Handle error
        effective_class_name = Attributes.objects.get(identifier=container_class, active=True).name
        effective_class = classes.my_class_import(effective_class_name)
        results = effective_class.objects.filter(Q(name__icontains=searching) | Q(short_name__icontains=searching) | Q(aliases__alias_value__icontains=searching)).order_by('name').distinct()
        results_list = [result.get_short_json() for result in results]
        context['securities'] = results_list
        context['action'] = action
    except:
        context['message'] = 'Error while querying for:' + searching
    return render(request, 'rendition/securities_list.html', context)

def positions(request):
    # TODO: Check user
    user = User.objects.get(id=request.user.id)
    container_id = request.GET['container_id']
    
    container_type = request.GET['container_type']
    container_class = container_type + '_CLASS'
    
    working_date = request.GET['working_date']
    
    # TODO: Handle error
    effective_class_name = Attributes.objects.get(identifier=container_class, active=True).name
    effective_class = classes.my_class_import(effective_class_name)
    
    container = effective_class.objects.get(id=container_id)
    filtering = lambda d, k: d[k]['data']
    fields = list(itertools.chain(*[filtering(setup_content.get_container_type_details()[container_type]['data'], k) for k in setup_content.get_container_type_details()[container_type]['data'].keys()]))
    # TODO: Handle other langage and factorize with other views
    labels = dict_to_json_compliance({label.identifier: label.field_label for label in FieldLabel.objects.filter(identifier__in=fields, langage='en')})
    positions = get_valuation_content_display(get_positions_portfolio(container)['data'])
    positions_date = sorted(positions.keys(), reverse=True)
    currencies = list(set([account.currency.short_name for account in container.accounts.all()]))
    working_date = get_closest_date(positions, datetime.datetime.strptime(working_date, '%Y-%m-%d'), False)
    context = {'currencies': currencies, 'positions': positions, 'positions_date': positions_date , 'working_date': working_date, 'complete_fields': complete_fields_information(effective_class,  {field:{} for field in fields}), 'container': container, 'container_json': dumps(dict_to_json_compliance(model_to_dict(container), effective_class)), 'container_type': container_type, 'labels': labels}
    return render(request,'rendition/container_type/details/positions.html', context)

def accounts(request, view_extension):
    user = User.objects.get(id=request.user.id)
    container_id = request.GET['container_id']
    account_id = request.GET['accounts_id']
    container_type = request.GET['container_type']
    if request.GET.has_key('working_date'):
        working_date = datetime.datetime.strptime(request.GET['working_date'],'%Y-%m-%d')
    else:
        working_date = None
    container_class = container_type + '_CLASS'
    # TODO: Handle error
    effective_class_name = Attributes.objects.get(identifier=container_class, active=True).name
    effective_class = classes.my_class_import(effective_class_name)
    
    container = effective_class.objects.get(id=container_id)
    account = AccountContainer.objects.get(id=account_id)
    account_history = get_account_history(account)
    if account_history!=None:
        account_history = account_history['data']
        account_history = get_valuation_content_display(account_history, start_date=None, end_date=working_date)
    accounts_dates = sorted(account_history.keys(), reverse=True)
    operations = FinancialOperation.objects.filter(Q(source__id=account_id) | Q(target__id=account_id))
    sorted_operations = {}
    for operation in operations:
        key = operation.value_date.strftime('%Y-%m-%d')
        if not sorted_operations.has_key(key):
            sorted_operations[key] = []
        if operation.operation_type.identifier in ['OPE_TYPE_SPOT_BUY','OPE_TYPE_SPOT_SELL']:
            if operation.target.id==account.id:
                operation.amount = operation.amount * operation.spot
            else:
                operation.amount = operation.amount * -1.0
        sorted_operations[key].append(operation)
    context = {'container': container, 'container_json': dumps(dict_to_json_compliance(model_to_dict(container), effective_class)),
               'account' : account, 'history': account_history,
               'operations': sorted_operations,
               'dates': accounts_dates, 'date': working_date}
    return render(request,'rendition/container_type/details/accounts.' + view_extension, context)

def valuation(request, view_extension):
    # TODO: Check user
    user = User.objects.get(id=request.user.id)
    working_date = request.GET['working_date']
    container_id = request.GET['container_id']
    container_type = request.GET['container_type']
    container_class = container_type + '_CLASS'
    # TODO: Handle error
    effective_class_name = Attributes.objects.get(identifier=container_class, active=True).name
    effective_class = classes.my_class_import(effective_class_name)
    
    container = effective_class.objects.get(id=container_id)
    
    previous_date = get_previous_date(datetime.datetime.strptime(working_date,'%Y-%m-%d'), container.frequency)
    # TODO Optimize, do not convert all the items
    valuations = get_portfolio_valuations(container)
    if valuations!=None:
        valuations = get_valuation_content_display(valuations['data'])
        valuation = get_closest_value(valuations, working_date, False)
    else:
        valuation = None
    positions = get_positions_portfolio(container)
    if positions!=None:
        positions = get_valuation_content_display(positions['data'])
        current_positions = get_closest_value(positions, working_date, False)
        previous_positions = get_closest_value(positions, previous_date, False)
    securities = SecurityContainer.objects.filter(id__in=current_positions.keys())
    securities = {str(security.id): dict_to_json_compliance(model_to_dict(security), SecurityContainer) for security in securities}
    
    context = {'container': container, 'container_json': dumps(dict_to_json_compliance(model_to_dict(container), effective_class)),
               'securities': dumps(securities),
               'valuation': dumps(valuation),
               'previous_positions': dumps(previous_positions),
               'positions': dumps(current_positions),
               'date': working_date,
               'aggregates': ['currency.short_name']}
    return render(request,'rendition/container_type/details/valuation.' + view_extension, context)

def valuations(request, view_extension):
    # TODO: Check user
    user = User.objects.get(id=request.user.id)
    container_id = request.GET['container_id']
    container_type = request.GET['container_type']
    container_class = container_type + '_CLASS'
    # TODO: Handle error
    effective_class_name = Attributes.objects.get(identifier=container_class, active=True).name
    effective_class = classes.my_class_import(effective_class_name)
    
    container = effective_class.objects.get(id=container_id)
    # TODO: Handle other langage and factorize with other views
    valuations = get_valuation_content_display(get_portfolio_valuations(container)['data'])
    valuations_date = sorted(valuations.keys(), reverse=True)
    currencies = list(set([account.currency.short_name for account in container.accounts.all()]))
    context = {'currencies': currencies, 'valuations': valuations, 'valuations_date': valuations_date, 'container': container, 'container_json': dumps(dict_to_json_compliance(model_to_dict(container), effective_class)), 'container_type': container_type}
    return render(request,'rendition/container_type/details/valuations.' + view_extension, context)
