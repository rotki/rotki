import random
from contextlib import ExitStack
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest
import requests

from rotkehlchen.accounting.constants import (
    FREE_PNL_EVENTS_LIMIT,
    FREE_REPORTS_LOOKUP_LIMIT,
)
from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.chain.ethereum.oracles.uniswap import UniswapV2Oracle, UniswapV3Oracle
from rotkehlchen.constants.assets import A_BTC, A_DAI, A_EUR
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.misc import AccountingError
from rotkehlchen.externalapis.coingecko import Coingecko
from rotkehlchen.externalapis.cryptocompare import Cryptocompare
from rotkehlchen.externalapis.defillama import Defillama
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.swap import create_swap_events
from rotkehlchen.history.events.structures.types import (
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.history.types import HistoricalPriceOracle
from rotkehlchen.tests.fixtures.websockets import WebsocketReader
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response_with_result,
    assert_proper_sync_response_with_result,
    wait_for_async_task,
)
from rotkehlchen.tests.utils.constants import ETH_ADDRESS1, ETH_ADDRESS2, ETH_ADDRESS3
from rotkehlchen.tests.utils.factories import make_evm_tx_hash
from rotkehlchen.tests.utils.history import (
    assert_pnl_debug_import,
    mock_etherscan_transaction_response,
    prepare_rotki_for_history_processing_test,
    prices,
)
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.tests.utils.pnl_report import query_api_create_and_get_report
from rotkehlchen.types import (
    AssetAmount,
    Location,
    Timestamp,
    TimestampMS,
)
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('have_decoders', [True])
@pytest.mark.parametrize(
    'added_exchanges',
    [(Location.BINANCE, Location.POLONIEX, Location.BITMEX, Location.KRAKEN)],
)
@pytest.mark.parametrize('ethereum_accounts', [[ETH_ADDRESS1, ETH_ADDRESS2, ETH_ADDRESS3]])
@pytest.mark.parametrize('mocked_price_queries', [prices])
@pytest.mark.parametrize(
    ('start_ts', 'end_ts'),
    [(0, 1601040361), (1539713237, 1539713238)],
)
@pytest.mark.parametrize('db_settings', [
    {'include_fees_in_cost_basis': True},
    {'include_fees_in_cost_basis': False},
])
@pytest.mark.parametrize('initialize_accounting_rules', [True])
@pytest.mark.parametrize('legacy_messages_via_websockets', [True])
def test_query_history(rotkehlchen_api_server_with_exchanges: 'APIServer', start_ts: Timestamp, end_ts: Timestamp, websocket_connection: WebsocketReader) -> None:   # noqa: E501
    """Test that the history processing REST API endpoint works. Similar to test_history.py

    Both a test for full and limited time range.
    Also tests different values of `include_fees_in_cost_basis`.
    """
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    with rotki.data.db.conn.read_ctx() as cursor:
        fees_in_cost_basis = rotki.data.db.get_settings(cursor).include_fees_in_cost_basis

    report_id, report_result, events_result = query_api_create_and_get_report(
        server=rotkehlchen_api_server_with_exchanges,
        start_ts=start_ts,
        end_ts=end_ts,
        prepare_mocks=True,
    )

    # Simply check that the results got returned here. The actual correctness of
    # accounting results is checked in other tests such as test_simple_accounting
    assert report_result['entries_found'] == 1
    assert report_result['entries_limit'] == FREE_REPORTS_LOOKUP_LIMIT
    report = report_result['entries'][0]
    assert len(report) == 10  # 10 entries in the report api endpoint
    assert report['first_processed_timestamp'] == 1428994442
    assert report['last_processed_timestamp'] == end_ts if end_ts == 1539713238 else 1566572401
    assert report['identifier'] == report_id

    overview = report['overview']
    if start_ts == 0:
        assert len(overview) == 5
        assert overview[str(AccountingEventType.ASSET_MOVEMENT)] is not None
        assert overview[str(AccountingEventType.MARGIN_POSITION)] is not None
        assert overview[str(AccountingEventType.TRANSACTION_EVENT)] is not None
        assert overview[str(AccountingEventType.FEE)] is not None
    elif fees_in_cost_basis is True:  # start_ts is 1539713237
        assert len(overview) == 1
        # Fees events are not taxable in this case, so they should not be included in total pnls.
        assert str(AccountingEventType.FEE) not in overview
    else:  # start_ts is 1539713237 and fees_in_cost_basis is False
        assert len(overview) == 2
        assert overview[str(AccountingEventType.FEE)] is not None
    assert overview[str(AccountingEventType.TRADE)] is not None

    settings = report['settings']
    assert len(settings) == 8
    assert settings['profit_currency'] == 'EUR'
    assert settings['calculate_past_cost_basis'] is True
    assert settings['include_crypto2crypto'] is True
    assert settings['include_gas_costs'] is True
    assert settings['taxfree_after_period'] == 31536000
    assert settings['cost_basis_method'] == 'fifo'
    assert settings['eth_staking_taxable_after_withdrawal_enabled'] is True
    assert settings['include_fees_in_cost_basis'] == fees_in_cost_basis

    assert events_result['entries_limit'] == FREE_PNL_EVENTS_LIMIT
    entries_length = 37 if start_ts == 0 else 34
    assert events_result['entries_found'] == entries_length
    assert isinstance(events_result['entries'], list)
    # TODO: These events are not actually checked anywhere for correctness
    #       A test should probably be made for their correctness, even though
    #       they are assumed correct if the overview is correct
    assert len(events_result['entries']) == entries_length

    # And now make sure that messages have also been generated for the query of
    # the unsupported/unknown assets
    websocket_connection.wait_until_messages_num(num=20, timeout=10)
    assert [msg for msg in websocket_connection.messages if msg['type'] != 'history_events_status'][::-1] == [  # noqa: E501
        {'type': 'exchange_unknown_asset', 'data': {'location': 'poloniex', 'name': 'poloniex', 'identifier': 'IDONTEXIST', 'details': 'asset movement'}},  # noqa: E501
        {'type': 'legacy', 'data': {'verbosity': 'warning', 'value': 'Found withdrawal of unsupported poloniex asset BALLS. Ignoring it.'}},  # noqa: E501
        {'type': 'exchange_unknown_asset', 'data': {'location': 'poloniex', 'name': 'poloniex', 'identifier': 'IDONTEXIST', 'details': 'asset movement'}},  # noqa: E501
        {'type': 'legacy', 'data': {'verbosity': 'warning', 'value': 'Found deposit of unsupported poloniex asset EBT. Ignoring it.'}},  # noqa: E501
        {'type': 'exchange_unknown_asset', 'data': {'location': 'poloniex', 'name': 'poloniex', 'identifier': 'NOEXISTINGASSET', 'details': 'trade'}},  # noqa: E501
        {'type': 'legacy', 'data': {'verbosity': 'warning', 'value': 'Found poloniex trade with unsupported asset BALLS. Ignoring it.'}},  # noqa: E501
        {'type': 'legacy', 'data': {'verbosity': 'error', 'value': "Failed to read ledger event from kraken {'refid': 'D3', 'time': 1408994442, 'type': 'deposit', 'subtype': '', 'aclass': 'currency', 'asset': 'IDONTEXISTEITHER', 'amount': '10', 'fee': '0', 'balance': '100'} due to Unknown asset IDONTEXISTEITHER provided."}},  # noqa: E501
        {'type': 'legacy', 'data': {'verbosity': 'error', 'value': "Failed to read ledger event from kraken {'refid': 'W3', 'time': 1408994442, 'type': 'withdrawal', 'subtype': '', 'aclass': 'currency', 'asset': 'IDONTEXISTEITHER', 'amount': '-10', 'fee': '0.11', 'balance': '100'} due to Unknown asset IDONTEXISTEITHER provided."}},  # noqa: E501
    ]

    response = requests.get(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            'historyactionableitemsresource',
        ),
    )
    result = assert_proper_sync_response_with_result(response=response, status_code=HTTPStatus.OK)
    assert len(result['missing_acquisitions']) == (10 if fees_in_cost_basis is False else 9)
    assert len(result['missing_prices']) == 0
    assert result['report_id'] == 1


