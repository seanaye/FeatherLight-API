from ariadne import UnionType
from classes.error import Error

USER_INVOICE_RESPONSE = UnionType('UserInvoiceResponse')
PAY_INVOICE_RESPONSE = UnionType('PaidInvoiceResponse')


@USER_INVOICE_RESPONSE.type_resolver
@PAY_INVOICE_RESPONSE.type_resolver
def r_add_invoice_response(obj, _, resolve_type):
    if isinstance(obj, Error):
        return 'Error'
    if str(resolve_type) == 'PaidInvoiceResponse':
        return 'PaidInvoice'
    if str(resolve_type) == 'UserInvoiceResponse':
        return 'UserInvoice'