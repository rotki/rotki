from contextlib import ExitStack
from datetime import datetime
from http import HTTPStatus
from unittest.mock import call, patch

import pytest
from requests import Response

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.errors import RemoteError, SystemClockNotSyncedError
from rotkehlchen.exchanges.bitfinex import (
    API_KEY_ERROR_CODE,
    API_KEY_ERROR_MESSAGE,
    API_RATE_LIMITS_ERROR_MESSAGE,
    API_SYSTEM_CLOCK_NOT_SYNCED_ERROR_CODE,
    Bitfinex,
    CurrencyMapResponse,
)
from rotkehlchen.exchanges.data_structures import AssetMovement, Trade, TradeType
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.typing import (
    AssetAmount,
    AssetMovementCategory,
    Fee,
    Location,
    Price,
    Timestamp,
    TradePair,
)


def test_name():
    exchange = Bitfinex('a', b'a', object(), object())
    assert exchange.name == str(Location.BITFINEX)


def test_validate_api_key_system_clock_not_synced_error_code(mock_bitfinex):
    """Test the error code related with the local system clock not being synced
    raises SystemClockNotSyncedError.
    """
    def mock_api_query_response(endpoint):  # pylint: disable=unused-argument
        return MockResponse(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            f'["error", {API_SYSTEM_CLOCK_NOT_SYNCED_ERROR_CODE}, "nonce: small"]',
        )

    with patch.object(mock_bitfinex, '_api_query', side_effect=mock_api_query_response):
        with pytest.raises(SystemClockNotSyncedError):
            mock_bitfinex.validate_api_key()


def test_validate_api_key_invalid_key(mock_bitfinex):
    """Test the error code related with an invalid API key/secret returns the
    tuple (False, <invalid api key error message>).
    """
    def mock_api_query_response(endpoint):  # pylint: disable=unused-argument
        return MockResponse(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            f'["error", {API_KEY_ERROR_CODE}, "apikey: invalid"]',
        )

    with patch.object(mock_bitfinex, '_api_query', side_effect=mock_api_query_response):
        result, msg = mock_bitfinex.validate_api_key()

        assert result is False
        assert msg == API_KEY_ERROR_MESSAGE


@pytest.mark.parametrize('should_mock_current_price_queries', [True])
def test_query_balances_asset_balance(mock_bitfinex, inquirer):  # pylint: disable=unused-argument
    """Test a result that can't get its USD price is skipped
    """
    response = Response()
    response.status_code = HTTPStatus.OK
    currency_map_response = CurrencyMapResponse(
        success=True,
        response=response,
        currency_map={
            'UST': 'USDt',
            'GNT': 'GLM',
        },
    )
    balances_data = (
        """
        [
            ["exchange"],
            ["exchange", "UST"],
            ["exchange", "", 12345],
            ["exchange", "WBT", 0.0000000],
            ["margin", "UST", 19788.6529257],
            ["exchange", "", 19788.6529257],
            ["exchange", "UST", 19788.6529257],
            ["exchange", "LINK", 777.777777],
            ["exchange", "GNT", 0.0000001],
            ["exchange", "EUR", 99.9999999]
        ]
        """
    )

    def mock_api_query_response(endpoint):  # pylint: disable=unused-argument
        return MockResponse(HTTPStatus.OK, balances_data)

    currency_map_patch = patch.object(
        target=mock_bitfinex,
        attribute='_query_currency_map',
        return_value=currency_map_response,
    )
    balances_query_patch = patch.object(
        target=mock_bitfinex,
        attribute='_api_query',
        side_effect=mock_api_query_response,
    )
    with ExitStack() as stack:
        stack.enter_context(currency_map_patch)
        stack.enter_context(balances_query_patch)
        asset_balance, msg = mock_bitfinex.query_balances()

        assert asset_balance == {
            Asset('USDT'): Balance(
                amount=FVal('19788.6529257'),
                usd_value=FVal('29682.97938855'),
            ),
            Asset('LINK'): Balance(
                amount=FVal('777.777777'),
                usd_value=FVal('1166.6666655'),
            ),
            Asset('GLM'): Balance(
                amount=FVal('0.0000001'),
                usd_value=FVal('0.00000015'),
            ),
            Asset('EUR'): Balance(
                amount=FVal('99.9999999'),
                usd_value=FVal('149.99999985'),
            ),
        }
        assert msg == ''


