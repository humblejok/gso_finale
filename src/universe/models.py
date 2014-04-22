from django.contrib.auth.models import User
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Q
from django.db.models.fields import FieldDoesNotExist
from openpyxl.reader.excel import load_workbook
from seq_common.utils import classes
from xlrd.xldate import xldate_as_tuple
import datetime
import logging
import os
import xlrd


MAIN_PATH = 'c:\\DEV\\Sources\\gso_finale\\resources'

LOGGER = logging.getLogger(__name__)

def setup():
    populate_attributes_from_xlsx('universe.models.Attributes', os.path.join(MAIN_PATH,'Repository Setup.xlsx'))
    populate_attributes_from_xlsx('universe.models.Dictionary', os.path.join(MAIN_PATH,'Repository Setup.xlsx'))
    populate_model_from_xlsx('universe.models.CompanyContainer', os.path.join(MAIN_PATH,'Repository Setup.xlsx'))
    populate_model_from_xlsx('universe.models.AccountContainer', os.path.join(MAIN_PATH,'Repository Setup.xlsx'))
    populate_model_from_xlsx('universe.models.PersonContainer', os.path.join(MAIN_PATH,'Repository Setup.xlsx'))


def populate_attributes_from_xlsx(model_name, xlsx_file):
    model = classes.my_class_import(model_name)
    workbook = load_workbook(xlsx_file)
    sheet = workbook.get_sheet_by_name(name=model.__name__)
    row_index = 0
    # Reading header
    header = []
    for column_index in range(0, sheet.get_highest_column()):
        value = sheet.cell(row = row_index, column=column_index).value
        if value!=None:
            header.append(value if value!='' else header[-1])
        else:
            break
    LOGGER.info('Using header:' + str(header))
    row_index += 1
    while row_index<sheet.get_highest_row():
        if model.objects.filter(identifier=sheet.cell(row = row_index, column=0).value).exists():
            instance = model.objects.get(identifier=sheet.cell(row = row_index, column=0).value)
        else:
            instance = model()
        for i in range(0,len(header)):
            value = sheet.cell(row = row_index, column=i).value
            setattr(instance, header[i], value)
        instance.save()
        row_index += 1

def populate_model_from_xlsx(model_name, xlsx_file):
    model = classes.my_class_import(model_name)
    workbook = load_workbook(xlsx_file)
    sheet = workbook.get_sheet_by_name(name=model.__name__)
    row_index = 0
    # Reading header
    header = []
    for column_index in range(0, sheet.get_highest_column()):
        value = sheet.cell(row = row_index, column=column_index).value
        if value!=None:
            header.append(value if value!='' else header[-1])
        else:
            break
    LOGGER.info('Using header:' + str(header))
    row_index += 1
    while row_index<sheet.get_highest_row():
        instance = model()
        for i in range(0,len(header)):
            value = sheet.cell(row = row_index, column=i).value
            field_info = Attributes()
            field_info.short_name = header[i]
            field_info.name = header[i]
            instance.set_attribute('excel', field_info, value)
        instance.save()
        row_index += 1

