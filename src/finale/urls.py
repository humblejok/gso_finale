from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # DJango default views
    url(r'^accounts/', include('allauth.urls')),
    url(r'^admin/', include(admin.site.urls)),
    # Common views
    url(r'^check_execution.html', 'universe.views.check_execution', name='check_execution'),
    
    # Universes related views
    url(r'^universes.html$', 'universe.views.universes', name='universes'),
    url(r'^universe_duplicate.html$', 'universe.views.universe_duplicate', name='universe_duplicate.html'),
    url(r'^universe_delete.html$', 'universe.views.universe_delete', name='universe_delete'),
    url(r'^universe_edit_base.html', 'universe.views.universe_edit_base', name='universe_edit_base'),
    url(r'^universe_get.html', 'universe.views.universe_get', name='universe_get'),
    
    # Financials related views
    url(r'^financials_bloomberg_wizard.html', 'universe.views.bloomberg_wizard', name='bloomberg_wizard', kwargs={'entity':'financials'}),
    url(r'^financials_bloomberg_wizard_execute.html', 'universe.views.bloomberg_wizard_execute', name='bloomberg_wizard_execute', kwargs={'entity':'financials'}),

)