@pytest.mark.parametrize('have_decoders', [True])
@pytest.mark.parametrize(
    'added_exchanges',
    [(Location.BINANCE, Location.POLONIEX, Location.BITMEX, Location.KRAKEN)],
)
@pytest.mark.parametrize('ethereum_accounts', [[ETH_ADDRESS1, ETH_ADDRESS2, ETH_ADDRESS3]])
@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_query_history_remote_errors(rotkehlchen_api_server_with_exchanges: 'APIServer') -> None:
    """Test that the history processing REST API endpoint works. Similar to test_history.py"""
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    setup = prepare_rotki_for_history_processing_test(
        rotki,
        should_mock_history_processing=True,
        remote_errors=True,
    )

    # Query history processing to start the history processing
    with ExitStack() as stack:
        for manager in setup:
            stack.enter_context(manager)
        response = requests.get(
            api_url_for(rotkehlchen_api_server_with_exchanges, 'historyprocessingresource'),
        )

    assert_error_response(
        response=response,
        status_code=HTTPStatus.OK,
        contained_in_msg=[
            'invalid JSON', 'binance', 'Bittrex', 'Bitmex', 'Kraken', 'Poloniex',
        ],
    )
    warnings = rotki.msg_aggregator.consume_warnings()
    assert len(warnings) == 0
    errors = rotki.msg_aggregator.consume_errors()
    assert len(errors) == 1
    assert 'kraken' in errors[0]
    # The history processing is completely mocked away and omitted in this test.
    # because it is only for the history creation not its processing.
    # For history processing tests look at test_accounting.py and
    # test_accounting_events.py