def test_api_query_paginated_stops_requesting(mock_bitfinex):
    """Test requests are stopped after retry limit is reached.
    """

    def mock_api_query_response(endpoint, options):  # pylint: disable=unused-argument
        return MockResponse(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            f'{{"error":"{API_RATE_LIMITS_ERROR_MESSAGE}"}}',
        )

    api_request_retry_times_patch = patch(
        target='rotkehlchen.exchanges.bitfinex.API_REQUEST_RETRY_TIMES',
        new=0,
    )
    # Just in case the test fails, we don't want to wait 60s
    api_request_retry_after_seconds_patch = patch(
        target='rotkehlchen.exchanges.bitfinex.API_REQUEST_RETRY_AFTER_SECONDS',
        new=0,
    )
    api_query_patch = patch.object(
        target=mock_bitfinex,
        attribute='_api_query',
        side_effect=mock_api_query_response,
    )
    with ExitStack() as stack:
        stack.enter_context(api_request_retry_times_patch)
        stack.enter_context(api_request_retry_after_seconds_patch)
        stack.enter_context(api_query_patch)
        with pytest.raises(RemoteError) as e:
            mock_bitfinex._api_query_paginated(
                options={'limit': 2},
                case='trades',
                currency_map={},
            )
        expected_msg = f'{mock_bitfinex.name} trades request failed after retrying 0 times.'
        assert expected_msg in str(e.value)


def test_api_query_paginated_retries_request(mock_bitfinex):
    """Test retry logic works as expected.

    It also tests that that trying to decode first the unsuccessful response
    JSON as a dict and later as a list (via `_process_unsuccessful_response()`)
    works as expected.
    """

    def get_paginated_response():
        results = [
            f'{{"error":"{API_RATE_LIMITS_ERROR_MESSAGE}"}}',
            '["error", 10000, "unknown error"]',
        ]
        for result_ in results:
            yield result_

    def mock_api_query_response(endpoint, options):  # pylint: disable=unused-argument
        return MockResponse(HTTPStatus.INTERNAL_SERVER_ERROR, next(get_response))

    get_response = get_paginated_response()
    api_request_retry_times_patch = patch(
        target='rotkehlchen.exchanges.bitfinex.API_REQUEST_RETRY_TIMES',
        new=1,
    )
    api_request_retry_after_seconds_patch = patch(
        target='rotkehlchen.exchanges.bitfinex.API_REQUEST_RETRY_AFTER_SECONDS',
        new=0,
    )
    api_query_patch = patch.object(
        target=mock_bitfinex,
        attribute='_api_query',
        side_effect=mock_api_query_response,
    )
    with ExitStack() as stack:
        stack.enter_context(api_request_retry_times_patch)
        stack.enter_context(api_request_retry_after_seconds_patch)
        stack.enter_context(api_query_patch)
        result = mock_bitfinex._api_query_paginated(
            options={'limit': 2},
            case='trades',
            currency_map={},
        )
        assert result == []


def test_deserialize_trade_buy(mock_bitfinex):
    currency_map = {
        'WBT': 'WBTC',
        'UST': 'USDt',
    }
    raw_result = [
        399251013,
        'WBT:UST',
        1573485493000,
        33963608932,
        0.26334268,
        187.37,
        'LIMIT',
        None,
        -1,
        -0.09868591,
        'UST',
    ]
    expected_trade = Trade(
        timestamp=Timestamp(1573485493),
        location=Location.BITFINEX,
        pair=TradePair('WBTC_USDT'),
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('0.26334268')),
        rate=Price(FVal('187.37')),
        fee=Fee(FVal('0.09868591')),
        fee_currency=Asset('USDT'),
        link='399251013',
        notes='',
    )
    trade = mock_bitfinex._deserialize_trade(
        raw_result=raw_result,
        currency_map=currency_map,
    )
    assert trade == expected_trade


