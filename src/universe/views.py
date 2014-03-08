# Create your views here.
from universe.models import Universe
from django.db.models import Q
from django.shortcuts import render


def universes(request):
    print request.user
    print request.user.id
    universes = Universe.objects.filter(Q(public=True)|Q(owner__id=request.user.id))
    context = {'universes': universes}
    return render(request, 'universes.html', context)