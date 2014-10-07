'''
Created on Oct 3, 2014

@author: sdejonckheere
'''
import json
import logging
import os

from universe.models import Attributes, TrackContainer
from seq_common.utils import classes
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from utilities import setup_content
from django.template.context import Context
from django.template import loader
from django.db.models import Q
from finale.settings import STATICS_PATH

from django.http.response import HttpResponse
from finale.utils import complete_fields_information


LOGGER = logging.getLogger(__name__)

def list(request):
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
    all_data[container_setup["type"]] = container_setup["fields"]
    getattr(setup_content, 'set_' + item + '_' + item_view_type)(all_data)
    context = Context({"fields":complete_fields_information(effective_class,  container_setup["fields"]), "container" : container_setup["type"]})
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
    
    source.type = container_attribute
    source.name = request.POST['name']
    source.short_name = request.POST['short_name']
    source.status = active_status
    source.save()
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
    context = {'container': container, 'tracks': tracks}
    return render(request,'container/' + container.type.identifier + '.html', context)


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
