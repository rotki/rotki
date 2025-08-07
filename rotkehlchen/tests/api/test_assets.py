from contextlib import ExitStack
from http import HTTPStatus
from typing import Any
from uuid import uuid4

import pytest
import requests
from polyleven import levenshtein

from rotkehlchen.accounting.structures.balance import Balance, BalanceType
from rotkehlchen.api.server import APIServer
from rotkehlchen.assets.asset import CryptoAsset, CustomAsset, EvmToken
from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.assets.types import AssetType
from rotkehlchen.balances.manual import ManuallyTrackedBalance
from rotkehlchen.constants.assets import A_BTC, A_DAI, A_EUR, A_OP, A_SAI, A_USD, A_USDC
from rotkehlchen.constants.misc import DEFAULT_BALANCE_LABEL, ONE
from rotkehlchen.constants.resolver import solana_address_to_identifier
from rotkehlchen.db.custom_assets import DBCustomAssets
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import ModifiableDBSettings
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.cache import (
    globaldb_get_general_cache_values,
    globaldb_set_general_cache_values,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.globaldb.utils import set_token_spam_protocol
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response,
    assert_proper_sync_response_with_result,
)
from rotkehlchen.tests.utils.checks import assert_asset_result_order
from rotkehlchen.tests.utils.constants import A_GNO, A_RDN
from rotkehlchen.tests.utils.database import clean_ignored_assets
from rotkehlchen.tests.utils.factories import (
    UNIT_BTC_ADDRESS1,
    UNIT_BTC_ADDRESS2,
    make_evm_address,
)
from rotkehlchen.tests.utils.rotkehlchen import setup_balances
from rotkehlchen.types import (
    SPAM_PROTOCOL,
    BTCAddress,
    CacheType,
    ChainID,
    ChecksumEvmAddress,
    Location,
    SolanaAddress,
    TimestampMS,
    TokenKind,
)


def assert_substring_in_search_result(
        data: list[dict[str, Any]],
        substring: str,
) -> None:
    """Asserts that a given substring is present in the search result."""
    for entry in data:
        substr_in_name = substr_in_symbol = None
        if entry['name'] is not None:
            substr_in_name = substring.casefold() in entry['name'].casefold()
        if entry['symbol'] is not None:
            substr_in_symbol = substring.casefold() in entry['symbol'].casefold()
        assert substr_in_name or substr_in_symbol, f'no match for {substring}'


def assert_asset_at_top_position(
        asset_id: str,
        max_position_index: int,
        result: list[dict[str, Any]],
) -> None:
    """Asserts that an asset appears at the top of the search results."""
    assert any(asset_id == entry['identifier'] for entry in result)
    for index, entry in enumerate(result):
        if entry['identifier'] == asset_id:
            assert index <= max_position_index


@pytest.mark.parametrize('number_of_eth_accounts', [2])
@pytest.mark.parametrize('btc_accounts', [[UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2]])
@pytest.mark.parametrize('added_exchanges', [(Location.BINANCE, Location.POLONIEX)])
def test_query_owned_assets(
        rotkehlchen_api_server_with_exchanges: APIServer,
        ethereum_accounts: list[ChecksumEvmAddress],
        btc_accounts: list[BTCAddress],
) -> None:
    """Test that using the query all owned assets endpoint works"""
    # Disable caching of query results
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    rotki.chains_aggregator.cache_ttl_secs = 0
    setup = setup_balances(
        rotki=rotki,
        ethereum_accounts=ethereum_accounts,
        btc_accounts=btc_accounts,
        manually_tracked_balances=[ManuallyTrackedBalance(
            identifier=-1,
            asset=A_EUR,
            label='My EUR bank',
            amount=FVal(1550),
            location=Location.BANKS,
            tags=None,
            balance_type=BalanceType.ASSET,
        )],
    )

    db = DBHistoryEvents(rotki.data.db)
    with db.db.user_write() as write_cursor:
        db.add_history_event(
            write_cursor=write_cursor,
            event=HistoryEvent(
                event_identifier='1',
                sequence_index=1,
                timestamp=TimestampMS(1),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.TRADE,
                event_subtype=HistoryEventSubType.RECEIVE,
                asset=A_USDC,
                amount=ONE,
            ),
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
    result = assert_proper_sync_response_with_result(response)
    assert set(result) == {'ETH', 'BTC', 'EUR', A_RDN, A_USDC}


@pytest.mark.parametrize('new_db_unlock_actions', [None])
def test_ignored_assets_modification(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that using the ignored assets endpoint to modify the ignored assets list works fine"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    clean_ignored_assets(rotki.data.db)
    # add three assets to ignored assets
    ignored_assets = [A_GNO.identifier, A_RDN.identifier, 'XMR']
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'ignoredassetsresource',
        ), json={'assets': ignored_assets},
    )
    result = assert_proper_sync_response_with_result(response)
    expected_ignored_assets = set(ignored_assets)
    assert expected_ignored_assets == set(result['successful'])

    with rotki.data.db.conn.read_ctx() as cursor:
        # check they are there
        assert rotki.data.db.get_ignored_asset_ids(cursor) == expected_ignored_assets
        # Query for ignored assets and check that the response returns them
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                'ignoredassetsresource',
            ),
        )
        result = assert_proper_sync_response_with_result(response)
        assert expected_ignored_assets == set(result)

        # remove 2 assets from ignored assets
        response = requests.delete(
            api_url_for(
                rotkehlchen_api_server,
                'ignoredassetsresource',
            ), json={'assets': [A_GNO.identifier, 'XMR']},
        )
        result = assert_proper_sync_response_with_result(response)
        assert set(result['successful']) == {A_GNO.identifier, 'XMR'}
        assert len(result['no_action']) == 0

        # check that the changes are reflected
        assets_after_deletion = {A_RDN.identifier}
        assert rotki.data.db.get_ignored_asset_ids(cursor) == assets_after_deletion
        # Query for ignored assets and check that the response returns them
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                'ignoredassetsresource',
            ),
        )
        result = assert_proper_sync_response_with_result(response)
        assert assets_after_deletion == set(result)