def test_deserialize_trade_sell(mock_bitfinex):
    currency_map = {'UST': 'USDt'}
    raw_result = [
        399251013,
        'ETHUST',
        1573485493000,
        33963608932,
        -0.26334268,
        187.37,
        'LIMIT',
        None,
        -1,
        -0.09868591,
        'UST',
    ]
    expected_trade = Trade(
        timestamp=Timestamp(1573485493),
        location=Location.BITFINEX,
        pair=TradePair('ETH_USDT'),
        trade_type=TradeType.SELL,
        amount=AssetAmount(FVal('0.26334268')),
        rate=Price(FVal('187.37')),
        fee=Fee(FVal('0.09868591')),
        fee_currency=Asset('ETH'),
        link='399251013',
        notes='',
    )
    trade = mock_bitfinex._deserialize_trade(
        raw_result=raw_result,
        currency_map=currency_map,
    )
    assert trade == expected_trade


@pytest.mark.freeze_time(datetime(2020, 12, 3, 12, 0, 0))
def test_query_online_trade_history_case_1(mock_bitfinex):
    """Test pagination logic for trades works as expected when each request
    does not return a result already processed.

    Other things tested:
      - Stop requesting (break the loop) when result timestamp is greater than
      'end_ts'.
      - '_api_query' call arguments.

    First request: 2 results
    Second request: 2 results
    Third request: 1 result, out of time range (its timestamp is gt 'end_ts')

    Trades with id 1 to 4 are expected to be returned.
    """
    api_limit = 2
    response = Response()
    response.status_code = HTTPStatus.OK
    currency_map_response = CurrencyMapResponse(
        success=True,
        response=response,
        currency_map={
            'UST': 'USDt',
            'WBT': 'WBTC',
        },
    )
    # Buy ETH with USDT
    trade_1 = """
    [
        1,
        "ETH:UST",
        1606899600000,
        10,
        0.26334268,
        187.37,
        "LIMIT",
        null,
        -1,
        -0.09868591,
        "UST"
    ]
    """
    # Sell ETH for USDT
    trade_2 = """
    [
        2,
        "ETH:UST",
        1606901400000,
        20,
        -0.26334268,
        187.37,
        "LIMIT",
        null,
        -1,
        -0.09868591,
        "ETH"
    ]
    """
    # Buy WBTC for USD
    trade_3 = """
    [
        3,
        "WBTUSD",
        1606932000000,
        30,
        10000.00000000,
        0.00005000,
        "LIMIT",
        null,
        -1,
        -20.00000000,
        "USD"
    ]
    """
    # Sell WBTC for USD
    trade_4 = """
    [
        4,
        "WBTUSD",
        1606986000000,
        40,
        -10000.00000000,
        0.00005000,
        "LIMIT",
        null,
        -1,
        -20.00000000,
        "WBT"
    ]
    """
    # Sell ETH for EUR, outside time range (gt 'end_ts')
    trade_5 = """
    [
        5,
        "ETH:EUR",
        1606996801000,
        50,
        -0.26334268,
        163.29,
        "LIMIT",
        null,
        -1,
        -0.09868591,
        "ETH"
    ]
    """
    expected_calls = [
        call(
            endpoint='trades',
            options={
                'start': 0,
                'end': 1606996800000,
                'limit': 2,
                'sort': 1,
            },
        ),
        call(
            endpoint='trades',
            options={
                'start': 1606901400000,
                'end': 1606996800000,
                'limit': 2,
                'sort': 1,
            },
        ),
        call(
            endpoint='trades',
            options={
                'start': 1606986000000,
                'end': 1606996800000,
                'limit': 2,
                'sort': 1,
            },
        ),
    ]

    def get_paginated_response():
        results = [
            f'[{trade_1},{trade_2}]',
            f'[{trade_3},{trade_4}]',
            f'[{trade_5}]',
        ]
        for result_ in results:
            yield result_

    def mock_api_query_response(endpoint, options):  # pylint: disable=unused-argument
        return MockResponse(HTTPStatus.OK, next(get_response))

    get_response = get_paginated_response()
    currency_map_patch = patch.object(
        target=mock_bitfinex,
        attribute='_query_currency_map',
        return_value=currency_map_response,
    )
    api_limit_patch = patch(
        target='rotkehlchen.exchanges.bitfinex.API_TRADES_MAX_LIMIT',
        new=api_limit,
    )
    api_query_patch = patch.object(
        target=mock_bitfinex,
        attribute='_api_query',
        side_effect=mock_api_query_response,
    )
    with ExitStack() as stack:
        stack.enter_context(api_limit_patch)
        stack.enter_context(currency_map_patch)
        api_query_mock = stack.enter_context(api_query_patch)
        trades = mock_bitfinex.query_online_trade_history(
            start_ts=Timestamp(0),
            end_ts=Timestamp(int(datetime.now().timestamp())),
        )
        assert api_query_mock.call_args_list == expected_calls
        expected_trades = [
            Trade(
                timestamp=Timestamp(1606899600),
                location=Location.BITFINEX,
                pair=TradePair('ETH_USDT'),
                trade_type=TradeType.BUY,
                amount=AssetAmount(FVal('0.26334268')),
                rate=Price(FVal('187.37')),
                fee=Fee(FVal('0.09868591')),
                fee_currency=Asset('USDT'),
                link='1',
                notes='',
            ),
            Trade(
                timestamp=Timestamp(1606901400),
                location=Location.BITFINEX,
                pair=TradePair('ETH_USDT'),
                trade_type=TradeType.SELL,
                amount=AssetAmount(FVal('0.26334268')),
                rate=Price(FVal('187.37')),
                fee=Fee(FVal('0.09868591')),
                fee_currency=Asset('ETH'),
                link='2',
                notes='',
            ),
            Trade(
                timestamp=Timestamp(1606932000),
                location=Location.BITFINEX,
                pair=TradePair('WBTC_USD'),
                trade_type=TradeType.BUY,
                amount=AssetAmount(FVal('10000.0')),
                rate=Price(FVal('0.00005')),
                fee=Fee(FVal('20.0')),
                fee_currency=Asset('USD'),
                link='3',
                notes='',
            ),
            Trade(
                timestamp=Timestamp(1606986000),
                location=Location.BITFINEX,
                pair=TradePair('WBTC_USD'),
                trade_type=TradeType.SELL,
                amount=AssetAmount(FVal('10000.0')),
                rate=Price(FVal('0.00005')),
                fee=Fee(FVal('20.0')),
                fee_currency=Asset('WBTC'),
                link='4',
                notes='',
            ),
        ]
        assert trades == expected_trades


