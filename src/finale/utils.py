import re
from universe.models import CompanyContainer, Attributes, RelatedCompany,\
    Universe
import logging
import datetime
from django.contrib.auth.models import User
from django.db.models.fields import FieldDoesNotExist

LOGGER = logging.getLogger(__name__)

isin = re.compile("^[A-Z]{2}[A-Z0-9]{10,11}$")
bbgid = re.compile("^BBG[A-Z0-9]{9,11}")

def is_isin(code):
    return isin.match(code)

def is_bbgid(code):
    return bbgid.match(code)

def to_bloomberg_code(code, terminal=False):
    if is_isin(code):
        return ('/isin/' + code) if terminal else (code+'|ISIN|')
    elif is_bbgid(code):
        return ('/bbgid/' + code) if terminal else (code+'|BBGID|')
    else:
        return code

def get_bloomberg_provider():
    bloomberg_company = CompanyContainer.objects.get(name='Bloomberg LP')
    data_provider = Attributes.objects.get(identifier='SCR_DP', active=True)
    
    if not RelatedCompany.objects.filter(company=bloomberg_company, role=data_provider).exists():
        LOGGER.info("Creating Bloomberg LP as a data providing company.")
        bloomberg_provider = RelatedCompany()
        bloomberg_provider.company = bloomberg_company
        bloomberg_provider.role = data_provider
        bloomberg_provider.save()
    else:
        bloomberg_provider = RelatedCompany.objects.get(company=bloomberg_company, role=data_provider)
    return bloomberg_provider

def get_universe_from_datasource(datasource):
    universe = Universe.objects.filter(short_name=datasource.upper())
    if universe.exists():
        universe = universe[0]
        universe.members.clear()
        universe.save()
    else:
        universe = Universe()
        universe.name = datasource.capitalize() + ' Universe'
        universe.short_name = datasource.upper()
        universe.type = Attributes.objects.get(identifier='CONT_UNIVERSE')
        universe.inception_date = datetime.date.today()
        universe.closed_date = None
        universe.status = Attributes.objects.get(identifier='STATUS_ACTIVE')
        universe.public = True
        universe.owner = User.objects.get(id=1)
        universe.description = 'This universe contains all securities extracted from ' + datasource.capitalize() + '.'
        universe.save()
    return universe

def batch(iterable, n = 1):
    l = len(iterable)
    for ndx in range(0, l, n):
        yield iterable[ndx:min(ndx+n, l)]
        
def get_static_fields(clazz, trail = []):
    object_static_fields = {}
    LOGGER.debug("Parsing ->" + str(clazz))
    for field_name in clazz._meta.get_all_field_names():
        try:
            if not field_name.endswith('_rel') and not field_name.endswith('_ptr'):
                LOGGER.debug("\tField ->" + str(field_name))
                if clazz._meta.get_field(field_name).get_internal_type()=='ForeignKey' or clazz._meta.get_field(field_name).get_internal_type()=='ManyToManyField':
                    foreign_class = clazz._meta.get_field(field_name).rel.to
                    if clazz._meta.get_field(field_name).get_internal_type()=='ForeignKey':
                        linked_to = clazz._meta.get_field(field_name).rel.limit_choices_to
                        linked_to = dict(linked_to)
                    else:
                        linked_to = {}
                    if foreign_class.__name__!=clazz.__name__ and foreign_class.__name__ not in trail:
                        object_static_fields[field_name] = {'type': clazz._meta.get_field(field_name).get_internal_type(), 'fields': get_static_fields(foreign_class, trail + [foreign_class.__name__]), 'link': linked_to}
                    else:
                        object_static_fields[field_name] = {'type': 'FIELD_TYPE_TEXT', 'link': linked_to}
                    foreign_class
                else:
                    object_static_fields[field_name] = {'type': 'FIELD_TYPE_TEXT'}
        except FieldDoesNotExist:
            None
    return object_static_fields