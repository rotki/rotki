import warnings as test_warnings
from contextlib import ExitStack
from datetime import datetime
from http import HTTPStatus
from unittest.mock import MagicMock, call, patch

import pytest

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.converters import (
    BITFINEX_EXCHANGE_TEST_ASSETS,
    UNSUPPORTED_BITFINEX_ASSETS,
    asset_from_bitfinex,
)
from rotkehlchen.constants.assets import A_BTC, A_ETH, A_EUR, A_LINK, A_USD, A_USDT, A_WBTC
from rotkehlchen.errors import UnknownAsset, UnsupportedAsset
from rotkehlchen.exchanges.bitfinex import (
    API_ERR_AUTH_NONCE_CODE,
    API_ERR_AUTH_NONCE_MESSAGE,
    API_KEY_ERROR_CODE,
    API_KEY_ERROR_MESSAGE,
    API_RATE_LIMITS_ERROR_MESSAGE,
    Bitfinex,
)
from rotkehlchen.exchanges.data_structures import AssetMovement, Trade, TradeType
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.constants import A_GLM, A_NEO
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.typing import AssetAmount, AssetMovementCategory, Fee, Location, Price, Timestamp


def test_name():
    exchange = Bitfinex('bitfinex1', 'a', b'a', object(), object())
    assert exchange.location == Location.BITFINEX
    assert exchange.name == 'bitfinex1'


def test_assets_are_known(mock_bitfinex):
    """This tests only exchange (trades) assets (not margin, nor futures ones).
    """
    currencies_response = mock_bitfinex._query_currencies()
    if currencies_response.success is False:
        response = currencies_response.response
        test_warnings.warn(UserWarning(
            f'Failed to request {mock_bitfinex.name} currencies list. '
            f'Response status code: {response.status_code}. '
            f'Response text: {response.text}. Xfailing this test',
        ))
        pytest.xfail('Failed to request {mock_bitfinex.name} currencies list')

    exchange_pairs_response = mock_bitfinex._query_exchange_pairs()
    if exchange_pairs_response.success is False:
        response = exchange_pairs_response.response
        test_warnings.warn(UserWarning(
            f'Failed to request {mock_bitfinex.name} exchange pairs list. '
            f'Response status code: {response.status_code}. '
            f'Response text: {response.text}. Xfailing this test',
        ))
        pytest.xfail('Failed to request {mock_bitfinex.name} exchange pairs list')

    currency_map_response = mock_bitfinex._query_currency_map()
    if currency_map_response.success is False:
        response = currency_map_response.response
        test_warnings.warn(UserWarning(
            f'Failed to request {mock_bitfinex.name} currency map. '
            f'Response status code: {response.status_code}. '
            f'Response text: {response.text}. Xfailing this test',
        ))
        pytest.xfail('Failed to request {mock_bitfinex.name} currency map')

    test_assets = set(BITFINEX_EXCHANGE_TEST_ASSETS)
    unsupported_assets = set(UNSUPPORTED_BITFINEX_ASSETS)
    currency_map = currency_map_response.currency_map
    symbols = set()
    for symbol in currencies_response.currencies:
        if symbol in test_assets:
            continue
        for pair in exchange_pairs_response.pairs:
            if pair.startswith(symbol) or pair.endswith(symbol):
                symbols.add(symbol)
                break

    for symbol in symbols:
        try:
            asset_from_bitfinex(
                bitfinex_name=symbol,
                currency_map=currency_map,
            )
        except UnsupportedAsset:
            assert symbol in unsupported_assets
        except UnknownAsset as e:
            test_warnings.warn(UserWarning(
                f'Found unknown asset {e.asset_name} in {mock_bitfinex.name}. '
                f'Support for it has to be added',
            ))