def populate_track_from_lyxor(lyxor_file):
    # Excel input
    workbook = xlrd.open_workbook(lyxor_file)
    sheet = workbook.sheet_by_name('Weekly NAV')
    # Lyxor default
    lyxor_company = CompanyContainer.objects.get(name='Lyxor Asset Management')
    nav_value = Attributes.objects.get(identifier='NUM_TYPE_NAV', active=True)
    official_type = Attributes.objects.get(identifier='PRICE_TYPE_OFFICIAL', active=True)
    weekly = Attributes.objects.get(identifier='FREQ_WEEKLY', active=True)
    tuesday = Attributes.objects.get(identifier='DT_REF_THURSDAY', active=True)
    row_index = 9
    isin_cache = {}
    while row_index<sheet.nrows:
        full_date = datetime.datetime(*xldate_as_tuple(sheet.cell_value(row_index, 1), workbook.datemode))
        simple_date = datetime.date(full_date.year, full_date.month, full_date.day)
        LOGGER.info("DATE:" + str(simple_date))
        for col_index in range(2,sheet.ncols):
            if sheet.cell_type(row_index,col_index)!=xlrd.XL_CELL_EMPTY and sheet.cell_value(row_index,col_index)!=None and sheet.cell_value(row_index,col_index)!='':
                isin = sheet.cell_value(5,col_index)
                if not isin_cache.has_key(isin):
                    targets = FundContainer.objects.filter(aliases__alias_type__name='ISIN', aliases__alias_value=isin)
                    isin_cache[isin] = targets
                else:
                    targets = isin_cache[isin]
                LOGGER.info("Updating " + str(len(targets)) + " entities with ISIN like " + str(isin));
                for target in targets:
                    new_nav_value = ContainerNumericValue()
                    new_nav_value.effective_container  = target
                    new_nav_value.type = nav_value
                    new_nav_value.quality = official_type
                    new_nav_value.source = lyxor_company
                    new_nav_value.day = simple_date
                    new_nav_value.time = None
                    new_nav_value.frequency = weekly
                    new_nav_value.frequency_reference = tuesday
                    new_nav_value.value = float(sheet.cell_value(row_index,col_index))
                    new_nav_value.save()
        row_index += 1
    
def populate_security_from_bloomberg_protobuf(data):
    securities = {}
    for row in data.rows:
        if row.errorCode==0:
            if not securities.has_key(row.ticker):
                if row.ticker.find('LX')>=0:
                    securities[row.ticker] = FundContainer()
                else:
                    securities[row.ticker] = SecurityContainer()
            field_info = Attributes.objects.filter(type='bloomberg_field', name=row.field)
            LOGGER.info(field_info)
            if field_info.exists():
                securities[row.ticker].set_attribute('bloomberg', field_info[0], row.valueString)
            else:
                LOGGER.info("Cannot find matching field for " + row.field)
    for ticker in securities:
        securities[ticker].status = Attributes.objects.get(identifier='STATUS_TO_BE_VALIDATED')
        securities[ticker].save()
    return securities