@pytest.mark.freeze_time(datetime(2020, 12, 3, 12, 0, 0))
# def test_query_online_trade_history_case_2(mock_bitfinex):
def test_pepe(mock_bitfinex):
    """Test pagination logic for trades works as expected when a request
    returns a result already processed in the previous request.

    Other things tested:
      - Stop requesting when number of entries is less than limit.

    First request: 2 results
    Second request: 2 results, both trades are repeated from the 1st request.
    Third request: 2 results, first trade is repeated from the 2nd request.
    Fourth request: 1 result

    Trades with id 1 to 4 are expected to be returned.
    """
    api_limit = 2
    response = Response()
    response.status_code = HTTPStatus.OK
    currency_map_response = CurrencyMapResponse(
        success=True,
        response=response,
        currency_map={
            'UST': 'USDt',
            'WBT': 'WBTC',
        },
    )
    # Buy ETH with USDT
    trade_1 = """
    [
        1,
        "ETH:UST",
        1606899600000,
        10,
        0.26334268,
        187.37,
        "LIMIT",
        null,
        -1,
        -0.09868591,
        "UST"
    ]
    """
    # Sell ETH for USDT
    trade_2 = """
    [
        2,
        "ETH:UST",
        1606901400000,
        20,
        -0.26334268,
        187.37,
        "LIMIT",
        null,
        -1,
        -0.09868591,
        "ETH"
    ]
    """
    # Buy WBTC for USD
    trade_3 = """
    [
        3,
        "WBTUSD",
        1606932000000,
        30,
        10000.00000000,
        0.00005000,
        "LIMIT",
        null,
        -1,
        -20.00000000,
        "USD"
    ]
    """
    # Sell WBTC for USD
    trade_4 = """
    [
        4,
        "WBTUSD",
        1606986000000,
        40,
        -10000.00000000,
        0.00005000,
        "LIMIT",
        null,
        -1,
        -20.00000000,
        "WBT"
    ]
    """

    def get_paginated_response():
        results = [
            f'[{trade_1},{trade_2}]',
            f'[{trade_1},{trade_2}]',  # repeated line
            f'[{trade_2},{trade_3}]',  # contains repeated
            f'[{trade_4}]',
        ]
        for result_ in results:
            yield result_

    def mock_api_query_response(endpoint, options):  # pylint: disable=unused-argument
        return MockResponse(HTTPStatus.OK, next(get_response))

    get_response = get_paginated_response()
    currency_map_patch = patch.object(
        target=mock_bitfinex,
        attribute='_query_currency_map',
        return_value=currency_map_response,
    )
    api_limit_patch = patch(
        target='rotkehlchen.exchanges.bitfinex.API_TRADES_MAX_LIMIT',
        new=api_limit,
    )
    api_query_patch = patch.object(
        target=mock_bitfinex,
        attribute='_api_query',
        side_effect=mock_api_query_response,
    )
    with ExitStack() as stack:
        stack.enter_context(api_limit_patch)
        stack.enter_context(currency_map_patch)
        stack.enter_context(api_query_patch)
        trades = mock_bitfinex.query_online_trade_history(
            start_ts=Timestamp(0),
            end_ts=Timestamp(int(datetime.now().timestamp())),
        )
        expected_trades = [
            Trade(
                timestamp=Timestamp(1606899600),
                location=Location.BITFINEX,
                pair=TradePair('ETH_USDT'),
                trade_type=TradeType.BUY,
                amount=AssetAmount(FVal('0.26334268')),
                rate=Price(FVal('187.37')),
                fee=Fee(FVal('0.09868591')),
                fee_currency=Asset('USDT'),
                link='1',
                notes='',
            ),
            Trade(
                timestamp=Timestamp(1606901400),
                location=Location.BITFINEX,
                pair=TradePair('ETH_USDT'),
                trade_type=TradeType.SELL,
                amount=AssetAmount(FVal('0.26334268')),
                rate=Price(FVal('187.37')),
                fee=Fee(FVal('0.09868591')),
                fee_currency=Asset('ETH'),
                link='2',
                notes='',
            ),
            Trade(
                timestamp=Timestamp(1606932000),
                location=Location.BITFINEX,
                pair=TradePair('WBTC_USD'),
                trade_type=TradeType.BUY,
                amount=AssetAmount(FVal('10000.0')),
                rate=Price(FVal('0.00005')),
                fee=Fee(FVal('20.0')),
                fee_currency=Asset('USD'),
                link='3',
                notes='',
            ),
            Trade(
                timestamp=Timestamp(1606986000),
                location=Location.BITFINEX,
                pair=TradePair('WBTC_USD'),
                trade_type=TradeType.SELL,
                amount=AssetAmount(FVal('10000.0')),
                rate=Price(FVal('0.00005')),
                fee=Fee(FVal('20.0')),
                fee_currency=Asset('WBTC'),
                link='4',
                notes='',
            ),
        ]
        assert trades == expected_trades


