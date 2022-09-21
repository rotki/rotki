from contextlib import ExitStack
from http import HTTPStatus
from typing import Union
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.accounting.structures.balance import BalanceType
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.balances.manual import ManuallyTrackedBalance
from rotkehlchen.constants.assets import A_EUR
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response,
    assert_proper_response_with_result,
)
from rotkehlchen.tests.utils.constants import A_GNO, A_RDN
from rotkehlchen.tests.utils.factories import UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.tests.utils.rotkehlchen import setup_balances
from rotkehlchen.types import Location

KICK_TOKEN = EvmToken('eip155:1/erc20:0x824a50dF33AC1B41Afc52f4194E2e8356C17C3aC')


def mock_cryptoscamdb_request():
    def mock_requests_get(url, *args, **kwargs):  # pylint: disable=unused-argument
        response = 'Error generating response'
        return MockResponse(200, response)

    return patch('requests.get', side_effect=mock_requests_get)


def assert_asset_result_order(
        data: Union[list, dict],
        is_ascending: bool,
        order_field: str,
) -> None:
    """Asserts the ordering of the result received matches the query provided."""
    last_entry = ''
    result = data.values() if isinstance(data, dict) else data
    for index, entry in enumerate(result):
        if index == 0:
            last_entry = entry[order_field]
            continue
        # the .casefold() is needed because the sorting is case-insensitive
        if is_ascending is True:
            assert entry[order_field].casefold() > last_entry.casefold()
        else:
            assert entry[order_field].casefold() < last_entry.casefold()


@pytest.mark.parametrize('number_of_eth_accounts', [2])
@pytest.mark.parametrize('btc_accounts', [[UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2]])
@pytest.mark.parametrize('added_exchanges', [(Location.BINANCE, Location.POLONIEX)])
def test_query_owned_assets(
        rotkehlchen_api_server_with_exchanges,
        ethereum_accounts,
        btc_accounts,
):
    """Test that using the query all owned assets endpoint works"""
    # Disable caching of query results
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    rotki.chain_manager.cache_ttl_secs = 0
    setup = setup_balances(
        rotki=rotki,
        ethereum_accounts=ethereum_accounts,
        btc_accounts=btc_accounts,
        manually_tracked_balances=[ManuallyTrackedBalance(
            id=-1,
            asset=A_EUR,
            label='My EUR bank',
            amount=FVal('1550'),
            location=Location.BANKS,
            tags=None,
            balance_type=BalanceType.ASSET,
        )],
    )

    # Get all our mocked balances and save them in the DB
    with ExitStack() as stack:
        setup.enter_all_patches(stack)
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                'allbalancesresource',
            ), json={'save_data': True},
        )
    assert_proper_response(response)

    # And now check that the query owned assets endpoint works
    with ExitStack() as stack:
        setup.enter_all_patches(stack)
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                'ownedassetsresource',
            ),
        )
    result = assert_proper_response_with_result(response)
    assert set(result) == {'ETH', 'BTC', 'EUR', A_RDN.identifier}


@pytest.mark.parametrize('perform_migrations_at_unlock', [True])
@pytest.mark.parametrize('data_migration_version', [0])
def test_ignored_assets_modification(rotkehlchen_api_server_with_exchanges):
    """Test that using the ignored assets endpoint to modify the ignored assets list works fine"""
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen

    # add three assets to ignored assets
    kick_token_id = KICK_TOKEN.identifier
    ignored_assets = [A_GNO.identifier, A_RDN.identifier, 'XMR']
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            'ignoredassetsresource',
        ), json={'assets': ignored_assets},
    )
    result = assert_proper_response_with_result(response)
    expected_ignored_assets = set(ignored_assets + [KICK_TOKEN.identifier])
    assert expected_ignored_assets <= set(result)

    with rotki.data.db.conn.read_ctx() as cursor:
        # check they are there
        assert set(rotki.data.db.get_ignored_assets(cursor)) >= expected_ignored_assets
        # Query for ignored assets and check that the response returns them
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                'ignoredassetsresource',
            ),
        )
        result = assert_proper_response_with_result(response)
        assert expected_ignored_assets <= set(result)

        # remove 3 assets from ignored assets
        response = requests.delete(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                'ignoredassetsresource',
            ), json={'assets': [A_GNO.identifier, 'XMR', kick_token_id]},
        )
        assets_after_deletion = {A_RDN.identifier}
        result = assert_proper_response_with_result(response)
        assert assets_after_deletion <= set(result)

        # check that the changes are reflected
        assert set(rotki.data.db.get_ignored_assets(cursor)) >= assets_after_deletion
        # Query for ignored assets and check that the response returns them
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                'ignoredassetsresource',
            ),
        )
        result = assert_proper_response_with_result(response)
        assert assets_after_deletion <= set(result)

        # Fetch remote assets to be ignored
        response = requests.post(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                'ignoredassetsresource',
            ),
        )
        result = assert_proper_response_with_result(response)
        assert result >= 1
        assert len(rotki.data.db.get_ignored_assets(cursor)) > len(assets_after_deletion)

    # Simulate remote error from cryptoscamdb
    with mock_cryptoscamdb_request():
        response = requests.post(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                'ignoredassetsresource',
            ),
        )
        assert response.status_code == HTTPStatus.BAD_GATEWAY