def populate_security_from_lyxor(lyxor_file, clean=True):
    universe = Universe.objects.filter(short_name='LYXOR')
    if universe.exists():
        universe = universe[0]
        universe.members.clear()
        universe.save()
    else:
        universe = Universe()
        universe.name = 'Lyxor Universe'
        universe.short_name = 'LYXOR'
        universe.type = Attributes.objects.get(identifier='CONT_UNIVERSE')
        universe.inception_date = datetime.date.today()
        universe.closed_date = None
        universe.status = Attributes.objects.get(identifier='STATUS_ACTIVE')
        universe.public = True
        universe.owner = User.objects.get(id=3)
        universe.description = "This universe contains all Lyxor B ETFs and trackers."
        universe.save()
    if clean:
        SecurityContainer.objects.all().delete()
    
    lyxor_company = CompanyContainer.objects.get(name='Lyxor Asset Management')
    data_provider = Attributes.objects.get(identifier='SCR_DP', active=True)
    lyxor_provider = RelatedCompany()
    lyxor_provider.company = lyxor_company
    lyxor_provider.role = data_provider
    lyxor_provider.save()
    weekly = Attributes.objects.get(identifier='FREQ_WEEKLY', active=True)
    tuesday = Attributes.objects.get(identifier='DT_REF_THURSDAY', active=True)
    security_type = Attributes.objects.get(identifier='CONT_SECURITY')
    fund_type = Attributes.objects.get(identifier='SECTYP_FUND')
    workbook = xlrd.open_workbook(lyxor_file)
    sheet = workbook.sheet_by_name('Lyxor Accounts')
    row_index = 6
    # Reading header
    HEADER = []
    for column_index in range(1, sheet.ncols):
        value = sheet.cell_value(row_index, column_index)
        HEADER.append(value if value!='' else HEADER[-1])
    LOGGER.info('Using header:' + str(HEADER))
    row_index += 1
    while row_index<sheet.nrows:
        value = sheet.cell_value(row_index,2)
        if not sheet.cell_type(row_index,2)==xlrd.XL_CELL_EMPTY and value.strip()!='':
            update = SecurityContainer.objects.filter(aliases__alias_type__name='ISIN', aliases__alias_value=value)
            if update.exists():
                LOGGER.info('Found ' + len(update) + ' securities with identifier [' + value + ']')
                update = [FundContainer.objects.get(id=security.id) for security in update]
            else:
                update = [FundContainer.create()]
                [security.save() for security in update]
                LOGGER.info('Creating new entry ' + FundContainer.__name__)
            for i in range(1,sheet.ncols):
                value = sheet.cell_value(row_index,i)
                if sheet.cell_type(row_index,i)==xlrd.XL_CELL_DATE:
                    value = datetime.date(*xldate_as_tuple(value, workbook.datemode)[:3])
                field_info = Attributes.objects.filter(type='lyxor_field', name=HEADER[i-1])
                if field_info.exists():
                    [security.set_attribute('lyxor', field_info[0], value) for security in update]
                else:
                    LOGGER.debug("Cannot find matching field for " + HEADER[i-1])
            [setattr(security,'type', security_type) for security in update]
            [setattr(security,'security_type', fund_type) for security in update]
            [setattr(security,'frequency', weekly) for security in update]
            [setattr(security,'frequency_reference', tuesday) for security in update]
            [security.finalize() for security in update]
            [security.associated_companies.add(lyxor_provider) for security in update]
            [security.save() for security in update]
            [LOGGER.info("Aliases:" + str(len(security.aliases.all()))) for security in update]
            [universe.members.add(security) for security in update]
        row_index += 1


class CoreModel(models.Model):

    def get_editable_fields(self):
        values = []
        for field in self.get_fields():
            if self._meta.get_field(field).get_internal_type()!='ManyToManyField':
                values.append(field)
        return values
        
    def get_associable_field(self):
        values = []
        for field in self.get_fields():
            if self._meta.get_field(field).get_internal_type()=='ManyToManyField':
                values.append(field)
        return values        

    def get_fields(self):
        return []
    
    def get_identifier(self):
        return 'name'
    
    def list_values(self):
        values = []
        for field in self.get_fields():
            LOGGER.debug(self.__class__.__name__ + ' * ' + field)
            if field in self._meta.get_all_field_names():
                if self._meta.get_field(field).get_internal_type()=='ManyToManyField' and getattr(self,field)!=None:
                    values.append(str([e.list_values() for e in list(getattr(self,field).all())]))
                elif self._meta.get_field(field).get_internal_type()=='ForeignKey' and getattr(self,field)!=None:
                    values.append(getattr(self,field).get_value())
                else:
                    values.append(str(getattr(self,field)))
            else:
                # Generic foreign key
                values.append(getattr(self,field).get_value())
        return values
    
    def get_value(self):
        if self.get_identifier()!=None:
            return getattr(self, self.get_identifier())
        else:
            return None
        
    def __unicode__(self):
        return unicode(self.get_value())
    
    class Meta:
        ordering = ['id']
    
class Attributes(CoreModel):
    
    identifier = models.CharField(max_length=128)
    name = models.CharField(max_length=128)
    short_name = models.CharField(max_length=32)
    type = models.CharField(max_length=64)
    active = models.BooleanField()
    
    def get_fields(self):
        return ['identifier','name','short_name','type','active']
    
    class Meta:
        ordering = ['name']
    
class Dictionary(CoreModel):
    identifier = models.CharField(max_length=128)
    name = models.CharField(max_length=128)
    auto_create = models.BooleanField()
    
    def get_fields(self):
        return ['identifier','name','auto_create']
    
    class Meta:
        ordering = ['name']
        