def test_first_connection(mock_bitfinex):
    """Test 'currency_map' and 'pair_bfx_symbols_map' contain the expected data.
    """
    assert mock_bitfinex.first_connection_made is False
    assert hasattr(mock_bitfinex, 'currency_map') is False
    assert hasattr(mock_bitfinex, 'pair_bfx_symbols_map') is False

    mock_bitfinex.first_connection()

    assert mock_bitfinex.currency_map['UST'] == 'USDt'
    assert mock_bitfinex.currency_map['WBT'] == 'WBTC'
    assert mock_bitfinex.pair_bfx_symbols_map['BTCUST'] == ('BTC', 'UST')
    assert mock_bitfinex.pair_bfx_symbols_map['UDCUSD'] == ('UDC', 'USD')
    assert mock_bitfinex.first_connection_made is True


def test_api_key_err_auth_nonce(mock_bitfinex):
    """Test the error code related with the nonce authentication is properly handled"""
    def mock_api_query_response(endpoint, options=None):  # pylint: disable=unused-argument
        return MockResponse(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            f'["error", {API_ERR_AUTH_NONCE_CODE}, "nonce: small"]',
        )

    mock_bitfinex.first_connection_made = True
    with patch.object(mock_bitfinex, '_api_query', side_effect=mock_api_query_response):
        result, msg = mock_bitfinex.query_balances()
        assert result is False
        assert msg == API_ERR_AUTH_NONCE_MESSAGE

        result, msg = mock_bitfinex.validate_api_key()
        assert result is False
        assert msg == API_ERR_AUTH_NONCE_MESSAGE

        movements = mock_bitfinex.query_online_deposits_withdrawals(0, 1)
        assert movements == []
        errors = mock_bitfinex.msg_aggregator.consume_errors()
        assert len(errors) == 1
        assert API_ERR_AUTH_NONCE_MESSAGE in errors[0]

        trades = mock_bitfinex.query_online_trade_history(0, 1)
        assert trades == []
        errors = mock_bitfinex.msg_aggregator.consume_errors()
        assert len(errors) == 1
        assert API_ERR_AUTH_NONCE_MESSAGE in errors[0]


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
    """Test the balances of the assets are returned as expected.

    Also test the following logic:
      - An asset balance is the result of aggregating its balances per wallet
      type (i.e. exchange, margin and funding).
      - The balance of an asset in UNSUPPORTED_BITFINEX_ASSETS is skipped.
      - The asset ticker is standardized (e.g. WBT to WBTC, UST to USDT).
    """
    mock_bitfinex.first_connection = MagicMock()
    mock_bitfinex.currency_map = {
        'UST': 'USDt',
        'GNT': 'GLM',
        'WBT': 'WBTC',
    }
    balances_data = (
        """
        [
            ["exchange"],
            ["exchange", "UST"],
            ["exchange", "", 12345],
            ["exchange", "WBT", 0.0000000],
            ["exchange", "", 19788.6529257],
            ["exchange", "UST", 19788.6529257],
            ["margin", "UST", 0.50000000],
            ["funding", "UST", 1],
            ["exchange", "LINK", 777.777777],
            ["exchange", "GNT", 0.0000001],
            ["exchange", "EUR", 99.9999999],
            ["margin", "WBT", 1.00000000],
            ["funding", "NEO", 1.00000000],
            ["exchange", "B21X", 1.00000000]
        ]
        """
    )

    def mock_api_query_response(endpoint):  # pylint: disable=unused-argument
        return MockResponse(HTTPStatus.OK, balances_data)

    with patch.object(
        target=mock_bitfinex,
        attribute='_api_query',
        side_effect=mock_api_query_response,
    ):
        asset_balance, msg = mock_bitfinex.query_balances()

        assert asset_balance == {
            A_EUR: Balance(
                amount=FVal('99.9999999'),
                usd_value=FVal('149.99999985'),
            ),
            A_GLM: Balance(
                amount=FVal('0.0000001'),
                usd_value=FVal('0.00000015'),
            ),
            A_LINK: Balance(
                amount=FVal('777.777777'),
                usd_value=FVal('1166.6666655'),
            ),
            A_NEO: Balance(
                amount=FVal('1'),
                usd_value=FVal('1.5'),
            ),
            A_USDT: Balance(
                amount=FVal('19790.1529257'),
                usd_value=FVal('29685.22938855'),
            ),
            A_WBTC: Balance(
                amount=FVal('1'),
                usd_value=FVal('1.5'),
            ),
        }
        assert msg == ''


