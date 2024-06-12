from http import HTTPStatus
from typing import Any

import pytest
import requests

from rotkehlchen.accounting.structures.types import ActionType
from rotkehlchen.api.v1.schemas import TradeSchema
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_AAVE, A_BTC, A_DAI, A_ETH, A_EUR, A_GUSD, A_WETH
from rotkehlchen.constants.limits import FREE_TRADES_LIMIT
from rotkehlchen.exchanges.data_structures import Trade
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.accounting import toggle_ignore_an_asset
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response,
    assert_proper_sync_response_with_result,
    assert_simple_ok_response,
)
from rotkehlchen.tests.utils.factories import make_random_trades
from rotkehlchen.tests.utils.history import (
    assert_binance_trades_result,
    assert_poloniex_trades_result,
    mock_history_processing_and_exchanges,
)
from rotkehlchen.types import AssetAmount, Fee, Location, Price, Timestamp, TradeType
from rotkehlchen.utils.misc import ts_now


@pytest.mark.parametrize('added_exchanges', [(Location.BINANCE, Location.POLONIEX)])
@pytest.mark.parametrize('start_with_valid_premium', [False, True])
def test_query_trades(rotkehlchen_api_server_with_exchanges, start_with_valid_premium):
    """Test that querying the trades endpoint works as expected

    Many similarities with test_exchanges.py::test_exchange_query_trades since
    those two endpoints got merged.
    """
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    setup = mock_history_processing_and_exchanges(rotki)

    # Simply get all trades without any filtering
    with setup.binance_patch, setup.polo_patch:
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                'tradesresource',
            ),
        )
    result = assert_proper_sync_response_with_result(response)
    result = result['entries']
    assert len(result) == 5  # 3 polo and 2 binance trades
    binance_ids = [t['entry']['trade_id'] for t in result if t['entry']['location'] == 'binance']
    assert_binance_trades_result([t['entry'] for t in result if t['entry']['location'] == 'binance'])  # noqa: E501
    assert_poloniex_trades_result([t['entry'] for t in result if t['entry']['location'] == 'poloniex'])  # noqa: E501
    msg = 'should have no ignored trades at start'
    assert all(t['ignored_in_accounting'] is False for t in result), msg

    # now also try to ignore all binance trades for accounting
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            'ignoredactionsresource',
        ), json={'action_type': 'trade', 'data': binance_ids},
    )
    assert_simple_ok_response(response)
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    with rotki.data.db.conn.read_ctx() as cursor:
        result = rotki.data.db.get_ignored_action_ids(cursor, None)
    assert result[ActionType.TRADE] == set(binance_ids)

    def assert_okay(response):
        """Helper function to run next query and its assertion twice"""
        result = assert_proper_sync_response_with_result(response)['entries']
        assert len(result) == 2  # only 2 binance trades
        assert_binance_trades_result([t['entry'] for t in result if t['entry']['location'] == 'binance'])  # noqa: E501
        msg = 'binance trades should now be ignored for accounting'
        assert all(t['ignored_in_accounting'] is True for t in result if t['entry']['location'] == 'binance'), msg  # noqa: E501

    # Now filter by location with json body
    with setup.binance_patch, setup.polo_patch:
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                'tradesresource',
            ), json={'location': 'binance'},
        )
    assert_okay(response)
    # Now filter by location with query params
    with setup.binance_patch, setup.polo_patch:
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                'tradesresource',
            ) + '?location=binance',
        )
    assert_okay(response)

    # Now filter by time
    with setup.binance_patch, setup.polo_patch:
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                'tradesresource',
            ), json={'from_timestamp': 1512561942, 'to_timestamp': 1539713237},
        )
    result = assert_proper_sync_response_with_result(response)['entries']
    assert len(result) == 3  # 1 binance trade and 2 poloniex trades
    assert_binance_trades_result(
        trades=[t['entry'] for t in result if t['entry']['location'] == 'binance'],
        trades_to_check=(0,),
    )
    assert_poloniex_trades_result(
        trades=[t['entry'] for t in result if t['entry']['location'] == 'poloniex'],
        trades_to_check=(1, 2),
    )

    # filter by both time and location
    with setup.binance_patch, setup.polo_patch:
        data = {'from_timestamp': 1512561942, 'to_timestamp': 1539713237, 'location': 'poloniex'}
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                'tradesresource',
            ), json=data,
        )
    result = assert_proper_sync_response_with_result(response)['entries']
    assert len(result) == 2  # only 2/3 poloniex trades
    assert_poloniex_trades_result(
        trades=[t['entry'] for t in result if t['entry']['location'] == 'poloniex'],
        trades_to_check=(1, 2),
    )

    # test pagination
    data = {'location': 'poloniex', 'offset': 1, 'limit': 1, 'only_cache': True}
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            'tradesresource',
        ), json=data,
    )
    result = assert_proper_sync_response_with_result(response)
    assert result['entries_limit'] == -1 if start_with_valid_premium else FREE_TRADES_LIMIT
    assert result['entries_total'] == 5
    assert result['entries_found'] == 3  # for this filter
    result = result['entries']
    assert len(result) == 1  # this filter and pagination
    assert_poloniex_trades_result(
        trades=[t['entry'] for t in result if t['entry']['location'] == 'poloniex'],
        trades_to_check=(1,),
    )

    def assert_order_by(order_by: str):
        """A helper to keep things DRY in the test"""
        data = {'order_by_attributes': [order_by], 'ascending': [False], 'only_cache': True}
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                'tradesresource',
            ), json=data,
        )
        result = assert_proper_sync_response_with_result(response)
        assert result['entries_limit'] == -1 if start_with_valid_premium else FREE_TRADES_LIMIT
        assert result['entries_total'] == 5
        assert result['entries_found'] == 5
        desc_result = result['entries']
        assert len(desc_result) == 5
        data = {'order_by_attributes': [order_by], 'ascending': [True], 'only_cache': True}
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                'tradesresource',
            ), json=data,
        )
        result = assert_proper_sync_response_with_result(response)
        assert result['entries_limit'] == -1 if start_with_valid_premium else FREE_TRADES_LIMIT
        assert result['entries_total'] == 5
        assert result['entries_found'] == 5
        asc_result = result['entries']
        assert len(asc_result) == 5
        return desc_result, asc_result

    # test order by location
    desc_result, asc_result = assert_order_by('location')
    assert all(x['entry']['location'] == 'binance' for x in desc_result[:2])
    assert all(x['entry']['location'] == 'poloniex' for x in desc_result[2:])
    assert all(x['entry']['location'] == 'poloniex' for x in asc_result[:3])
    assert all(x['entry']['location'] == 'binance' for x in asc_result[3:])

    # test order by type
    desc_result, asc_result = assert_order_by('type')
    assert all(x['entry']['trade_type'] == 'sell' for x in desc_result[:2])
    assert all(x['entry']['trade_type'] == 'buy' for x in desc_result[2:])
    assert all(x['entry']['trade_type'] == 'buy' for x in asc_result[:3])
    assert all(x['entry']['trade_type'] == 'sell' for x in asc_result[3:])

    # test order by amount
    desc_result, asc_result = assert_order_by('amount')
    for idx, x in enumerate(desc_result):
        if idx < len(desc_result) - 1:
            assert FVal(x['entry']['amount']) >= FVal(desc_result[idx + 1]['entry']['amount'])
    for idx, x in enumerate(asc_result):
        if idx < len(asc_result) - 1:
            assert FVal(x['entry']['amount']) <= FVal(asc_result[idx + 1]['entry']['amount'])

    # test order by rate
    desc_result, asc_result = assert_order_by('rate')
    for idx, x in enumerate(desc_result):
        if idx < len(desc_result) - 1:
            assert FVal(x['entry']['rate']) >= FVal(desc_result[idx + 1]['entry']['rate'])
    for idx, x in enumerate(asc_result):
        if idx < len(asc_result) - 1:
            assert FVal(x['entry']['rate']) <= FVal(asc_result[idx + 1]['entry']['rate'])

    # test order by fee
    desc_result, asc_result = assert_order_by('fee')
    for idx, x in enumerate(desc_result):
        if idx < len(desc_result) - 1:
            assert FVal(x['entry']['fee']) >= FVal(desc_result[idx + 1]['entry']['fee'])
    for idx, x in enumerate(asc_result):
        if idx < len(asc_result) - 1:
            assert FVal(x['entry']['fee']) <= FVal(asc_result[idx + 1]['entry']['fee'])


