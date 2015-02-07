'''
Created on Feb 6, 2015

@author: sdejonckheere
'''
import requests
from finale.settings import MAILGUN_DOMAIN, MAILGUN_KEY,\
    MAILGUN_DEFAULT_CAMPAIGN, MAILGUN_FROM

def send_message(mail_subject, mail_content, addressees, attachments=[], campaign_id=MAILGUN_DEFAULT_CAMPAIGN):
    for addressee in addressees:
        requests.post(
        "https://api.mailgun.net/v2/" + MAILGUN_DOMAIN +"/messages",
        auth=("api", MAILGUN_KEY),
        files=[("attachment", open(attachment, "rb")) for attachment in attachments],
        data={"from": MAILGUN_FROM,
              "to": addressee[1].email_address,
              "subject": mail_subject.replace('%%NAME%%', addressee[0].name).replace('%%FIRST_NAME%%',addressee[0].first_name).replace('%%LAST_NAME%%',addressee[0].last_name),
              "html": mail_content.replace('%%NAME%%', addressee[0].name).replace('%%FIRST_NAME%%',addressee[0].first_name).replace('%%LAST_NAME%%',addressee[0].last_name),
              "o:tracking": "yes",
              "o:tracking-clicks": "yes",
              "o:tracking-opens": "yes",
              "o:campaign": campaign_id
              })

def create_campaign(campaign_name):
    return requests.post(
        "https://api.mailgun.net/v2/" + MAILGUN_DOMAIN +"/campaigns",
        auth=('api', MAILGUN_KEY), data={'name': campaign_name})

def get_campaigns():
    return requests.get(
        "https://api.mailgun.net/v2/" + MAILGUN_DOMAIN +"/campaigns",
        auth=('api', MAILGUN_KEY))
    
def get_detailed_history(campaign_id):
    return requests.get(
        "https://api.mailgun.net/v2/" + MAILGUN_DOMAIN +"/campaigns/" + campaign_id + "/events",
        auth=('api', MAILGUN_KEY))