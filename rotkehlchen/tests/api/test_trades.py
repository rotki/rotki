from http import HTTPStatus

import pytest
import requests

from rotkehlchen.exchanges.data_structures import Trade
from rotkehlchen.tests.utils.api import api_url_for, assert_error_response, assert_proper_response
from rotkehlchen.tests.utils.history import (
    assert_binance_trades_result,
    assert_poloniex_trades_result,
    mock_history_processing_and_exchanges,
)


@pytest.mark.parametrize('added_exchanges', [('binance', 'poloniex')])
def test_query_trades(rotkehlchen_api_server_with_exchanges):
    """Test that querying the trades endpoint works as expected"""
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen

    setup = mock_history_processing_and_exchanges(rotki)

    # Query trades of all exchanges to get them saved in the DB
    with setup.binance_patch, setup.polo_patch:
        response = requests.get(
            api_url_for(rotkehlchen_api_server_with_exchanges, "exchangetradesresource"))
    assert_proper_response(response)

    # Simply get all trades without any filtering
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            "tradesresource",
        ),
    )
    assert_proper_response(response)
    data = response.json()
    assert data['message'] == ''
    assert len(data['result']) == 5  # 3 polo and 2 binance trades
    assert_binance_trades_result([t for t in data['result'] if t['location'] == 'binance'])
    assert_poloniex_trades_result([t for t in data['result'] if t['location'] == 'poloniex'])

    # Now filter by location
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            "tradesresource",
        ), json={'location': 'binance'},
    )
    assert_proper_response(response)
    data = response.json()
    assert data['message'] == ''
    assert len(data['result']) == 2  # only 2 binance trades
    assert_binance_trades_result([t for t in data['result'] if t['location'] == 'binance'])

    # Now filter by time
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            "tradesresource",
        ), json={'from_timestamp': 1512561942, 'to_timestamp': 1539713237},
    )
    assert_proper_response(response)
    data = response.json()
    assert data['message'] == ''
    assert len(data['result']) == 3  # 1 binance trade and 2 poloniex trades
    assert_binance_trades_result(
        trades=[t for t in data['result'] if t['location'] == 'binance'],
        trades_to_check=(1,),
    )
    assert_poloniex_trades_result(
        trades=[t for t in data['result'] if t['location'] == 'poloniex'],
        trades_to_check=(0, 1),
    )

    # and now filter by both time and location
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            "tradesresource",
        ), json={'from_timestamp': 1512561942, 'to_timestamp': 1539713237, 'location': 'poloniex'},
    )
    assert_proper_response(response)
    data = response.json()
    assert data['message'] == ''
    assert len(data['result']) == 2  # only 2/3 poloniex trades
    assert_poloniex_trades_result(
        trades=[t for t in data['result'] if t['location'] == 'poloniex'],
        trades_to_check=(0, 1),
    )


def test_query_trades_errors(rotkehlchen_api_server_with_exchanges):
    """Test that the trades endpoint handles invalid get requests properly"""
    # Test that invalid value for from_timestamp is handled
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            "tradesresource",
        ), json={'from_timestamp': 'fooo'},
    )
    assert_error_response(
        response=response,
        contained_in_msg='Failed to deserialize a timestamp entry from string fooo',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # Test that invalid value for to_timestamp is handled
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            "tradesresource",
        ), json={'to_timestamp': [55.2]},
    )
    assert_error_response(
        response=response,
        contained_in_msg='Failed to deserialize a timestamp entry. Unexpected type',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # Test that invalid type for location is handled
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            "tradesresource",
        ), json={'location': 3452},
    )
    assert_error_response(
        response=response,
        contained_in_msg='Failed to deserialize location symbol',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # Test that non-existing location is handled
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            "tradesresource",
        ), json={'location': 'foo'},
    )
    assert_error_response(
        response=response,
        contained_in_msg='Failed to deserialize location symbol. Unknown symbol foo for location',
        status_code=HTTPStatus.BAD_REQUEST,
    )


def test_add_trades(rotkehlchen_api_server):
    """Test that adding trades to the trades endpoint works as expected"""
    # add a new external trade
    new_trade = {
        'timestamp': 1575640208,
        'location': 'external',
        'pair': 'BTC_EUR',
        'trade_type': 'buy',
        'amount': '0.5541',
        'rate': '8422.1',
        'fee': '0.55',
        'fee_currency': 'USD',
        'link': 'optional trader identifier',
        'notes': 'optional notes',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            "tradesresource",
        ), json=new_trade,
    )
    assert_proper_response(response)
    data = response.json()
    assert data['message'] == ''
    # And check that the identifier is correctly generated when returning the trade
    new_trade['trade_id'] = Trade(**new_trade).identifier
    assert data['result'] == new_trade

    # and now make sure the trade is saved by querying for it
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            "tradesresource",
        ),
    )
    assert_proper_response(response)
    data = response.json()
    assert data['message'] == ''
    assert data['result'] == [new_trade]