@pytest.mark.parametrize('new_db_unlock_actions', [None])
@pytest.mark.parametrize('method', ['put', 'delete'])
@pytest.mark.parametrize('data_migration_version', [0])
def test_ignored_assets_endpoint_errors(rotkehlchen_api_server: 'APIServer', method: str) -> None:
    """Test errors are handled properly at the ignored assets endpoint"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    # add three assets to ignored assets
    ignored_assets = [A_GNO.identifier, A_RDN.identifier, 'XMR']
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'ignoredassetsresource',
        ), json={'assets': ignored_assets},
    )
    assert_proper_response(response)

    # Test that omitting the assets argument is an error
    response = getattr(requests, method)(
        api_url_for(
            rotkehlchen_api_server,
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
            rotkehlchen_api_server,
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
            rotkehlchen_api_server,
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
    asset = 'ETH' if method == 'put' else 'XMR'
    response = getattr(requests, method)(
        api_url_for(
            rotkehlchen_api_server,
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
        assert rotki.data.db.get_ignored_asset_ids(cursor) >= set(ignored_assets)

        # Test the adding an already existing asset or removing a non-existing asset is an error
        asset = A_RDN.identifier if method == 'put' else 'ETH'
        response = getattr(requests, method)(
            api_url_for(
                rotkehlchen_api_server,
                'ignoredassetsresource',
            ), json={'assets': [asset]},
        )
        result = assert_proper_sync_response_with_result(response)
        assert result == {
            'successful': [],
            'no_action': [asset],
        }
        # Check that assets did not get modified
        assert rotki.data.db.get_ignored_asset_ids(cursor) >= set(ignored_assets)


def test_get_all_assets(rotkehlchen_api_server: 'APIServer') -> None:
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
    result = assert_proper_sync_response_with_result(response)
    assert len(result['entries']) == 20
    assert 'entries_found' in result
    assert 'entries_total' in result
    assert 'entries_limit' in result
    for entry in result['entries']:
        assert entry['asset_type'] == 'fiat'
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
    result = assert_proper_sync_response_with_result(response)
    assert len(result['entries']) == 50
    assert 'entries_found' in result
    assert 'entries_total' in result
    assert 'entries_limit' in result
    for entry in result['entries']:
        assert 'uniswap' in entry['name'].lower()
        if entry['asset_type'] == AssetType.EVM_TOKEN.serialize():
            assert entry['evm_chain'] in [x.to_name() for x in ChainID]
    assert_asset_result_order(data=result['entries'], is_ascending=False, order_field='symbol')

    # test that ignored assets filter works
    with rotkehlchen_api_server.rest_api.rotkehlchen.data.db.user_write() as write_cursor:
        rotkehlchen_api_server.rest_api.rotkehlchen.data.db.add_to_ignored_assets(
            write_cursor=write_cursor,
            asset=A_USD,
        )
        rotkehlchen_api_server.rest_api.rotkehlchen.data.db.add_to_ignored_assets(
            write_cursor=write_cursor,
            asset=A_EUR,
        )
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
            'ignored_assets_handling': 'exclude',
        },
    )
    result = assert_proper_sync_response_with_result(response)
    assert len(result['entries']) == 20
    assert 'entries_found' in result
    assert 'entries_total' in result
    assert 'entries_limit' in result
    for entry in result['entries']:
        assert entry['asset_type'] == 'fiat'
        assert entry['symbol'] not in (A_USD.resolve_to_asset_with_symbol().symbol, A_EUR.resolve_to_asset_with_symbol().symbol)  # noqa: E501
    assert_asset_result_order(data=result['entries'], is_ascending=True, order_field='name')

    # test that user owned assets filter works
    GlobalDBHandler.add_user_owned_assets([A_BTC, A_DAI, A_SAI])
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json={
            'limit': 2,
            'offset': 0,
            'order_by_attributes': ['name'],
            'ascending': [True],
            'show_user_owned_assets_only': True,
        },
    )
    result = assert_proper_sync_response_with_result(response)
    assets_names = {r['name'] for r in result['entries']}
    assets_chain = {r.get('evm_chain', None) for r in result['entries']}
    assert result['entries_found'] == 3
    assert assets_chain.issubset({*[x.to_name() for x in ChainID], None})
    assert A_BTC.resolve_to_asset_with_name_and_type().name in assets_names
    assert A_DAI.resolve_to_asset_with_name_and_type().name in assets_names
    assert A_SAI.resolve_to_asset_with_name_and_type().name not in assets_names
    assert_asset_result_order(data=result['entries'], is_ascending=True, order_field='name')

    # add custom asset and filter results using `custom asset` type.
    db_custom_assets = DBCustomAssets(
        db_handler=rotkehlchen_api_server.rest_api.rotkehlchen.data.db,
    )
    custom_asset_id = str(uuid4())
    db_custom_assets.add_custom_asset(CustomAsset.initialize(
        identifier=custom_asset_id,
        name='My Custom Prop',
        custom_asset_type='random',
    ))
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json={
            'limit': 10,
            'offset': 0,
            'order_by_attributes': ['name'],
            'asset_type': 'custom asset',
            'ascending': [True],
        },
    )
    result = assert_proper_sync_response_with_result(response)
    assert len(result['entries']) == 1
    assert result['entries'][0]['identifier'] == custom_asset_id
    assert result['entries'][0]['asset_type'] == 'custom asset'

    # filter by name & symbol
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json={
            'limit': 50,
            'offset': 0,
            'name': 'Uniswap',
            'symbol': 'UNI',
            'order_by_attributes': ['symbol'],
            'ascending': [False],
            'ignored_assets_handling': 'exclude',
        },
    )
    result = assert_proper_sync_response_with_result(response)
    assert 50 == len(result['entries']) > 2
    for entry in result['entries']:
        assert 'uniswap' in entry['name'].casefold()
        assert 'UNI' in entry['symbol']
        if entry['asset_type'] == AssetType.EVM_TOKEN.serialize():
            assert entry['evm_chain'] in [x.to_name() for x in ChainID]

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

    # test asking for a single evm token
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json={
            'identifiers': [A_DAI.identifier],
        },
    )
    result = assert_proper_sync_response_with_result(response)
    assert result['entries'][0]['identifier'] == A_DAI
    assert 'address' in result['entries'][0]
    assert 'decimals' in result['entries'][0]
    assert result['entries'][0]['evm_chain'] == 'ethereum'
    assert result['entries'][0]['asset_type'] == AssetType.EVM_TOKEN.serialize()

    # ask for a crypto asset and a fiat asset (test multiple asset query)
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json={
            'identifiers': [A_BTC.identifier, A_USD.identifier, custom_asset_id],
        },
    )
    result = assert_proper_sync_response_with_result(response)
    assert result['entries'][0]['identifier'] == A_USD
    assert result['entries'][1]['identifier'] == custom_asset_id
    assert result['entries'][2]['identifier'] == A_BTC

    # check that evm tokens with underlying tokens are shown
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json={'asset_type': 'evm token'},
    )
    result = assert_proper_sync_response_with_result(response)
    for entry in result['entries']:
        assert 'underlying_tokens' in entry
        assert entry['evm_chain'] in [x.to_name() for x in ChainID]

    # test that wrong combination of evm_chain & asset_type fails.
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json={'asset_type': 'fiat', 'evm_chain': 'ethereum'},
    )
    assert_error_response(
        response=response,
        contained_in_msg='Filtering by evm_chain is only supported for evm tokens',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # check that filtering by evm_chain & symbol works.
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json={'evm_chain': 'ethereum', 'symbol': 'UNI'},
    )
    result = assert_proper_sync_response_with_result(response)
    assert all(i['evm_chain'] == 'ethereum' and 'UNI' in i['symbol'].upper() for i in result['entries'])  # noqa: E501

    # check that filtering by address and evm_chain works.
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json={
            'evm_chain': 'ethereum',
            'address': '0x6b175474e89094c44da98b954eedeac495271d0f',
        },
    )
    result = assert_proper_sync_response_with_result(response)
    assert len(result['entries']) == 1
    assert result['entries'][0]['address'] == '0x6B175474E89094C44Da98b954EedeAC495271d0F'
    assert result['entries'][0]['evm_chain'] == 'ethereum'
    assert result['entries'][0]['name'] == 'Multi Collateral Dai'
    assert result['entries'][0]['symbol'] == 'DAI'


def test_get_assets_mappings(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that providing a list of asset identifiers, the appropriate assets mappings are returned."""  # noqa: E501
    queried_assets = ('BTC', 'TRY', 'EUR', A_DAI.identifier, A_OP.identifier)
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        set_token_spam_protocol(
            write_cursor=write_cursor,
            token=A_DAI.resolve_to_evm_token(),
            is_spam=True,
        )

    # add custom asset
    db_custom_assets = DBCustomAssets(
        db_handler=rotkehlchen_api_server.rest_api.rotkehlchen.data.db,
    )
    custom_asset_id = str(uuid4())
    db_custom_assets.add_custom_asset(CustomAsset.initialize(
        identifier=custom_asset_id,
        name='My Custom Prop',
        custom_asset_type='random',
    ))
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'assetsmappingresource',
        ),
        json={'identifiers': queried_assets},
    )
    result = assert_proper_sync_response_with_result(response)
    assets = result['assets']
    assert len(assets) == len(queried_assets)
    for identifier, details in assets.items():
        assert identifier in queried_assets
        if identifier == A_DAI.identifier:
            assert details['evm_chain'] == 'ethereum'
            assert 'custom_asset_type' not in details
            assert details['asset_type'] != 'custom asset'
            assert details['collection_id'] == '23'
            assert details['is_spam'] is True
            assert details['coingecko'] == 'dai'
            assert details['cryptocompare'] == 'DAI'
        elif identifier == A_OP.identifier:
            assert details['evm_chain'] == 'optimism'
            assert 'custom_asset_type' not in details
            assert details['asset_type'] != 'custom asset'
            assert details['coingecko'] == 'optimism'
            assert details['cryptocompare'] == 'OP'
        elif identifier == custom_asset_id:
            assert details['custom_asset_type'] == 'random'
            assert details['asset_type'] == 'custom asset'
        else:
            assert 'evm_chain' not in details
            assert 'custom_asset_type' not in details
            assert details['asset_type'] != 'custom asset'

    assert result['asset_collections'] == {
        '23': {
            'name': 'Multi Collateral Dai',
            'symbol': 'DAI',
            'main_asset': 'eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F',
        },
        '40': {
            'name': 'Bitcoin',
            'symbol': 'BTC',
            'main_asset': 'BTC',
        },
    }

    # check that providing an invalid identifier returns only valid ones if any.
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'assetsmappingresource',
        ),
        json={'identifiers': ['BTC', 'TRY', 'invalid']},
    )
    result = assert_proper_sync_response_with_result(response)
    assets = result['assets']
    assert len(assets) == 2
    assert all(identifier in {'BTC', 'TRY'} for identifier in assets)