def test_deserialize_asset_movement_deposit(mock_bitfinex):
    currency_map = {'WBT': 'WBTC'}
    raw_result = [
        13105603,
        'WBT',
        'Wrapped Bitcoin',
        None,
        None,
        1569348774000,
        1569348774000,
        None,
        None,
        'COMPLETED',
        None,
        None,
        0.26300954,
        -0.00135,
        None,
        None,
        'DESTINATION_ADDRESS',
        None,
        None,
        None,
        'TRANSACTION_ID',
        None,
    ]
    fee_asset = Asset('WBTC')
    expected_asset_movement = AssetMovement(
        timestamp=Timestamp(1569348774),
        location=Location.BITFINEX,
        category=AssetMovementCategory.DEPOSIT,
        address='DESTINATION_ADDRESS',
        transaction_id='TRANSACTION_ID',
        asset=fee_asset,
        amount=FVal('0.26300954'),
        fee_asset=fee_asset,
        fee=Fee(FVal('0.00135')),
        link=str(13105603),
    )
    asset_movement = mock_bitfinex._deserialize_asset_movement(
        raw_result=raw_result,
        currency_map=currency_map,
    )
    assert asset_movement == expected_asset_movement


def test_deserialize_asset_movement_withdrawal(mock_bitfinex):
    """Test also both 'address' and 'transaction_id' are None for fiat
    movements.
    """
    currency_map = {}
    raw_result = [
        13105603,
        'EUR',
        'Euro',
        None,
        None,
        1569348774000,
        1569348774000,
        None,
        None,
        'COMPLETED',
        None,
        None,
        -0.26300954,
        -0.00135,
        None,
        None,
        'DESTINATION_ADDRESS',
        None,
        None,
        None,
        'TRANSACTION_ID',
        None,
    ]
    fee_asset = Asset('EUR')
    expected_asset_movement = AssetMovement(
        timestamp=Timestamp(1569348774),
        location=Location.BITFINEX,
        category=AssetMovementCategory.WITHDRAWAL,
        address=None,
        transaction_id=None,
        asset=fee_asset,
        amount=FVal('0.26300954'),
        fee_asset=fee_asset,
        fee=Fee(FVal('0.00135')),
        link=str(13105603),
    )
    asset_movement = mock_bitfinex._deserialize_asset_movement(
        raw_result=raw_result,
        currency_map=currency_map,
    )
    assert asset_movement == expected_asset_movement


