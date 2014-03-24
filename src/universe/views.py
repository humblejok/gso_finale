# Create your views here.
from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import render, redirect
from universe.models import Universe, ContainerNumericValue
import re
from providers.BloombergTasks import DEFAULT_GET_DATA_FIELDS
from providers import BloombergTasks


def financials_bloomberg_wizard(request):
    # TODO: Check user
    return render(request,'financials/bloomberg_wizard.html')

def execute_financials_bloomberg_wizard(request):
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
            
    fields = DEFAULT_GET_DATA_FIELDS
    response =  BloombergTasks.send_bloomberg_get_data(prepared_entries, ticker_type='TICKER')
    print response
    
    return render(request,'financials/bloomberg_wizard.html')

def universes(request):
    # TODO: Check user
    universes = Universe.objects.filter(Q(public=True)|Q(owner__id=request.user.id))
    context = {'universes': universes}
    return render(request, 'universes.html', context)

def duplicate_universe(request):
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

def delete_universe(request):
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

def edit_base_information_universe(request):
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

def get_universe(request):
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