class Address(CoreModel):
    address_type = models.ForeignKey(Attributes, limit_choices_to={'type':'address_type'}, related_name='address_type_rel', null=True)
    line_1 = models.CharField(max_length=128, null=True)
    line_2 = models.CharField(max_length=128, null=True)
    zip_code = models.CharField(max_length=16, null=True)
    city = models.CharField(max_length=128, null=True)

    def get_identifier(self):
        return 'id'

    def get_fields(self):
        return ['address_type','line_1','line_2','zip_code','city']

class Email(CoreModel):
    address_type = models.ForeignKey(Attributes, limit_choices_to={'type':'email_type'}, related_name='email_type_rel', null=True)
    address = models.EmailField()

    def get_identifier(self):
        return 'id'

    def get_fields(self):
        return ['address_type','address']
    
class Phone(CoreModel):
    line_type = models.ForeignKey(Attributes, limit_choices_to={'type':'phone_type'}, related_name='phone_type_rel', null=True)
    phone = models.TextField(max_length=32)

    def get_identifier(self):
        return 'id'

    def get_fields(self):
        return ['line_type','phone']
    
class Alias(CoreModel):
    alias_type = models.ForeignKey(Attributes, limit_choices_to={'type':'alias_type'}, related_name='alias_type', null=True)
    alias_value = models.CharField(max_length=512)
    alias_additional = models.CharField(max_length=512)
    
    def get_identifier(self):
        return 'id'
    
    def get_fields(self):
        return ['alias_type','alias_value','alias_additional']
    
    @staticmethod
    def retrieve_or_create(source, key, value):
        translation = Attributes.objects.filter(active=True, name=key, type=source.lower() + '_translation')
        if translation.exists():
            translation = translation[0].short_name
        else:
            translation = key
        new_alias = Alias()        
        new_alias.alias_type = Attributes.objects.get(Q(active=True), Q(type='alias_type'), Q(name=translation) | Q(short_name=translation))
        new_alias.alias_value = value
        new_alias.alias_additional = ''
        new_alias.save()
        return new_alias

    class Meta:
        ordering = ['alias_value']
    