def test_query_trades_errors(rotkehlchen_api_server_with_exchanges):
    """Test that the trades endpoint handles invalid get requests properly"""
    # Test that invalid value for from_timestamp is handled
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            'tradesresource',
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
            'tradesresource',
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
            'tradesresource',
        ), json={'location': 3452},
    )
    assert_error_response(
        response=response,
        contained_in_msg='Failed to deserialize Location value from non string value',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # Test that non-existing location is handled
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            'tradesresource',
        ), json={'location': 'foo'},
    )
    assert_error_response(
        response=response,
        contained_in_msg='Failed to deserialize Location value foo',
        status_code=HTTPStatus.BAD_REQUEST,
    )


@pytest.mark.parametrize('start_with_valid_premium', [False, True])
@pytest.mark.parametrize('added_exchanges', [(Location.BINANCE, Location.POLONIEX)])
def test_query_trades_over_limit(rotkehlchen_api_server_with_exchanges, start_with_valid_premium):
    """
    Test querying the trades endpoint with trades over the limit limits the result if non premium
    """
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    setup = mock_history_processing_and_exchanges(rotki)

    spam_trades = [Trade(
        timestamp=x,
        location=Location.EXTERNAL,
        base_asset=A_BTC,
        quote_asset=A_EUR,
        trade_type=TradeType.BUY,
        amount=FVal(x + 1),
        rate=ONE,
        fee=ZERO,
        fee_currency=A_EUR,
        link='',
        notes='') for x in range(FREE_TRADES_LIMIT + 50)
    ]
    with rotki.data.db.user_write() as cursor:
        rotki.data.db.add_trades(cursor, spam_trades)

    # Check that we get all trades correctly even if we query two times
    for _ in range(2):
        with setup.binance_patch, setup.polo_patch:
            response = requests.get(
                api_url_for(
                    rotkehlchen_api_server_with_exchanges,
                    'tradesresource',
                ),
            )
        result = assert_proper_sync_response_with_result(response)

        all_trades_num = FREE_TRADES_LIMIT + 50 + 5  # 5 = 3 polo and 2 binance
        if start_with_valid_premium:
            assert len(result['entries']) == all_trades_num
            assert result['entries_limit'] == -1
            assert result['entries_found'] == all_trades_num
        else:
            assert len(result['entries']) == FREE_TRADES_LIMIT
            assert result['entries_limit'] == FREE_TRADES_LIMIT
            assert result['entries_found'] == all_trades_num