@pytest.mark.freeze_time(datetime(2020, 12, 3, 12, 0, 0))
def test_query_online_deposits_withdrawals_case_1(mock_bitfinex):
    """Test pagination logic for asset movements works as expected when each
    request does not return a result already processed.

    Other things tested:
      - Skip result when status is not 'COMPLETED'.
      - Stop requesting (break the loop) when result timestamp is greater than
      'end_ts'.
      - '_api_query' call arguments.

    First request: 2 results
    Second request: 2 results, 1 not completed.
    Third request: 1 result, out of time range (its timestamp is gt 'end_ts')

    Movements with id 1, 2 and 4 are expected to be returned.
    """
    api_limit = 2
    response = Response()
    response.status_code = HTTPStatus.OK
    currency_map_response = CurrencyMapResponse(
        success=True,
        response=response,
        currency_map={'WBT': 'WBTC'},
    )
    # Deposit WBTC
    movement_1 = """
    [
        1,
        "WBT",
        "Wrapped Bitcoin",
        null,
        null,
        1606899600000,
        1606899700000,
        null,
        null,
        "COMPLETED",
        null,
        null,
        0.26300954,
        -0.00135,
        null,
        null,
        "DESTINATION_ADDRESS",
        null,
        null,
        null,
        "TRANSACTION_ID",
        null
    ]
    """
    # Withdraw WBTC
    movement_2 = """
    [
        2,
        "WBT",
        "Wrapped Bitcoin",
        null,
        null,
        1606901400000,
        1606901500000,
        null,
        null,
        "COMPLETED",
        null,
        null,
        -0.26300954,
        -0.00135,
        null,
        null,
        "DESTINATION_ADDRESS",
        null,
        null,
        null,
        "TRANSACTION_ID",
        null
    ]
    """
    # Deposit WBTC, not completed
    movement_3 = """
    [
        3,
        "WBT",
        "Wrapped Bitcoin",
        null,
        null,
        1606932000000,
        1606932100000,
        null,
        null,
        "WHATEVER",
        null,
        null,
        0.26300954,
        -0.00135,
        null,
        null,
        "DESTINATION_ADDRESS",
        null,
        null,
        null,
        "TRANSACTION_ID",
        null
    ]
    """
    # Withdraw EUR
    movement_4 = """
    [
        4,
        "EUR",
        "Euro",
        null,
        null,
        1606986000000,
        1606986100000,
        null,
        null,
        "COMPLETED",
        null,
        null,
        -0.26300954,
        -0.00135,
        null,
        null,
        "",
        null,
        null,
        null,
        "",
        null
    ]
    """
    # Deposit WBTC, outside time range (gt 'end_ts')
    movement_5 = """
    [
        5,
        "WBT",
        "Wrapped Bitcoin",
        null,
        null,
        1606996801000,
        1606996901000,
        null,
        null,
        "COMPLETED",
        null,
        null,
        0.26300954,
        -0.00135,
        null,
        null,
        "DESTINATION_ADDRESS",
        null,
        null,
        null,
        "TRANSACTION_ID",
        null
    ]
    """
    expected_calls = [
        call(
            endpoint='movements',
            options={
                'start': 0,
                'end': 1606996800000,
                'limit': 2,
                'sort': 1,
            },
        ),
        call(
            endpoint='movements',
            options={
                'start': 1606901400000,
                'end': 1606996800000,
                'limit': 2,
                'sort': 1,
            },
        ),
        call(
            endpoint='movements',
            options={
                'start': 1606986000000,
                'end': 1606996800000,
                'limit': 2,
                'sort': 1,
            },
        ),
    ]

    def get_paginated_response():
        results = [
            f'[{movement_1},{movement_2}]',
            f'[{movement_3},{movement_4}]',
            f'[{movement_5}]',
        ]
        for result_ in results:
            yield result_

    def mock_api_query_response(endpoint, options):  # pylint: disable=unused-argument
        return MockResponse(HTTPStatus.OK, next(get_response))

    get_response = get_paginated_response()
    currency_map_patch = patch.object(
        target=mock_bitfinex,
        attribute='_query_currency_map',
        return_value=currency_map_response,
    )
    api_limit_patch = patch(
        target='rotkehlchen.exchanges.bitfinex.API_MOVEMENTS_MAX_LIMIT',
        new=api_limit,
    )
    api_query_patch = patch.object(
        target=mock_bitfinex,
        attribute='_api_query',
        side_effect=mock_api_query_response,
    )
    with ExitStack() as stack:
        stack.enter_context(api_limit_patch)
        stack.enter_context(currency_map_patch)
        api_query_mock = stack.enter_context(api_query_patch)
        asset_movements = mock_bitfinex.query_online_deposits_withdrawals(
            start_ts=Timestamp(0),
            end_ts=Timestamp(int(datetime.now().timestamp())),
        )
        assert api_query_mock.call_args_list == expected_calls

        wbtc_fee_asset = Asset('WBTC')
        eur_fee_asset = Asset('EUR')
        expected_asset_movements = [
            AssetMovement(
                timestamp=Timestamp(1606899600),
                location=Location.BITFINEX,
                category=AssetMovementCategory.DEPOSIT,
                address='DESTINATION_ADDRESS',
                transaction_id='TRANSACTION_ID',
                asset=wbtc_fee_asset,
                amount=FVal('0.26300954'),
                fee_asset=wbtc_fee_asset,
                fee=Fee(FVal('0.00135')),
                link=str(1),
            ),
            AssetMovement(
                timestamp=Timestamp(1606901400),
                location=Location.BITFINEX,
                category=AssetMovementCategory.WITHDRAWAL,
                address='DESTINATION_ADDRESS',
                transaction_id='TRANSACTION_ID',
                asset=wbtc_fee_asset,
                amount=FVal('0.26300954'),
                fee_asset=wbtc_fee_asset,
                fee=Fee(FVal('0.00135')),
                link=str(2),
            ),
            AssetMovement(
                timestamp=Timestamp(1606986000),
                location=Location.BITFINEX,
                category=AssetMovementCategory.WITHDRAWAL,
                address=None,
                transaction_id=None,
                asset=eur_fee_asset,
                amount=FVal('0.26300954'),
                fee_asset=eur_fee_asset,
                fee=Fee(FVal('0.00135')),
                link=str(4),
            ),
        ]
        assert asset_movements == expected_asset_movements