class Container(CoreModel):
    name = models.CharField(max_length=1024)
    short_name = models.CharField(max_length=512)
    type = models.ForeignKey(Attributes, limit_choices_to={'type':'container_type'}, related_name='container_type_rel', null=True)
    inception_date = models.DateField(null=True)
    closed_date = models.DateField(null=True)
    status = models.ForeignKey(Attributes,limit_choices_to = {'type':'status'}, related_name='container_status_rel', null=True)
    
    many_fields = {}
    
    @classmethod
    def create(cls):
        entity = cls()
        entity.many_fields = {}
        return entity
    
    def get_fields(self):
        return ['name','short_name','type','inception_date','closed_date','status']
    
    def set_attribute(self, source, field_info, string_value):
        if string_value!='' and string_value!=None:
            if self._meta.get_field(field_info.short_name).get_internal_type()=='ManyToManyField':
                if not self.many_fields.has_key(field_info.short_name):
                    self.many_fields[field_info.short_name] = []
                foreign = self._meta.get_field(field_info.short_name).rel.to                
                self.many_fields[field_info.short_name].append(foreign.retrieve_or_create(source, field_info.name, string_value))
            elif self._meta.get_field(field_info.short_name).get_internal_type()=='DateField' or self._meta.get_field(field_info.short_name).get_internal_type()=='DateTimeField':
                try:
                    dt = datetime.datetime.strptime(string_value,'%m/%d/%Y')
                    if self._meta.get_field(field_info.short_name).get_internal_type()=='DateField':
                        dt = datetime.date(dt.year, dt.month, dt.day)
                except:
                    dt = string_value # This is not a String???
                setattr(self, field_info.short_name, dt)
            elif self._meta.get_field(field_info.short_name).get_internal_type()=='ForeignKey':
                linked_to = self._meta.get_field(field_info.short_name).rel.limit_choices_to
                foreign = self._meta.get_field(field_info.short_name).rel.to
                filtering_by_name = dict(linked_to)
                filtering_by_name['name'] = string_value
                by_name = foreign.objects.filter(**filtering_by_name)
                filtering_by_short = dict(linked_to)
                filtering_by_short['short_name'] = string_value
                by_short = foreign.objects.filter(**filtering_by_short)
                if by_name.exists():
                    setattr(self, field_info.short_name, by_name[0])
                elif by_short.exists():
                    setattr(self, field_info.short_name, by_short[0])
                else:
                    dict_entry = Dictionary.objects.filter(name=linked_to['type'], auto_create=True)
                    if dict_entry.exists():
                        LOGGER.info('Creating new attribute for ' + linked_to['type'] + ' with value ' + string_value)
                        new_attribute = Attributes()
                        new_attribute.active = True
                        new_attribute.identifier = dict_entry[0].identifier + str(string_value.upper()).replace(' ', '_')
                        new_attribute.name = string_value
                        new_attribute.short_name = string_value[0:32]
                        new_attribute.type = linked_to['type']
                        new_attribute.save()
                        setattr(self, field_info.short_name, new_attribute)
                    else:
                        LOGGER.warn('Cannot find foreign key instance on ' + str(self) + '.' + field_info.short_name + ' for value [' + string_value + '] and relation ' + str(linked_to))
            else:
                setattr(self, field_info.short_name, string_value)
    
    def finalize(self):
        active = Attributes.objects.get(active=True, type='status', identifier='STATUS_ACTIVE')
        self.status = active
        self.save()
        # TODO Loop on many to many only
        for field_name in self._meta.get_all_field_names():
            try:
                if self._meta.get_field(field_name).get_internal_type()=='ManyToManyField':
                    if self.many_fields.has_key(field_name):
                        values = list(self.many_fields[field_name])
                        setattr(self, field_name, values)
            except FieldDoesNotExist:
                None
        self.save()
        
    def clean(self):
        for field_name in self._meta.get_all_field_names():
            try:
                if self._meta.get_field(field_name).get_internal_type()=='ForeignKey':
                    setattr(self, field_name, None)
                elif self._meta.get_field(field_name).get_internal_type()=='ManyToManyField':
                    setattr(self, field_name, [])
            except FieldDoesNotExist:
                None

    def clone(self, _class):
        _clone = _class()
        [setattr(_clone, fld.name, getattr(self, fld.name)) for fld in self._meta.fields if fld.name != self._meta.pk and fld.name.find('_ptr')==-1]
        _clone.id = None
        _clone.pk = None
        return _clone

    class Meta:
        ordering = ['name']

class Universe(Container):
    public = models.BooleanField()
    members = models.ManyToManyField("SecurityContainer", related_name='universe_financial_rel')
    owner = models.ForeignKey(User, related_name='universe_owner_rel')
    description = models.TextField(null=True, blank=True)
            
class FinancialContainer(Container):
    currency = models.ForeignKey(Attributes, limit_choices_to = {'type':'currency'}, related_name='container_currency_rel', null=True)
    owner_role = models.ForeignKey(Attributes, limit_choices_to={'type':'third_party_role'}, related_name='owner_role_rel', null=True)
    owner = models.ForeignKey(Container, limit_choices_to = {'type__identifier':'third_party'}, related_name='container_owner_rel', null=True)
    aliases = models.ManyToManyField(Alias, related_name='financial_alias_rel')
    frequency = models.ForeignKey(Attributes, limit_choices_to={'type':'frequency'}, related_name='financial_frequency_rel', null=True)
    frequency_reference = models.ForeignKey(Attributes, limit_choices_to={'type':'date_reference'}, related_name='financial_date_reference_rel', null=True)
    
    def get_fields(self):
        return super(FinancialContainer, self).get_fields() + ['currency','owner_role','owner','aliases']
    