def test_add_trades(rotkehlchen_api_server):
    """Test that adding trades to the trades endpoint works as expected"""
    new_trades = [{  # own chain to fiat
        'timestamp': 1575640208,
        'location': 'external',
        'base_asset': 'BTC',
        'quote_asset': 'EUR',
        'trade_type': 'buy',
        'amount': '0.5541',
        'rate': '8422.1',
        'fee': '0.55',
        'fee_currency': 'USD',
        'link': 'optional trader identifier',
        'notes': 'optional notes',
    }, {  # own chain to eth token, with some optional fields (link,notes) missing
        'timestamp': 1585640208,
        'location': 'external',
        'base_asset': 'ETH',
        'quote_asset': A_AAVE.identifier,
        'trade_type': 'buy',
        'amount': '0.5541',
        'rate': '8422.1',
        'fee': '0.55',
        'fee_currency': 'USD',
    }, {  # token to token, with all optional fields (fee,fee_currency,link,notes) missing
        'timestamp': 1595640208,
        'location': 'external',
        'base_asset': A_DAI.identifier,
        'quote_asset': A_AAVE.identifier,
        'trade_type': 'buy',
        'amount': '1.5541',
        'rate': '22.1',
    }]
    # add multple trades
    all_expected_trades = []
    for new_trade in new_trades:
        response = requests.put(
            api_url_for(
                rotkehlchen_api_server,
                'tradesresource',
            ), json=new_trade,
        )
        result = assert_proper_sync_response_with_result(response)
        # And check that the identifier is correctly generated when returning the trade
        new_trade['trade_id'] = Trade(**TradeSchema().load(new_trade)).identifier
        expected_trade = new_trade.copy()
        for x in ('fee', 'fee_currency', 'link', 'notes'):
            expected_trade[x] = new_trade.get(x, None)
        assert result == expected_trade
        all_expected_trades.insert(0, expected_trade)
        # and now make sure the trade is saved by querying for it
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                'tradesresource',
            ),
        )
        result = assert_proper_sync_response_with_result(response)
        data = response.json()
        assert data['message'] == ''
        assert result['entries'] == [{'entry': x, 'ignored_in_accounting': False} for x in all_expected_trades]  # noqa: E501

    # Test trade with rate 0. Should fail
    zero_rate_trade = {
        'timestamp': 1575640208,
        'location': 'external',
        'base_asset': 'ETH',
        'quote_asset': A_WETH.identifier,
        'trade_type': 'buy',
        'amount': '0.5541',
        'rate': '0',
        'fee': '0.01',
        'fee_currency': 'USD',
        'link': 'optional trader identifier',
        'notes': 'optional notes',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'tradesresource',
        ), json=zero_rate_trade,
    )
    assert_error_response(
        response=response,
        contained_in_msg='A zero rate is not allowed',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Test trade with negative rate. Should fail
    negative_rate_trade = {
        'timestamp': 1575640208,
        'location': 'external',
        'base_asset': 'ETH',
        'quote_asset': A_WETH.identifier,
        'trade_type': 'buy',
        'amount': '0.5541',
        'rate': '-1',
        'fee': '0.01',
        'fee_currency': 'USD',
        'link': 'optional trader identifier',
        'notes': 'optional notes',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'tradesresource',
        ), json=negative_rate_trade,
    )
    assert_error_response(
        response=response,
        contained_in_msg='A negative price is not allowed',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Test trade with invalid timestamp
    zero_rate_trade = {
        'timestamp': Timestamp(ts_now() + 200),
        'location': 'external',
        'base_asset': 'ETH',
        'quote_asset': A_WETH.identifier,
        'trade_type': 'buy',
        'amount': '0.5541',
        'rate': '1',
        'fee': '0.01',
        'fee_currency': 'USD',
        'link': 'optional trader identifier',
        'notes': 'optional notes',
    }

    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'tradesresource',
        ), json=zero_rate_trade,
    )

    assert_error_response(
        response=response,
        contained_in_msg='Given date cannot be in the future',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Test with fee & without fee_currency
    fee_and_no_fee_currency_trade = {
        'timestamp': 1595640208,
        'location': 'external',
        'base_asset': 'ETH',
        'quote_asset': 'USD',
        'trade_type': 'buy',
        'amount': '1.5541',
        'rate': '22.1',
        'fee': '0.55',
    }

    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'tradesresource',
        ), json=fee_and_no_fee_currency_trade,
    )

    assert_error_response(
        response=response,
        contained_in_msg='fee and fee_currency must be provided',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Test with fee is zero
    fee_is_zero_trade = {
        'timestamp': 1595640208,
        'location': 'external',
        'base_asset': 'ETH',
        'quote_asset': 'USD',
        'trade_type': 'buy',
        'amount': '1.5541',
        'rate': '22.1',
        'fee': '0',
        'fee_currency': 'USD',
    }

    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'tradesresource',
        ), json=fee_is_zero_trade,
    )

    assert_error_response(
        response=response,
        contained_in_msg='fee cannot be zero',
        status_code=HTTPStatus.BAD_REQUEST,
    )


