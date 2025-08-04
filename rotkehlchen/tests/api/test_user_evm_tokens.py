from copy import deepcopy
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

import pytest
import requests

from rotkehlchen.accounting.structures.balance import BalanceType
from rotkehlchen.assets.asset import Asset, EvmToken, UnderlyingToken
from rotkehlchen.balances.manual import ManuallyTrackedBalance
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_BAT
from rotkehlchen.constants.resolver import (
    ethaddress_to_identifier,
    evm_address_to_identifier,
)
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response,
    assert_proper_sync_response_with_result,
)
from rotkehlchen.tests.utils.constants import A_MKR
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.tests.utils.globaldb import (
    USER_TOKEN3,
    create_initial_expected_globaldb_test_tokens,
    create_initial_globaldb_test_tokens,
    underlying_address1,
    underlying_address2,
    underlying_address3,
    underlying_address4,
    user_token_address1,
)
from rotkehlchen.types import ChainID, Location, TokenKind

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer


def assert_token_entry_exists_in_result(
        result: list[dict[str, Any]],
        expected_result: list[dict[str, Any]]) -> None:
    """Make sure token entry exists in result.

    We append the identifier to each entry since it's returned
    """
    for entry in expected_result:
        assert entry in result


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('generatable_user_ethereum_tokens', [True])
@pytest.mark.parametrize('user_ethereum_tokens', [create_initial_globaldb_test_tokens])
def test_query_user_tokens(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that using the query user ethereum tokens endpoint works"""
    expected_tokens = create_initial_expected_globaldb_test_tokens()
    # Test querying by address
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json={'address': user_token_address1, 'evm_chain': ChainID.ETHEREUM.to_name()},
    )
    result: Any = assert_proper_sync_response_with_result(response)['entries'][0]
    expected_result = expected_tokens[0].to_dict()
    expected_result['identifier'] = ethaddress_to_identifier(user_token_address1)
    assert result == expected_result

    # Test querying all
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json={'asset_type': 'evm token'},
    )
    result = assert_proper_sync_response_with_result(response)['entries']
    expected_result_2 = [x.to_dict() for x in expected_tokens]
    assert_token_entry_exists_in_result(result, expected_result_2)
    # This check is to make sure the sqlite query works correctly and queries only for tokens
    assert all(x['address'] is not None for x in result), 'All returned tokens should have address'

    # test that querying an unknown address for a token is properly handled
    unknown_address = make_evm_address()
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json={'address': unknown_address, 'evm_chain': ChainID.ETHEREUM.to_name()},
    )
    result = assert_proper_sync_response_with_result(response)
    assert len(result['entries']) == 0


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('start_with_logged_in_user', [True])
@pytest.mark.parametrize('generatable_user_ethereum_tokens', [True])
@pytest.mark.parametrize('user_ethereum_tokens', [create_initial_globaldb_test_tokens])
@pytest.mark.parametrize('coingecko_cache_coinlist', [{
    'internet-computer': {'symbol': 'ICP', 'name': 'Internet computer'},
}])
@pytest.mark.parametrize('cryptocompare_cache_coinlist', [{'ICP': {}}])
def test_adding_user_tokens(
        rotkehlchen_api_server: 'APIServer',
        cache_coinlist: list[dict[str, dict]],
) -> None:  # pylint: disable=unused-argument
    """Test that the endpoint for adding a user ethereum token works"""
    initial_tokens = create_initial_globaldb_test_tokens()
    expected_tokens = create_initial_expected_globaldb_test_tokens()
    serialized_token = USER_TOKEN3.to_dict()
    del serialized_token['identifier']
    del serialized_token['forked']
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=serialized_token,
    )
    result = assert_proper_sync_response_with_result(response)
    assert result == {'identifier': USER_TOKEN3.identifier}

    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json={'asset_type': 'evm token'},
    )
    result = assert_proper_sync_response_with_result(response)['entries']
    expected_tokens = expected_tokens.copy() + [
        USER_TOKEN3,
        EvmToken.initialize(
            address=underlying_address4,
            chain_id=ChainID.ETHEREUM,
            token_kind=TokenKind.ERC20,
        ),
    ]
    expected_result = [x.to_dict() for x in expected_tokens]
    assert_token_entry_exists_in_result(result, expected_result)

    # test that adding an already existing address is handled properly
    serialized_token = initial_tokens[1].to_dict()
    del serialized_token['identifier']
    del serialized_token['forked']
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=serialized_token,
    )
    expected_msg = (
        f'Ethereum token with address {initial_tokens[1].evm_address} already '
        f'exists in the DB',
    )
    assert_error_response(
        response=response,
        contained_in_msg=expected_msg,
        status_code=HTTPStatus.CONFLICT,
    )

    # also test that the addition of underlying tokens has created proper asset entries for them
    with GlobalDBHandler().conn.read_ctx() as cursor:
        result = cursor.execute(
            'SELECT COUNT(*) from assets WHERE identifier IN (?, ?, ?, ?)',
            [ethaddress_to_identifier(x) for x in [underlying_address1, underlying_address2, underlying_address3, underlying_address4]],  # noqa: E501
        ).fetchone()[0]
        assert result == 4
        result = cursor.execute(
            'SELECT COUNT(*) from evm_tokens WHERE address IN (?, ?, ?, ?)',
            (underlying_address1, underlying_address2, underlying_address3, underlying_address4),
        ).fetchone()[0]
        assert result == 4

    # now test that adding a token with underlying tokens adding up to more than 100% is caught
    bad_token: EvmToken = EvmToken.initialize(
        address=make_evm_address(),
        chain_id=ChainID.ETHEREUM,
        token_kind=TokenKind.ERC20,
        decimals=18,
        name='foo',
        symbol='BBB',
        underlying_tokens=[
            UnderlyingToken(address=make_evm_address(), weight=FVal('0.5055'), token_kind=TokenKind.ERC20),  # noqa: E501
            UnderlyingToken(address=make_evm_address(), weight=FVal('0.7055'), token_kind=TokenKind.ERC20),  # noqa: E501
        ],
    )
    serialized_token = bad_token.to_dict()
    del serialized_token['identifier']
    del serialized_token['forked']
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=serialized_token,
    )
    expected_msg = (
        f'The sum of underlying token weights for {bad_token.evm_address} is '
        f'121.1000 and exceeds 100%',
    )
    assert_error_response(
        response=response,
        contained_in_msg=expected_msg,
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # and test that adding a token with underlying tokens adding up to less than 100% is caught
    bad_token = EvmToken.initialize(
        address=make_evm_address(),
        chain_id=ChainID.ETHEREUM,
        token_kind=TokenKind.ERC20,
        decimals=18,
        name='foo',
        symbol='BBB',
        underlying_tokens=[
            UnderlyingToken(address=make_evm_address(), weight=FVal('0.1055'), token_kind=TokenKind.ERC20),  # noqa: E501
            UnderlyingToken(address=make_evm_address(), weight=FVal('0.2055'), token_kind=TokenKind.ERC20),  # noqa: E501
        ],
    )
    serialized_token = bad_token.to_dict()
    del serialized_token['identifier']
    del serialized_token['forked']
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=serialized_token,
    )
    expected_msg = (
        f'The sum of underlying token weights for {bad_token.evm_address} is '
        f'31.1000 and does not add up to 100%',
    )
    assert_error_response(
        response=response,
        contained_in_msg=expected_msg,
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # and test that adding a token with empty list of underlying tokens and not null is an error
    bad_token = EvmToken.initialize(
        address=make_evm_address(),
        chain_id=ChainID.ETHEREUM,
        token_kind=TokenKind.ERC20,
        decimals=18,
        name='foo',
        symbol='BBB',
        underlying_tokens=[],
    )
    serialized_bad_token = bad_token.to_dict()
    del serialized_bad_token['identifier']
    del serialized_bad_token['forked']
    serialized_bad_token['underlying_tokens'] = []
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=serialized_bad_token,
    )
    assert_error_response(
        response=response,
        contained_in_msg='{"underlying_tokens": ["List cant be empty"]}',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # test that adding invalid coingecko fails
    bad_identifier = 'INVALIDID'
    bad_token_2 = {
        'asset_type': 'evm token',
        'address': make_evm_address(),
        'evm_chain': 'ethereum',
        'token_kind': 'erc20',
        'decimals': 18,
        'name': 'Bad token',
        'symbol': 'NAUGHTY',
        'coingecko': bad_identifier,
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=bad_token_2,
    )
    assert_error_response(
        response=response,
        contained_in_msg=f'Given coingecko identifier {bad_identifier} is not valid',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # test that adding invalid cryptocompare fails
    bad_token_2['cryptocompare'] = bad_identifier
    bad_token_2['coingecko'] = None
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=bad_token_2,
    )
    assert_error_response(
        response=response,
        contained_in_msg=f'Given cryptocompare identifier {bad_identifier} is not valid',
        status_code=HTTPStatus.BAD_REQUEST,
    )


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('start_with_logged_in_user', [True])
@pytest.mark.parametrize('generatable_user_ethereum_tokens', [True])
@pytest.mark.parametrize('user_ethereum_tokens', [create_initial_globaldb_test_tokens])
@pytest.mark.parametrize('coingecko_cache_coinlist', [{
    'internet-computer': {'symbol': 'ICP', 'name': 'Internet computer'},
}])
@pytest.mark.parametrize('cryptocompare_cache_coinlist', [{'ICP': {}}])
def test_editing_user_tokens(
        rotkehlchen_api_server: 'APIServer',
        cache_coinlist: list[dict[str, dict]],
) -> None:  # pylint: disable=unused-argument
    """Test that the endpoint for editing a user ethereum token works"""
    expected_tokens = create_initial_expected_globaldb_test_tokens()
    new_token: dict[str, Any] = expected_tokens[0].to_dict()
    del new_token['identifier']
    del new_token['forked']
    new_name = 'Edited token'
    new_symbol = 'ESMBL'
    new_protocol = 'curve'
    new_swapped_for = A_BAT.identifier
    new_token['name'] = new_name
    new_token['symbol'] = new_symbol
    new_token['swapped_for'] = new_swapped_for
    new_token['protocol'] = new_protocol
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=new_token,
    )
    assert_proper_response(response)

    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json={'asset_type': 'evm token'},
    )
    result = assert_proper_sync_response_with_result(response)['entries']
    expected_tokens = deepcopy(expected_tokens)
    object.__setattr__(expected_tokens[0], 'name', new_name)
    object.__setattr__(expected_tokens[0], 'symbol', new_symbol)
    object.__setattr__(expected_tokens[0], 'protocol', new_protocol)
    object.__setattr__(expected_tokens[0], 'swapped_for', A_BAT)
    expected_result = [x.to_dict() for x in expected_tokens]
    assert_token_entry_exists_in_result(result, expected_result)

    # test that editing an non existing address is handled properly
    non_existing_token = expected_tokens[0].to_dict()
    del non_existing_token['identifier']
    del non_existing_token['forked']
    non_existing_address = make_evm_address()
    non_existing_token['address'] = non_existing_address
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=non_existing_token,
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
    bad_token = new_token.copy()
    bad_identifier = 'INVALIDID'
    bad_token['coingecko'] = bad_identifier
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=bad_token,
    )
    assert_error_response(
        response=response,
        contained_in_msg=f'Given coingecko identifier {bad_identifier} is not valid',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # test that editing with an invalid cryptocompare identifier is handled
    bad_token = new_token.copy()
    bad_identifier = 'INVALIDID'
    bad_token['cryptocompare'] = bad_identifier
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=bad_token,
    )
    assert_error_response(
        response=response,
        contained_in_msg=f'Given cryptocompare identifier {bad_identifier} is not valid',
        status_code=HTTPStatus.BAD_REQUEST,
    )


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('start_with_logged_in_user', [True])
@pytest.mark.parametrize('generatable_user_ethereum_tokens', [True])
@pytest.mark.parametrize('user_ethereum_tokens', [create_initial_globaldb_test_tokens])
def test_deleting_user_tokens(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that the endpoint for deleting a user ethereum token works"""
    initial_tokens = create_initial_globaldb_test_tokens()
    initial_expected_tokens: list[EvmToken] = create_initial_expected_globaldb_test_tokens()
    token0_id = ethaddress_to_identifier(initial_tokens[0].evm_address)
    token1_id = ethaddress_to_identifier(initial_tokens[1].evm_address)
    underlying1_id = ethaddress_to_identifier(underlying_address1)
    underlying2_id = ethaddress_to_identifier(underlying_address2)
    underlying3_id = ethaddress_to_identifier(underlying_address3)
    with GlobalDBHandler().conn.read_ctx() as cursor:
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
            'allassetsresource',
        ),
        json={'identifier': initial_tokens[1].identifier},
    )
    assert_proper_response(response)

    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json={'asset_type': 'evm token'},
    )
    result = assert_proper_sync_response_with_result(response)['entries']
    expected_tokens = initial_expected_tokens[:-1]
    expected_result = [x.to_dict() for x in expected_tokens]
    assert_token_entry_exists_in_result(result, expected_result)
    # also check the mapping for the underlying still tokens exists
    with GlobalDBHandler().conn.read_ctx() as cursor:
        result = cursor.execute('SELECT COUNT(*) from underlying_tokens_list').fetchone()[0]
        assert result == initial_underlying_num, 'check underlying tokens mapping is unchanged'

    # test that deleting a non existing address is handled properly
    non_existent_address = make_evm_address()
    non_existent_identifier = evm_address_to_identifier(
        address=non_existent_address,
        chain_id=ChainID.ETHEREUM,
        token_type=TokenKind.ERC20,
    )
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json={'identifier': non_existent_identifier},
    )
    expected_msg = (
        f'Tried to delete asset with identifier {non_existent_identifier} '
        f'but it was not found in the DB'
    )
    assert_error_response(
        response=response,
        contained_in_msg=expected_msg,
        status_code=HTTPStatus.CONFLICT,
    )

    # test that trying to delete an underlying token that exists in a mapping
    # of another token is handled correctly, and it works.
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json={'identifier': evm_address_to_identifier(
            address=underlying_address1,
            chain_id=ChainID.ETHEREUM,
            token_type=TokenKind.ERC20,
        )},
    )
    assert_proper_response(response)

    # Check that the initial token of the test has MKR as swapped for token
    # this is just a sanity check as the fixture initialization should take care of it
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json={'address': initial_tokens[0].evm_address, 'evm_chain': ChainID.ETHEREUM.to_name()},
    )
    result = assert_proper_sync_response_with_result(response)['entries'][0]
    assert result['swapped_for'] == A_MKR.identifier

    # test that trying to delete a token (MKR) that is used as swapped_for
    # of another token is handled correctly
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json={'identifier': A_MKR.identifier},
    )
    assert_proper_response(response)
    # Check that with the MKR deletion `swapped_for` was set to null
    with GlobalDBHandler().conn.read_ctx() as cursor:
        new_swapped_for = cursor.execute('SELECT swapped_for FROM common_asset_details WHERE identifier = ?', (token0_id,)).fetchone()  # noqa: E501
        assert new_swapped_for is not None and new_swapped_for[0] is None

    # now test that deleting the token with underlying tokens works
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json={'identifier': initial_tokens[0].identifier},
    )
    assert_proper_response(response)

    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json={'asset_type': 'evm token'},
    )
    result = assert_proper_sync_response_with_result(response)['entries']
    expected_tokens = initial_expected_tokens[2:-1]
    expected_result = [x.to_dict() for x in expected_tokens]
    assert_token_entry_exists_in_result(result, expected_result)
    # and removes the mapping of all underlying tokens
    result = cursor.execute('SELECT COUNT(*) from underlying_tokens_list').fetchone()[0]
    assert result == initial_underlying_num - 7
    # and that the equivalent asset entries were also deleted
    with GlobalDBHandler().conn.read_ctx() as cursor:
        result = cursor.execute(
            'SELECT COUNT(*) from assets WHERE identifier IN (?, ?)',
            (token0_id, token1_id),
        ).fetchone()[0]
        assert result == 0


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('start_with_logged_in_user', [True])
@pytest.mark.parametrize('generatable_user_ethereum_tokens', [True])
@pytest.mark.parametrize('user_ethereum_tokens', [create_initial_globaldb_test_tokens])
def test_user_tokens_delete_guard(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that deleting an owned ethereum token is guarded against"""
    expected_tokens: list[EvmToken] = create_initial_expected_globaldb_test_tokens()
    user_db = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    token0_id = ethaddress_to_identifier(expected_tokens[0].evm_address)
    with user_db.user_write() as cursor:
        user_db.add_manually_tracked_balances(cursor, [ManuallyTrackedBalance(
            identifier=-1,
            asset=Asset(token0_id),
            label='manual1',
            amount=ONE,
            location=Location.EXTERNAL,
            tags=None,
            balance_type=BalanceType.ASSET,
        )])

    # Try to delete the token and see it fails because a user owns it
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json={'identifier': expected_tokens[0].identifier},
    )
    expected_msg = 'Failed to delete asset with id'
    assert_error_response(
        response=response,
        contained_in_msg=expected_msg,
        status_code=HTTPStatus.CONFLICT,
    )


def test_add_non_ethereum_token(rotkehlchen_api_server: 'APIServer') -> None:
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json={
            'asset_type': 'evm token',
            'name': 'Some random name',
            'symbol': 'XYZ',
            'cryptocompare': None,
            'coingecko': None,
            'started': 1599646888,
            'swapped_for': None,
            'address': '0xC88eA7a5df3A7BA59C72393C5b2dc2CE260ff04D',
            'evm_chain': 'binance_sc',  # important that is not `ethereum` here
            'token_kind': 'erc20',
            'decimals': 18,
            'protocol': 'my-own-protocol',
            'underlying_tokens': None,
        },
    )
    identifier = assert_proper_sync_response_with_result(response)['identifier']
    assert identifier == 'eip155:56/erc20:0xC88eA7a5df3A7BA59C72393C5b2dc2CE260ff04D'
    token = EvmToken(identifier)
    assert token.name == 'Some random name'
    assert token.symbol == 'XYZ'
    assert token.chain_id == ChainID.BINANCE_SC
    assert token.protocol == 'my-own-protocol'


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('coingecko_cache_coinlist', [{
    'blackpool-token': {'symbol': 'BPT', 'name': 'Blackpool token'},
}])
def test_adding_evm_token_with_underlying_token(
        rotkehlchen_api_server: 'APIServer',
        cache_coinlist: list[dict[str, dict]],
) -> None:  # pylint: disable=unused-argument
    """
    Test that the adding an evm token with underlying tokens is correctly processed by the API
    """
    token_address = string_to_evm_address('0xD2F574637898526FCddfb3D487cc73c957Fa0268')
    token_identifier = evm_address_to_identifier(
        address=token_address,
        chain_id=ChainID.ETHEREUM,
        token_type=TokenKind.ERC20,
    )
    swapped_for = evm_address_to_identifier(
        address='0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
        chain_id=ChainID.ETHEREUM,
        token_type=TokenKind.ERC20,
    )
    payload = {
        'asset_type': 'evm token',
        'address': token_address,
        'name': 'my balancer token',
        'symbol': 'BPT',
        'decimals': 18,
        'coingecko': 'blackpool-token',
        'cryptocompare': None,
        'underlying_tokens': [
            {
                'address': '0xB2FdD60AD80ca7bA89B9BAb3b5336c2601C020b4',
                'token_kind': 'erc20',
                'weight': '50',
            },
            {
                'address': '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
                'token_kind': 'erc20',
                'weight': '50',
            },
        ],
        'evm_chain': 'ethereum',
        'token_kind': 'erc20',
        'protocol': 'balancer',
        'swapped_for': swapped_for,
        'started': 10,
    }
    # also add a token with the similar name to test pagination
    new_token_address = make_evm_address()
    underlying_token_1 = make_evm_address()
    underlying_token_2 = make_evm_address()
    bp_token_2 = EvmToken.initialize(
        name='my balancer token b',
        symbol='BPT',
        address=new_token_address,
        chain_id=ChainID.ETHEREUM,
        token_kind=TokenKind.ERC20,
        underlying_tokens=[
            UnderlyingToken(
                address=underlying_token_1,
                weight=FVal('0.5'),
                token_kind=TokenKind.ERC20,
            ),
            UnderlyingToken(
                address=underlying_token_2,
                weight=FVal('0.5'),
                token_kind=TokenKind.ERC20,
            ),
        ],
    )
    GlobalDBHandler.add_asset(bp_token_2)
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=payload,
    )
    result = assert_proper_sync_response_with_result(response)
    assert result['identifier'] == token_identifier

    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json={
            'identifiers': [token_identifier],
        },
    )
    result = assert_proper_sync_response_with_result(response)
    underlying_tokens = [
        {
            'address': '0xB2FdD60AD80ca7bA89B9BAb3b5336c2601C020b4',
            'token_kind': 'erc20',
            'weight': '50.0',
        },
        {
            'address': '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
            'token_kind': 'erc20',
            'weight': '50.0',
        },
    ]
    expected_result = [
        {
            'identifier': token_identifier,
            'asset_type': 'evm token',
            'name': 'my balancer token',
            'address': token_address,
            'evm_chain': 'ethereum',
            'token_kind': 'erc20',
            'decimals': 18,
            'underlying_tokens': underlying_tokens,
            'protocol': 'balancer',
            'symbol': 'BPT',
            'started': 10,
            'swapped_for': swapped_for,
            'forked': None,
            'cryptocompare': None,
            'coingecko': 'blackpool-token',
        },
    ]
    assert result['entries'] == expected_result

    # Check that pagination with underlying tokens returns the correct result
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json={
            'name': 'my balancer token',
            'limit': 2,
        },
    )
    result = assert_proper_sync_response_with_result(response)
    assert result['entries_found'] == 2
    assert result['entries'][1]['underlying_tokens'] == underlying_tokens
    assert len(result['entries'][0]['underlying_tokens']) == 2

    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json={
            'name': 'my balancer token',
            'limit': 1,
            'offset': 1,
            'order_by_attributes': ['name'],
            'ascending': [True],
        },
    )
    result = assert_proper_sync_response_with_result(response)
    assert result['entries_found'] == 2
    assert result['entries'][0]['underlying_tokens'] == [
        {
            'address': underlying_token_1,
            'token_kind': 'erc20',
            'weight': '50.0',
        },
        {
            'address': underlying_token_2,
            'token_kind': 'erc20',
            'weight': '50.0',
        },
    ]