class FinancialOperation(CoreModel):
    name = models.CharField(max_length=512)
    short_name = models.CharField(max_length=128)
    status = models.ForeignKey(Attributes,limit_choices_to = {'type':'operation_status'}, related_name='operation_status_rel', null=True)
    operation_type = models.ForeignKey(Attributes,limit_choices_to = {'type':'operation_type'}, related_name='operation_type_rel', null=True)
    creation_date = models.DateTimeField(default=datetime.datetime.today())
    operator = models.ForeignKey('ThirdPartyContainer', related_name='operator_rel', null=True)
    validator = models.ForeignKey('ThirdPartyContainer', related_name='validator_rel', null=True)
    source = models.ForeignKey('AccountContainer', related_name='source_rel', null=True)
    target = models.ForeignKey('FinancialContainer', related_name='target_rel', null=True)
    spot = models.ForeignKey('ContainerNumericValue', related_name='spot_rel', null=True)
    repository = models.ForeignKey('AccountContainer', related_name='repository_rel', null=True)
    quantity = models.FloatField(null=True)
    amount = models.FloatField(null=True)
    price = models.ForeignKey('ContainerNumericValue', related_name='operation_price_rel', null=True)
    operation_date = models.DateTimeField(default=datetime.datetime.today())
    operation_pnl = models.FloatField(null=True)
    value_date = models.DateTimeField(default=datetime.datetime.today())
    termination_date = models.DateTimeField(default=datetime.datetime.today())
    associated_operation = models.ForeignKey('FinancialOperation', related_name='parent_operation_rel', null=True)
    
    def get_fields(self):
        return ['name','short_name','status','operation_type','creation_date','operator','validator','source','target','spot','repository','quantity','amount','price','operation_date','operation_pnl','value_date','termination_date','associated_operation']
    
    class Meta:
        ordering = ['name']

class ThirdPartyContainer(Container):
    addresses = models.ManyToManyField(Address)
    emails = models.ManyToManyField(Email)
    phones = models.ManyToManyField(Phone)

    def get_fields(self):
        return super(ThirdPartyContainer, self).get_fields() + ['addresses','emails','phones']

class PersonContainer(ThirdPartyContainer):
    first_name = models.CharField(max_length=128)
    last_name = models.CharField(max_length=128)
    birth_date = models.DateField(null=True)
    
    def get_fields(self):
        return super(PersonContainer, self).get_fields() + ['first_name','last_name','birth_date']

class CompanySubsidiary(CoreModel):
    company = models.ForeignKey('CompanyContainer', null=True)
    role = models.ForeignKey(Attributes, limit_choices_to={'type':'company_subsidiary_role'}, related_name='company_subsidiary_role_rel', null=True)

    def get_identifier(self):
        return 'id'
    
    def get_fields(self):
        return ['company','role']

class CompanyMember(CoreModel):
    person = models.ForeignKey(PersonContainer, null=True)
    role = models.ForeignKey(Attributes, limit_choices_to={'type':'company_member_role'}, related_name='company_member_role_rel', null=True)

    def get_identifier(self):
        return 'id'

    def get_fields(self):
        return ['person','role']

class CompanyContainer(ThirdPartyContainer):
    members = models.ManyToManyField(CompanyMember)
    subsidiary = models.ManyToManyField(CompanySubsidiary)
    
    def get_fields(self):
        return super(CompanyContainer, self).get_fields() + ['members','subsidiary']

class AccountContainer(FinancialContainer):
    account_type = models.ForeignKey(Attributes, limit_choices_to={'type':'account_type'}, related_name='account_type_rel', null=True)
    bank = models.ForeignKey(CompanyContainer, related_name='account_bank_rel', null=True)
    
    def get_fields(self):
        return super(AccountContainer, self).get_fields() + ['account_type','bank']
    