@pytest.mark.parametrize('have_decoders', [True])
@pytest.mark.parametrize('ethereum_accounts', [[ETH_ADDRESS1]])
@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_fatal_error_during_query_history(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that an accounting error is propagated correctly to the api"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    error_patch = patch(
        'rotkehlchen.accounting.accountant.Accountant._process_event',
        side_effect=AccountingError(message='mocked error'),
    )
    etherscan_patch = mock_etherscan_transaction_response(
        etherscan=rotki.chains_aggregator.ethereum.node_inquirer.etherscan,
        remote_errors=True,
    )

    with ExitStack() as stack:
        stack.enter_context(error_patch)
        stack.enter_context(etherscan_patch)

        response = requests.get(
            api_url_for(rotkehlchen_api_server, 'historyprocessingresource'),
            json={'from_timestamp': 0, 'to_timestamp': 1, 'async_query': True},
        )
        task_id = assert_ok_async_response(response)
        outcome = wait_for_async_task(
            rotkehlchen_api_server,
            task_id,
        )
        assert outcome == {
            'result': 1,
            'message': 'mocked error',
            'status_code': HTTPStatus.CONFLICT,
        }


@pytest.mark.parametrize('have_decoders', [True])
def test_query_history_errors(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that errors in the history query REST API endpoint are handled properly"""
    # invalid from timestamp value
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'historyprocessingresource'),
        json={'from_timestamp': -1},
    )
    assert_error_response(
        response=response,
        contained_in_msg=(
            'Failed to deserialize a timestamp entry. Timestamps can not have negative values'
        ),
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # invalid to timestamp value
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'historyprocessingresource'),
        json={'from_timestamp': 0, 'to_timestamp': 'foo'},
    )
    assert_error_response(
        response=response,
        contained_in_msg=(
            'Failed to deserialize a timestamp entry from string foo'
        ),
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # invalid async_query type
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'historyprocessingresource'),
        json={'from_timestamp': 0, 'to_timestamp': 1, 'async_query': 'boo'},
    )
    assert_error_response(
        response=response,
        contained_in_msg='async_query": ["Not a valid boolean',
        status_code=HTTPStatus.BAD_REQUEST,
    )


@pytest.mark.parametrize('have_decoders', [True])
@pytest.mark.parametrize('ethereum_accounts', [[]])
@pytest.mark.parametrize('mocked_price_queries', [prices])
@pytest.mark.parametrize('initialize_accounting_rules', [True])
def test_query_history_external_exchanges(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that history is processed for external exchanges too"""
    start_ts = Timestamp(0)
    end_ts = Timestamp(1631455982)

    # import blockfi trades
    dir_path = Path(__file__).resolve().parent.parent
    filepath = dir_path / 'data' / 'blockfi-trades.csv'
    json_data = {'source': 'blockfi_trades', 'file': str(filepath)}
    requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'dataimportresource',
        ), json=json_data,
    )

    # Query history processing to start the history processing
    _, report_result, events_result = query_api_create_and_get_report(
        server=rotkehlchen_api_server,
        start_ts=start_ts,
        end_ts=end_ts,
        prepare_mocks=False,
    )
    assert len(events_result['entries']) == 2
    overview = report_result['entries'][0]['overview']
    assert FVal('4645.8444065096').is_close(FVal(overview[str(AccountingEventType.TRADE)]['taxable']))  # noqa: E501


