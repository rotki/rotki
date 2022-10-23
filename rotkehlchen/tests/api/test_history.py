import random
from contextlib import ExitStack
from http import HTTPStatus
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from rotkehlchen.accounting.constants import FREE_PNL_EVENTS_LIMIT, FREE_REPORTS_LOOKUP_LIMIT
from rotkehlchen.accounting.ledger_actions import LedgerAction, LedgerActionType
from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.constants.assets import A_BTC, A_DAI, A_EUR
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.ledger_actions import DBLedgerActions
from rotkehlchen.exchanges.data_structures import Trade
from rotkehlchen.externalapis.cryptocompare import Cryptocompare
from rotkehlchen.externalapis.defillama import Defillama
from rotkehlchen.fval import FVal
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.history.types import HistoricalPriceOracle
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response_with_result,
    assert_simple_ok_response,
    wait_for_async_task_with_result,
)
from rotkehlchen.tests.utils.constants import ETH_ADDRESS1, ETH_ADDRESS2, ETH_ADDRESS3
from rotkehlchen.tests.utils.history import (
    assert_pnl_debug_import,
    prepare_rotki_for_history_processing_test,
    prices,
)
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.tests.utils.pnl_report import query_api_create_and_get_report
from rotkehlchen.types import AssetAmount, Fee, Location, Price, TradeType


@pytest.mark.parametrize(
    'added_exchanges',
    [(Location.BINANCE, Location.POLONIEX, Location.BITTREX, Location.BITMEX, Location.KRAKEN)],
)
@pytest.mark.parametrize('ethereum_accounts', [[ETH_ADDRESS1, ETH_ADDRESS2, ETH_ADDRESS3]])
@pytest.mark.parametrize('mocked_price_queries', [prices])
@pytest.mark.parametrize(
    'start_ts,end_ts',
    [(0, 1601040361), (1539713237, 1539713238)],
)
def test_query_history(rotkehlchen_api_server_with_exchanges, start_ts, end_ts):
    """Test that the history processing REST API endpoint works. Similar to test_history.py

    Both a test for full and limited time range.
    """
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
    assert len(report) == 11  # 11 entries in the report api endpoint
    assert report['first_processed_timestamp'] == 1428994442
    assert report['last_processed_timestamp'] == end_ts if end_ts == 1539713238 else 1566572401
    assert report['identifier'] == report_id
    assert report['size_on_disk'] > 0

    overview = report['overview']
    if start_ts == 0:
        assert len(overview) == 5
        assert overview[str(AccountingEventType.ASSET_MOVEMENT)] is not None
        assert overview[str(AccountingEventType.MARGIN_POSITION)] is not None
        assert overview[str(AccountingEventType.TRANSACTION_EVENT)] is not None
    else:
        assert len(overview) == 2
    assert overview[str(AccountingEventType.TRADE)] is not None
    assert overview[str(AccountingEventType.FEE)] is not None

    settings = report['settings']
    assert len(settings) == 8
    assert settings['profit_currency'] == 'EUR'
    assert settings['account_for_assets_movements'] is True
    assert settings['calculate_past_cost_basis'] is True
    assert settings['include_crypto2crypto'] is True
    assert settings['include_gas_costs'] is True
    assert settings['taxfree_after_period'] == 31536000
    assert settings['cost_basis_method'] == 'fifo'
    assert settings['eth_staking_taxable_after_withdrawal_enabled'] is False

    assert events_result['entries_limit'] == FREE_PNL_EVENTS_LIMIT
    entries_length = 43 if start_ts == 0 else 40
    assert events_result['entries_found'] == entries_length
    assert isinstance(events_result['entries'], list)
    # TODO: These events are not actually checked anywhere for correctness
    #       A test should probably be made for their correctness, even though
    #       they are assumed correct if the overview is correct
    assert len(events_result['entries']) == entries_length

    # And now make sure that warnings have also been generated for the query of
    # the unsupported/unknown assets
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    warnings = rotki.msg_aggregator.consume_warnings()
    assert len(warnings) == 8
    assert 'poloniex trade with unknown asset NOEXISTINGASSET' in warnings[0]
    assert 'poloniex trade with unsupported asset BALLS' in warnings[1]
    assert 'withdrawal of unknown poloniex asset IDONTEXIST' in warnings[2]
    assert 'withdrawal of unsupported poloniex asset DIS' in warnings[3]
    assert 'deposit of unknown poloniex asset IDONTEXIST' in warnings[4]
    assert 'deposit of unsupported poloniex asset EBT' in warnings[5]
    assert 'bittrex trade with unsupported asset PTON' in warnings[6]
    assert 'bittrex trade with unknown asset IDONTEXIST' in warnings[7]

    errors = rotki.msg_aggregator.consume_errors()
    assert len(errors) == 3
    assert 'bittrex trade with unprocessable pair %$#%$#%#$%' in errors[0]
    assert 'Failed to read ledger event from kraken' in errors[1]
    assert 'Failed to read ledger event from kraken ' in errors[2]

    response = requests.get(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            'historyactionableitemsresource',
        ),
    )
    result = assert_proper_response_with_result(response=response, status_code=HTTPStatus.OK)
    assert len(result['missing_acquisitions']) == 10
    assert len(result['missing_prices']) == 0
    assert result['report_id'] == 1


