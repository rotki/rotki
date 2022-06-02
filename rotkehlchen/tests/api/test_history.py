from contextlib import ExitStack
from http import HTTPStatus
from pathlib import Path

import pytest
import requests

from rotkehlchen.accounting.constants import FREE_PNL_EVENTS_LIMIT, FREE_REPORTS_LOOKUP_LIMIT
from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response_with_result,
)
from rotkehlchen.tests.utils.constants import ETH_ADDRESS1, ETH_ADDRESS2, ETH_ADDRESS3
from rotkehlchen.tests.utils.history import prepare_rotki_for_history_processing_test, prices
from rotkehlchen.tests.utils.pnl_report import query_api_create_and_get_report
from rotkehlchen.types import Location


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
        assert len(overview) == 6
        assert overview[str(AccountingEventType.ASSET_MOVEMENT)] is not None
        assert overview[str(AccountingEventType.LOAN)] is not None
        assert overview[str(AccountingEventType.MARGIN_POSITION)] is not None
        assert overview[str(AccountingEventType.TRANSACTION_EVENT)] is not None
    else:
        assert len(overview) == 2
    assert overview[str(AccountingEventType.TRADE)] is not None
    assert overview[str(AccountingEventType.FEE)] is not None

    settings = report['settings']
    assert len(settings) == 6
    assert settings['profit_currency'] == 'EUR'
    assert settings['account_for_assets_movements'] is True
    assert settings['calculate_past_cost_basis'] is True
    assert settings['include_crypto2crypto'] is True
    assert settings['include_gas_costs'] is True
    assert settings['taxfree_after_period'] == 31536000

    assert events_result['entries_limit'] == FREE_PNL_EVENTS_LIMIT
    entries_length = 47 if start_ts == 0 else 44
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
    assert len(warnings) == 10
    assert 'poloniex trade with unknown asset NOEXISTINGASSET' in warnings[0]
    assert 'poloniex trade with unsupported asset BALLS' in warnings[1]
    assert 'withdrawal of unknown poloniex asset IDONTEXIST' in warnings[2]
    assert 'withdrawal of unsupported poloniex asset DIS' in warnings[3]
    assert 'deposit of unknown poloniex asset IDONTEXIST' in warnings[4]
    assert 'deposit of unsupported poloniex asset EBT' in warnings[5]
    assert 'poloniex loan with unsupported asset BDC' in warnings[6]
    assert 'poloniex loan with unknown asset NOTEXISTINGASSET' in warnings[7]
    assert 'bittrex trade with unsupported asset PTON' in warnings[8]
    assert 'bittrex trade with unknown asset IDONTEXIST' in warnings[9]

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
    json_data = {'source': 'blockfi-trades', 'file': str(filepath)}
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
                'ascending': ascending_timestamp,
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

    assert len(events) == 47
    for idx, x in enumerate(events):
        if idx == len(events) - 1:
            break

        if ascending_timestamp:
            assert x['timestamp'] <= events[idx + 1]['timestamp']
        else:
            assert x['timestamp'] >= events[idx + 1]['timestamp']
