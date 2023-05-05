"""After removal of reports, this test file does not test the new way of querying
trades, deposits and withdrawals.


Lefteris tested with his own coinbase pro account at 21/03/2021 and they do work though.

TODO: Make some mock tests at some point
"""


import warnings as test_warnings
from enum import Enum
from typing import Literal
from unittest.mock import patch

from rotkehlchen.constants.assets import A_BAT, A_ETH
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.exchanges.coinbasepro import Coinbasepro, coinbasepro_to_worldpair
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import Location

PRODUCTS_RESPONSE = """[{
"id": "BAT-ETH",
 "base_currency": "BAT",
 "quote_currency": "ETH",
 "base_min_size": "1.0",
 "base_max_size": "2500000.0",
 "quote_increment": "0.000001",
 "base_increment": "1.0",
 "display_name": "BAT/ETH",
 "min_market_funds": "0.1",
 "max_market_funds": "100000.0",
 "margin_enabled": false,
 "post_only": false,
 "limit_only": true,
 "cancel_only": false,
 "status": "online",
 "status_message": ""}]"""

ETH_ACCOUNT_ID = 'e316cb9a-0808-4fd7-8914-97829c1925de'
BAT_ACCOUNT_ID = '71452118-efc7-4cc4-8780-a5e22d4baa53'

ETH_ACCOUNTS = f"""{{
"id": "{ETH_ACCOUNT_ID}",
"currency": "ETH",
"balance": "2.5",
"available": "2.15",
"hold": "0.35",
"profile_id": "75da88c5-05bf-4f54-bc85-5c775bd68254"
}}"""

ACCOUNTS_RESPONSE = f"""[{{
"id": "{BAT_ACCOUNT_ID}",
"currency": "BAT",
"balance": "10.5000000000",
"available": "10.00000000",
"hold": "0.5000000000000000",
"profile_id": "75da88c5-05bf-4f54-bc85-5c775bd68254"
}},{ETH_ACCOUNTS}]"""


UNKNOWN_ASSET_ACCOUNTS_RESPONSE = f"""[{{
"id": "71452118-efc7-4cc4-8780-a5e22d4baa53",
"currency": "UNKNOWN",
"balance": "10.5000000000",
"available": "10.00000000",
"hold": "0.5000000000000000",
"profile_id": "75da88c5-05bf-4f54-bc85-5c775bd68254"
}},{ETH_ACCOUNTS}]"""

INVALID_ACCOUNTS_RESPONSE = '[{"id": "71452118-efc7-4cc4-8780-a5e22d4baa53",,,}]'
KEYERROR_ACCOUNTS_RESPONSE = f'[{{"id": "foo"}}, {ETH_ACCOUNTS}]'


class ErrorEmulation(Enum):
    NONE = 0
    UNKNOWN_ASSET = 1
    INVALID_RESPONSE = 2
    KEY_ERROR = 3
    INVALID_RESPONSE_POST_REPORT = 4
    INVALID_RESPONSE_GET_REPORT = 5
    ASSET_MOVEMENTS_WRONG_FORMAT = 6


def create_coinbasepro_query_mock(
        cb: Coinbasepro,
        emulate_errors: ErrorEmulation = ErrorEmulation.NONE,
):

    def mock_coinbasepro_request(
            request_method: Literal['get', 'post'],  # pylint: disable=unused-argument
            url: str,
            timeout: int,  # pylint: disable=unused-argument
            data: str = '',  # pylint: disable=unused-argument
            allow_redirects: bool = True,  # pylint: disable=unused-argument
    ) -> MockResponse:
        if 'products' in url:
            # just return one product so not too many requests happen during tests
            text = PRODUCTS_RESPONSE
        elif 'accounts' in url:
            if emulate_errors == ErrorEmulation.UNKNOWN_ASSET:
                text = UNKNOWN_ASSET_ACCOUNTS_RESPONSE
            elif emulate_errors == ErrorEmulation.INVALID_RESPONSE:
                text = INVALID_ACCOUNTS_RESPONSE
            elif emulate_errors == ErrorEmulation.KEY_ERROR:
                text = KEYERROR_ACCOUNTS_RESPONSE
            else:
                text = ACCOUNTS_RESPONSE
        else:
            raise AssertionError(f'Unknown url: {url} encountered during CoinbasePro mocking')
        return MockResponse(200, text)

    coinbasepro_mock = patch.object(cb.session, 'request', side_effect=mock_coinbasepro_request)
    return coinbasepro_mock


