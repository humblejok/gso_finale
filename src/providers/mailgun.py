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
import itertools
import datetime

LOGGER = logging.getLogger(__name__)

def send_message(mail_subject, mail_content, addressees, attachments=[], campaign_id=MAILGUN_DEFAULT_CAMPAIGN, tags="No Tag"):
    for addressee in addressees:
        requests.post(
        "https://api.mailgun.net/v3/" + MAILGUN_DOMAIN +"/messages",
        auth=("api", MAILGUN_KEY),
        files=[("attachment", open(attachment, "rb")) for attachment in attachments],
        data={"from": MAILGUN_FROM,
              "to": addressee[1].email_address,
              "subject": mail_subject.replace('%%NAME%%', addressee[0].name.capitalize()).replace('%%FIRST_NAME%%',addressee[0].first_name.capitalize()).replace('%%LAST_NAME%%',addressee[0].last_name.capitalize()) if addressee[0].type.identifier=="CONT_PERSON" else mail_subject.replace('%%NAME%%', 'Sir or Madam').replace('%%FIRST_NAME%%', 'Sir or Madam').replace('%%LAST_NAME%%', 'Sir or Madam'),
              "html": mail_content.replace('%%NAME%%', addressee[0].name.capitalize()).replace('%%FIRST_NAME%%',addressee[0].first_name.capitalize()).replace('%%LAST_NAME%%',addressee[0].last_name.capitalize()) if addressee[0].type.identifier=="CONT_PERSON" else mail_content.replace('%%NAME%%', 'Sir or Madam').replace('%%FIRST_NAME%%', 'Sir or Madam').replace('%%LAST_NAME%%', 'Sir or Madam'),
              "o:tracking": "yes",
              "o:tracking-clicks": "yes",
              "o:tracking-opens": "yes",
              "o:campaign": campaign_id,
              "o:tag": [tag.strip() for tag in tags.split(",")]
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
    all_events = []
    page = 1
    response = requests.get("https://api.mailgun.net/v3/" + MAILGUN_DOMAIN +"/campaigns/" + campaign_id + "/events?page=" + str(page),auth=('api', MAILGUN_KEY))
    response_data = response.json()
    while response.status_code==200 and len(response_data)>0:
        all_events += response_data
        page += 1
        response = requests.get("https://api.mailgun.net/v3/" + MAILGUN_DOMAIN +"/campaigns/" + campaign_id + "/events?page=" + str(page),auth=('api', MAILGUN_KEY))
        if response.status_code==200 and len(response_data)>0:
            response_data = response.json()
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
    
def treat_emails(mail_tag=None, mail_subject=None):
    if mail_tag==None:
        response = requests.get("https://api.mailgun.net/v3/sequoia-ge.com/events", auth=("api", "key-531bd6d34425805a27746678af906ec2"), params={"pretty":"yes", "subject": mail_subject})
    else:
        response = requests.get("https://api.mailgun.net/v3/sequoia-ge.com/events", auth=("api", "key-531bd6d34425805a27746678af906ec2"), params={"pretty":"yes", "tags": mail_tag})
    response_data = response.json()
    all_data = []
    while response.status_code==200 and len(response_data['items'])>0:
        all_data += response_data['items']
        if response_data['paging'].has_key('next') and response_data['paging']['next']!=None and response_data['paging']['next']!='':
            response = requests.get(response_data['paging']['next'], auth=("api", "key-531bd6d34425805a27746678af906ec2"))
            if response.status_code==200 and len(response_data['items'])>0:
                response_data = response.json()
    return all_data

def treat_events(campaign_id):
    events = get_detailed_history(campaign_id)
    campaign_information = {'stats_keys': ['opened', 'clicked', 'bounced', 'rejected','received'] ,'persons':{}, 'companies':{}, 'received': {},'opened': {}, 'clicked': {}, 'bounced': {}, 'rejected': {}}
    for event in events:
        LOGGER.info("Working on " + event['recipient'])
        recipient = event['recipient']
        email = Email.objects.filter(email_address=recipient)
        persons = PersonContainer.objects.filter(emails__in=email)
        companies = CompanyContainer.objects.filter(emails__in=email)
        for contact in list(itertools.chain(persons, companies)):
            contact_id = str(contact.id)
            main_key = 'persons' if isinstance(contact, PersonContainer) else 'companies'
            if not campaign_information[main_key].has_key(contact_id):
                campaign_information[main_key][contact_id] = {'name': contact.name, 'received': False,'opened': False, 'clicked': False, 'bounced': False, 'rejected': False}
                if isinstance(contact, PersonContainer):
                    working_companies = CompanyContainer.objects.filter(members__in=[contact])
                    campaign_information[main_key]['companies'] = []
                    for company in working_companies:
                        campaign_information[main_key]['companies'].append({'id': company.id, 'name': company.name})
            if event['event']=='delivered':
                campaign_information[main_key][contact_id]['received'] = True
                campaign_information['received'][contact_id] = {'id': contact.id, 'name': contact.name, 'container_type': contact.type.identifier, 'email': event['recipient'], 'date': datetime.datetime.strptime(event['timestamp'],'%a, %d %b %Y %H:%M:%S %Z')}
            if event['event']=='opened':
                campaign_information[main_key][contact_id]['received'] = True
                campaign_information[main_key][contact_id]['opened'] = True
                campaign_information['opened'][contact_id] = {'id': contact.id, 'name': contact.name, 'container_type': contact.type.identifier, 'email': event['recipient'], 'date': datetime.datetime.strptime(event['timestamp'],'%a, %d %b %Y %H:%M:%S %Z')}
            if event['event']=='clicked':
                campaign_information[main_key][contact_id]['received'] = True
                campaign_information[main_key][contact_id]['opened'] = True
                campaign_information[main_key][contact_id]['clicked'] = True
                campaign_information['clicked'][contact_id] = {'id': contact.id, 'name': contact.name, 'container_type': contact.type.identifier, 'email': event['recipient'], 'date': datetime.datetime.strptime(event['timestamp'],'%a, %d %b %Y %H:%M:%S %Z')}
            if event['event']=='dropped':
                campaign_information[main_key][contact_id]['rejected'] = True
                campaign_information['rejected'][contact_id] = {'id': contact.id, 'name': contact.name, 'container_type': contact.type.identifier, 'email': event['recipient'], 'date': datetime.datetime.strptime(event['timestamp'],'%a, %d %b %Y %H:%M:%S %Z')}
            if event['event']=='bounced':
                campaign_information[main_key][contact_id]['bounced'] = True
                campaign_information['bounced'][contact_id] = {'id': contact.id, 'name': contact.name, 'container_type': contact.type.identifier, 'email': event['recipient'], 'date': datetime.datetime.strptime(event['timestamp'],'%a, %d %b %Y %H:%M:%S %Z')}
    return campaign_information