def assert_all_missing_fields_are_handled(correct_trade, server):
    fields = correct_trade.keys()

    for field in fields:
        if field in {'link', 'notes', 'fee', 'fee_currency'}:
            # Optional fields missing is fine
            continue

        broken_trade = correct_trade.copy()
        broken_trade.pop(field)
        response = requests.put(
            api_url_for(
                server,
                'tradesresource',
            ), json=broken_trade,
        )
        assert_error_response(
            response=response,
            contained_in_msg=f'"{field}": ["Missing data for required field',
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
        'base_asset': 'BTC',
        'quote_asset': 'EUR',
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
            'tradesresource',
        ), json=broken_trade,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Failed to deserialize a timestamp entry from string foo',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # Test that invalid location type is handled
    broken_trade = correct_trade.copy()
    broken_trade['location'] = 55
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'tradesresource',
        ), json=broken_trade,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Failed to deserialize Location value from non string value',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # Test that invalid location is handled
    broken_trade = correct_trade.copy()
    broken_trade['location'] = 'foo'
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'tradesresource',
        ), json=broken_trade,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Failed to deserialize Location value foo',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # Test that invalid base_asset type is handled
    broken_trade = correct_trade.copy()
    broken_trade['base_asset'] = 55
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'tradesresource',
        ), json=broken_trade,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Tried to initialize an asset out of a non-string identifier',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # Test that unknown base_asset type is handled
    broken_trade = correct_trade.copy()
    broken_trade['base_asset'] = 'definitelyunknownassetid'
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'tradesresource',
        ), json=broken_trade,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Unknown asset definitelyunknownassetid provided',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # Test that invalid value type for trade_type is handled
    broken_trade = correct_trade.copy()
    broken_trade['trade_type'] = 53
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'tradesresource',
        ), json=broken_trade,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Failed to deserialize trade type symbol from',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # Test that unknown value for trade_type is handled
    broken_trade = correct_trade.copy()
    broken_trade['trade_type'] = 'foo'
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'tradesresource',
        ), json=broken_trade,
    )
    assert_error_response(
        response=response,
        contained_in_msg=(
            'Failed to deserialize trade type symbol. Unknown symbol foo for trade type'
        ),
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # Test that invalid value for amount is handled
    broken_trade = correct_trade.copy()
    broken_trade['amount'] = 'foo'
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'tradesresource',
        ), json=broken_trade,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Failed to deserialize an amount entry',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # Test that negative value for amount is handled
    broken_trade = correct_trade.copy()
    broken_trade['amount'] = '-6.1'
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'tradesresource',
        ), json=broken_trade,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Non-positive amount -6.1 given. Amount should be > 0',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # Test that zero value for amount is handled
    broken_trade = correct_trade.copy()
    broken_trade['amount'] = '0.0'
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'tradesresource',
        ), json=broken_trade,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Non-positive amount 0.0 given. Amount should be > 0',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # Test that invalid value for rate is handled
    broken_trade = correct_trade.copy()
    broken_trade['rate'] = [55, 22]
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'tradesresource',
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
            'tradesresource',
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
            'tradesresource',
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
            'tradesresource',
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
            'tradesresource',
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
            'tradesresource',
        ), json=broken_trade,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Not a valid string',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # Test that '0' value for fee is handled
    broken_trade = correct_trade.copy()
    broken_trade['fee'] = '0'
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'tradesresource',
        ), json=broken_trade,
    )
    assert_error_response(
        response=response,
        contained_in_msg='fee cannot be zero',
        status_code=HTTPStatus.BAD_REQUEST,
    )


