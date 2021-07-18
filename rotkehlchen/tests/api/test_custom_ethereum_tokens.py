from copy import deepcopy
from http import HTTPStatus
from typing import Any, Dict, List

import pytest
import requests

from rotkehlchen.assets.asset import Asset, EthereumToken, UnderlyingToken
from rotkehlchen.balances.manual import ManuallyTrackedBalance
from rotkehlchen.constants.assets import A_BAT
from rotkehlchen.constants.resolver import ETHEREUM_DIRECTIVE
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response_with_result,
)
from rotkehlchen.tests.utils.constants import A_MKR
from rotkehlchen.tests.utils.factories import make_ethereum_address
from rotkehlchen.tests.utils.globaldb import (
    CUSTOM_TOKEN3,
    INITIAL_EXPECTED_TOKENS,
    INITIAL_TOKENS,
    custom_address1,
    underlying_address1,
    underlying_address2,
    underlying_address3,
    underlying_address4,
)
from rotkehlchen.typing import Location


def assert_token_entry_exists_in_result(
        result: List[Dict[str, Any]],
        expected_result: List[Dict[str, Any]]):
    """Make sure token entry exists in result.

    We append the identifier to each entry since it's returned
    """
    for entry in expected_result:
        entry['identifier'] = ETHEREUM_DIRECTIVE + entry['address']
        assert entry in result


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('start_with_logged_in_user', [False])
@pytest.mark.parametrize('custom_ethereum_tokens', [INITIAL_TOKENS])
def test_query_custom_tokens(rotkehlchen_api_server):
    """Test that using the query custom ethereum tokens endpoint works"""
    # Test querying by address
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumassetsresource',
        ),
        json={'address': custom_address1},
    )
    result = assert_proper_response_with_result(response)
    expected_result = INITIAL_TOKENS[0].serialize_all_info()
    expected_result['identifier'] = ETHEREUM_DIRECTIVE + custom_address1
    assert result == expected_result

    # Test querying all
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumassetsresource',
        ),
    )
    result = assert_proper_response_with_result(response)
    expected_result = [x.serialize_all_info() for x in INITIAL_EXPECTED_TOKENS]
    assert_token_entry_exists_in_result(result, expected_result)
    # This check is to make sure the sqlite query works correctly and queries only for tokens
    assert all(x['address'] is not None for x in result), 'All returned tokens should have address'

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
@pytest.mark.parametrize('start_with_logged_in_user', [True])
@pytest.mark.parametrize('custom_ethereum_tokens', [INITIAL_TOKENS])
def test_adding_custom_tokens(rotkehlchen_api_server):
    """Test that the endpoint for adding a custom ethereum token works"""
    serialized_token = CUSTOM_TOKEN3.serialize_all_info()
    del serialized_token['identifier']
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumassetsresource',
        ),
        json={'token': serialized_token},
    )
    result = assert_proper_response_with_result(response)
    assert result == {'identifier': ETHEREUM_DIRECTIVE + CUSTOM_TOKEN3.ethereum_address}

    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumassetsresource',
        ),
    )
    result = assert_proper_response_with_result(response)
    expected_tokens = INITIAL_EXPECTED_TOKENS.copy() + [
        CUSTOM_TOKEN3,
        EthereumToken.initialize(address=underlying_address4),
    ]
    expected_result = [x.serialize_all_info() for x in expected_tokens]
    assert_token_entry_exists_in_result(result, expected_result)

    # test that adding an already existing address is handled properly
    serialized_token = INITIAL_TOKENS[1].serialize_all_info()
    del serialized_token['identifier']
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumassetsresource',
        ),
        json={'token': serialized_token},
    )
    expected_msg = (
        f'Ethereum token with address {INITIAL_TOKENS[1].ethereum_address} already '
        f'exists in the DB',
    )
    assert_error_response(
        response=response,
        contained_in_msg=expected_msg,
        status_code=HTTPStatus.CONFLICT,
    )

    # also test that the addition of underlying tokens has created proper asset entires for them
    cursor = GlobalDBHandler()._conn.cursor()
    result = cursor.execute(
        'SELECT COUNT(*) from assets WHERE identifier IN (?, ?, ?, ?)',
        [ETHEREUM_DIRECTIVE + x for x in [underlying_address1, underlying_address2, underlying_address3, underlying_address4]],  # noqa: E501
    ).fetchone()[0]
    assert result == 4
    result = cursor.execute(
        'SELECT COUNT(*) from ethereum_tokens WHERE address IN (?, ?, ?, ?)',
        (underlying_address1, underlying_address2, underlying_address3, underlying_address4),  # noqa: E501
    ).fetchone()[0]
    assert result == 4

    # now test that adding a token with underlying tokens adding up to more than 100% is caught
    bad_token = EthereumToken.initialize(
        address=make_ethereum_address(),
        decimals=18,
        name='foo',
        symbol='BBB',
        underlying_tokens=[
            UnderlyingToken(address=make_ethereum_address(), weight=FVal('0.5055')),
            UnderlyingToken(address=make_ethereum_address(), weight=FVal('0.7055')),
        ],
    )
    serialized_token = bad_token.serialize_all_info()
    del serialized_token['identifier']
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumassetsresource',
        ),
        json={'token': serialized_token},
    )
    expected_msg = (
        f'The sum of underlying token weights for {bad_token.ethereum_address} is '
        f'121.1000 and exceeds 100%'
    )
    assert_error_response(
        response=response,
        contained_in_msg=expected_msg,
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # and test that adding a token with underlying tokens adding up to less than 100% is caught
    bad_token = EthereumToken.initialize(
        address=make_ethereum_address(),
        decimals=18,
        name='foo',
        symbol='BBB',
        underlying_tokens=[
            UnderlyingToken(address=make_ethereum_address(), weight=FVal('0.1055')),
            UnderlyingToken(address=make_ethereum_address(), weight=FVal('0.2055')),
        ],
    )
    serialized_token = bad_token.serialize_all_info()
    del serialized_token['identifier']
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumassetsresource',
        ),
        json={'token': serialized_token},
    )
    expected_msg = (
        f'The sum of underlying token weights for {bad_token.ethereum_address} is '
        f'31.1000 and does not add up to 100%'
    )
    assert_error_response(
        response=response,
        contained_in_msg=expected_msg,
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # and test that adding a token with empty list of underlying tokens and not null is an error
    bad_token = EthereumToken.initialize(
        address=make_ethereum_address(),
        decimals=18,
        name='foo',
        symbol='BBB',
        underlying_tokens=[],
    )
    serialized_bad_token = bad_token.serialize_all_info()
    del serialized_bad_token['identifier']
    serialized_bad_token['underlying_tokens'] = []
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumassetsresource',
        ),
        json={'token': serialized_bad_token},
    )
    expected_msg = (
        f'Gave an empty list for underlying tokens of {bad_token.ethereum_address}'
    )
    assert_error_response(
        response=response,
        contained_in_msg=expected_msg,
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # test that adding invalid coingecko fails
    bad_identifier = 'INVALIDID'
    bad_token = {
        'address': make_ethereum_address(),
        'decimals': 18,
        'name': 'Bad token',
        'symbol': 'NAUGHTY',
        'coingecko': bad_identifier,
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumassetsresource',
        ),
        json={'token': bad_token},
    )
    assert_error_response(
        response=response,
        contained_in_msg=f'Given coingecko identifier {bad_identifier} is not valid',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # test that adding invalid cryptocompare fails
    bad_token['cryptocompare'] = bad_identifier
    bad_token['coingecko'] = None
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumassetsresource',
        ),
        json={'token': bad_token},
    )
    assert_error_response(
        response=response,
        contained_in_msg=f'Given cryptocompare identifier {bad_identifier} isnt valid',
        status_code=HTTPStatus.BAD_REQUEST,
    )


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('start_with_logged_in_user', [True])
@pytest.mark.parametrize('custom_ethereum_tokens', [INITIAL_TOKENS])
def test_editing_custom_tokens(rotkehlchen_api_server):
    """Test that the endpoint for editing a custom ethereum token works"""
    new_token1 = INITIAL_TOKENS[0].serialize_all_info()
    del new_token1['identifier']
    new_name = 'Edited token'
    new_symbol = 'ESMBL'
    new_protocol = 'curve'
    new_swapped_for = A_BAT.identifier
    new_token1['name'] = new_name
    new_token1['symbol'] = new_symbol
    new_token1['swapped_for'] = new_swapped_for
    new_token1['protocol'] = new_protocol
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumassetsresource',
        ),
        json={'token': new_token1},
    )
    result = assert_proper_response_with_result(response)
    token0_id = ETHEREUM_DIRECTIVE + INITIAL_TOKENS[0].ethereum_address
    assert result == {'identifier': token0_id}

    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumassetsresource',
        ),
    )
    result = assert_proper_response_with_result(response)
    expected_tokens = deepcopy(INITIAL_EXPECTED_TOKENS)
    object.__setattr__(expected_tokens[0], 'name', new_name)
    object.__setattr__(expected_tokens[0], 'symbol', new_symbol)
    object.__setattr__(expected_tokens[0], 'protocol', new_protocol)
    object.__setattr__(expected_tokens[0], 'swapped_for', A_BAT)
    expected_result = [x.serialize_all_info() for x in expected_tokens]
    assert_token_entry_exists_in_result(result, expected_result)

    # test that editing an non existing address is handled properly
    non_existing_token = INITIAL_TOKENS[0].serialize_all_info()
    del non_existing_token['identifier']
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

    # test that editing with an invalid coingecko identifier is handled
    bad_token = new_token1.copy()
    bad_identifier = 'INVALIDID'
    bad_token['coingecko'] = bad_identifier
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumassetsresource',
        ),
        json={'token': bad_token},
    )
    assert_error_response(
        response=response,
        contained_in_msg=f'Given coingecko identifier {bad_identifier} is not valid',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # test that editing with an invalid cryptocompare identifier is handled
    bad_token = new_token1.copy()
    bad_identifier = 'INVALIDID'
    bad_token['cryptocompare'] = bad_identifier
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumassetsresource',
        ),
        json={'token': bad_token},
    )
    assert_error_response(
        response=response,
        contained_in_msg=f'Given cryptocompare identifier {bad_identifier} isnt valid',
        status_code=HTTPStatus.BAD_REQUEST,
    )


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('start_with_logged_in_user', [True])
@pytest.mark.parametrize('custom_ethereum_tokens', [INITIAL_TOKENS])
def test_deleting_custom_tokens(rotkehlchen_api_server):
    """Test that the endpoint for deleting a custom ethereum token works"""
    token0_id = ETHEREUM_DIRECTIVE + INITIAL_TOKENS[0].ethereum_address
    token1_id = ETHEREUM_DIRECTIVE + INITIAL_TOKENS[1].ethereum_address
    underlying1_id = ETHEREUM_DIRECTIVE + underlying_address1
    underlying2_id = ETHEREUM_DIRECTIVE + underlying_address2
    underlying3_id = ETHEREUM_DIRECTIVE + underlying_address3
    cursor = GlobalDBHandler()._conn.cursor()
    initial_underlying_num = cursor.execute('SELECT COUNT(*) from underlying_tokens_list').fetchone()[0]  # noqa: E501

    # Make sure the equivalent assets we will delete exist in the DB
    result = cursor.execute(
        'SELECT COUNT(*) from assets WHERE identifier IN (?, ?, ?, ?, ?)',
        (token0_id, token1_id, underlying1_id, underlying2_id, underlying3_id),
    ).fetchone()[0]
    assert result == 5
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumassetsresource',
        ),
        json={'address': INITIAL_TOKENS[1].ethereum_address},
    )
    result = assert_proper_response_with_result(response)
    assert result == {'identifier': token1_id}

    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumassetsresource',
        ),
    )
    result = assert_proper_response_with_result(response)
    expected_tokens = INITIAL_EXPECTED_TOKENS[:-1]
    expected_result = [x.serialize_all_info() for x in expected_tokens]
    assert_token_entry_exists_in_result(result, expected_result)
    # also check the mapping for the underlying still tokens exists
    result = cursor.execute('SELECT COUNT(*) from underlying_tokens_list').fetchone()[0]
    assert result == initial_underlying_num, 'check underlying tokens mapping is unchanged'  # noqa: E501

    # test that deleting a non existing address is handled properly
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
        f'but it was not found in the DB'
    )
    assert_error_response(
        response=response,
        contained_in_msg=expected_msg,
        status_code=HTTPStatus.CONFLICT,
    )

    # test that trying to delete an underlying token that exists in a mapping
    # of another token is handled correctly
    non_existing_address = make_ethereum_address()
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumassetsresource',
        ),
        json={'address': underlying_address1},
    )
    expected_msg = (
        f'Tried to delete ethereum token with address {underlying_address1} '
        f'but its deletion would violate a constraint so deletion failed'
    )
    assert_error_response(
        response=response,
        contained_in_msg=expected_msg,
        status_code=HTTPStatus.CONFLICT,
    )

    # Check that the initial token of the test has MKR as swapped for token
    # this is just a sanity check as the fixture initialization should take care of it
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumassetsresource',
        ),
        json={'address': INITIAL_TOKENS[0].ethereum_address},
    )
    result = assert_proper_response_with_result(response)
    assert result['swapped_for'] == A_MKR.identifier

    # test that trying to delete a token (MKR) that is used as swapped_for
    # of another token is handled correctly
    non_existing_address = make_ethereum_address()
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumassetsresource',
        ),
        json={'address': A_MKR.ethereum_address},
    )
    expected_msg = (
        f'Tried to delete ethereum token with address {A_MKR.ethereum_address} '
        f'but its deletion would violate a constraint so deletion failed'
    )
    assert_error_response(
        response=response,
        contained_in_msg=expected_msg,
        status_code=HTTPStatus.CONFLICT,
    )

    # now test that deleting the token with underlying tokens works
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumassetsresource',
        ),
        json={'address': INITIAL_TOKENS[0].ethereum_address},
    )
    result = assert_proper_response_with_result(response)
    assert result == {'identifier': token0_id}
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumassetsresource',
        ),
    )
    result = assert_proper_response_with_result(response)
    expected_tokens = INITIAL_EXPECTED_TOKENS[1:-1]
    expected_result = [x.serialize_all_info() for x in expected_tokens]
    assert_token_entry_exists_in_result(result, expected_result)
    # and removes the mapping of all underlying tokens
    result = cursor.execute('SELECT COUNT(*) from underlying_tokens_list').fetchone()[0]
    assert result == initial_underlying_num - 3
    # and that the equivalent asset entries were also deleted
    result = cursor.execute(
        'SELECT COUNT(*) from assets WHERE identifier IN (?, ?)',
        (token0_id, token1_id),
    ).fetchone()[0]
    assert result == 0


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('start_with_logged_in_user', [True])
@pytest.mark.parametrize('custom_ethereum_tokens', [INITIAL_TOKENS])
def test_custom_tokens_delete_guard(rotkehlchen_api_server):
    """Test that deleting an owned ethereum token is guarded against"""
    user_db = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    token0_id = ETHEREUM_DIRECTIVE + INITIAL_TOKENS[0].ethereum_address
    user_db.add_manually_tracked_balances([ManuallyTrackedBalance(
        asset=Asset(token0_id),
        label='manual1',
        amount=FVal(1),
        location=Location.EXTERNAL,
        tags=None,
    )])

    # Try to delete the token and see it fails because a user owns it
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'ethereumassetsresource',
        ),
        json={'address': INITIAL_TOKENS[0].ethereum_address},
    )
    expected_msg = 'Failed to delete asset with id'
    assert_error_response(
        response=response,
        contained_in_msg=expected_msg,
        status_code=HTTPStatus.CONFLICT,
    )
