'''
Created on Apr 16, 2015

@author: sdejonckheere
'''
import datetime

from django.contrib.auth.models import User
from django.db.models import Q
from django.http.response import HttpResponse
from django.shortcuts import render

from finale.utils import get_effective_instance
from providers import mailgun
from universe.models import MailCampaignContainer, Attributes, Container
from utilities.external_content import set_mailgun_data

def mails_import(request):
    campaign_id = request.GET['container_id']
    campaign = get_effective_instance(Container.objects.get(id=campaign_id))
    mailgun.treat_emails(None, campaign.name)

def campaign_import(request):
    campaign_id = request.GET['container_id']
    campaign = get_effective_instance(Container.objects.get(id=campaign_id))
    set_mailgun_data(campaign.external_id, mailgun.treat_events(campaign.external_id))
    
    return HttpResponse('{"result": true, "status_message": "Imported"}',"json")

def get_campaigns(request):
    # TODO Check user
    
    campaigns = mailgun.get_campaigns()
    campaigns = campaigns.json()
    
    user = User.objects.get(id=request.user.id)
    
    campaign_type = Attributes.objects.get(type='container_type', active=True, identifier='CONT_MAIL_CAMPAIGN')
    active_type = Attributes.objects.get(type='status', active=True, identifier='STATUS_ACTIVE')
    
    for campaign in campaigns['items']:
        working_campaign = MailCampaignContainer.objects.filter(external_id=campaign['id'])
        if working_campaign.exists():
            working_campaign = working_campaign[0]
        else:
            working_campaign = MailCampaignContainer()
            working_campaign.name = campaign['name']
            working_campaign.short_name = ''
            working_campaign.type = campaign_type
            working_campaign.inception_date = datetime.datetime.strptime(campaign['created_at'],'%a, %d %b %Y %H:%M:%S %Z')
            working_campaign.closed_date = None
            working_campaign.short_description = ''
            working_campaign.status = active_type
            working_campaign.owner = user
            working_campaign.description = ''
            working_campaign.external_id = campaign['id']
            working_campaign.imported = False
            working_campaign.clicked_count = 0
            working_campaign.opened_count = 0
            working_campaign.submitted_count = 0
            working_campaign.delivered_count = 0
            working_campaign.unsubscribed_count = 0
            working_campaign.bounced_count = 0
            working_campaign.complained_count = 0
            working_campaign.dropped_count = 0
            working_campaign.save()
    
        working_campaign.clicked_count = campaign['clicked_count']
        working_campaign.opened_count = campaign['opened_count']
        working_campaign.submitted_count = campaign['submitted_count']
        working_campaign.delivered_count = campaign['delivered_count']
        working_campaign.unsubscribed_count = campaign['unsubscribed_count']
        working_campaign.bounced_count = campaign['bounced_count']
        working_campaign.complained_count = campaign['complained_count']
        working_campaign.dropped_count = campaign['dropped_count']
        working_campaign.save()
    campaigns = MailCampaignContainer.objects.filter(status__identifier=active_type.identifier)
    context = {'campaigns': campaigns}
    
    return render(request,'crm/campaigns_list.html', context)