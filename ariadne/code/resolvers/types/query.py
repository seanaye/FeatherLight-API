"""resolvers for query types"""
from datetime import (
    datetime,
    timedelta
)
from ariadne import QueryType
from protobuf_to_dict import protobuf_to_dict
import rpc_pb2 as ln
import rpc_pb2_grpc as lnrpc
from code.classes.User import User
from code.helpers.async_future import fwrap


query = QueryType()

@query.field('echo')
def r_echo(*_, string=None):
    return string


@query.field('walletBalance')
async def r_walllet_balance(_, info):
    response = await fwrap(info.context.lnd.WalletBalance.future(ln.WalletBalanceRequest()))
    return {
        'totalBalance': response.total_balance,
        'confirmedBalance': response.confirmed_balance
    }


@query.field('login')
async def r_auth(obj, info, user, pw):
    if not (u := await User.from_credentials(ctx=info.context, login=user, pw=pw)):
        return {
            'ok': False,
            'error': 'Invalid Credentials'
        }
    else:
        access = {
            'token': u.userid,
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(minutes=15)
        }
        refresh = {
            'token': u.userid,
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(days=7)
        }
        return {
            'ok': True,
            'access': info.context.jwt.encode(access, kind='access'),
            'refresh': info.context.jwt.encode(refresh, kind='refresh')
        }


@query.field('token')
async def r_get_token(_, info):
    if (cookie := info.context.req.cookies.get(info.context.cookie_name)):
        send = cookie.encode('utf-8')
        jsn = info.context.jwt.decode(send, kind='refresh')
        return await User.from_refresh(ctx=info.context, refresh_token=jsn['token'])
    return None


@query.field('BTCAddress')
async def r_get_address(_, info):
    if not (u := await info.context.user_from_header()):
        return {
            'ok': False,
            'error': 'Invalid auth token'
        }
    addr = await u.get_address()
    if not addr:
        await u.generate_address()
        addr = await u.get_address()
    return {
        'ok': True,
        'address': addr.decode('utf-8')
    }

@query.field('balance')
async def r_balance(_, info):
    if not (u := await info.context.user_from_header()):
        return {
            'ok': False,
            'error': 'Invalid auth token'
        }
    addr = await u.get_address()
    if not addr:
        await u.generate_address()
    await u.account_for_possible_txids()
    balance = u.get_balance()
    if (balance < 0):
        balance = 0
    return {
        'ok': True,
        'availableBalance': balance
    }

@query.field('info')
async def r_info(_, info):
    if not (u := await info.context.user_from_header()):
        return {
            'ok': False,
            'error': 'Invalid auth token'
        }
    request = ln.GetInfoRequest()
    response = await fwrap(info.context.lnd.GetInfo.future(request, timeout=5000))
    d = protobuf_to_dict(response)
    if 'chains' in d:
        del d['chains']
    if 'uris' in d:
        del d['uris']
    if 'features' in d:
        del d['features'] #TODO remove these and add the types in gql schema
    return {
        'ok': True,
        **d
    }
    