def test_search_assets(rotkehlchen_api_server: 'APIServer') -> None:
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
    result = assert_proper_sync_response_with_result(response)
    assert len(result) <= 50
    for entry in result:
        assert 'bitcoin' in entry['name'].lower()
    assert_asset_result_order(data=result, is_ascending=True, order_field='name')
    assert all('custom_asset_type' not in entry and not entry['is_custom_asset'] for entry in result)  # noqa: E501

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
    result = assert_proper_sync_response_with_result(response)
    assert len(result) <= 10
    for entry in result:
        assert 'eth' in entry['symbol'].lower()
    assert_asset_result_order(data=result, is_ascending=False, order_field='symbol')
    assert all('custom_asset_type' not in entry and not entry['is_custom_asset'] for entry in result)  # noqa: E501

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
    result = assert_proper_sync_response_with_result(response)
    assert len(result) == 0

    # use the return_exact_matches flag
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'assetssearchresource',
        ),
        json={
            'value': 'ETH',
            'search_column': 'symbol',
            'limit': 10,
            'return_exact_matches': True,
            'order_by_attributes': ['name'],
            'ascending': [False],
        },
    )
    result = assert_proper_sync_response_with_result(response)
    assert len(result) == 6
    assert any(entry['name'] == 'Ethereum' for entry in result)
    for entry in result:
        assert entry['symbol'] == 'ETH'
    assert_asset_result_order(data=result, is_ascending=False, order_field='name')
    assert all('custom_asset_type' not in entry and not entry['is_custom_asset'] for entry in result)  # noqa: E501

    # check that treat_eth2_as_eth` setting is respected
    # using the test above.
    db = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    with db.user_write() as cursor:
        db.set_settings(cursor, ModifiableDBSettings(treat_eth2_as_eth=True))

    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'assetssearchresource',
        ),
        json={
            'value': 'ETH',
            'search_column': 'symbol',
            'limit': 10,
            'return_exact_matches': True,
            'order_by_attributes': ['name'],
            'ascending': [True],
        },
    )
    result = assert_proper_sync_response_with_result(response)
    assert len(result) == 6
    assert any(entry['name'] == 'Ethereum' for entry in result)
    for entry in result:
        assert entry['symbol'] == 'ETH'
        assert entry['identifier'] != 'ETH2'
        if entry['name'] == 'Binance-Peg Ethereum Token':
            assert entry['evm_chain'] == 'binance_sc'
        elif entry['name'] == 'Ether':
            assert entry['evm_chain'] == 'optimism'
        elif entry['identifier'].startswith('eip155:8453'):
            assert entry['evm_chain'] == 'base'
        elif entry['identifier'].startswith('eip155:137'):
            assert entry['evm_chain'] == 'polygon_pos'
        elif entry['identifier'].startswith('eip155:250'):
            assert entry['evm_chain'] == 'fantom'
        else:
            assert 'evm_chain' not in entry
    assert_asset_result_order(data=result, is_ascending=True, order_field='name')
    assert all('custom_asset_type' not in entry and not entry['is_custom_asset'] for entry in result)  # noqa: E501

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

    # test that the evm_chain column is included
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'assetssearchresource',
        ),
        json={
            'value': 'DAI',
            'search_column': 'symbol',
            'limit': 10,
            'return_exact_matches': True,
            'order_by_attributes': ['name'],
            'ascending': [True],
        },
    )
    result = assert_proper_sync_response_with_result(response)
    assert {asset['evm_chain'] for asset in result} == {
        'polygon_pos',
        'optimism',
        'ethereum',
        'arbitrum_one',
        'binance_sc',
        'base',
        'scroll',
        'gnosis',
        'fantom',
    }

    # check that using evm_chain filter works.
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'assetssearchresource',
        ),
        json={
            'value': 'DAI',
            'search_column': 'symbol',
            'limit': 50,
            'evm_chain': 'ethereum',
            'order_by_attributes': ['name'],
            'ascending': [True],
        },
    )
    result = assert_proper_sync_response_with_result(response)
    assert 50 >= len(result) > 10
    assert all(entry['evm_chain'] == 'ethereum' and 'DAI' in entry['symbol'] for entry in result)
    assert_asset_result_order(data=result, is_ascending=True, order_field='name')

    # check that using an unsupported evm_chain fails
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'assetssearchresource',
        ),
        json={
            'value': 'dai',
            'search_column': 'symbol',
            'limit': 50,
            'evm_chain': 'prettychain',
            'order_by_attributes': ['name'],
            'ascending': [True],
        },
    )
    assert_error_response(response, contained_in_msg='Failed to deserialize evm chain value prettychain')  # noqa: E501


