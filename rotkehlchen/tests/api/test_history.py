import csv
import os
from contextlib import ExitStack
from http import HTTPStatus
from pathlib import Path

import pytest
import requests

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.csv_exporter import (
    FILENAME_ALL_CSV,
    FILENAME_ASSET_MOVEMENTS_CSV,
    FILENAME_GAS_CSV,
    FILENAME_LOAN_PROFITS_CSV,
    FILENAME_MARGIN_CSV,
    FILENAME_TRADES_CSV,
)
from rotkehlchen.exchanges.manager import SUPPORTED_EXCHANGES
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response,
    wait_for_async_task,
)
from rotkehlchen.tests.utils.history import prepare_rotki_for_history_processing_test, prices
from rotkehlchen.utils.misc import create_timestamp


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
            api_url_for(rotkehlchen_api_server_with_exchanges, "historyprocessingresource"),
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

    # And now make sure that warnings have also been generated for the query of
    # the unsupported/unknown assets
    warnings = rotki.msg_aggregator.consume_warnings()
    assert len(warnings) == 13
    assert 'kraken trade with unknown asset IDONTEXISTTOO' in warnings[0]
    assert 'unknown kraken asset IDONTEXIST. Ignoring its deposit/withdrawals query' in warnings[1]
    msg = 'unknown kraken asset IDONTEXISTEITHER. Ignoring its deposit/withdrawals query'
    assert msg in warnings[2]
    assert 'poloniex trade with unknown asset NOEXISTINGASSET' in warnings[3]
    assert 'poloniex trade with unsupported asset BALLS' in warnings[4]
    assert 'withdrawal of unknown poloniex asset IDONTEXIST' in warnings[5]
    assert 'withdrawal of unsupported poloniex asset DIS' in warnings[6]
    assert 'deposit of unknown poloniex asset IDONTEXIST' in warnings[7]
    assert 'deposit of unsupported poloniex asset EBT' in warnings[8]
    assert 'poloniex loan with unsupported asset BDC' in warnings[9]
    assert 'poloniex loan with unknown asset NOTEXISTINGASSET' in warnings[10]
    assert 'bittrex trade with unsupported asset PTON' in warnings[11]
    assert 'bittrex trade with unknown asset IDONTEXIST' in warnings[12]

    errors = rotki.msg_aggregator.consume_errors()
    assert len(errors) == 3
    assert 'kraken trade with unprocessable pair IDONTEXISTZEUR' in errors[0]
    assert 'kraken trade with unprocessable pair %$#%$#%$#%$#%$#%' in errors[1]
    assert 'bittrex trade with unprocessable pair %$#%$#%#$%' in errors[2]


@pytest.mark.parametrize(
    'added_exchanges',
    [('binance', 'poloniex', 'bittrex', 'bitmex', 'kraken')],
)
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
            api_url_for(rotkehlchen_api_server_with_exchanges, "historyprocessingresource"),
        )

    assert_proper_response(response)
    data = response.json()
    warnings = rotki.msg_aggregator.consume_warnings()
    assert len(warnings) == 0
    errors = rotki.msg_aggregator.consume_errors()
    assert len(errors) == 1
    assert 'Etherscan returned invalid JSON response: [{' in errors[0]

    # The history processing is completely mocked away and omitted in this test.
    # because it is only for the history creation not its processing.
    # For history processing tests look at test_accounting.py and
    # test_accounting_events.py
    assert 'invalid JSON' in data['message']
    assert 'Binance' in data['message']
    assert 'Bittrex' in data['message']
    assert 'Bitmex' in data['message']
    assert 'Kraken' in data['message']
    assert 'Poloniex' in data['message']
    assert data['result'] == {}


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

    response = requests.get(
        api_url_for(rotkehlchen_api_server_with_exchanges, "periodicdataresource"),
    )
    assert_proper_response(response)
    data = response.json()
    assert data['result']['last_balance_save'] == 0
    assert data['result']['eth_node_connection'] is False
    assert data['result']['history_process_start_ts'] == 1428994442
    assert data['result']['history_process_current_ts'] == end_ts


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