def test_name():
    exchange = Coinbasepro('coinbasepro1', 'a', b'a', object(), object(), '')
    assert exchange.location == Location.COINBASEPRO
    assert exchange.name == 'coinbasepro1'


def test_coverage_of_products():
    """Test that we can process all pairs and assets of the offered coinbasepro products"""
    exchange = Coinbasepro('coinbasepro1', 'a', b'a', object(), object(), '')
    products, _ = exchange._api_query('products', request_method='GET')
    for product in products:
        try:
            # Make sure all products can be processed
            coinbasepro_to_worldpair(product['id'])
        except UnknownAsset as e:
            test_warnings.warn(UserWarning(
                f'Found unknown asset {e.identifier} in Coinbase Pro. '
                f'Support for it has to be added',
            ))


def test_query_balances(function_scope_coinbasepro):
    """Test that querying balances from coinbasepro works fine"""
    cb = function_scope_coinbasepro

    cb_mock = create_coinbasepro_query_mock(cb)
    with cb_mock:
        balances, message = cb.query_balances()

    assert message == ''
    assert len(balances) == 2
    assert balances[A_BAT].amount == FVal('10.5')
    assert balances[A_BAT].usd_value == FVal('15.75')
    assert balances[A_ETH].amount == FVal('2.5')
    assert balances[A_ETH].usd_value == FVal('3.75')


def test_query_balances_unknown_asset(function_scope_coinbasepro):
    """Test that unknown assets are handled when querying balances from coinbasepro"""
    cb = function_scope_coinbasepro

    with create_coinbasepro_query_mock(cb, emulate_errors=ErrorEmulation.UNKNOWN_ASSET):
        balances, message = cb.query_balances()

    assert message == ''
    assert len(balances) == 1
    assert balances[A_ETH].amount == FVal('2.5')
    assert balances[A_ETH].usd_value == FVal('3.75')

    warnings = cb.msg_aggregator.consume_warnings()
    assert len(warnings) == 1
    assert 'Found coinbase pro balance result with unknown asset UNKNOWN' in warnings[0]
    errors = cb.msg_aggregator.consume_errors()
    assert len(errors) == 0


def test_query_balances_invalid_response(function_scope_coinbasepro):
    """Test that an invalid response is handled when querying balances from coinbasepro"""
    cb = function_scope_coinbasepro

    cb_query_mock = create_coinbasepro_query_mock(
        cb,
        emulate_errors=ErrorEmulation.INVALID_RESPONSE,
    )
    with cb_query_mock:
        balances, message = cb.query_balances()

    assert balances is None
    assert 'returned invalid JSON response' in message

    warnings = cb.msg_aggregator.consume_warnings()
    assert len(warnings) == 0
    errors = cb.msg_aggregator.consume_errors()
    assert len(errors) == 0


def test_query_balances_keyerror_response(function_scope_coinbasepro):
    """Test that a key error is handled when querying balances from coinbasepro"""
    cb = function_scope_coinbasepro

    cb_query_mock = create_coinbasepro_query_mock(
        cb,
        emulate_errors=ErrorEmulation.KEY_ERROR,
    )
    with cb_query_mock:
        balances, message = cb.query_balances()

    assert message == ''
    assert len(balances) == 1
    assert balances[A_ETH].amount == FVal('2.5')
    assert balances[A_ETH].usd_value is not None

    warnings = cb.msg_aggregator.consume_warnings()
    assert len(warnings) == 0
    errors = cb.msg_aggregator.consume_errors()
    assert len(errors) == 1
    assert 'Error processing a coinbase pro account balance' in errors[0]
