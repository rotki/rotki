from http import HTTPStatus

import pytest
import requests

from rotkehlchen.chain.ethereum.typing import CustomEthereumToken, UnderlyingToken
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response_with_result,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.tests.utils.factories import make_ethereum_address
from rotkehlchen.typing import Timestamp
from rotkehlchen.fval import FVal

underlying_address1 = make_ethereum_address()
underlying_address2 = make_ethereum_address()
underlying_address3 = make_ethereum_address()

custom_address1 = make_ethereum_address()
custom_address2 = make_ethereum_address()
INITIAL_TOKENS = [
    CustomEthereumToken(
        address=custom_address1,
        decimals=4,
        name='Custom 1',
        symbol='CST1',
        started=Timestamp(0),
        coingecko='foo',
        cryptocompare='boo',
        underlying_tokens=[
            UnderlyingToken(address=underlying_address1, weight=FVal('0.5055')),
            UnderlyingToken(address=underlying_address2, weight=FVal('0.1545')),
            UnderlyingToken(address=underlying_address3, weight=FVal('0.34')),
        ],
    ),
    CustomEthereumToken(
        address=custom_address2,
        decimals=18,
        name='Custom 2',
        symbol='CST2',
    ),
]

INITIAL_EXPECTED_TOKENS = [INITIAL_TOKENS[0]] + [
    CustomEthereumToken(underlying_address1),
    CustomEthereumToken(underlying_address2),
    CustomEthereumToken(underlying_address3),
] + [INITIAL_TOKENS[1]]