def test_api_query_paginated_stops_requesting(mock_bitfinex):
    """Test requests are stopped after retry limit is reached.
    """
    mock_bitfinex.currency_map = {}

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
        result = mock_bitfinex._api_query_paginated(
            options={'limit': 2},
            case='trades',
        )
        assert result == []


def test_api_query_paginated_retries_request(mock_bitfinex):
    """Test retry logic works as expected.

    It also tests that that trying to decode first the unsuccessful response
    JSON as a dict and later as a list (via `_process_unsuccessful_response()`)
    works as expected.
    """
    mock_bitfinex.currency_map = {}

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
        )
        assert result == []


def test_deserialize_trade_buy(mock_bitfinex):
    mock_bitfinex.currency_map = {
        'WBT': 'WBTC',
        'UST': 'USDt',
    }
    mock_bitfinex.pair_bfx_symbols_map = {'WBTUST': ('WBT', 'UST')}
    raw_result = [
        399251013,
        'tWBT:UST',
        1573485493000,
        33963608932,
        0.26334268,
        187.37,
        'LIMIT',
        None,
        -1,
        -0.09868591,
        'USD',
    ]
    expected_trade = Trade(
        timestamp=Timestamp(1573485493),
        location=Location.BITFINEX,
        base_asset=A_WBTC,
        quote_asset=A_USDT,
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('0.26334268')),
        rate=Price(FVal('187.37')),
        fee=Fee(FVal('0.09868591')),
        fee_currency=A_USD,
        link='399251013',
        notes='',
    )
    trade = mock_bitfinex._deserialize_trade(raw_result=raw_result)
    assert trade == expected_trade