@pytest.mark.parametrize('have_decoders', [True])
@pytest.mark.parametrize(
    'added_exchanges',
    [(Location.BINANCE, Location.POLONIEX, Location.BITMEX, Location.KRAKEN)],
)
@pytest.mark.parametrize('ethereum_accounts', [[ETH_ADDRESS1, ETH_ADDRESS2, ETH_ADDRESS3]])
@pytest.mark.parametrize('mocked_price_queries', [prices])
@pytest.mark.parametrize('ascending_timestamp', [False, True])
@pytest.mark.parametrize('initialize_accounting_rules', [True])
def test_query_pnl_report_events_pagination_filtering(
        rotkehlchen_api_server_with_exchanges: 'APIServer',
        ascending_timestamp: bool,
) -> None:
    """Test that for PnL reports pagination, filtering and order work fine"""
    start_ts = Timestamp(0)
    end_ts = Timestamp(1601040361)
    report_id, _, _ = query_api_create_and_get_report(
        server=rotkehlchen_api_server_with_exchanges,
        start_ts=start_ts,
        end_ts=end_ts,
        prepare_mocks=True,
    )

    response = requests.post(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            'per_report_data_resource',
            report_id=report_id,
        ),
    )
    events_result = assert_proper_sync_response_with_result(response)
    master_events = events_result['entries']

    events = []
    for offset in (0, 10, 20, 30, 40):
        response = requests.post(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                'per_report_data_resource',
                report_id=report_id,
            ),
            json={
                'offset': offset,
                'limit': 10,
                'order_by_attributes': ['timestamp'],
                'ascending': [ascending_timestamp],
            },
        )
        events_result = assert_proper_sync_response_with_result(response)
        assert len(events_result['entries']) <= 10
        events.extend(events_result['entries'])

    if ascending_timestamp is False:
        assert master_events == events
    else:
        reverse_master = master_events[::-1]
        # Verify all events are there. Order should be ascending ... but
        # since some events have same timestamps order when ascending is not
        # guaranteed to be the exact reverse as when descending
        for x in events:
            assert x in reverse_master
            reverse_master.remove(x)

    assert len(events) == 37
    for idx, x in enumerate(events):
        if idx == len(events) - 1:
            break

        if ascending_timestamp:
            assert x['timestamp'] <= events[idx + 1]['timestamp']
        else:
            assert x['timestamp'] >= events[idx + 1]['timestamp']