class RelatedCompany(CoreModel):
    company = models.ForeignKey(CompanyContainer, null=True)
    role = models.ForeignKey(Attributes, limit_choices_to={'type':'security_company_role'}, related_name='security_company_role_rel', null=True)

    def get_identifier(self):
        return 'id'

    def get_fields(self):
        return ['company','role']
    
    @staticmethod
    def retrieve_or_create(source, key, value):
        translation = Attributes.objects.filter(active=True, name=key, type=source.lower() + '_translation')
        if translation.exists():
            translation = translation[0].short_name
        else:
            translation = key
        company = CompanyContainer.objects.filter(name=value)
        if company.exists():
            company = company[0]
        else:
            company = CompanyContainer()
            company.name = value
            company.short_name = 'To be defined'
            tbv = Attributes.objects.get(active=True, type='status', identifier='STATUS_TO_BE_VALIDATED')
            company.status = tbv
            company.type = Attributes.objects.get(active=True, type='container_type', identifier='CONT_COMPANY')
            company.save()
            
        new_relation = RelatedCompany()        
        new_relation.role = Attributes.objects.get(Q(active=True), Q(type='security_company_role'), Q(name=translation) | Q(short_name=translation))
        new_relation.company = company
        new_relation.save()
        return new_relation

class RelatedThird(CoreModel):
    third = models.ForeignKey(PersonContainer)
    role = models.ForeignKey(Attributes, limit_choices_to={'type':'security_third_role'}, related_name='security_third_role_rel', null=True)

    def get_identifier(self):
        return 'id'

    def get_fields(self):
        return ['third','role']
    
class PortfolioContainer(FinancialContainer):
    accounts = models.ManyToManyField('AccountContainer', related_name='portfolio_accounts_rel')
    
    def get_fields(self):
        return super(PortfolioContainer, self).get_fields() + ['accounts']

class CurrencyContainer(FinancialContainer):
    target = models.ForeignKey(Attributes, limit_choices_to={'type':'currency'}, related_name='source_currency_rel')
    duration = models.FloatField(null=True, blank=True)
    
    def get_fields(self):
        return super(FinancialContainer, self).get_fields() + ['target', 'duration']

class SecurityContainer(FinancialContainer):
    associated_companies = models.ManyToManyField(RelatedCompany)
    associated_thirds = models.ManyToManyField(RelatedThird)
    security_type = models.ForeignKey(Attributes, limit_choices_to={'type':'security_type'}, related_name='security_type_rel', null=True)
    bb_security_type = models.ForeignKey(Attributes, limit_choices_to={'type':'bloomberg_security_type'}, related_name='bb_security_type_rel', null=True)
    industry_sector = models.ForeignKey(Attributes, limit_choices_to={'type':'industry_sector'}, related_name='industry_sector_rel', null=True)
    industry_group = models.ForeignKey(Attributes, limit_choices_to={'type':'industry_group'}, related_name='industry_group_rel', null=True)
    industry_sub_group = models.ForeignKey(Attributes, limit_choices_to={'type':'industry_sub_group'}, related_name='industry_sub_group_rel', null=True)
    bics_name_level_1 = models.ForeignKey(Attributes, limit_choices_to={'type':'bics_name_level_1'}, related_name='bics_name_level_1_rel', null=True)
    bics_name_level_2 = models.ForeignKey(Attributes, limit_choices_to={'type':'bics_name_level_2'}, related_name='bics_name_level_2_rel', null=True)
    bics_name_level_3 = models.ForeignKey(Attributes, limit_choices_to={'type':'bics_name_level_3'}, related_name='bics_name_level_3_rel', null=True)
    country = models.ForeignKey(Attributes, limit_choices_to={'type':'country_iso2'}, related_name='security_country_rel', null=True)
    bb_country = models.ForeignKey(Attributes, limit_choices_to={'type':'bloomberg_country_lookup'}, related_name='bb_security_country_rel', null=True)
    region = models.CharField(max_length=128, null=True, blank=True)
    market_sector = models.CharField(max_length=128, null=True, blank=True)
    exchange = models.ForeignKey(Attributes, limit_choices_to={'type':'bloomberg_exchange_lookup'}, related_name='bloomberg_exchange_rel', null=True)
    parent_security = models.ForeignKey('SecurityContainer', related_name='parent_security_rel', null=True)
    
    attached_account = models.ForeignKey('AccountContainer', related_name='financials_account_rel', null=True)
    
    def get_fields(self):
        return super(SecurityContainer, self).get_fields() + ['associated_companies','associated_thirds','security_type','bb_security_type','industry_sector','industry_group','industry_sub_group','bics_name_level_1','bics_name_level_2','bics_name_level_3','country','bb_country','region','market_sector','exchange','parent_security','attached_account']

