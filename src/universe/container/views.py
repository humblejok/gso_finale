'''
Created on Oct 3, 2014

@author: sdejonckheere
'''
import json
import logging
import os

from universe.models import Attributes, TrackContainer, FieldLabel
from seq_common.utils import classes
from django.shortcuts import render, redirect, render_to_response
from django.contrib.auth.models import User
from utilities import setup_content
from django.template.context import Context
from django.template import loader
from django.db.models import Q
from finale.settings import STATICS_PATH

from django.http.response import HttpResponse
from finale.utils import complete_fields_information, dict_to_json_compliance
from django.forms.models import model_to_dict
from json import dumps
from bson import json_util
import itertools


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
    all_data[container_setup["type"]] = container_setup['information' if item_view_type=='details' else 'fields']
    getattr(setup_content, 'set_' + item + '_' + item_view_type)(all_data)
    if item_view_type=='details':
        context = Context({"information": container_setup['information'], "container" : container_setup["type"]})
    else:
        data_as_dict = container_setup["fields"]
        # TODO Clean the mess
        if isinstance(container_setup["fields"], list):
            data_as_dict = {}
            for field in container_setup["fields"]:
                if '.' not in field:
                    data_as_dict[field] = {'name': field}
        context = Context({"fields":container_setup['fields'], "complete_fields": complete_fields_information(effective_class,  data_as_dict), "container" : container_setup["type"]})
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
    tracks = TrackContainer.objects.filter(effective_container_id=container_id).order_by('source','type','quality','frequency','id')
    filtering = lambda d, k: d[k]['data']
    fields = list(itertools.chain(*[filtering(setup_content.get_container_type_details()[container_type]['data'], k) for k in setup_content.get_container_type_details()[container_type]['data'].keys()]))
    # TODO: Handle other langage and factorize with other views
    labels = dict_to_json_compliance({label.identifier: label.field_label for label in FieldLabel.objects.filter(identifier__in=fields, langage='en')})
    context = {'complete_fields': complete_fields_information(effective_class,  {field:{} for field in fields}), 'container': container, 'container_json': dumps(dict_to_json_compliance(model_to_dict(container), effective_class)), 'tracks': tracks, 'container_type': container_type, 'layout': setup_content.get_container_type_details()[container_type], 'labels': labels}
    return render(request,'rendition/container_type/details/view.html', context)

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
    context = {'title': widget_title, 'index':widget_index, 'data': getattr(container,container_field), 'fields': foreign_class.get_displayed_fields(rendition_witdh), 'labels': {label.identifier: label.field_label for label in FieldLabel.objects.filter(identifier__in=foreign_class.get_displayed_fields(rendition_witdh), langage='en')}}
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
