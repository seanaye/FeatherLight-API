"""Module to define directive for valiadtion user requests"""
from asyncio import iscoroutinefunction
from typing import Union, Optional
from ariadne import SchemaDirectiveVisitor
from graphql import default_field_resolver
from pymacaroons import Macaroon
from pymacaroons.exceptions import (
    MacaroonDeserializationException,
    MacaroonInvalidSignatureException
)
from classes.error import Error
from classes.user import User
from helpers.mixins import LoggerMixin
from helpers.crypto import verify


class AuthDirective(SchemaDirectiveVisitor, LoggerMixin):
    """Directive class"""
    def __init__(self, *args):
        super().__init__(*args)
        self.get_macaroon = None
        if 'REFRESH' in self.args.get('caveats'):
            self.get_macaroon = lambda info: info.context['request'].cookies.get('refresh')
        else:
            def get_access(info):
                """helper to correctly retrieve access macaroon from req headers"""
                auth = info.context['request'].headers.get('Authorization')
                if not auth:
                    return None
                return auth.replace('Bearer ', '')
            self.get_macaroon = get_access


    async def check_auth(self, info) -> Union[User, Error]:
        """Function to check authentication of user"""
        # check if auth header is present
        if not (serial_macaroon:= self.get_macaroon(info)):
            return Error('NoCredentials', 'No token sent. You are not logged in')
        # attempt to deserialize macaroon
        try:
            macaroon = Macaroon.deserialize(serial_macaroon)
        except MacaroonDeserializationException:
            return Error('AuthenticationError', 'Invalid token sent')
        # lookup user by identifier
        db_user: Optional[User] = await User.get(macaroon.identifier)
        if not db_user:
            return Error('AuthenticationError', 'Could not find user')

        # verify macaroon against directive arguments
        try:
            verify(
                macaroon=macaroon,
                key=db_user.key,
                roles=self.args.get('roles'),
                caveats=self.args.get('caveats'),
                req=info.context['request']
            )
        except MacaroonInvalidSignatureException:
            return Error('AuthenticationError', 'You do not have the permission to do that')

        return db_user

    def visit_field_definition(self, field, object_type):
        orig_resolver = field.resolve or default_field_resolver
        is_subscription = getattr(field, 'subscribe', None)

        if is_subscription:
            orig_source = field.subscribe
            #source gen
            async def gen(_, info, **kwargs):

                root = await self.check_auth(info)
                if isinstance(root, Error):
                    yield root
                    return
                async for item in orig_source(root, info, **kwargs):
                    yield item
            field.subscribe = gen
        else:
            async def call(_, info, **kwargs):
                root = await self.check_auth(info)
                # if auth is invalid return error to union resolver
                if isinstance(root, Error):
                    return root

                # attempt to pass user into root resolver
                if iscoroutinefunction(orig_resolver):
                    return await orig_resolver(root, info, **kwargs)
                else:
                    return orig_resolver(root, info, **kwargs)

            field.resolve = call
            
        return field