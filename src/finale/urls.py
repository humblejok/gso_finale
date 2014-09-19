from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # DJango default views
    url(r'^accounts/', include('allauth.urls')),
    url(r'^admin/', include(admin.site.urls)),
    
    # Main page
    url(r'^index.html$', 'universe.views.universes', name='index'),
    
    # Common views
    url(r'^check_execution.html', 'universe.views.check_execution', name='check_execution'),
    url(r'^get_execution.html', 'universe.views.get_execution', name='get_execution'),
    
    url(r'^call_external.html', 'universe.views.call_external', name='call_external'),
    
    url(r'^container_delete.html', 'universe.views.container_delete', name='container_delete'),
    
    url(r'^object_base_edit.html', 'universe.views.object_base_edit', name='object_base_edit'),
    url(r'^object_save.html', 'universe.views.object_save', name='object_save'),
    
    # Setup views
    url(r'^setup.html', 'universe.views.setup', name='setup'),

    # Universes related views
    url(r'^universes.html$', 'universe.views.universes', name='universes'),
    url(r'^universe_backtest_wizard.html$', 'universe.views.universe_backtest_wizard', name='universe_backtest_wizard.html'),
    url(r'^universe_change_members.html$', 'universe.views.universe_change_members', name='universe_change_members.html'),
    url(r'^universe_create.html$', 'universe.views.universe_create', name='universe_create.html'),
    url(r'^universe_delete.html$', 'universe.views.universe_delete', name='universe_delete'),
    url(r'^universe_base_edit.html', 'universe.views.universe_base_edit', name='universe_edit_base'),
    url(r'^universe_description_edit.html', 'universe.views.universe_description_edit', name='universe_edit_description'),
    url(r'^universe_duplicate.html$', 'universe.views.universe_duplicate', name='universe_duplicate'),
    url(r'^universe_details_edit.html', 'universe.views.universe_details_edit', name='universe_details_edit'),
    url(r'^universe_details.html', 'universe.views.universe_details', name='universe_details'),
    url(r'^universe_export.html', 'universe.views.universe_export', name='universe_export'),    
    url(r'^universe_member_delete.html$', 'universe.views.universe_member_delete', name='universe_member_delete'),
    url(r'^universe_report.html$', 'universe.views.universe_report', name='universe_report'),
    url(r'^universe_add_security.html$', 'universe.views.universe_add_security', name='universe_add_security'),
    
    url(r'^backtest_wizard_execute.html$', 'universe.views.backtest_wizard_execute', name='backtest_wizard_execute'),

    # Financials related views
    url(r'^bloomberg_update.html', 'universe.views.bloomberg_update', name='bloomberg_update'),
    url(r'^financials_bloomberg_wizard.html', 'universe.views.bloomberg_wizard', name='bloomberg_wizard', kwargs={'entity':'financials'}),
    url(r'^financials_bloomberg_wizard_execute.html', 'universe.views.bloomberg_wizard_execute', name='bloomberg_wizard_execute', kwargs={'entity':'financials'}),
    url(r'^financial_container_get.html', 'universe.views.financial_container_get', name='financial_container_get'),
    # Securities views
    url(r'^securities.html', 'universe.views.securities', name='securities'),
    url(r'^security_search.html', 'universe.views.security_search', name='security_search'),
    
    
    
    # Companies views
    url(r'^companies.html', 'universe.views.companies', name='companies'),
    url(r'^company_base_edit.html', 'universe.views.company_base_edit', name='company_base_edit'),
    
    # Portfolios views
    url(r'^portfolios.html', 'universe.views.portfolios', name='portfolios'),
    url(r'^portfolio_base_edit.html', 'universe.views.portfolio_base_edit', name='portfolio_base_edit'),

    # Tracks related views
    url(r'^track_get.html', 'universe.views.track_get', name='track_get'),
    
    url(r'^external_import.html', 'universe.views.external_import', name='external_import'),
    
    

)