def test_search_assets_with_levenshtein(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that searching for assets using a keyword works(levenshtein approach)."""
    globaldb = GlobalDBHandler()
    # search by address
    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'assetssearchlevenshteinresource'),
        json={'address': '0xDDAfbb505ad214D7b80b1f830fcCc89B60fb7A83', 'limit': 10},
    )
    result = assert_proper_sync_response_with_result(response)
    assert len(result) == 1 and result[0]['identifier'] == 'eip155:100/erc20:0xDDAfbb505ad214D7b80b1f830fcCc89B60fb7A83'  # noqa: E501  # USDC on gnosis

    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'assetssearchlevenshteinresource'),
        json={'value': 'Bitcoin', 'limit': 50},
    )
    result = assert_proper_sync_response_with_result(response)
    assert len(result) <= 50
    # check that Bitcoin(BTC) appears at the top of result.
    assert_asset_at_top_position('BTC', max_position_index=1, result=result)
    assert_substring_in_search_result(result, 'Bitcoin')
    assert all('custom_asset_type' not in entry and entry['asset_type'] != 'custom asset' for entry in result)  # noqa: E501

    # use a different keyword
    # but add assets without name/symbol and see that nothing breaks
    asset_without_name_id = str(uuid4())
    asset_without_symbol_id = str(uuid4())
    globaldb.add_asset(CryptoAsset.initialize(
        identifier=asset_without_name_id,
        asset_type=AssetType.OWN_CHAIN,
        symbol='ETH',
    ))
    globaldb.add_asset(CryptoAsset.initialize(
        identifier=asset_without_symbol_id,
        asset_type=AssetType.OWN_CHAIN,
        name='ETH',
    ))
    globaldb.add_asset(CryptoAsset.initialize(
        identifier=str(uuid4()),
        asset_type=AssetType.OWN_CHAIN,
    ))
    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'assetssearchlevenshteinresource'),
        json={'value': 'ETH', 'limit': 50},
    )
    result = assert_proper_sync_response_with_result(response)
    assert len(result) <= 50
    assert_substring_in_search_result(result, 'ETH')
    # check that Ethereum(ETH) appear at the top of result.
    assert_asset_at_top_position('ETH', max_position_index=1, result=result)
    assert any(asset_without_name_id == entry['identifier'] for entry in result)
    assert any(asset_without_symbol_id == entry['identifier'] for entry in result)
    assert all('custom_asset_type' not in entry and entry['asset_type'] != 'custom asset' for entry in result)  # noqa: E501

    # check that treat_eth2_as_eth` setting is respected
    # using the test above.
    db = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    with db.user_write() as cursor:
        db.set_settings(cursor, ModifiableDBSettings(treat_eth2_as_eth=True))

    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'assetssearchlevenshteinresource'),
        json={'value': 'ETH', 'limit': 50},
    )
    result = assert_proper_sync_response_with_result(response)
    assert len(result) <= 50
    assert_substring_in_search_result(result, 'ETH')
    # check that Ethereum(ETH) appears at the top of result.
    assert_asset_at_top_position('ETH', max_position_index=1, result=result)
    assert all(entry['identifier'] != 'ETH2' and entry['asset_type'] != 'custom asset' and 'custom_asset_type' not in entry for entry in result)  # noqa: E501

    # check that searching for a non-existent asset returns nothing
    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'assetssearchlevenshteinresource'),
        json={'value': 'idontexist', 'limit': 50},
    )
    result = assert_proper_sync_response_with_result(response)
    assert len(result) == 0

    # check that using evm_chain filter works.
    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'assetssearchlevenshteinresource'),
        json={'value': 'dai', 'limit': 50, 'evm_chain': 'ethereum'},
    )
    result = assert_proper_sync_response_with_result(response)
    assert 50 >= len(result) > 10
    assert all(entry['evm_chain'] == 'ethereum' and entry['asset_type'] != 'custom asset' and 'custom_asset_type' not in entry for entry in result if 'evm_chain' in entry)  # noqa: E501

    assert_substring_in_search_result(result, 'dai')
    # check that Dai(DAI) appears at the top of result.
    assert_asset_at_top_position(
        asset_id=A_DAI.identifier,
        max_position_index=0,
        result=result,
    )

    # check that searching for assets with long name works
    db_custom_assets = DBCustomAssets(
        db_handler=rotkehlchen_api_server.rest_api.rotkehlchen.data.db,
    )
    custom_asset_id = str(uuid4())
    db_custom_assets.add_custom_asset(CustomAsset.initialize(
        identifier=custom_asset_id,
        name='My Custom Prop that has a very long name haha',
        custom_asset_type='random',
    ))
    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'assetssearchlevenshteinresource'),
        json={'value': 'my custom', 'limit': 50},
    )
    result = assert_proper_sync_response_with_result(response)
    assert_substring_in_search_result(result, 'my custom')
    assert all(custom_asset_id == entry['identifier'] and entry['asset_type'] == 'custom asset' and entry['custom_asset_type'] == 'random' for entry in result)  # noqa: E501

    # check that using an unsupported evm_chain fails
    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'assetssearchlevenshteinresource'),
        json={'value': 'dai', 'limit': 50, 'evm_chain': 'charlesfarm'},
    )
    assert_error_response(response, contained_in_msg='Failed to deserialize evm chain value charlesfarm')  # noqa: E501

    # check that filtering by chain does include assets without chain
    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'assetssearchlevenshteinresource'),
        json={'value': 'eth', 'limit': 50, 'evm_chain': 'optimism'},
    )
    result = assert_proper_sync_response_with_result(response)
    assert 'ETH' in {x['identifier'] for x in result}


def test_search_nfts_with_levenshtein(rotkehlchen_api_server: 'APIServer') -> None:
    with rotkehlchen_api_server.rest_api.rotkehlchen.data.db.user_write() as cursor:
        cursor.execute('INSERT INTO assets VALUES (?)', ('my-nft-identifier',))
        cursor.execute(
            'INSERT INTO nfts(identifier, name, collection_name, manual_price, is_lp, '
            'last_price, last_price_asset) VALUES (?, ?, ?, ?, ?, ?, ?)',
            ('my-nft-identifier', 'super-duper-nft', 'Bitcoin smth', False, False, 0, 'ETH'),
        )

    # check that searching by nft name works
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'assetssearchlevenshteinresource',
        ),
        json={
            'value': 'super-duper',
            'limit': 50,
            'search_nfts': True,
        },
    )
    result = assert_proper_sync_response_with_result(response)
    assert result == [{
        'identifier': 'my-nft-identifier',
        'name': 'super-duper-nft',
        'collection_name': 'Bitcoin smth',
        'asset_type': 'nft',
    }]

    # Check that:
    # 1. Searching by nft collection name works
    # 2. Nfts are searched only with search_nfts set to True
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
    results_without_nfts = [x['identifier'] for x in assert_proper_sync_response_with_result(response)]  # noqa: E501

    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'assetssearchlevenshteinresource',
        ),
        json={
            'value': 'Bitcoin',
            'limit': 50,
            'search_nfts': True,
        },
    )
    result = assert_proper_sync_response_with_result(response)
    results_with_nfts = [x['identifier'] for x in result]
    assert set(results_with_nfts) - set(results_without_nfts) == {'my-nft-identifier'}

    # Check that the order makes sense
    previous_levenshtein_distance = 0
    for entry in result:
        if entry['asset_type'] == 'nft':
            current_levenshtein_distance = min(
                levenshtein('bitcoin', entry['name']),
                levenshtein('bitcoin', entry['collection_name']),
            )
        else:
            current_levenshtein_distance = min(
                levenshtein('bitcoin', entry['name']),
                levenshtein('bitcoin', entry['symbol']),
            )
        assert current_levenshtein_distance >= previous_levenshtein_distance


def test_only_ignored_assets(rotkehlchen_api_server: 'APIServer') -> None:
    """Test it's possible to ask to only see the ignored assets"""
    clean_ignored_assets(rotkehlchen_api_server.rest_api.rotkehlchen.data.db)
    ignored_assets = [A_GNO.identifier, A_RDN.identifier]
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'ignoredassetsresource',
        ), json={'assets': ignored_assets},
    )
    assert_proper_response(response)
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json={
            'ignored_assets_handling': 'show_only',
        },
    )
    result = assert_proper_sync_response_with_result(response)
    assert {entry['identifier'] for entry in result['entries']} == set(ignored_assets)