def _check_trade_is_edited(original_trade: dict[str, Any], result_trade: dict[str, Any]) -> None:
    for key, value in result_trade.items():
        if key == 'trade_id':
            assert value != original_trade[key]
        elif key == 'amount':
            assert value == '1337.5'
        elif key == 'notes':
            assert value == 'edited trade'
        else:
            assert value == original_trade[key]


@pytest.mark.parametrize('added_exchanges', [(Location.BINANCE, Location.POLONIEX)])
def test_edit_trades(rotkehlchen_api_server_with_exchanges):
    """Test that editing a trade via the trades endpoint works as expected"""
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    setup = mock_history_processing_and_exchanges(rotki)

    # Simply get all trades without any filtering
    with setup.binance_patch, setup.polo_patch:
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                'tradesresource',
            ),
        )
    assert_proper_response(response)
    trades = response.json()['result']['entries']

    # get the binance trades
    original_binance_trades = [t['entry'] for t in trades if t['entry']['location'] == 'binance']

    # get the poloniex trades
    original_poloniex_trades = [t['entry'] for t in trades if t['entry']['location'] == 'poloniex']

    # Test that setting '0' as value for `fee` fails
    original_poloniex_trades[0]['fee'] = '0'
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            'tradesresource',
        ), json=original_poloniex_trades[0],
    )
    assert_error_response(response, contained_in_msg='fee cannot be zero')

    # Test that popping either of `fee` or `fee_currency` fails
    original_poloniex_trades[1].pop('fee', None)
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            'tradesresource',
        ), json=original_poloniex_trades[1],
    )
    assert_error_response(response, contained_in_msg='fee and fee_currency must be provided')

    # Test that setting both `fee` and `fee_currency` passes
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            'tradesresource',
        ), json=original_poloniex_trades[2],
    )
    assert_proper_response(response)

    for trade in original_binance_trades:
        # edit two fields of each binance trade
        trade['amount'] = '1337.5'
        trade['notes'] = 'edited trade'
        response = requests.patch(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                'tradesresource',
            ), json=trade,
        )
        assert_proper_response(response)
        data = response.json()
        assert data['message'] == ''
        # check that the returned trade is edited
        _check_trade_is_edited(original_trade=trade, result_trade=data['result'])

    # Finally also query binance trades to see they are edited
    with setup.binance_patch, setup.polo_patch:
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                'tradesresource',
            ), json={'location': 'binance'},
        )
    trades = assert_proper_sync_response_with_result(response)['entries']
    assert len(trades) == 2  # only 2 binance trades
    for idx, trade in enumerate(trades):
        _check_trade_is_edited(original_trade=original_binance_trades[idx], result_trade=trade['entry'])  # noqa: E501


