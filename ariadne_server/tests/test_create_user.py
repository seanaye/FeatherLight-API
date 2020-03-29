from secrets import token_hex
import pytest
from ariadne import graphql
from classes.error import Error
from helpers.crypto import decode as decode_jwt

@pytest.mark.asyncio()
@pytest.mark.dependency()
@pytest.mark.parametrize('role', [('ADMIN'), ('USER')])
@pytest.mark.usefixtures('schema')
async def test_create_user(role, schema):
    query = '''
        mutation createUser($role: Role){
            createUser(role: $role) {
                __typename
                ... on User {
                    username
                    password
                    role
                    btcAddress
                    tokens {
                        access
                        refresh
                    }
                    balance
                    invoices {
                        paymentHash
                    }
                }
            }
        }
    '''
    response = await graphql(
        schema,
        {
            'query': query,
            'variables': {
                'role': role
            }
        }
    )
    print(response)
    r = response['data']['createUser']
    assert r['username']
    assert r['password']
    assert r['role'] == role
    assert len(r['invoices']) == 0
    assert r['balance'] == 0
    assert r['btcAddress']
    pytest.users.append(r)