def test_deserialize_trade_sell(mock_bitfinex):
    mock_bitfinex.currency_map = {'UST': 'USDt'}
    mock_bitfinex.pair_bfx_symbols_map = {'ETHUST': ('ETH', 'UST')}
    raw_result = [
        399251013,
        'tETHUST',
        1573485493000,
        33963608932,
        -0.26334268,
        187.37,
        'LIMIT',
        None,
        -1,
        -0.09868591,
        'USD',
    ]
    expected_trade = Trade(
        timestamp=Timestamp(1573485493),
        location=Location.BITFINEX,
        base_asset=A_ETH,
        quote_asset=A_USDT,
        trade_type=TradeType.SELL,
        amount=AssetAmount(FVal('0.26334268')),
        rate=Price(FVal('187.37')),
        fee=Fee(FVal('0.09868591')),
        fee_currency=A_USD,
        link='399251013',
        notes='',
    )
    trade = mock_bitfinex._deserialize_trade(raw_result=raw_result)
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
    mock_bitfinex.first_connection = MagicMock()
    mock_bitfinex.currency_map = {
        'UST': 'USDt',
        'WBT': 'WBTC',
    }
    mock_bitfinex.pair_bfx_symbols_map = {
        'ETHUST': ('ETH', 'UST'),
        'WBTUSD': ('WBT', 'USD'),
        'ETHEUR': ('ETH', 'EUR'),
    }
    # Buy ETH with USDT
    trade_1 = """
    [
        1,
        "tETH:UST",
        1606899600000,
        10,
        0.26334268,
        187.37,
        "LIMIT",
        null,
        -1,
        -0.09868591,
        "USD"
    ]
    """
    # Sell ETH for USDT
    trade_2 = """
    [
        2,
        "tETH:UST",
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
        "tWBTUSD",
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
        "tWBTUSD",
        1606986000000,
        40,
        -10000.00000000,
        0.00005000,
        "LIMIT",
        null,
        -1,
        -20.00000000,
        "BTC"
    ]
    """
    # Sell ETH for EUR, outside time range (gt 'end_ts')
    trade_5 = """
    [
        5,
        "tETH:EUR",
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
                base_asset=A_ETH,
                quote_asset=A_USDT,
                trade_type=TradeType.BUY,
                amount=AssetAmount(FVal('0.26334268')),
                rate=Price(FVal('187.37')),
                fee=Fee(FVal('0.09868591')),
                fee_currency=A_USD,
                link='1',
                notes='',
            ),
            Trade(
                timestamp=Timestamp(1606901400),
                location=Location.BITFINEX,
                base_asset=A_ETH,
                quote_asset=A_USDT,
                trade_type=TradeType.SELL,
                amount=AssetAmount(FVal('0.26334268')),
                rate=Price(FVal('187.37')),
                fee=Fee(FVal('0.09868591')),
                fee_currency=A_ETH,
                link='2',
                notes='',
            ),
            Trade(
                timestamp=Timestamp(1606932000),
                location=Location.BITFINEX,
                base_asset=A_WBTC,
                quote_asset=A_USD,
                trade_type=TradeType.BUY,
                amount=AssetAmount(FVal('10000.0')),
                rate=Price(FVal('0.00005')),
                fee=Fee(FVal('20.0')),
                fee_currency=A_USD,
                link='3',
                notes='',
            ),
            Trade(
                timestamp=Timestamp(1606986000),
                location=Location.BITFINEX,
                base_asset=A_WBTC,
                quote_asset=A_USD,
                trade_type=TradeType.SELL,
                amount=AssetAmount(FVal('10000.0')),
                rate=Price(FVal('0.00005')),
                fee=Fee(FVal('20.0')),
                fee_currency=A_BTC,
                link='4',
                notes='',
            ),
        ]
        assert trades == expected_trades


@pytest.mark.freeze_time(datetime(2020, 12, 3, 12, 0, 0))
def test_query_online_trade_history_case_2(mock_bitfinex):
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
    mock_bitfinex.first_connection = MagicMock()
    mock_bitfinex.currency_map = {
        'UST': 'USDt',
        'WBT': 'WBTC',
    }
    mock_bitfinex.pair_bfx_symbols_map = {
        'ETHUST': ('ETH', 'UST'),
        'WBTUSD': ('WBT', 'USD'),
        'ETHEUR': ('ETH', 'EUR'),
    }
    # Buy ETH with USDT
    trade_1 = """
    [
        1,
        "tETH:UST",
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
        "tETH:UST",
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
        "tWBTUSD",
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
        "tWBTUSD",
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
        stack.enter_context(api_query_patch)
        trades = mock_bitfinex.query_online_trade_history(
            start_ts=Timestamp(0),
            end_ts=Timestamp(int(datetime.now().timestamp())),
        )
        expected_trades = [
            Trade(
                timestamp=Timestamp(1606899600),
                location=Location.BITFINEX,
                base_asset=A_ETH,
                quote_asset=A_USDT,
                trade_type=TradeType.BUY,
                amount=AssetAmount(FVal('0.26334268')),
                rate=Price(FVal('187.37')),
                fee=Fee(FVal('0.09868591')),
                fee_currency=A_USDT,
                link='1',
                notes='',
            ),
            Trade(
                timestamp=Timestamp(1606901400),
                location=Location.BITFINEX,
                base_asset=A_ETH,
                quote_asset=A_USDT,
                trade_type=TradeType.SELL,
                amount=AssetAmount(FVal('0.26334268')),
                rate=Price(FVal('187.37')),
                fee=Fee(FVal('0.09868591')),
                fee_currency=A_ETH,
                link='2',
                notes='',
            ),
            Trade(
                timestamp=Timestamp(1606932000),
                location=Location.BITFINEX,
                base_asset=A_WBTC,
                quote_asset=A_USD,
                trade_type=TradeType.BUY,
                amount=AssetAmount(FVal('10000.0')),
                rate=Price(FVal('0.00005')),
                fee=Fee(FVal('20.0')),
                fee_currency=A_USD,
                link='3',
                notes='',
            ),
            Trade(
                timestamp=Timestamp(1606986000),
                location=Location.BITFINEX,
                base_asset=A_WBTC,
                quote_asset=A_USD,
                trade_type=TradeType.SELL,
                amount=AssetAmount(FVal('10000.0')),
                rate=Price(FVal('0.00005')),
                fee=Fee(FVal('20.0')),
                fee_currency=A_WBTC,
                link='4',
                notes='',
            ),
        ]
        assert trades == expected_trades


def test_deserialize_asset_movement_deposit(mock_bitfinex):
    mock_bitfinex.currency_map = {'WBT': 'WBTC'}
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
    fee_asset = A_WBTC
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
    asset_movement = mock_bitfinex._deserialize_asset_movement(raw_result=raw_result)
    assert asset_movement == expected_asset_movement


def test_deserialize_asset_movement_withdrawal(mock_bitfinex):
    """Test also both 'address' and 'transaction_id' are None for fiat
    movements.
    """
    mock_bitfinex.currency_map = {}
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
    fee_asset = A_EUR
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
    asset_movement = mock_bitfinex._deserialize_asset_movement(raw_result=raw_result)
    assert asset_movement == expected_asset_movement


@pytest.mark.freeze_time(datetime(2020, 12, 3, 12, 0, 0))
def test_query_online_deposits_withdrawals_case_1(mock_bitfinex):
    """Test pagination logic for asset movements works as expected when each
    request does not return a result already processed.

    Other things tested:
      - Results are sorted by id in ascending mode.
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
    mock_bitfinex.first_connection = MagicMock()
    mock_bitfinex.currency_map = {'WBT': 'WBTC'}
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
            },
        ),
        call(
            endpoint='movements',
            options={
                'start': 1606901400000,
                'end': 1606996800000,
                'limit': 2,
            },
        ),
        call(
            endpoint='movements',
            options={
                'start': 1606986000000,
                'end': 1606996800000,
                'limit': 2,
            },
        ),
    ]

    def get_paginated_response():
        results = [
            f'[{movement_2},{movement_1}]',
            f'[{movement_4},{movement_3}]',
            f'[{movement_5}]',
        ]
        for result_ in results:
            yield result_

    def mock_api_query_response(endpoint, options):  # pylint: disable=unused-argument
        return MockResponse(HTTPStatus.OK, next(get_response))

    get_response = get_paginated_response()
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
        api_query_mock = stack.enter_context(api_query_patch)
        asset_movements = mock_bitfinex.query_online_deposits_withdrawals(
            start_ts=Timestamp(0),
            end_ts=Timestamp(int(datetime.now().timestamp())),
        )
        assert api_query_mock.call_args_list == expected_calls

        wbtc_fee_asset = A_WBTC
        eur_fee_asset = A_EUR
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
    mock_bitfinex.first_connection = MagicMock()
    mock_bitfinex.currency_map = {'WBT': 'WBTC'}
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
            f'[{movement_2},{movement_1}]',
            f'[{movement_2},{movement_1}]',
            f'[{movement_3},{movement_2}]',
            f'[{movement_4}]',
        ]
        for result_ in results:
            yield result_

    def mock_api_query_response(endpoint, options):  # pylint: disable=unused-argument
        return MockResponse(HTTPStatus.OK, next(get_response))

    get_response = get_paginated_response()
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
        stack.enter_context(api_query_patch)
        asset_movements = mock_bitfinex.query_online_deposits_withdrawals(
            start_ts=Timestamp(0),
            end_ts=Timestamp(int(datetime.now().timestamp())),
        )
        wbtc_fee_asset = A_WBTC
        eur_fee_asset = A_EUR
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
