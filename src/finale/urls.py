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
    url(r'^file_upload.html', 'universe.views.file_upload', name='file_upload'),
    url(r'^get_attributes.html', 'universe.views.get_attributes', name='get_attributes'),
    url(r'^check_execution.html', 'universe.views.check_execution', name='check_execution'),
    url(r'^get_execution.html', 'universe.views.get_execution', name='get_execution'),
    
    url(r'^call_external.html', 'universe.views.call_external', name='call_external'),
    
    url(r'^object_base_edit.html', 'universe.views.object_base_edit', name='object_base_edit'),
    url(r'^object_delete.html', 'universe.views.object_delete', name='object_delete'),
    url(r'^object_fields_get.html', 'universe.views.object_fields_get', name='object_fields_get'),
    url(r'^object_custom_fields_get.html', 'universe.views.object_custom_fields_get', name='object_custom_fields_get'),    
    
    url(r'^object_save.html', 'universe.views.object_save', name='object_save'),
    
    url(r'^get_filtering_entry.html', 'universe.views.get_filtering_entry', name='get_filtering_entry'),
    # Rendition views
    url(r'^render_operation_types.html', 'universe.container.views.render_operation_types', name='render_operation_types'),
    

    # Setup views
    url(r'^setup.html', 'universe.views.setup', name='setup'),
    url(r'^menu_setup_render.html', 'universe.views.menu_setup_render', name='menu_setup_render'),
    # Custom view
    url(r'^custom_edit.html', 'universe.views.custom_edit', name='custom_edit'),
    url(r'^custom_view.html', 'universe.views.custom_view', name='custom_view'),
    url(r'^custom_export.html', 'universe.views.custom_export', name='custom_export'),
    url(r'^custom_save.html', 'universe.views.custom_save', name='custom_save'),

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
    url(r'^universe_mass_mail.html$', 'universe.views.universe_mass_mail', name='universe_mass_mail'),
    url(r'^universe_mass_mail_execute.html$', 'universe.views.universe_mass_mail_execute', name='universe_mass_mail_execute'),
    
    url(r'^backtest_wizard_execute.html$', 'universe.views.backtest_wizard_execute', name='backtest_wizard_execute'),

    # Financials related views
    url(r'^bloomberg_update.html', 'universe.views.bloomberg_update', name='bloomberg_update'),
    url(r'^financials_bloomberg_wizard.html', 'universe.views.bloomberg_wizard', name='bloomberg_wizard', kwargs={'entity':'financials'}),
    url(r'^financials_bloomberg_wizard_execute.html', 'universe.views.bloomberg_wizard_execute', name='bloomberg_wizard_execute', kwargs={'entity':'financials'}),

    # Containers views
    url(r'^container_accounts.html', 'universe.container.views.accounts', name='accounts', kwargs={'view_extension':'html'}),
    url(r'^containers.html', 'universe.container.views.lists', name='containers'),
    url(r'^container_definition_save.html','universe.container.views.definition_save', name='container_definition_save'),
    url(r'^container_delete.html', 'universe.container.views.delete', name='container_delete'),
    url(r'^container_get.html', 'universe.container.views.get', name='container_get'),
    url(r'^container_setup_save.html', 'universe.container.views.setup_save', name='container_setup_save'),
    url(r'^container_search.html', 'universe.container.views.search', name='container_search'),
    url(r'^container_base_edit.html', 'universe.container.views.base_edit', name='container_base_edit'),
    url(r'^container_filter.html', 'universe.container.views.filters', name='container_filter'),
    url(r'^container_render_many_to_many.html', 'universe.container.views.render_many_to_many', name='container_render_many_to_many'),
    url(r'^container_render_singles_list.html', 'universe.container.views.render_singles_list', name='container_render_singles_list'),
    url(r'^container_render_history_chart.html', 'universe.container.views.render_history_chart', name='container_render_history_chart'),
    url(r'^container_render_custom_standard.html', 'universe.container.views.render_custom_standard', name='container_render_custom_standard'),
    url(r'^container_render_custom_template.html', 'universe.container.views.render_custom_template', name='container_render_custom_template'),
    
    url(r'^container_external_import.html', 'universe.container.views.external_import', name='external_import'),
    url(r'^container_valuations_compute.html', 'universe.container.views.valuations_compute', name='valuations_compute'),
    url(r'^container_valuation.html', 'universe.container.views.valuation', name='valuation', kwargs={'view_extension':'html'}),
    url(r'^container_operation.html', 'universe.container.views.operation', name='operation', kwargs={'view_extension':'html'}),
    url(r'^container_operation_update.html', 'universe.container.views.operation_update', name='operation_update'),
    url(r'^container_valuations.html', 'universe.container.views.valuations', name='valuations', kwargs={'view_extension':'html'}),
    url(r'^container_valuations.csv', 'universe.container.views.valuations', name='valuations', kwargs={'view_extension':'csv'}),
    url(r'^container_positions.html', 'universe.container.views.positions', name='positions'),
    url(r'^container_partial_save.html', 'universe.container.views.partial_save', name='partial_save'),
    url(r'^container_partial_delete.html', 'universe.container.views.partial_delete', name='partial_delete'),
    url(r'^container_add_price.html', 'universe.container.views.add_price', name='add_price'),
    url(r'^container_security_operation.html', 'universe.container.views.security_operation', name='security_operation'),
    url(r'^container_cash_operation.html', 'universe.container.views.cash_operation', name='cash_operation'),
    url(r'^container_security_operation_create.html', 'universe.container.views.security_operation_create', name='container_security_operation_create'),
    url(r'^container_cash_operation_create.html', 'universe.container.views.cash_operation_create', name='container_cash_operation_create'),
    url(r'^container_accounts_compute.html', 'universe.container.views.compute_accounts_statuses', name='container_compute_accounts_statuses'),
    url(r'^container_render_account_selection.html', 'universe.container.views.render_account_selection', name='container_render_account_selection'),
    url(r'^container_operation_remove.html', 'universe.container.views.operation_remove', name='container_operation_remove'),
    url(r'^container_campaign_import.html', 'universe.crm.views.campaign_import', name='container_campaign_import'),
    url(r'^container_mails_import.html', 'universe.crm.views.mails_import', name='container_campaign_import'),
    
    # CRM views
    url(r'^crm_get_campaigns.html', 'universe.crm.views.get_campaigns', name='crm_campaigns'),
    # url(r'^crm_get_campaign_details.html', 'universe.crm.views.get_campaign_details', name='crm_get_campaign_details'),
    
    
    url(r'^track_end_date.html', 'universe.views.track_end_date', name='track_end_date'),
    
    # Tracks related views
    url(r'^track_get.html', 'universe.views.track_get', name='track_get'),
    
    url(r'^external_import.html', 'universe.views.external_import', name='external_import'),
    
    

)