def test_false_positive(rotkehlchen_api_server: APIServer, globaldb: GlobalDBHandler) -> None:
    """Test the endpoint to add/remove an asset from the whitelist of spam assets"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    db = rotki.data.db
    with globaldb.conn.read_ctx() as cursor:
        existing_whitelisted_count = cursor.execute(
            'SELECT COUNT(*) from general_cache WHERE key=?',
            ('SPAM_ASSET_FALSE_POSITIVE',),
        ).fetchone()[0]

    # setup as if DAI was in the spam assets
    with db.user_write() as write_cursor:
        db.add_to_ignored_assets(write_cursor=write_cursor, asset=A_DAI)

    with globaldb.conn.write_ctx() as write_cursor:
        write_cursor.execute(
            'UPDATE evm_tokens SET protocol=? WHERE identifier=?',
            (SPAM_PROTOCOL, A_DAI.identifier),
        )
    AssetResolver.clean_memory_cache(A_DAI.identifier)

    dai = A_DAI.resolve_to_evm_token()
    assert dai.protocol == SPAM_PROTOCOL

    response = requests.post(  # mark it as false positive
        api_url_for(
            rotkehlchen_api_server,
            'falsepositivespamtokenresource',
        ), json={'token': A_DAI.identifier},
    )
    assert_proper_response(response)

    # check that the asset is not ignored and has the right protocol value
    dai = A_DAI.resolve_to_evm_token()
    assert dai.protocol is None
    with db.conn.read_ctx() as cursor:
        assert A_DAI not in db.get_ignored_asset_ids(cursor=cursor)

    with globaldb.conn.read_ctx() as cursor:
        assert A_DAI.identifier in globaldb_get_general_cache_values(
            cursor=cursor,
            key_parts=(CacheType.SPAM_ASSET_FALSE_POSITIVE,),
        )

    # check that we can query it from the api
    response = requests.get(api_url_for(rotkehlchen_api_server, 'falsepositivespamtokenresource'))
    result = assert_proper_sync_response_with_result(response)
    assert A_DAI in result

    # test that the filter in the search for assets works
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ), json={'show_whitelisted_assets_only': True},
    )
    result = assert_proper_sync_response_with_result(response)
    with globaldb.conn.read_ctx() as cursor:
        assert result['entries_found'] == existing_whitelisted_count + 1
    assert A_DAI.identifier in {entry['identifier'] for entry in result['entries']}

    # remove it from the list of false positives
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'falsepositivespamtokenresource',
        ), json={'token': A_DAI.identifier},
    )
    with globaldb.conn.read_ctx() as cursor:
        assert len(globaldb_get_general_cache_values(
            cursor=cursor,
            key_parts=(CacheType.SPAM_ASSET_FALSE_POSITIVE,),
        )) == existing_whitelisted_count


def test_setting_tokens_as_spam(rotkehlchen_api_server: APIServer) -> None:
    """Test the endpoints which set the spam protocol on tokens"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    db = rotki.data.db
    globaldb = GlobalDBHandler()

    # add token to whitelist to see that it gets removed
    with globaldb.conn.write_ctx() as write_cursor:
        globaldb_set_general_cache_values(
            write_cursor=write_cursor,
            key_parts=(CacheType.SPAM_ASSET_FALSE_POSITIVE,),
            values=(A_DAI.identifier,),
        )

    eth_address = make_evm_address()
    rotki.chains_aggregator.balances.eth[eth_address].assets[A_DAI][DEFAULT_BALANCE_LABEL] = Balance(amount=FVal(30))  # noqa: E501
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'spamevmtokenresource',
        ), json={'tokens': [A_DAI.identifier, A_OP.identifier]},
    )
    assert_proper_response(response)
    assert A_DAI.resolve_to_evm_token().protocol == SPAM_PROTOCOL
    assert A_OP.resolve_to_evm_token().protocol == SPAM_PROTOCOL
    with db.conn.read_ctx() as cursor:
        assert {A_DAI, A_OP}.issubset(rotki.data.db.get_ignored_asset_ids(cursor))

    # check that we removed the asset from the balances
    assert len(rotki.chains_aggregator.balances.eth[eth_address].assets) == 0

    with globaldb.conn.read_ctx() as cursor:
        assert A_DAI.identifier not in globaldb_get_general_cache_values(
            cursor=cursor,
            key_parts=(CacheType.SPAM_ASSET_FALSE_POSITIVE,),
        )

    # check that it fails if we try to add any other asset type
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'spamevmtokenresource',
        ), json={'tokens': [A_BTC.identifier]},
    )
    assert_error_response(
        response=response,
        contained_in_msg='to be EvmToken but in fact it was',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # remove the spam protocol
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'spamevmtokenresource',
        ), json={'token': A_DAI.identifier},
    )
    assert_proper_response(response)
    assert A_DAI.resolve_to_evm_token().protocol is None