underlying_address4 = make_ethereum_address()
custom_address3 = make_ethereum_address()
CUSTOM_TOKEN3 = CustomEthereumToken(
    address=custom_address3,
    decimals=15,
    name='Custom 3',
    symbol='CST3',
    cryptocompare='goo',
    underlying_tokens=[
        UnderlyingToken(address=custom_address1, weight=FVal('0.55')),
        UnderlyingToken(address=underlying_address4, weight=FVal('0.45')),
    ],
)


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('start_with_logged_in_user', [False])
@pytest.mark.parametrize('custom_ethereum_tokens', [INITIAL_TOKENS])
def test_query_custom_tokens(rotkehlchen_api_server):
    """Test that using the query custom ethereum tokens endpoint works"""
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumassetsresource',
        ),
        json={'address': custom_address1},
    )
    result = assert_proper_response_with_result(response)

    assert result == INITIAL_TOKENS[0].serialize()

    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumassetsresource',
        ),
    )
    result = assert_proper_response_with_result(response)
    assert result == [x.serialize() for x in INITIAL_EXPECTED_TOKENS]

    # test that querying an unknown address for a token is properly handled
    unknown_address = make_ethereum_address()
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumassetsresource',
        ),
        json={'address': unknown_address},
    )
    assert_error_response(
        response=response,
        contained_in_msg=f'Custom token with address {unknown_address} not found',
        status_code=HTTPStatus.NOT_FOUND,
    )


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('start_with_logged_in_user', [False])
@pytest.mark.parametrize('custom_ethereum_tokens', [INITIAL_TOKENS])
def test_adding_custom_tokens(rotkehlchen_api_server):
    """Test that the endpoint for adding a custom ethereum token works"""
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumassetsresource',
        ),
        json={'token': CUSTOM_TOKEN3.serialize()},
    )
    result = assert_proper_response_with_result(response)
    assert result == {'identifier': CUSTOM_TOKEN3.identifier()}

    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumassetsresource',
        ),
    )
    result = assert_proper_response_with_result(response)
    expected_tokens = INITIAL_EXPECTED_TOKENS.copy() + [
        CUSTOM_TOKEN3,
        CustomEthereumToken(address=underlying_address4),
    ]
    assert result == [x.serialize() for x in expected_tokens]

    # test that adding an already existing address is handled properly
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumassetsresource',
        ),
        json={'token': INITIAL_TOKENS[1].serialize()},
    )
    expected_msg = (
        f'Ethereum token with address {INITIAL_TOKENS[1].address} already '
        f'exists in the DB',
    )
    assert_error_response(
        response=response,
        contained_in_msg=expected_msg,
        status_code=HTTPStatus.CONFLICT,
    )
    # and that same tokens as before are in the DB
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumassetsresource',
        ),
    )
    result = assert_proper_response_with_result(response)
    assert result == [x.serialize() for x in expected_tokens]

    # now test that adding a token with underlying tokens adding up to more than 100% is caught
    bad_token = CustomEthereumToken(
        address=make_ethereum_address(),
        decimals=18,
        name='foo',
        symbol='BBB',
        underlying_tokens=[
            UnderlyingToken(address=make_ethereum_address(), weight=FVal('0.5055')),
            UnderlyingToken(address=make_ethereum_address(), weight=FVal('0.7055')),
        ],
    )
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumassetsresource',
        ),
        json={'token': bad_token.serialize()},
    )
    expected_msg = (
        f'The sum of underlying token weights for {bad_token.address} is '
        f'121.1000 and exceeds 100%'
    )
    assert_error_response(
        response=response,
        contained_in_msg=expected_msg,
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # and test that adding a token with empty list of underlying tokens and not null is an error
    bad_token = CustomEthereumToken(
        address=make_ethereum_address(),
        decimals=18,
        name='foo',
        symbol='BBB',
        underlying_tokens=[],
    )
    serialized_bad_token = bad_token.serialize()
    serialized_bad_token['underlying_tokens'] = []
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumassetsresource',
        ),
        json={'token': serialized_bad_token},
    )
    expected_msg = (
        f'Gave an empty list for underlying tokens of {bad_token.address}'
    )
    assert_error_response(
        response=response,
        contained_in_msg=expected_msg,
        status_code=HTTPStatus.BAD_REQUEST,
    )


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('start_with_logged_in_user', [False])
@pytest.mark.parametrize('custom_ethereum_tokens', [INITIAL_TOKENS])
def test_editing_custom_tokens(rotkehlchen_api_server):
    """Test that the endpoint for editing a custom ethereum token works"""
    new_token1 = INITIAL_TOKENS[0].serialize()
    new_name = 'Edited token'
    new_symbol = 'ESMBL'
    new_token1['name'] = new_name
    new_token1['symbol'] = new_symbol
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumassetsresource',
        ),
        json={'token': new_token1},
    )
    result = assert_proper_response_with_result(response)
    assert result == {'identifier': INITIAL_TOKENS[0].identifier()}

    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumassetsresource',
        ),
    )
    result = assert_proper_response_with_result(response)
    expected_tokens = INITIAL_EXPECTED_TOKENS.copy()
    expected_tokens[0].name = new_name
    expected_tokens[0].symbol = new_symbol
    assert result == [x.serialize() for x in expected_tokens]

    # test that editing an non existing address is handled properly
    non_existing_token = INITIAL_TOKENS[0].serialize()
    non_existing_address = make_ethereum_address()
    non_existing_token['address'] = non_existing_address
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumassetsresource',
        ),
        json={'token': non_existing_token},
    )
    expected_msg = (
        f'Tried to edit non existing ethereum token with '
        f'address {non_existing_address}',
    )
    assert_error_response(
        response=response,
        contained_in_msg=expected_msg,
        status_code=HTTPStatus.CONFLICT,
    )
    # and that same tokens as before are in the DB
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumassetsresource',
        ),
    )
    result = assert_proper_response_with_result(response)
    assert result == [x.serialize() for x in expected_tokens]


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('start_with_logged_in_user', [False])
@pytest.mark.parametrize('custom_ethereum_tokens', [INITIAL_TOKENS])
def test_deleting_custom_tokens(rotkehlchen_api_server):
    """Test that the endpoint for deleting a custom ethereum token works"""
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumassetsresource',
        ),
        json={'address': INITIAL_TOKENS[1].address},
    )
    result = assert_proper_response_with_result(response)
    assert result is True

    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumassetsresource',
        ),
    )
    result = assert_proper_response_with_result(response)
    expected_tokens = INITIAL_EXPECTED_TOKENS[:-1]
    assert result == [x.serialize() for x in expected_tokens]
    # also check the mapping for the underlying still tokens exists
    cursor = GlobalDBHandler()._conn.cursor()
    result = cursor.execute('SELECT COUNT(*) from underlying_tokens_list').fetchone()[0]
    assert result == 3

    # test that deleting an non existing address is handled properly
    non_existing_address = make_ethereum_address()
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumassetsresource',
        ),
        json={'address': non_existing_address},
    )
    expected_msg = (
        f'Tried to delete ethereum token with address {non_existing_address} '
        f'but it was not found in the DB',
    )
    assert_error_response(
        response=response,
        contained_in_msg=expected_msg,
        status_code=HTTPStatus.CONFLICT,
    )
    # and that same tokens as before are in the DB
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumassetsresource',
        ),
    )
    result = assert_proper_response_with_result(response)
    assert result == [x.serialize() for x in expected_tokens]

    # now test that deleting the token with underlying tokens works
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumassetsresource',
        ),
        json={'address': INITIAL_TOKENS[0].address},
    )
    result = assert_proper_response_with_result(response)
    assert result is True
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumassetsresource',
        ),
    )
    result = assert_proper_response_with_result(response)
    expected_tokens = INITIAL_EXPECTED_TOKENS[1:-1]
    assert result == [x.serialize() for x in expected_tokens]
    # and removes the mapping of all underlying tokens
    result = cursor.execute('SELECT COUNT(*) from underlying_tokens_list').fetchone()[0]
    assert result == 0