def assert_csv_export_response(response, profit_currency, csv_dir):
    assert_proper_response(response)
    data = response.json()
    assert data['message'] == ''
    assert data['result'] is True

    # and check the csv files were generated succesfully. Here we are only checking
    # for valid CSV and not for the values to be valid.
    # TODO: In the future make a test that checks the values are also valid
    with open(os.path.join(csv_dir, FILENAME_TRADES_CSV), newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        count = 0
        for row in reader:
            assert len(row) == 14
            assert row['type'] in ('buy', 'sell')
            assert Asset(row['asset']).identifier is not None
            assert FVal(row[f'fee_in_{profit_currency.identifier}']) >= ZERO
            assert FVal(row[f'price_in_{profit_currency.identifier}']) >= ZERO
            assert FVal(row[f'fee_in_{profit_currency.identifier}']) is not None
            assert FVal(row[f'gained_or_invested_{profit_currency.identifier}']) is not None
            assert FVal(row['amount']) > ZERO
            assert row['taxable_amount'] is not None
            assert Asset(row['exchanged_for']).identifier is not None
            key = f'exchanged_asset_{profit_currency.identifier}_exchange_rate'
            assert FVal(row[key]) >= ZERO
            key = f'taxable_bought_cost_in_{profit_currency.identifier}'
            assert row[key] is not None
            assert FVal(row[f'taxable_gain_in_{profit_currency.identifier}']) >= ZERO
            assert row[f'taxable_profit_loss_in_{profit_currency.identifier}'] is not None
            assert create_timestamp(row['time'], '%d/%m/%Y %H:%M:%S') > 0
            assert row['is_virtual'] in ('True', 'False')

            count += 1
    num_trades = 18
    assert count == num_trades, 'Incorrect amount of trade CSV entries found'

    with open(os.path.join(csv_dir, FILENAME_LOAN_PROFITS_CSV), newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        count = 0
        for row in reader:
            assert len(row) == 6
            assert create_timestamp(row['open_time'], '%d/%m/%Y %H:%M:%S') > 0
            assert create_timestamp(row['close_time'], '%d/%m/%Y %H:%M:%S') > 0
            assert Asset(row['gained_asset']).identifier is not None
            assert FVal(row['gained_amount']) > ZERO
            assert FVal(row['lent_amount']) > ZERO
            assert FVal(row[f'profit_in_{profit_currency.identifier}']) > ZERO
            count += 1
    num_loans = 2
    assert count == num_loans, 'Incorrect amount of loans CSV entries found'

    with open(os.path.join(csv_dir, FILENAME_ASSET_MOVEMENTS_CSV), newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        count = 0
        for row in reader:
            assert len(row) == 6
            assert create_timestamp(row['time'], '%d/%m/%Y %H:%M:%S') > 0
            assert row['exchange'] in SUPPORTED_EXCHANGES
            assert row['type'] in ('deposit', 'withdrawal')
            assert Asset(row['moving_asset']).identifier is not None
            assert FVal(row['fee_in_asset']) >= ZERO
            assert FVal(row[f'fee_in_{profit_currency.identifier}']) >= ZERO
            count += 1
    num_asset_movements = 11
    assert count == num_asset_movements, 'Incorrect amount of asset movement CSV entries found'

    with open(os.path.join(csv_dir, FILENAME_GAS_CSV), newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        count = 0
        for row in reader:
            assert len(row) == 4
            assert create_timestamp(row['time'], '%d/%m/%Y %H:%M:%S') > 0
            assert row['transaction_hash'] is not None
            assert FVal(row['eth_burned_as_gas']) > ZERO
            assert FVal(row[f'cost_in_{profit_currency.identifier}']) > ZERO
            count += 1
    num_transactions = 3
    assert count == num_transactions, 'Incorrect amount of transaction costs CSV entries found'

    with open(os.path.join(csv_dir, FILENAME_MARGIN_CSV), newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        count = 0
        for row in reader:
            assert len(row) == 5
            assert row['name'] is not None
            assert create_timestamp(row['time'], '%d/%m/%Y %H:%M:%S') > 0
            assert Asset(row['gain_loss_asset']).identifier is not None
            assert FVal(row['gain_loss_amount']) is not None
            assert FVal(row[f'profit_loss_in_{profit_currency.identifier}']) is not None
            count += 1
    num_margins = 2
    assert count == num_margins, 'Incorrect amount of margin CSV entries found'

    # None of this in the current history. TODO: add
    # with open(os.path.join(csv_dir, FILENAME_LOAN_SETTLEMENTS_CSV), newline='') as csvfile:
    #     reader = csv.DictReader(csvfile)
    #     count = 0
    #     for row in reader:
    #         assert len(row) == 6
    #         assert Asset(row['asset']).identifier is not None
    #         assert FVal(row['amount']) is not None
    #         assert FVal(row[f'price_in_{profit_currency.identifier}']) > ZERO
    #         assert FVal(row[f'fee_in_{profit_currency.identifier}']) >= ZERO
    #         assert row[f'loss_in_{profit_currency.identifier}'] is not None
    #         assert create_timestamp(row['time'], '%d/%m/%Y %H:%M:%S') > 0
    #         count += 1
    # num_loan_settlements = 2
    # assert count == num_loan_settlements, 'Incorrect amount of loan settlement CSV entries found'

    with open(os.path.join(csv_dir, FILENAME_ALL_CSV), newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        count = 0
        for row in reader:
            assert len(row) == 12
            assert row['type'] in (
                'buy',
                'sell',
                'asset_movement',
                'tx_gas_cost',
                'interest_rate_payment',
                'margin_position_close',
            )
            paid_asset = row['paid_asset']
            if paid_asset != '':
                assert Asset(paid_asset).identifier is not None
            assert FVal(row['paid_in_asset']) >= ZERO
            assert row['taxable_amount'] is not None
            received_asset = row['received_asset']
            if received_asset != '':
                assert Asset(received_asset).identifier is not None
            assert FVal(row['received_in_asset']) >= ZERO
            assert row['net_profit_or_loss'] is not None
            assert create_timestamp(row['time'], '%d/%m/%Y %H:%M:%S') > 0
            assert row['is_virtual'] in ('True', 'False')
            assert FVal(row[f'paid_in_{profit_currency.identifier}']) >= ZERO
            assert row[f'taxable_received_in_{profit_currency.identifier}'] is not None
            assert row[f'taxable_bought_cost_in_{profit_currency.identifier}'] is not None
            count += 1
    assert count == (
        num_trades + num_loans + num_asset_movements + num_transactions + num_margins
    )


@pytest.mark.parametrize(
    'added_exchanges',
    [('binance', 'poloniex', 'bittrex', 'bitmex', 'kraken')],
)
@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_history_export_csv(
        rotkehlchen_api_server_with_exchanges,
        tmpdir_factory,
):
    """Test that the csv export REST API endpoint works correctly"""
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    profit_currency = rotki.data.db.get_main_currency()
    setup = prepare_rotki_for_history_processing_test(
        rotki,
        should_mock_history_processing=False,
    )
    csv_dir = str(tmpdir_factory.mktemp('test_csv_dir'))
    csv_dir2 = str(tmpdir_factory.mktemp('test_csv_dir2'))

    # First, query history processing to have data for exporting
    with ExitStack() as stack:
        for manager in setup:
            if manager is None:
                continue
            stack.enter_context(manager)
        response = requests.get(
            api_url_for(rotkehlchen_api_server_with_exchanges, "historyprocessingresource"),
        )
    assert_proper_response(response)

    # now query the export endpoint with json body
    response = requests.get(
        api_url_for(rotkehlchen_api_server_with_exchanges, "historyexportingresource"),
        json={'directory_path': csv_dir},
    )
    assert_csv_export_response(response, profit_currency, csv_dir)
    # now query the export endpoint with query params
    response = requests.get(
        api_url_for(rotkehlchen_api_server_with_exchanges, "historyexportingresource") +
        f'?directory_path={csv_dir2}',
    )
    assert_csv_export_response(response, profit_currency, csv_dir2)


@pytest.mark.parametrize(
    'added_exchanges',
    [('binance', 'poloniex', 'bittrex', 'bitmex', 'kraken')],
)
@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_history_export_csv_errors(
        rotkehlchen_api_server_with_exchanges,
        tmpdir_factory,
):
    """Test that errors on the csv export REST API endpoint are handled correctly"""
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    setup = prepare_rotki_for_history_processing_test(
        rotki,
        should_mock_history_processing=False,
    )
    csv_dir = str(tmpdir_factory.mktemp('test_csv_dir'))

    # Query the export endpoint without first having queried the history
    response = requests.get(
        api_url_for(rotkehlchen_api_server_with_exchanges, "historyexportingresource"),
        json={'directory_path': csv_dir},
    )
    assert_error_response(
        response=response,
        contained_in_msg='No history processed in order to perform an export',
        status_code=HTTPStatus.CONFLICT,
    )

    # Now, query history processing to have data for exporting
    with ExitStack() as stack:
        for manager in setup:
            if manager is None:
                continue
            stack.enter_context(manager)
        response = requests.get(
            api_url_for(rotkehlchen_api_server_with_exchanges, "historyprocessingresource"),
        )
    assert_proper_response(response)

    # And now provide non-existing path for directory
    response = requests.get(
        api_url_for(rotkehlchen_api_server_with_exchanges, "historyexportingresource"),
        json={'directory_path': '/idont/exist/for/sure/'},
    )
    assert_error_response(
        response=response,
        contained_in_msg="'directory_path': ['Given path /idont/exist/for/sure/ does not exist",
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # And now provide valid path but not directory
    tempfile = Path(Path(csv_dir) / 'f.txt')
    tempfile.touch()
    response = requests.get(
        api_url_for(rotkehlchen_api_server_with_exchanges, "historyexportingresource"),
        json={'directory_path': str(tempfile)},
    )
    assert_error_response(
        response=response,
        contained_in_msg='is not a directory',
        status_code=HTTPStatus.BAD_REQUEST,
    )