def test_edit_trades_errors(rotkehlchen_api_server):
    """Test that editing a trade with non-existing or invalid id is handled properly"""
    trade = {
        'timestamp': 1575640208,
        'location': 'external',
        'base_asset': 'BTC',
        'quote_asset': 'EUR',
        'trade_type': 'buy',
        'amount': '0.5541',
        'rate': '8422.1',
        'fee': '0.55',
        'fee_currency': 'USD',
        'link': 'optional trader identifier',
        'notes': 'optional notes',
    }
    # check that editing a trade without giving a trade id is handled as an error
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'tradesresource',
        ), json=trade,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Missing data for required field',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    trade['trade_id'] = 'this_id_does_not_exit'
    # Check that non-existing trade id is handled
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'tradesresource',
        ), json=trade,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Tried to edit non existing trade id',
        status_code=HTTPStatus.CONFLICT,
    )
    # Check that invalid trade_id type is handled
    trade['trade_id'] = 523
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'tradesresource',
        ), json=trade,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Not a valid string',
        status_code=HTTPStatus.BAD_REQUEST,
    )


@pytest.mark.parametrize('added_exchanges', [(Location.BINANCE, Location.POLONIEX)])
def test_delete_trades(rotkehlchen_api_server_with_exchanges):
    """Test that deleting a trade via the trades endpoint works as expected"""
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    setup = mock_history_processing_and_exchanges(rotki)

    # Simply get all trades without any filtering
    with setup.binance_patch, setup.polo_patch:
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                'tradesresource',
            ),
        )
    trades = assert_proper_sync_response_with_result(response)['entries']

    # get the poloniex trade ids
    poloniex_trade_ids = [t['entry']['trade_id'] for t in trades if t['entry']['location'] == 'poloniex']  # noqa: E501
    # delete all poloniex trades
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            'tradesresource',
        ), json={'trades_ids': poloniex_trade_ids},
    )
    assert_proper_response(response)
    data = response.json()
    assert data['message'] == ''
    assert data['result'] is True

    # Finally also query poloniex trades to see they no longer exist
    with setup.binance_patch, setup.polo_patch:
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                'tradesresource',
            ), json={'location': 'poloniex'},
        )
    trades = assert_proper_sync_response_with_result(response)['entries']
    assert len(trades) == 0