@pytest.mark.parametrize('perform_migrations_at_unlock', [True])
@pytest.mark.parametrize('method', ['put', 'delete'])
@pytest.mark.parametrize('data_migration_version', [0])
def test_ignored_assets_endpoint_errors(rotkehlchen_api_server_with_exchanges, method):
    """Test errors are handled properly at the ignored assets endpoint"""
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen

    # add three assets to ignored assets
    ignored_assets = [A_GNO.identifier, A_RDN.identifier, 'XMR']
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            'ignoredassetsresource',
        ), json={'assets': ignored_assets},
    )
    assert_proper_response(response)

    # Test that omitting the assets argument is an error
    response = getattr(requests, method)(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            'ignoredassetsresource',
        ),
    )
    assert_error_response(
        response=response,
        contained_in_msg='"assets": ["Missing data for required field',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Test that invalid type for assets list is an error
    response = getattr(requests, method)(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            'ignoredassetsresource',
        ), json={'assets': 'foo'},
    )
    assert_error_response(
        response=response,
        contained_in_msg='"assets": ["Not a valid list."',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Test that list with invalid asset is an error
    response = getattr(requests, method)(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            'ignoredassetsresource',
        ), json={'assets': ['notanasset']},
    )
    assert_error_response(
        response=response,
        contained_in_msg='Unknown asset notanasset provided',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Test that list with one valid and one invalid is rejected and not even the
    # valid one is processed
    if method == 'put':
        asset = 'ETH'
    else:
        asset = 'XMR'
    response = getattr(requests, method)(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            'ignoredassetsresource',
        ), json={'assets': [asset, 'notanasset']},
    )
    assert_error_response(
        response=response,
        contained_in_msg='Unknown asset notanasset provided',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # Check that assets did not get modified
    with rotki.data.db.conn.read_ctx() as cursor:
        expected_tokens = set(
            ignored_assets +
            [KICK_TOKEN],
        )
        assert set(rotki.data.db.get_ignored_assets(cursor)) >= expected_tokens

        # Test the adding an already existing asset or removing a non-existing asset is an error
        if method == 'put':
            asset = A_RDN.identifier
            expected_msg = f'{A_RDN.identifier} is already in ignored assets'
        else:
            asset = 'ETH'
            expected_msg = 'ETH is not in ignored assets'
        response = getattr(requests, method)(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                'ignoredassetsresource',
            ), json={'assets': [asset]},
        )
        assert_error_response(
            response=response,
            contained_in_msg=expected_msg,
            status_code=HTTPStatus.CONFLICT,
        )
        # Check that assets did not get modified
        assert set(rotki.data.db.get_ignored_assets(cursor)) >= expected_tokens