def assert_all_missing_fields_are_handled(correct_trade, server):
    fields = correct_trade.keys()

    for field in fields:
        if field in ('link', 'notes'):
            # Optional fields missing is fine
            continue

        broken_trade = correct_trade.copy()
        broken_trade.pop(field)
        response = requests.put(
            api_url_for(
                server,
                "tradesresource",
            ), json=broken_trade,
        )
        assert_error_response(
            response=response,
            contained_in_msg=f"{field}': ['Missing data for required field",
            status_code=HTTPStatus.BAD_REQUEST,
        )


def test_add_trades_errors(rotkehlchen_api_server):
    """Test that adding trades with erroneous data is handled properly

    This test also covers the trade editing errors, since they are handled by
    the same logic
    """
    # add a new external trade
    correct_trade = {
        'timestamp': 1575640208,
        'location': 'external',
        'pair': 'BTC_EUR',
        'trade_type': 'buy',
        'amount': '0.5541',
        'rate': '8422.1',
        'fee': '0.55',
        'fee_currency': 'USD',
        'link': 'optional trader identifier',
        'notes': 'optional notes',
    }

    assert_all_missing_fields_are_handled(correct_trade, rotkehlchen_api_server)
    # Test that invalid timestamp is handled
    broken_trade = correct_trade.copy()
    broken_trade['timestamp'] = 'foo'
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            "tradesresource",
        ), json=broken_trade,
    )
    assert_error_response(
        response=response,
        contained_in_msg="Failed to deserialize a timestamp entry from string foo",
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # Test that invalid location type is handled
    broken_trade = correct_trade.copy()
    broken_trade['location'] = 55
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            "tradesresource",
        ), json=broken_trade,
    )
    assert_error_response(
        response=response,
        contained_in_msg="Failed to deserialize location symbol from",
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # Test that invalid location is handled
    broken_trade = correct_trade.copy()
    broken_trade['location'] = 'foo'
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            "tradesresource",
        ), json=broken_trade,
    )
    assert_error_response(
        response=response,
        contained_in_msg="Failed to deserialize location symbol. Unknown symbol foo for location",
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # Test that invalid pair type is handled
    broken_trade = correct_trade.copy()
    broken_trade['pair'] = 55
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            "tradesresource",
        ), json=broken_trade,
    )
    assert_error_response(
        response=response,
        contained_in_msg="Provided non-string trade pair value 55",
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # Test that unparsable pair is handled
    broken_trade = correct_trade.copy()
    broken_trade['pair'] = 'notapair'
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            "tradesresource",
        ), json=broken_trade,
    )
    assert_error_response(
        response=response,
        contained_in_msg="Unprocessable pair notapair encountered",
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # Test that unknown assets in a pair are handled
    broken_trade = correct_trade.copy()
    broken_trade['pair'] = 'ETH_INVALIDASSET'
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            "tradesresource",
        ), json=broken_trade,
    )
    assert_error_response(
        response=response,
        contained_in_msg="Unknown asset INVALIDASSET found while processing trade pair",
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # Test that invalid value type for trade_type is handled
    broken_trade = correct_trade.copy()
    broken_trade['trade_type'] = 53
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            "tradesresource",
        ), json=broken_trade,
    )
    assert_error_response(
        response=response,
        contained_in_msg="Failed to deserialize trade type symbol from",
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # Test that unknown value for trade_type is handled
    broken_trade = correct_trade.copy()
    broken_trade['trade_type'] = 'foo'
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            "tradesresource",
        ), json=broken_trade,
    )
    assert_error_response(
        response=response,
        contained_in_msg=(
            "Failed to deserialize trade type symbol. Unknown symbol foo for trade type"
        ),
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # Test that invalid value for amount is handled
    broken_trade = correct_trade.copy()
    broken_trade['amount'] = 'foo'
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            "tradesresource",
        ), json=broken_trade,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Failed to deserialize an amount entry',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # Test that invalid value for rate is handled
    broken_trade = correct_trade.copy()
    broken_trade['rate'] = [55, 22]
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            "tradesresource",
        ), json=broken_trade,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Failed to deserialize a price/rate entry',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # Test that invalid value for fee is handled
    broken_trade = correct_trade.copy()
    broken_trade['fee'] = 'foo'
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            "tradesresource",
        ), json=broken_trade,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Failed to deserialize a fee entry',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # Test that invalid value type for fee currency is handled
    broken_trade = correct_trade.copy()
    broken_trade['fee_currency'] = 55
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            "tradesresource",
        ), json=broken_trade,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Tried to initialize an asset out of a non-string identifier',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # Test that non existing asset for fee currency is handled
    broken_trade = correct_trade.copy()
    broken_trade['fee_currency'] = 'NONEXISTINGASSET'
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            "tradesresource",
        ), json=broken_trade,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Unknown asset NONEXISTINGASSET provided',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # Test that invalid value type for link is handled
    broken_trade = correct_trade.copy()
    broken_trade['link'] = 55
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            "tradesresource",
        ), json=broken_trade,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Not a valid string',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # Test that invalid value type for link is handled
    broken_trade = correct_trade.copy()
    broken_trade['notes'] = 55
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            "tradesresource",
        ), json=broken_trade,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Not a valid string',
        status_code=HTTPStatus.BAD_REQUEST,
    )