class DerivativeContainer(SecurityContainer):
    contract_buy_date = models.DateTimeField()
    contract_buy_price = models.FloatField(null=True)
    contract_remaining_quantity = models.FloatField(null=True)
    contract_estimated_pnl = models.FloatField(null=True)
    maturity_date = models.DateField(null=True)

    def get_fields(self):
        return super(DerivativeContainer, self).get_fields() + ['contract_buy_date','contract_buy_price','contract_remaining_quantity','contract_estimated_pnl','maturity_date']

class OptionContainer(DerivativeContainer):
    None

class FundContainer(SecurityContainer):
    bb_geographical_focus = models.ForeignKey(Attributes, limit_choices_to={'type':'bloomberg_geo_focus'}, related_name='geo_focus_rel', null=True)
    bb_asset_class_focus = models.ForeignKey(Attributes, limit_choices_to={'type':'bloomberg_asset_focus'}, related_name='asset_focus_rel', null=True)
    bb_style = models.ForeignKey(Attributes, limit_choices_to={'type':'bloomberg_style'}, related_name='style_rel', null=True)
    bb_strategy = models.ForeignKey(Attributes, limit_choices_to={'type':'bloomberg_strategy'}, related_name='strategy_rel', null=True)
    bb_fund_type = models.ForeignKey(Attributes, limit_choices_to={'type':'bloomberg_fund_type'}, related_name='fund_type_rel', null=True)
    bb_fund_domiciliation = models.CharField(max_length=128)
    bb_rating_class_focus = models.CharField(max_length=128)
    
    def get_fields(self):
        return super(FundContainer, self).get_fields() + ['bb_geographical_focus','bb_asset_class_focus','bb_style','bb_strategy','bb_fund_type','bb_fund_domiciliation','bb_rating_class_focus']

class BondContainer(SecurityContainer):
    issue_date = models.DateField()
    coupon_rate = models.FloatField()
    coupon_frequency = models.ForeignKey(Attributes, limit_choices_to={'type':'frequency'}, related_name='bond_frequency_rel', null=True)
    maturity_date = models.DateField()
    
    def get_fields(self):
        return super(BondContainer, self).get_fields() + ['issue_date','coupon_rate','coupon_frequency','maturity_date']

class ContainerNumericValue(CoreModel):
    container = models.ForeignKey(ContentType)
    effective_container_id = models.PositiveIntegerField()
    effective_container = generic.GenericForeignKey('container', 'effective_container_id')
    type = models.ForeignKey(Attributes, limit_choices_to={'type':'numeric_type'}, related_name='numeric_type_rel', null=True)
    frequency = models.ForeignKey(Attributes, limit_choices_to={'type':'frequency'}, related_name='numeric_frequency_rel')
    frequency_reference = models.ForeignKey(Attributes, limit_choices_to={'type':'date_reference'}, related_name='numeric_date_reference_rel')
    quality = models.ForeignKey(Attributes, limit_choices_to={'type':'numeric_quality'}, related_name='numeric_quality_rel', null=True)
    source = models.ForeignKey(CompanyContainer, related_name='data_source_rel', null=True)
    day = models.DateField()
    time = models.TimeField(null=True, blank=True)
    value = models.FloatField()
    
    def get_identifier(self):
        return 'id'
    
    def get_fields(self):
        return ['effective_container','type','quality','source','day','time','value']
