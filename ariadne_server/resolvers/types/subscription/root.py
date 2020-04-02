from typing import Union
from ariadne import SubscriptionType, UnionType
from aiostream import streamcontext, stream
import rpc_pb2 as ln
from context import LND, PUBSUB
from models import Invoice
from classes.user import User
from classes.error import Error


_SUBSCRIPTION = SubscriptionType()


@_SUBSCRIPTION.source('invoice')
async def r_invoice_gen(user: Union[User, Error], *_):
    if isinstance(user, Error):
        # user wasnt authenticated from schema directive
        # pass error to union resolver and close generator
        yield user
        return
    #create new new pub sub client for streaming locally paid invoices
    local_stream = PUBSUB.add_client(user.id)

    #create stream for remotely paid invoices
    remote_stream = LND.stub.SubscribeInvoices(ln.InvoiceSubscription())

    global_stream = stream.merge(local_stream, remote_stream)

    async with global_stream.stream() as streamer:
        async for response in streamer:
            try:
                # check if response if from lnd - external payment or pubsub - local payment
                if isinstance(response, Invoice):
                    # invoice model received from pubsub client
                    # yield this and default resolver will retrieve requested fields
                    yield response
                else:
                    # payment comes from lnd, check if its associated with this user
                    invoice = None
                    if response.state == 1:
                        invoice = await Invoice.get(response.r_hash)
                    if invoice and invoice.payee == user.id:
                        #received a paid invoice with this user as payee
                        updated = invoice.update(
                            paid=True,
                            paid_at=invoice.settle_date
                        )
                        yield updated
                        # delegate db write to background process
                        await PUBSUB.background_tasks.put(updated.apply)
            except GeneratorExit:
                # user closed stream, del pubsub queue
                del local_stream
                if len(PUBSUB[user.id]) == 0:
                    del PUBSUB[user.id]



@_SUBSCRIPTION.field('invoice')
def r_invoice_field(invoice, *_):
    return invoice


_PAID_INVOICE_RESPONSE = UnionType('PaidInvoiceResponse')

@_PAID_INVOICE_RESPONSE.type_resolver
def r_paid_invoice_response(obj, *_):
    if isinstance(obj, Error):
        return 'Error'
    return 'UserInvoice'


EXPORT = [
    _PAID_INVOICE_RESPONSE,
    _SUBSCRIPTION
]