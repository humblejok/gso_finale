'''
Created on Feb 6, 2015

@author: sdejonckheere
'''
import requests
from finale.settings import MAILGUN_DOMAIN, MAILGUN_KEY,\
    MAILGUN_DEFAULT_CAMPAIGN, MAILGUN_FROM
from universe.models import Email, PersonContainer, CompanyContainer,\
    CompanyMember, MailCampaignContainer
import logging

LOGGER = logging.getLogger(__name__)

def send_message(mail_subject, mail_content, addressees, attachments=[], campaign_id=MAILGUN_DEFAULT_CAMPAIGN):
    for addressee in addressees:
        requests.post(
        "https://api.mailgun.net/v./" + MAILGUN_DOMAIN +"/messages",
        auth=("api", MAILGUN_KEY),
        files=[("attachment", open(attachment, "rb")) for attachment in attachments],
        data={"from": MAILGUN_FROM,
              "to": addressee[1].email_address,
              "subject": mail_subject.replace('%%NAME%%', addressee[0].name.capitalize()).replace('%%FIRST_NAME%%',addressee[0].first_name.capitalize()).replace('%%LAST_NAME%%',addressee[0].last_name.capitalize()) if addressee[0].type.identifier=="CONT_PERSON" else mail_subject.replace('%%NAME%%', 'Sir or Madam').replace('%%FIRST_NAME%%', 'Sir or Madam').replace('%%LAST_NAME%%', 'Sir or Madam'),
              "html": mail_content.replace('%%NAME%%', addressee[0].name.capitalize()).replace('%%FIRST_NAME%%',addressee[0].first_name.capitalize()).replace('%%LAST_NAME%%',addressee[0].last_name.capitalize()) if addressee[0].type.identifier=="CONT_PERSON" else mail_content.replace('%%NAME%%', 'Sir or Madam').replace('%%FIRST_NAME%%', 'Sir or Madam').replace('%%LAST_NAME%%', 'Sir or Madam'),
              "o:tracking": "yes",
              "o:tracking-clicks": "yes",
              "o:tracking-opens": "yes",
              "o:campaign": campaign_id
              })

def create_campaign(campaign_name):
    return requests.post(
        "https://api.mailgun.net/v3/" + MAILGUN_DOMAIN +"/campaigns",
        auth=('api', MAILGUN_KEY), data={'name': campaign_name})

def get_campaigns():
    return requests.get(
        "https://api.mailgun.net/v3/" + MAILGUN_DOMAIN +"/campaigns",
        auth=('api', MAILGUN_KEY))

def get_campaign_summary(campaign_id):
    return requests.get(
        "https://api.mailgun.net/v3/" + MAILGUN_DOMAIN +"/campaigns/" + campaign_id,
        auth=('api', MAILGUN_KEY))
    
def get_detailed_history(campaign_id):
    response = None
    all_events = []
    page = 1
    while response==None or len(response.json())!=0:
        response = requests.get(
        "https://api.mailgun.net/v3/" + MAILGUN_DOMAIN +"/campaigns/" + campaign_id + "/events",
        auth=('api', MAILGUN_KEY))
        if len(response.json())!=0:
            all_events = all_events + response.json()['items']
        page += 1
    return all_events

def get_clicks_history(campaign_id):
    return requests.get(
        "https://api.mailgun.net/v3/" + MAILGUN_DOMAIN +"/campaigns/" + campaign_id + "/clicks?groupby=recipient",
        auth=('api', MAILGUN_KEY))
    
def get_opens_history(campaign_id):
    return requests.get(
        "https://api.mailgun.net/v3/" + MAILGUN_DOMAIN +"/campaigns/" + campaign_id + "/opens?groupby=recipient",
        auth=('api', MAILGUN_KEY))
    
def get_bounces_history(campaign_id):
    return requests.get(
        "https://api.mailgun.net/v3/" + MAILGUN_DOMAIN +"/campaigns/" + campaign_id + "/bounces?groupby=recipient",
        auth=('api', MAILGUN_KEY))
    
def treat_events(campaign_id):
    current_campaign = MailCampaignContainer.objects.get(external_id=campaign_id)
    events = get_detailed_history(campaign_id)
    campaign_information = {'persons':{}, 'companies':{}, 'received': {},'opened': {}, 'clicked': {}, 'bounced': {}, 'rejected': {}}
    for event in events:
        LOGGER.info("Working on " + event['recipient'])
        recipient = event['recipient']
        email = Email.objects.filter(email_address=recipient)
        persons = PersonContainer.objects.filter(emails__in=email)
        companies = CompanyContainer.objects.filter(emails__in=email)
        for contact in persons + companies:
            main_key = 'persons' if isinstance(contact, PersonContainer) else 'companies'
            if not campaign_information[main_key].has_key(contact.id):
                campaign_information[main_key][contact.id] = {'name': contact.name, 'received': False,'opened': False, 'clicked': False, 'bounced': False, 'rejected': False}
                if isinstance(contact, PersonContainer):
                    working_companies = CompanyContainer.objects.filter(members__in=[contact])
                    campaign_information[main_key]['companies'] = []
                    for company in working_companies:
                        campaign_information[main_key]['companies'].append({'id': company.id, 'name': company.name})
            if event['event']=='delivered':
                campaign_information[main_key][contact.id]['received'] = True
                campaign_information[main_key]['received'][contact.id] = {'id': contact.id, 'name': contact.name }
            if event['event']=='opened':
                campaign_information[main_key][contact.id]['received'] = True
                campaign_information[main_key][contact.id]['opened'] = True
                campaign_information[main_key]['opened'][contact.id] = {'id': contact.id, 'name': contact.name }
            if event['event']=='clicked':
                campaign_information[main_key][contact.id]['received'] = True
                campaign_information[main_key][contact.id]['opened'] = True
                campaign_information[main_key][contact.id]['clicked'] = True
                campaign_information[main_key]['clicked'][contact.id] = {'id': contact.id, 'name': contact.name }
            if event['event']=='dropped':
                campaign_information[main_key][contact.id]['rejected'] = True
                campaign_information[main_key]['dropped'][contact.id] = {'id': contact.id, 'name': contact.name }
            if event['event']=='bounced':
                campaign_information[main_key][contact.id]['bounced'] = True
                campaign_information[main_key]['bounced'][contact.id] = {'id': contact.id, 'name': contact.name }
    return current_campaign