@pytest.mark.parametrize('ethereum_accounts', [[]])
@pytest.mark.parametrize('have_decoders', [[True]])
def test_history_debug_export(rotkehlchen_api_server: 'APIServer') -> None:
    """Check that the format of the data exported matches the expected type."""
    tx_id = '10' + str(make_evm_tx_hash())  # add a random tx id to the ignore list to ensure that at least one kind of event is ignored and is not empty  # noqa: E501
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    with rotki.data.db.user_write() as write_cursor:
        rotki.data.db.add_to_ignored_action_ids(
            write_cursor=write_cursor,
            identifiers=[tx_id],
        )

    expected_keys = ('events', 'settings', 'ignored_events_ids', 'pnl_settings')
    now = ts_now()
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'historyprocessingdebugresource',
        ),
        json={
            'from_timestamp': Timestamp(0),
            'to_timestamp': now,
        },
    )
    result = assert_proper_sync_response_with_result(response)
    assert tuple(result.keys()) == expected_keys
    assert result['pnl_settings'] == {'from_timestamp': Timestamp(0), 'to_timestamp': now}
    assert result['ignored_events_ids'] == [tx_id]


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_history_debug_import(rotkehlchen_api_server: 'APIServer') -> None:
    method = random.choice(['PATCH', 'PUT'])
    async_query = random.choice([True, False])
    filepath = Path(__file__).resolve().parent.parent / 'data' / 'pnl_debug.json'
    if method == 'PUT':
        response = requests.put(
            api_url_for(
                rotkehlchen_api_server,
                'historyprocessingdebugresource',
            ),
            json={
                'filepath': str(filepath),
                'async_query': async_query,
            },
        )
        assert assert_proper_response_with_result(
            response=response,
            rotkehlchen_api_server=rotkehlchen_api_server,
            async_query=async_query,
        )
    else:
        with open(str(filepath), encoding='utf8') as infile:
            response = requests.patch(
                api_url_for(
                    rotkehlchen_api_server,
                    'historyprocessingdebugresource',
                ),
                files={'filepath': infile},
                data={'async_query': async_query},
            )
            assert assert_proper_response_with_result(
                response=response,
                rotkehlchen_api_server=rotkehlchen_api_server,
                async_query=async_query,
            )
    assert_pnl_debug_import(
        filepath=filepath,
        database=rotkehlchen_api_server.rest_api.rotkehlchen.data.db,
    )


@pytest.mark.freeze_time('2023-05-11 15:06:00 GMT')  # set to make sure coingecko queries history ( < 1 year from events)  # noqa: E501
@pytest.mark.parametrize('have_decoders', [True])
@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('should_mock_price_queries', [False])
@pytest.mark.parametrize('initialize_accounting_rules', [True])
def test_missing_prices_in_pnl_report(rotkehlchen_api_server: 'APIServer') -> None:
    """
    Test missing prices propagated during the PNL report
    """
    # set environment
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    with rotki.data.db.user_write() as write_cursor:
        db = DBHistoryEvents(rotki.data.db)
        db.add_history_events(
            write_cursor=write_cursor,
            history=[HistoryEvent(
                event_identifier='whatever',
                sequence_index=0,
                timestamp=TimestampMS(1665336822000),
                location=Location.EXTERNAL,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                amount=FVal(0.5),
                asset=A_BTC,
            ), *create_swap_events(
                timestamp=TimestampMS(1665336822000),
                location=Location.EXTERNAL,
                spend=AssetAmount(amount=FVal('1'), asset=A_EUR),
                receive=AssetAmount(amount=FVal('320'), asset=A_DAI),
                event_identifier='tradeid1',
            )],
        )

    PriceHistorian.__instance = None
    price_historian = PriceHistorian(
        data_directory=rotki.data.data_directory,
        cryptocompare=MagicMock(spec=Cryptocompare),
        coingecko=Coingecko(database=None),
        defillama=MagicMock(spec=Defillama),
        uniswapv2=MagicMock(spec=UniswapV2Oracle),
        uniswapv3=MagicMock(spec=UniswapV3Oracle),
    )
    price_historian.set_oracles_order([HistoricalPriceOracle.COINGECKO])
    coingecko_api_calls = 0

    def mock_coingecko_return(url: str, *args: Any, **kwargs: Any) -> MockResponse:  # pylint: disable=unused-argument
        nonlocal coingecko_api_calls
        coingecko_api_calls += 1
        return MockResponse(HTTPStatus.TOO_MANY_REQUESTS, '{}')

    coingecko_patch = patch.object(price_historian._coingecko.session, 'get', side_effect=mock_coingecko_return)  # noqa: E501
    # create the PNL report
    with coingecko_patch:
        query_api_create_and_get_report(
            server=rotkehlchen_api_server,
            start_ts=Timestamp(1665336820),
            end_ts=Timestamp(1665336823),
            prepare_mocks=False,
        )

    # get the information about the report
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'historyactionableitemsresource',
        ),
    )
    result = assert_proper_sync_response_with_result(response=response, status_code=HTTPStatus.OK)
    assert coingecko_api_calls == 2  # 1 for BTC and 1 for DAI
    assert result['report_id'] == 1
    assert result['missing_prices'] == [{
        'from_asset': 'BTC',
        'to_asset': 'EUR',
        'time': 1665336822,
        'rate_limited': True,
    }]