def test_delete_trades_trades_errors(rotkehlchen_api_server):
    """Test that errors at the deleting a trade endpoint are handled properly"""
    # Check that omitting the trade id is handled
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'tradesresource',
        ),
    )
    assert_error_response(
        response=response,
        contained_in_msg='Missing data for required field',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Check that providing invalid value for trade id is handled
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'tradesresource',
        ), json={'trades_ids': [55]},
    )
    assert_error_response(
        response=response,
        contained_in_msg='Not a valid string',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # Check that providing non existing trade id is handled
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'tradesresource',
        ), json={'trades_ids': ['this_trade_id_does_not_exist']},
    )
    assert_error_response(
        response=response,
        contained_in_msg='Tried to delete one or more non-existing trade(s)',
        status_code=HTTPStatus.CONFLICT,
    )


@pytest.mark.parametrize('added_exchanges', [(Location.BINANCE, Location.POLONIEX)])
def test_query_trades_associated_locations(rotkehlchen_api_server_with_exchanges):
    """Test that querying the trades endpoint works as expected when we have associated
    locations including associated exchanges and imported locations.
    """
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    setup = mock_history_processing_and_exchanges(rotki)

    trades = [Trade(
        timestamp=Timestamp(1596429934),
        location=Location.EXTERNAL,
        base_asset=A_WETH,
        quote_asset=A_EUR,
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('1')),
        rate=Price(FVal('320')),
        fee=Fee(ZERO),
        fee_currency=A_EUR,
        link='',
        notes='',
    ), Trade(
        timestamp=Timestamp(1596429934),
        location=Location.KRAKEN,
        base_asset=A_WETH,
        quote_asset=A_EUR,
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('1')),
        rate=Price(FVal('320')),
        fee=Fee(ZERO),
        fee_currency=A_EUR,
        link='',
        notes='',
    ), Trade(
        timestamp=Timestamp(1596429934),
        location=Location.BISQ,
        base_asset=A_WETH,
        quote_asset=A_EUR,
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('1')),
        rate=Price(FVal('320')),
        fee=Fee(ZERO),
        fee_currency=A_EUR,
        link='',
        notes='',
    ), Trade(
        timestamp=Timestamp(1596429934),
        location=Location.BINANCE,
        base_asset=A_WETH,
        quote_asset=A_EUR,
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('1')),
        rate=Price(FVal('320')),
        fee=Fee(ZERO),
        fee_currency=A_EUR,
        link='',
        notes='',
    )]

    # Add multiple entries for same exchange + connected exchange
    with rotki.data.db.user_write() as cursor:
        rotki.data.db.add_trades(cursor, trades)

    # Simply get all trades without any filtering
    with setup.binance_patch, setup.polo_patch:
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                'tradesresource',
            ),
        )
    result = assert_proper_sync_response_with_result(response)
    result = result['entries']
    assert len(result) == 9  # 3 polo, (2 + 1) binance trades, 1 kraken, 1 external, 1 BISQ
    expected_locations = (
        Location.KRAKEN,
        Location.POLONIEX,
        Location.BINANCE,
        Location.BISQ,
        Location.EXTERNAL,
    )
    returned_locations = {x['entry']['location'] for x in result}
    assert returned_locations == set(map(str, expected_locations))

    response = requests.get(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            'tradesresource',
        ), json={'location': 'kraken', 'only_cache': True},
    )
    result = assert_proper_sync_response_with_result(response)
    result = result['entries']
    assert len(result) == 1

    response = requests.get(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            'tradesresource',
        ), json={'location': 'binance', 'only_cache': True},
    )
    result = assert_proper_sync_response_with_result(response)
    result = result['entries']
    assert len(result) == 3

    response = requests.get(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            'tradesresource',
        ), json={'location': 'nexo'},
    )
    result = assert_proper_sync_response_with_result(response)
    result = result['entries']
    assert len(result) == 0


