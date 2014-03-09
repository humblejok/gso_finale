from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    (r'^accounts/', include('allauth.urls')),
    url(r'^universes$', 'universe.views.universes', name='universes'),
    url(r'^duplicate_universe$', 'universe.views.duplicate_universe', name='duplicate_universe'),
    url(r'^delete_universe$', 'universe.views.delete_universe', name='delete_universe'),
    url(r'^edit_base_information_universe', 'universe.views.edit_base_information_universe', name='edit_base_information_universe'),
    url(r'^get_universe', 'universe.views.get_universe', name='get_universe'),
    
    # Examples:
    # url(r'^$', 'finale.views.home', name='home'),
    # url(r'^finale/', include('finale.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)
