# Create your views here.
from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import render, redirect
from universe.models import Universe, ContainerNumericValue
from django.core.cache import cache
from finale.threaded import bloomberg_data_query
from django.http.response import HttpResponse

import re
import threading
import uuid

def bloomberg_wizard(request, entity):
    # TODO: Check user
    return render(request, entity + '/bloomberg/wizard.html')

def bloomberg_wizard_execute(request, entity):
    # TODO: Check user
    # TODO: Check Bloomberg method
    entries = [str(entry).strip() for entry in request.POST['bloombergList'].split('\r')]
    isin = re.compile("^[A-Z]{2}[0-9]{10}$")
    prepared_entries = []
    for entry in entries:
        if isin.match(entry):
            prepared_entries.append(entry + '|ISIN|')
        else:
            prepared_entries.append(entry)
    response_key = uuid.uuid4().get_hex()
    # TODO: Implement CONSTANTS and dynamic choice
    if entity=='financials':
        bb_thread = threading.Thread(None, bloomberg_data_query, response_key, (response_key, prepared_entries))
    bb_thread.start()
    context = {'response_key': response_key}
    return render(request,entity + '/bloomberg/wizard_waiting.html', context)

def check_execution(request):
    response_key = request.POST['response_key']
    if cache.get(response_key)==1.0:
        return HttpResponse('{"result": true, "status": 1.0}',"json")
    else:
        return HttpResponse('{"result": false, "status":' + str(cache.get(response_key)) + '}',"json")

def universes(request):
    # TODO: Check user
    universes = Universe.objects.filter(Q(public=True)|Q(owner__id=request.user.id))
    context = {'universes': universes}
    return render(request, 'universes.html', context)

def universe_duplicate(request):
    source_id = request.GET['universe_id']
    # TODO: Check user
    user = User.objects.get(id=request.user.id)
    try:
        source = Universe.objects.get(Q(id=source_id),Q(public=True)|Q(owner__id=request.user.id))
    except:
        # TODO: Return error message
        return redirect('universes')
    destination = source.clone(Universe)
    destination.name = destination.name + ' (copy)'
    destination.owner = user
    destination.save()
    for member in source.members.all():
        destination.members.add(member)
    destination.save()
    # TODO: Return success message
    return redirect('universes')

def universe_delete(request):
    source_id = request.GET['universe_id']
    # TODO: Check user
    user = User.objects.get(id=request.user.id)
    try:
        source = Universe.objects.get(Q(id=source_id),Q(public=True)|Q(owner__id=request.user.id))
    except:
        # TODO: Return error message
        return redirect('universes')
    source.delete()
    # TODO: Return success message
    return redirect('universes')

def universe_edit_base(request):
    source_id = request.POST['universe_id']
    # TODO: Check user
    user = User.objects.get(id=request.user.id)
    try:
        source = Universe.objects.get(Q(id=source_id),Q(owner__id=request.user.id))
    except:
        # TODO: Return error message
        return redirect('universes')
    source.name = request.POST['name']
    source.short_name = request.POST['short_name']
    if request.POST.has_key('public'):
        source.public = True
    else:
        source.public = False
    source.save()
    # TODO: Return success message
    return redirect('/get_universe?universe_id=' + str(source_id))

def universe_get(request):
    if request.POST.has_key('universe_id'):
        source_id = request.POST['universe_id']
    else:
        source_id = request.GET['universe_id']
    # TODO: Check user
    user = User.objects.get(id=request.user.id)
    try:
        source = Universe.objects.get(Q(id=source_id),Q(public=True)|Q(owner__id=request.user.id))
    except:
        # TODO: Return error message
        return redirect('universes')
    context = {'universe': source, 'tracks': {}}
    for member in source.members.all():
        provider = member.associated_companies.filter(role__identifier='SCR_DP')
        if provider.exists():
            provider = provider[0]
            # TODO: Implement Intraday
            context['tracks']['track_' + str(member.id)] = ContainerNumericValue.objects.filter(effective_container_id=member.id, source_id=provider.company.id, time__isnull=True).order_by('day', 'time')
            print member.name + " loading track:" + str(len(context['tracks']['track_' + str(member.id)]))
    return render(request, 'universe_details.html', context)