def test_get_all_assets(rotkehlchen_api_server):
    """Test that fetching all assets returns a paginated result."""
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json={
            'limit': 20,
            'offset': 0,
            'asset_type': 'fiat',
            'order_by_attributes': ['name'],
            'ascending': [True],
        },
    )
    result = assert_proper_response_with_result(response)
    assert len(result['entries']) <= 20
    assert 'entries_found' in result
    assert 'entries_total' in result
    assert 'entries_limit' in result
    for entry in result['entries'].values():
        assert entry['type'] == 'fiat'
    assert_asset_result_order(data=result['entries'], is_ascending=True, order_field='name')

    # use a different filter
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json={
            'limit': 50,
            'offset': 0,
            'name': 'Uniswap',
            'order_by_attributes': ['symbol'],
            'ascending': [False],
        },
    )
    result = assert_proper_response_with_result(response)
    assert len(result['entries']) <= 50
    assert 'entries_found' in result
    assert 'entries_total' in result
    assert 'entries_limit' in result
    for entry in result['entries'].values():
        assert entry['name'] == 'Uniswap'
    assert_asset_result_order(data=result['entries'], is_ascending=False, order_field='symbol')

    # check that providing multiple order_by_attributes fails
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json={
            'limit': 20,
            'offset': 0,
            'asset_type': 'fiat',
            'order_by_attributes': ['name', 'symbol'],
            'ascending': [True, False],
        },
    )
    assert_error_response(response, contained_in_msg='Multiple fields ordering is not allowed.')


def test_get_assets_mappings(rotkehlchen_api_server):
    """Test that providing a list of asset identifiers, the appropriate assets mappings are returned."""  # noqa: E501
    queried_assets = ('BTC', 'TRY', 'EUR')
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'assetsmappingresource',
        ),
        json={'identifiers': queried_assets},
    )
    result = assert_proper_response_with_result(response)
    assert len(result) == 3
    for identifier in result.keys():
        assert identifier in queried_assets

    # check that providing multiple order_by_attributes fails
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'assetsmappingresource',
        ),
        json={'identifiers': ['BTC', 'TRY', 'invalid']},
    )
    assert_error_response(response, contained_in_msg='One or more of the given identifiers could not be found in the database')  # noqa: E501


def test_search_assets(rotkehlchen_api_server):
    """Test that searching for assets using a keyword works."""
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'assetssearchresource',
        ),
        json={
            'value': 'Bitcoin',
            'search_column': 'name',
            'limit': 50,
            'order_by_attributes': ['name'],
            'ascending': [True],
        },
    )
    result = assert_proper_response_with_result(response)
    assert len(result) <= 50
    for entry in result:
        assert 'bitcoin' in entry['name'].lower()
    assert_asset_result_order(data=result, is_ascending=True, order_field='name')

    # use a different keyword
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'assetssearchresource',
        ),
        json={
            'value': 'eth',
            'search_column': 'symbol',
            'limit': 10,
            'order_by_attributes': ['symbol'],
            'ascending': [False],
        },
    )
    result = assert_proper_response_with_result(response)
    assert len(result) <= 10
    for entry in result:
        assert 'eth' in entry['symbol'].lower()
    assert_asset_result_order(data=result, is_ascending=False, order_field='symbol')

    # check that searching for a non-existent asset returns nothing
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'assetssearchresource',
        ),
        json={
            'value': 'idontexist',
            'search_column': 'name',
            'limit': 50,
            'order_by_attributes': ['name'],
            'ascending': [True],
        },
    )
    result = assert_proper_response_with_result(response)
    assert len(result) == 0

    # search using a column that is not allowed
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'assetssearchresource',
        ),
        json={
            'value': 'idontexist',
            'search_column': 'identifier',
            'limit': 50,
            'order_by_attributes': ['name'],
            'ascending': [True],
        },
    )
    assert_error_response(response, contained_in_msg='Must be one of: name, symbol.')


def test_search_assets_with_levenshtein(rotkehlchen_api_server):
    """Test that searching for assets using a keyword works(levenshtein approach)."""
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'assetssearchlevenshteinresource',
        ),
        json={
            'value': 'Bitcoin',
            'limit': 50,
        },
    )
    result = assert_proper_response_with_result(response)
    assert len(result) <= 50
    for entry in result:
        assert 'bitcoin' in entry['name'].lower() or entry['symbol'].lower()

    # use a different keyword
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'assetssearchresource',
        ),
        json={
            'value': 'eth',
            'search_column': 'symbol',
            'limit': 10,
            'order_by_attributes': ['name'],
            'ascending': [False],
        },
    )
    result = assert_proper_response_with_result(response)
    assert len(result) <= 10
    for entry in result:
        assert 'eth' in entry['symbol'].lower()

    # check that searching for a non-existent asset returns nothing
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'assetssearchlevenshteinresource',
        ),
        json={
            'value': 'idontexist',
            'limit': 50,
        },
    )
    result = assert_proper_response_with_result(response)
    assert len(result) == 0