def test_ignoring_trades(rotkehlchen_api_server):
    """Check that ignoring trades and ignoring assets filter works as expected."""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    trades = make_random_trades(3)
    trade_to_ignore = trades[0].identifier

    trades[2].base_asset = A_AAVE
    trades[2].quote_asset = A_GUSD
    trade_with_asset_ignored = trades[2].identifier
    asset_to_ignore = A_GUSD

    # populate db with trades
    with rotki.data.db.user_write() as cursor:
        rotki.data.db.add_trades(cursor, trades)

    # ignore a trade
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'ignoredactionsresource',
        ), json={'action_type': 'trade', 'data': [trade_to_ignore]},
    )
    assert_simple_ok_response(response)
    with rotki.data.db.conn.read_ctx() as cursor:
        result = rotki.data.db.get_ignored_action_ids(cursor, None)
    assert result[ActionType.TRADE] == {trade_to_ignore}

    # now fetch trades and check for the behaviour of the `include_ignored_trades` filter
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'tradesresource',
        ), json={'include_ignored_trades': 'True'},
    )
    result = assert_proper_sync_response_with_result(response)
    assert len(result['entries']) == len(trades)
    assert trade_to_ignore in {entry['entry']['trade_id'] for entry in result['entries']}

    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'tradesresource',
        ), json={'include_ignored_trades': 'False'},
    )
    result = assert_proper_sync_response_with_result(response)
    assert len(result['entries']) == len(trades) - 1
    assert trade_to_ignore not in {entry['entry']['trade_id'] for entry in result['entries']}

    # ignore an asset
    toggle_ignore_an_asset(rotkehlchen_api_server, asset_to_ignore)

    # now fetch trades and check for the behaviour of the `exclude_ignored_assets` filter
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'tradesresource',
        ), json={'exclude_ignored_assets': 'True'},
    )
    result = assert_proper_sync_response_with_result(response)
    assert len(result['entries']) == len(trades) - 1
    assert trade_with_asset_ignored not in {
        entry['entry']['trade_id'] for entry in result['entries']
    }

    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'tradesresource',
        ), json={'exclude_ignored_assets': 'False'},
    )
    result = assert_proper_sync_response_with_result(response)
    assert len(result['entries']) == len(trades)
    assert trade_with_asset_ignored in {entry['entry']['trade_id'] for entry in result['entries']}


def test_ignoring_trades_with_pagination(rotkehlchen_api_server):
    """Check that pagination is respected when `include_ignored_trades` is True."""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    trades = make_random_trades(5, base_asset=A_ETH)
    trades.extend(make_random_trades(5, base_asset=A_BTC))
    trades.sort(key=lambda x: x.timestamp)
    trades_to_ignore = [trades[0].identifier, trades[1].identifier]

    # populate db with trades
    with rotki.data.db.user_write() as cursor:
        rotki.data.db.add_trades(cursor, trades)

    # ignore two trades
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'ignoredactionsresource',
        ), json={'action_type': 'trade', 'data': trades_to_ignore},
    )
    assert_simple_ok_response(response)
    with rotki.data.db.conn.read_ctx() as cursor:
        result = rotki.data.db.get_ignored_action_ids(cursor, None)
    assert result[ActionType.TRADE] == set(trades_to_ignore)

    # now fetch trades with pagination and `include_ignored_trades` is False
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'tradesresource',
        ), json={
            'include_ignored_trades': 'False',
            'limit': 7,
            'offset': 0,
        },
    )
    result = assert_proper_sync_response_with_result(response)
    assert len(result['entries']) == 7
    assert result['entries_found'] == 8
    assert result['entries_total'] == len(trades)
    assert all(entry['entry']['trade_id'] not in trades_to_ignore for entry in result['entries'])

    # now fetch trades with pagination and `include_ignored_trades` is True
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'tradesresource',
        ), json={
            'include_ignored_trades': 'True',
            'limit': 7,
            'offset': 0,
        },
    )
    result = assert_proper_sync_response_with_result(response)
    assert len(result['entries']) == 7
    assert result['entries_found'] == 10
    assert result['entries_total'] == len(trades)

    # ignore an asset and check it works fine with pagination
    toggle_ignore_an_asset(rotkehlchen_api_server, A_ETH)
    # now fetch trades and check that `exclude_ignored_assets` filter works with pagination
    for exclude_ignored_assets, expected_length in ((False, 8), (True, 5)):
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                'tradesresource',
            ), json={
                'exclude_ignored_assets': exclude_ignored_assets,
                'limit': 8,
                'offset': 0,
            },
        )
        result = assert_proper_sync_response_with_result(response)
        assert len(result['entries']) == expected_length
