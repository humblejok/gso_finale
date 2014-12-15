from universe.models import FinancialOperation, Attributes
def create_cash_movement(container, source, target, details, label):
    operation = FinancialOperation()
    operation.name = label if label!=None else generate_cash_movement_label(source, target)
    operation.short_name = generate_cash_movement_short_label(source, target)
    operation.status = Attributes.objects.get(identifier='OPE_STATUS_EXECUTED', active=True) if not details.has_key('status') else details['status']
    operation.operation_type = generate_cash_movement_operation_type(source, target, details)
    operation.creation_date = details.operation_date
    operation.operator = None
    operation.validator = None
    return operation

def generate_cash_movement_label(source, target):
    return 'LONG LABEL'

def generate_cash_movement_short_label(source, target):
    return 'SHORT LABEL'

def generate_cash_movement_operation_type(source, target, details):
    if source==None and target!=None:
        if details['cashier']:
            return Attributes.objects.get(identifier='OPE_TYPE_CASH_CONTRIBUTION', active=True)
        else:
            return Attributes.objects.get(identifier='OPE_TYPE_CONTRIBUTION', active=True)
    elif source!=None and target==None:
        if details['cashier']:
            return Attributes.objects.get(identifier='OPE_TYPE_CASH_WITHDRAWAL', active=True)
        else:
            return Attributes.objects.get(identifier='OPE_TYPE_WITHDRAWAL', active=True)