def test_edit_tokens_nullable(rotkehlchen_api_server: 'APIServer') -> None:
    """Check that evm tokens can be edited with symbol and decimal being None"""
    token = EvmToken.initialize(
        address=make_evm_address(),
        chain_id=ChainID.ETHEREUM,
        token_kind=TokenKind.ERC20,
        name='Custom 2',
    )
    GlobalDBHandler.add_asset(token)
    response = requests.patch(
        api_url_for(rotkehlchen_api_server, 'allassetsresource'),
        json={
            'asset_type': token.asset_type.serialize(),
            'identifier': token.identifier,
            'name': 'A new name',
            'address': token.evm_address,
            'token_kind': str(token.token_kind.name),
            'evm_chain': token.chain_id.to_name(),
            'symbol': None,
            'decimals': None,
        },
    )
    assert_proper_response(response)
    token = EvmToken(token.identifier)
    assert token.name == 'A new name'
    assert token.symbol == ''
    assert token.decimals == 18


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_add_solana_token(rotkehlchen_api_server: 'APIServer') -> None:
    token_identifier = solana_address_to_identifier(
        address=(token_address := SolanaAddress('BENGEso6uSrcCYyRsanYgmDwLi34QSpihU2FX2xvpump')),
        token_type=TokenKind.SPL_TOKEN,
    )
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=(payload := {
            'asset_type': 'solana token',
            'address': token_address,
            'name': 'TrollBoss',
            'symbol': 'TROLLBOSS',
            'decimals': 6,
            'coingecko': None,
            'cryptocompare': None,
            'token_kind': 'spl_token',
            'protocol': '',
            'started': 1754563797,
        }),
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
    assert result['entries_found'] == 1
    assert result['entries'] == [
        {
            'address': token_address,
            'identifier': token_identifier,
            'asset_type': payload['asset_type'],
            'coingecko': None,
            'cryptocompare': None,
            'decimals': payload['decimals'],
            'name': payload['name'],
            'symbol': payload['symbol'],
            'started': payload['started'],
            'forked': None,
            'swapped_for': None,
            'protocol': None,
            'token_kind': ' '.join(payload['token_kind'].split('_')),  # type: ignore[attr-defined]  # it is a string
        },
    ]
