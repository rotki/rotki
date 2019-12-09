from contextlib import ExitStack
from http import HTTPStatus

import pytest
import requests

from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response,
    wait_for_async_task,
)
from rotkehlchen.tests.utils.history import prepare_rotki_for_history_processing_test, prices


@pytest.mark.parametrize(
    'added_exchanges',
    [('binance', 'poloniex', 'bittrex', 'bitmex', 'kraken')],
)
@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_query_history(rotkehlchen_api_server_with_exchanges):
    """Test that the history processing REST API endpoint works. Similar to test_history.py"""
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    setup = prepare_rotki_for_history_processing_test(
        rotki,
        should_mock_history_processing=False,
    )

    # Query history processing to start the history processing
    with ExitStack() as stack:
        for manager in setup:
            if manager is None:
                continue
            stack.enter_context(manager)
        response = requests.get(
            api_url_for(rotkehlchen_api_server_with_exchanges, "historyprocessingresource")
        )

    # Simply check that the results got returned here. The actual correctness of
    # accounting results is checked in other tests such as test_simple_accounting
    assert_proper_response(response)
    data = response.json()
    assert data['message'] == ''
    assert len(data['result']) == 2
    overview = data['result']['overview']
    assert len(overview) == 9
    assert overview["loan_profit"] is not None
    assert overview["margin_positions_profit_loss"] is not None
    assert overview["settlement_losses"] is not None
    assert overview["ethereum_transaction_gas_costs"] is not None
    assert overview["asset_movement_fees"] is not None
    assert overview["general_trade_profit_loss"] is not None
    assert overview["taxable_trade_profit_loss"] is not None
    assert overview["total_taxable_profit_loss"] is not None
    assert overview["total_profit_loss"] is not None
    all_events = data['result']['all_events']
    assert isinstance(all_events, list)
    # TODO: These events are not actually checked anywhere for correctness
    #       A test should probably be made for their correctness, even though
    #       they are assumed correct if the overview is correct
    assert len(all_events) == 36


@pytest.mark.parametrize(
    'added_exchanges',
    [('binance', 'poloniex', 'bittrex', 'bitmex', 'kraken')],
)
@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_query_history_timerange(rotkehlchen_api_server_with_exchanges):
    """Same as test_query_history but on a limited timerange"""
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    start_ts = 1539713237
    end_ts = 1539713238
    setup = prepare_rotki_for_history_processing_test(
        rotki,
        should_mock_history_processing=False,
        history_start_ts=start_ts,
        history_end_ts=end_ts,
    )

    # Query history processing to start the history processing
    with ExitStack() as stack:
        for manager in setup:
            if manager is None:
                continue
            stack.enter_context(manager)
        response = requests.get(
            api_url_for(rotkehlchen_api_server_with_exchanges, "historyprocessingresource"),
            json={'from_timestamp': start_ts, 'to_timestamp': end_ts},
        )

    # Simply check that the results got returned here. The actual correctness of
    # accounting results is checked in other tests such as test_simple_accounting
    assert_proper_response(response)
    data = response.json()
    assert data['message'] == ''
    assert len(data['result']) == 2
    overview = data['result']['overview']
    assert len(overview) == 9
    assert overview["loan_profit"] is not None
    assert overview["margin_positions_profit_loss"] is not None
    assert overview["settlement_losses"] is not None
    assert overview["ethereum_transaction_gas_costs"] is not None
    assert overview["asset_movement_fees"] is not None
    assert overview["general_trade_profit_loss"] is not None
    assert overview["taxable_trade_profit_loss"] is not None
    assert overview["total_taxable_profit_loss"] is not None
    assert overview["total_profit_loss"] is not None
    all_events = data['result']['all_events']
    assert isinstance(all_events, list)
    assert len(all_events) == 4


@pytest.mark.parametrize(
    'added_exchanges',
    [('binance', 'poloniex', 'bittrex', 'bitmex', 'kraken')],
)
@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_query_history_async(rotkehlchen_api_server_with_exchanges):
    """Same as test_query_history but asynchronously"""
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    start_ts = 1539713237
    end_ts = 1539713238
    setup = prepare_rotki_for_history_processing_test(
        rotki,
        should_mock_history_processing=False,
        history_start_ts=start_ts,
        history_end_ts=end_ts,
    )

    # Query history processing to start the history processing
    with ExitStack() as stack:
        for manager in setup:
            if manager is None:
                continue
            stack.enter_context(manager)
        response = requests.get(
            api_url_for(rotkehlchen_api_server_with_exchanges, "historyprocessingresource"),
            json={'from_timestamp': start_ts, 'to_timestamp': end_ts, 'async_query': True},
        )
        task_id = assert_ok_async_response(response)
        outcome = wait_for_async_task(rotkehlchen_api_server_with_exchanges, task_id)

    assert len(outcome['result']) == 2
    overview = outcome['result']['overview']
    assert len(overview) == 9
    assert overview["loan_profit"] is not None
    assert overview["margin_positions_profit_loss"] is not None
    assert overview["settlement_losses"] is not None
    assert overview["ethereum_transaction_gas_costs"] is not None
    assert overview["asset_movement_fees"] is not None
    assert overview["general_trade_profit_loss"] is not None
    assert overview["taxable_trade_profit_loss"] is not None
    assert overview["total_taxable_profit_loss"] is not None
    assert overview["total_profit_loss"] is not None
    all_events = outcome['result']['all_events']
    assert isinstance(all_events, list)
    assert len(all_events) == 4


def test_query_history_errors(rotkehlchen_api_server):
    """Test that errors in the history query REST API endpoint are handled properly"""
    # invalid from timestamp value
    response = requests.get(
        api_url_for(rotkehlchen_api_server, "historyprocessingresource"),
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
        api_url_for(rotkehlchen_api_server, "historyprocessingresource"),
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
        api_url_for(rotkehlchen_api_server, "historyprocessingresource"),
        json={'from_timestamp': 0, 'to_timestamp': 1, 'async_query': 'boo'},
    )
    assert_error_response(
        response=response,
        contained_in_msg="async_query': ['Not a valid boolean",
        status_code=HTTPStatus.BAD_REQUEST,
    )