@pytest.mark.parametrize(
    'added_exchanges',
    [(Location.BINANCE, Location.POLONIEX, Location.BITTREX, Location.BITMEX, Location.KRAKEN)],
)
@pytest.mark.parametrize('ethereum_accounts', [[ETH_ADDRESS1, ETH_ADDRESS2, ETH_ADDRESS3]])
@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_query_history_remote_errors(rotkehlchen_api_server_with_exchanges):
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
            if manager is None:
                continue
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
    assert len(errors) == 11
    assert all('kraken' in e for e in errors[:2])
    assert 'Etherscan API request http://someurl.com returned invalid JSON response: [{' in errors[2]  # noqa: E501
    # The history processing is completely mocked away and omitted in this test.
    # because it is only for the history creation not its processing.
    # For history processing tests look at test_accounting.py and
    # test_accounting_events.py


def test_query_history_errors(rotkehlchen_api_server):
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


@pytest.mark.parametrize('ethereum_accounts', [[]])
@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_query_history_external_exchanges(rotkehlchen_api_server):
    """Test that history is processed for external exchanges too"""
    start_ts = 0
    end_ts = 1631455982

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
    assert FVal('5278.03086').is_close(FVal(overview[str(AccountingEventType.TRADE)]['taxable']))


@pytest.mark.parametrize(
    'added_exchanges',
    [(Location.BINANCE, Location.POLONIEX, Location.BITTREX, Location.BITMEX, Location.KRAKEN)],
)
@pytest.mark.parametrize('ethereum_accounts', [[ETH_ADDRESS1, ETH_ADDRESS2, ETH_ADDRESS3]])
@pytest.mark.parametrize('mocked_price_queries', [prices])
@pytest.mark.parametrize('ascending_timestamp', [False, True])
def test_query_pnl_report_events_pagination_filtering(
        rotkehlchen_api_server_with_exchanges,
        ascending_timestamp,
):
    """Test that for PnL reports pagination, filtering and order work fine"""
    start_ts = 0
    end_ts = 1601040361
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
    events_result = assert_proper_response_with_result(response)
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
        events_result = assert_proper_response_with_result(response)
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

    assert len(events) == 43
    for idx, x in enumerate(events):
        if idx == len(events) - 1:
            break

        if ascending_timestamp:
            assert x['timestamp'] <= events[idx + 1]['timestamp']
        else:
            assert x['timestamp'] >= events[idx + 1]['timestamp']


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_history_debug_import(rotkehlchen_api_server):
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
        if async_query is True:
            result = wait_for_async_task_with_result(
                server=rotkehlchen_api_server,
                task_id=response.json()['result']['task_id'],
            )
            assert result is True

        else:
            assert_simple_ok_response(response)
    else:
        response = requests.patch(
            api_url_for(
                rotkehlchen_api_server,
                'historyprocessingdebugresource',
            ),
            files={'filepath': open(str(filepath))},
            data={'async_query': async_query},
        )
        if async_query is True:
            result = wait_for_async_task_with_result(
                server=rotkehlchen_api_server,
                task_id=response.json()['result']['task_id'],
            )
            assert result is True
        else:
            assert_simple_ok_response(response)
    assert_pnl_debug_import(
        filepath=filepath,
        database=rotkehlchen_api_server.rest_api.rotkehlchen.data.db,
    )


@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('should_mock_price_queries', [False])
def test_missing_prices_in_pnl_report(rotkehlchen_api_server):
    """
    Test missing prices propagated during the PNL report
    """
    # set environment
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    action = LedgerAction(
        identifier=0,  # whatever
        timestamp=1665336822,
        action_type=LedgerActionType.INCOME,
        location=Location.EXTERNAL,
        amount=FVal(0.5),
        asset=A_BTC,
        rate=None,
        rate_asset=None,
        link=None,
        notes=None,
    )
    trade = Trade(
        timestamp=1665336822,
        location=Location.EXTERNAL,
        base_asset=A_DAI,
        quote_asset=A_EUR,
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('1')),
        rate=Price(FVal('320')),
        fee=Fee(ZERO),
        fee_currency=A_EUR,
        link='',
        notes='',
    )
    with rotki.data.db.user_write() as cursor:
        db = DBLedgerActions(rotki.data.db, rotki.msg_aggregator)
        db.add_ledger_action(cursor, action)
        rotki.data.db.add_trades(cursor, [trade])

    coingecko = PriceHistorian._coingecko
    PriceHistorian._PriceHistorian__instance = None
    price_historian = PriceHistorian(
        data_directory=MagicMock(spec=Path),
        cryptocompare=MagicMock(spec=Cryptocompare),
        coingecko=coingecko,
        defillama=MagicMock(spec=Defillama),
    )
    price_historian.set_oracles_order([HistoricalPriceOracle.COINGECKO])
    coingecko_api_calls = 0

    def mock_coingecko_return(url, *args, **kwargs):  # pylint: disable=unused-argument
        nonlocal coingecko_api_calls
        coingecko_api_calls += 1
        return MockResponse(HTTPStatus.TOO_MANY_REQUESTS, '{}')

    coingecko_patch = patch.object(PriceHistorian()._coingecko.session, 'get', side_effect=mock_coingecko_return)  # noqa: E501
    # create the PNL report
    with coingecko_patch:
        query_api_create_and_get_report(
            server=rotkehlchen_api_server,
            start_ts=1665336820,
            end_ts=1665336823,
            prepare_mocks=False,
        )

    # get the information about the report
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'historyactionableitemsresource',
        ),
    )
    result = assert_proper_response_with_result(response=response, status_code=HTTPStatus.OK)
    assert coingecko_api_calls == 2
    assert result['report_id'] == 1
    assert result['missing_prices'] == [{
        'from_asset': 'BTC',
        'to_asset': 'EUR',
        'time': 1665336822,
        'rate_limited': True,
    }]