@pytest.mark.freeze_time(datetime(2020, 12, 3, 12, 0, 0))
def test_query_online_deposits_withdrawals_case_2(mock_bitfinex):
    """Test pagination logic for asset movements works as expected when a
    request returns a result already processed in the previous request.

    Other things tested:
      - Stop requesting when number of entries is less than limit.

    First request: 2 results
    Second request: 2 results, both movements are repeated from the 1st request.
    Third request: 2 results, first movement is repeated from the 2nd request.
    Fourth request: 1 result

    Trades with id 1 to 4 are expected to be returned.
    """
    api_limit = 2
    response = Response()
    response.status_code = HTTPStatus.OK
    currency_map_response = CurrencyMapResponse(
        success=True,
        response=response,
        currency_map={'WBT': 'WBTC'},
    )
    # Deposit WBTC
    movement_1 = """
    [
        1,
        "WBT",
        "Wrapped Bitcoin",
        null,
        null,
        1606899600000,
        1606899700000,
        null,
        null,
        "COMPLETED",
        null,
        null,
        0.26300954,
        -0.00135,
        null,
        null,
        "DESTINATION_ADDRESS",
        null,
        null,
        null,
        "TRANSACTION_ID",
        null
    ]
    """
    # Withdraw WBTC
    movement_2 = """
    [
        2,
        "WBT",
        "Wrapped Bitcoin",
        null,
        null,
        1606901400000,
        1606901500000,
        null,
        null,
        "COMPLETED",
        null,
        null,
        -0.26300954,
        -0.00135,
        null,
        null,
        "DESTINATION_ADDRESS",
        null,
        null,
        null,
        "TRANSACTION_ID",
        null
    ]
    """
    # Withdraw EUR
    movement_3 = """
    [
        3,
        "EUR",
        "Euro",
        null,
        null,
        1606986000000,
        1606986100000,
        null,
        null,
        "COMPLETED",
        null,
        null,
        -0.26300954,
        -0.00135,
        null,
        null,
        "",
        null,
        null,
        null,
        "",
        null
    ]
    """
    # Deposit WBTC
    movement_4 = """
    [
        4,
        "WBT",
        "Wrapped Bitcoin",
        null,
        null,
        1606996800000,
        1606996900000,
        null,
        null,
        "COMPLETED",
        null,
        null,
        0.26300954,
        -0.00135,
        null,
        null,
        "DESTINATION_ADDRESS",
        null,
        null,
        null,
        "TRANSACTION_ID",
        null
    ]
    """

    def get_paginated_response():
        results = [
            f'[{movement_1},{movement_2}]',
            f'[{movement_1},{movement_2}]',
            f'[{movement_2},{movement_3}]',
            f'[{movement_4}]',
        ]
        for result_ in results:
            yield result_

    def mock_api_query_response(endpoint, options):  # pylint: disable=unused-argument
        return MockResponse(HTTPStatus.OK, next(get_response))

    get_response = get_paginated_response()
    currency_map_patch = patch.object(
        target=mock_bitfinex,
        attribute='_query_currency_map',
        return_value=currency_map_response,
    )
    api_limit_patch = patch(
        target='rotkehlchen.exchanges.bitfinex.API_MOVEMENTS_MAX_LIMIT',
        new=api_limit,
    )
    api_query_patch = patch.object(
        target=mock_bitfinex,
        attribute='_api_query',
        side_effect=mock_api_query_response,
    )
    with ExitStack() as stack:
        stack.enter_context(api_limit_patch)
        stack.enter_context(currency_map_patch)
        stack.enter_context(api_query_patch)
        asset_movements = mock_bitfinex.query_online_deposits_withdrawals(
            start_ts=Timestamp(0),
            end_ts=Timestamp(int(datetime.now().timestamp())),
        )
        wbtc_fee_asset = Asset('WBTC')
        eur_fee_asset = Asset('EUR')
        expected_asset_movements = [
            AssetMovement(
                timestamp=Timestamp(1606899600),
                location=Location.BITFINEX,
                category=AssetMovementCategory.DEPOSIT,
                address='DESTINATION_ADDRESS',
                transaction_id='TRANSACTION_ID',
                asset=wbtc_fee_asset,
                amount=FVal('0.26300954'),
                fee_asset=wbtc_fee_asset,
                fee=Fee(FVal('0.00135')),
                link=str(1),
            ),
            AssetMovement(
                timestamp=Timestamp(1606901400),
                location=Location.BITFINEX,
                category=AssetMovementCategory.WITHDRAWAL,
                address='DESTINATION_ADDRESS',
                transaction_id='TRANSACTION_ID',
                asset=wbtc_fee_asset,
                amount=FVal('0.26300954'),
                fee_asset=wbtc_fee_asset,
                fee=Fee(FVal('0.00135')),
                link=str(2),
            ),
            AssetMovement(
                timestamp=Timestamp(1606986000),
                location=Location.BITFINEX,
                category=AssetMovementCategory.WITHDRAWAL,
                address=None,
                transaction_id=None,
                asset=eur_fee_asset,
                amount=FVal('0.26300954'),
                fee_asset=eur_fee_asset,
                fee=Fee(FVal('0.00135')),
                link=str(3),
            ),
            AssetMovement(
                timestamp=Timestamp(1606996800),
                location=Location.BITFINEX,
                category=AssetMovementCategory.DEPOSIT,
                address='DESTINATION_ADDRESS',
                transaction_id='TRANSACTION_ID',
                asset=wbtc_fee_asset,
                amount=FVal('0.26300954'),
                fee_asset=wbtc_fee_asset,
                fee=Fee(FVal('0.00135')),
                link=str(4),
            ),
        ]
        assert asset_movements == expected_asset_movements
