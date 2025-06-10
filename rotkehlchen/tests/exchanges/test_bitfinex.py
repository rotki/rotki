import datetime
import warnings as test_warnings
from collections.abc import Generator
from contextlib import ExitStack
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Final
from unittest.mock import MagicMock, call, patch

import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.converters import BITFINEX_EXCHANGE_TEST_ASSETS, asset_from_bitfinex
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_BTC, A_ETH, A_EUR, A_GLM, A_LINK, A_USD, A_USDT, A_WBTC
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.exchanges.bitfinex import (
    API_ERR_AUTH_NONCE_CODE,
    API_ERR_AUTH_NONCE_MESSAGE,
    API_KEY_ERROR_CODE,
    API_KEY_ERROR_MESSAGE,
    API_RATE_LIMITS_ERROR_MESSAGE,
    Bitfinex,
)
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.swap import SwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.history.events.utils import create_event_identifier_from_unique_id
from rotkehlchen.tests.utils.constants import A_NEO
from rotkehlchen.tests.utils.exchanges import get_exchange_asset_symbols
from rotkehlchen.tests.utils.globaldb import is_asset_symbol_unsupported
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import (
    ChainID,
    EvmTokenKind,
    Location,
    LocationAssetMappingUpdateEntry,
    Timestamp,
    TimestampMS,
)
from rotkehlchen.utils.misc import ts_ms_to_sec

if TYPE_CHECKING:
    from rotkehlchen.globaldb.handler import GlobalDBHandler
    from rotkehlchen.inquirer import Inquirer


# Deposit WBTC
MOVEMENT_1: Final = """
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

# Buy ETH with USDT
TRADE_1: Final = """
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
TRADE_2: Final = """
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
TRADE_3: Final = """
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


def test_name():
    exchange = Bitfinex('bitfinex1', 'a', b'a', object(), object())
    assert exchange.location == Location.BITFINEX
    assert exchange.name == 'bitfinex1'


@pytest.mark.asset_test
def test_assets_are_known(mock_bitfinex, globaldb):
    """This tests only exchange (trades) assets (not margin, nor futures ones).
    """
    for asset in get_exchange_asset_symbols(Location.BITFINEX):
        assert is_asset_symbol_unsupported(globaldb, Location.BITFINEX, asset) is False, f'Bitfinex assets {asset} should not be unsupported'  # noqa: E501

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

    try:
        mock_bitfinex._query_currency_map()
    except RemoteError as e:
        test_warnings.warn(UserWarning(
            f'Failed to request {mock_bitfinex.name} currency map. '
            f'Xfailing this test. {e!s}',
        ))
        pytest.xfail('Failed to request {mock_bitfinex.name} currency map')

    test_assets = set(BITFINEX_EXCHANGE_TEST_ASSETS)
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
            asset_from_bitfinex(bitfinex_name=symbol)
        except UnsupportedAsset:
            assert is_asset_symbol_unsupported(globaldb, Location.BITFINEX, symbol)
        except UnknownAsset as e:
            test_warnings.warn(UserWarning(
                f'Found unknown asset {e.identifier} with symbol {symbol} in '
                f'{mock_bitfinex.name}. Support for it has to be added',
            ))


def test_first_connection(mock_bitfinex, globaldb):
    """Test that 'pair_bfx_symbols_map' contain the expected data.
    """
    assert mock_bitfinex.first_connection_made is False
    assert hasattr(mock_bitfinex, 'pair_bfx_symbols_map') is False

    bitfinex_db_serialized = Location.BITFINEX.serialize_for_db()
    with globaldb.conn.read_ctx() as cursor:
        mappings_before = set(cursor.execute(
            'SELECT exchange_symbol, local_id FROM location_asset_mappings '
            'WHERE location=?;',
            (bitfinex_db_serialized,),
        ).fetchall())

    mock_bitfinex.first_connection()

    with globaldb.conn.read_ctx() as cursor:
        mappings_after = set(cursor.execute(
            'SELECT exchange_symbol, local_id FROM location_asset_mappings '
            'WHERE location=?;',
            (bitfinex_db_serialized,),
        ).fetchall())

    new_mappings = mappings_after - mappings_before
    assert len(new_mappings) > 0

    with globaldb.conn.read_ctx() as cursor:
        for bfx_symbol, _ in new_mappings:
            assert cursor.execute(
                'SELECT COUNT(*) FROM location_unsupported_assets '
                'WHERE location=? AND exchange_symbol=?;',
                (bitfinex_db_serialized, bfx_symbol),
            ).fetchone()[0] == 0  # no new mapping added for unsupported assets

    assert mock_bitfinex.pair_bfx_symbols_map['BTCUST'] == ('BTC', 'UST')
    assert mock_bitfinex.pair_bfx_symbols_map['UDCUSD'] == ('UDC', 'USD')
    assert mock_bitfinex.first_connection_made is True


def test_api_key_err_auth_nonce(mock_bitfinex: 'Bitfinex') -> None:
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

        events, _ = mock_bitfinex.query_online_history_events(Timestamp(0), Timestamp(1))
        assert events == []
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
def test_query_balances_asset_balance(
        mock_bitfinex: 'Bitfinex',
        inquirer: 'Inquirer',  # pylint: disable=unused-argument
        globaldb: 'GlobalDBHandler',
):
    """Test the balances of the assets are returned as expected.

    Also test the following logic:
      - An asset balance is the result of aggregating its balances per wallet
      type (i.e. exchange, margin and funding).
      - The balance of an asset in location_unsupported_assets is skipped.
      - The asset ticker is standardized (e.g. WBT to WBTC, UST to USDT).
    """
    mock_bitfinex.first_connection = MagicMock()  # type: ignore
    globaldb.add_location_asset_mappings([
        LocationAssetMappingUpdateEntry(
            location=Location.BITFINEX,
            location_symbol='GNT',
            asset=A_GLM,
        ),
    ])
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


def test_api_query_paginated_stops_requesting(mock_bitfinex: 'Bitfinex') -> None:
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
        result, with_errors = mock_bitfinex._api_query_paginated(
            options={'limit': 2},
            case='trades',
        )
        assert result == []
        assert with_errors is True


def test_api_query_paginated_retries_request(mock_bitfinex: 'Bitfinex') -> None:
    """Test retry logic works as expected.

    It also tests that trying to decode first the unsuccessful response
    JSON as a dict and later as a list (via `_process_unsuccessful_response()`)
    works as expected.
    """
    def get_paginated_response() -> Generator[str, None, None]:
        results = [
            f'{{"error":"{API_RATE_LIMITS_ERROR_MESSAGE}"}}',
            '["error", 10000, "unknown error"]',
        ]
        yield from results

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
        result, with_errors = mock_bitfinex._api_query_paginated(
            options={'limit': 2},
            case='trades',
        )
        assert result == []
        assert with_errors is True


def test_deserialize_trade_buy(mock_bitfinex):
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
    assert mock_bitfinex._deserialize_trade(raw_result=raw_result) == [SwapEvent(
        timestamp=TimestampMS(1573485493000),
        location=Location.BITFINEX,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_USDT,
        amount=FVal('49.3425179516'),
        event_identifier=create_event_identifier_from_unique_id(
            location=Location.BITFINEX,
            unique_id='399251013',
        ),
        location_label='bitfinex',
    ), SwapEvent(
        timestamp=TimestampMS(1573485493000),
        location=Location.BITFINEX,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_WBTC,
        amount=FVal('0.26334268'),
        event_identifier=create_event_identifier_from_unique_id(
            location=Location.BITFINEX,
            unique_id='399251013',
        ),
        location_label='bitfinex',
    ), SwapEvent(
        timestamp=TimestampMS(1573485493000),
        location=Location.BITFINEX,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_USD,
        amount=FVal('0.09868591'),
        event_identifier=create_event_identifier_from_unique_id(
            location=Location.BITFINEX,
            unique_id='399251013',
        ),
        location_label='bitfinex',
    )]


def test_deserialize_trade_sell(mock_bitfinex):
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
    assert mock_bitfinex._deserialize_trade(raw_result=raw_result) == [SwapEvent(
        timestamp=TimestampMS(1573485493000),
        location=Location.BITFINEX,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_ETH,
        amount=FVal('0.26334268'),
        event_identifier=create_event_identifier_from_unique_id(
            location=Location.BITFINEX,
            unique_id='399251013',
        ),
        location_label='bitfinex',
    ), SwapEvent(
        timestamp=TimestampMS(1573485493000),
        location=Location.BITFINEX,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_USDT,
        amount=FVal('49.3425179516'),
        event_identifier=create_event_identifier_from_unique_id(
            location=Location.BITFINEX,
            unique_id='399251013',
        ),
        location_label='bitfinex',
    ), SwapEvent(
        timestamp=TimestampMS(1573485493000),
        location=Location.BITFINEX,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_USD,
        amount=FVal('0.09868591'),
        event_identifier=create_event_identifier_from_unique_id(
            location=Location.BITFINEX,
            unique_id='399251013',
        ),
        location_label='bitfinex',
    )]


def test_delisted_pair_trades_work(mock_bitfinex: 'Bitfinex') -> None:
    """A user reported inability to deserialize trades from delisted pairs

    This is a regression test for this. RLC was delisted and as such is no
    longer in their returned currency maps.
    """
    rlc = get_or_create_evm_token(
        userdb=mock_bitfinex.db,
        evm_address=string_to_evm_address('0x607F4C5BB672230e8672085532f7e901544a7375'),
        chain_id=ChainID.ETHEREUM,
        token_kind=EvmTokenKind.ERC20,
    )
    mock_bitfinex.pair_bfx_symbols_map = {}
    raw_result = [
        399251013,
        'tRLCETH',
        1573485493000,
        33963608932,
        -0.26334268,
        187.37,
        'LIMIT',
        None,
        -1,
        -0.09868591,
        'RLC',
    ]
    assert mock_bitfinex._deserialize_trade(raw_result=raw_result) == [SwapEvent(
        timestamp=TimestampMS(1573485493000),
        location=Location.BITFINEX,
        event_subtype=HistoryEventSubType.SPEND,
        asset=rlc,
        amount=FVal('0.26334268'),
        event_identifier=create_event_identifier_from_unique_id(
            location=Location.BITFINEX,
            unique_id='399251013',
        ),
        location_label='bitfinex',
    ), SwapEvent(
        timestamp=TimestampMS(1573485493000),
        location=Location.BITFINEX,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_ETH,
        amount=FVal('49.3425179516'),
        event_identifier=create_event_identifier_from_unique_id(
            location=Location.BITFINEX,
            unique_id='399251013',
        ),
        location_label='bitfinex',
    ), SwapEvent(
        timestamp=TimestampMS(1573485493000),
        location=Location.BITFINEX,
        event_subtype=HistoryEventSubType.FEE,
        asset=rlc,
        amount=FVal('0.09868591'),
        event_identifier=create_event_identifier_from_unique_id(
            location=Location.BITFINEX,
            unique_id='399251013',
        ),
        location_label='bitfinex',
    )]


@pytest.mark.freeze_time(datetime.datetime(2020, 12, 3, 12, 0, 0, tzinfo=datetime.UTC))
def test_query_online_trade_history_case_1(mock_bitfinex: 'Bitfinex') -> None:
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
    mock_bitfinex.first_connection = MagicMock()  # type: ignore
    mock_bitfinex.pair_bfx_symbols_map = {
        'ETHUST': ('ETH', 'UST'),
        'WBTUSD': ('WBT', 'USD'),
        'ETHEUR': ('ETH', 'EUR'),
    }
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
            endpoint='movements',
            options={
                'start': 0,
                'end': 1606996800000,
                'limit': 1000,
            },
        ),
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

    def get_paginated_response() -> Generator[str, None, None]:
        results = [
            f'[{TRADE_1},{TRADE_2}]',
            f'[{TRADE_3},{trade_4}]',
            f'[{trade_5}]',
        ]
        yield from results

    def mock_api_query_response(endpoint, options):  # pylint: disable=unused-argument
        if endpoint == 'trades':
            return MockResponse(HTTPStatus.OK, next(get_response))

        return MockResponse(HTTPStatus.OK, '[]')

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
        events, actual_end_ts = mock_bitfinex.query_online_history_events(
            start_ts=Timestamp(0),
            end_ts=(end_ts := Timestamp(int(datetime.datetime.now(tz=datetime.UTC).timestamp()))),
        )
        assert api_query_mock.call_args_list == expected_calls
        assert end_ts == actual_end_ts
        assert events == [SwapEvent(
            timestamp=TimestampMS(1606899600000),
            location=Location.BITFINEX,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_USDT,
            amount=FVal('49.3425179516'),
            event_identifier=create_event_identifier_from_unique_id(
                location=Location.BITFINEX,
                unique_id='1',
            ),
            location_label='bitfinex',
        ), SwapEvent(
            timestamp=TimestampMS(1606899600000),
            location=Location.BITFINEX,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ETH,
            amount=FVal('0.26334268'),
            event_identifier=create_event_identifier_from_unique_id(
                location=Location.BITFINEX,
                unique_id='1',
            ),
            location_label='bitfinex',
        ), SwapEvent(
            timestamp=TimestampMS(1606899600000),
            location=Location.BITFINEX,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_USD,
            amount=FVal('0.09868591'),
            event_identifier=create_event_identifier_from_unique_id(
                location=Location.BITFINEX,
                unique_id='1',
            ),
            location_label='bitfinex',
        ), SwapEvent(
            timestamp=TimestampMS(1606901400000),
            location=Location.BITFINEX,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            amount=FVal('0.26334268'),
            event_identifier=create_event_identifier_from_unique_id(
                location=Location.BITFINEX,
                unique_id='2',
            ),
            location_label='bitfinex',
        ), SwapEvent(
            timestamp=TimestampMS(1606901400000),
            location=Location.BITFINEX,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_USDT,
            amount=FVal('49.3425179516'),
            event_identifier=create_event_identifier_from_unique_id(
                location=Location.BITFINEX,
                unique_id='2',
            ),
            location_label='bitfinex',
        ), SwapEvent(
            timestamp=TimestampMS(1606901400000),
            location=Location.BITFINEX,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.09868591'),
            event_identifier=create_event_identifier_from_unique_id(
                location=Location.BITFINEX,
                unique_id='2',
            ),
            location_label='bitfinex',
        ), SwapEvent(
            timestamp=TimestampMS(1606932000000),
            location=Location.BITFINEX,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_USD,
            amount=FVal('0.500000'),
            event_identifier=create_event_identifier_from_unique_id(
                location=Location.BITFINEX,
                unique_id='3',
            ),
            location_label='bitfinex',
        ), SwapEvent(
            timestamp=TimestampMS(1606932000000),
            location=Location.BITFINEX,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_WBTC,
            amount=FVal('10000.0'),
            event_identifier=create_event_identifier_from_unique_id(
                location=Location.BITFINEX,
                unique_id='3',
            ),
            location_label='bitfinex',
        ), SwapEvent(
            timestamp=TimestampMS(1606932000000),
            location=Location.BITFINEX,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_USD,
            amount=FVal('20.0'),
            event_identifier=create_event_identifier_from_unique_id(
                location=Location.BITFINEX,
                unique_id='3',
            ),
            location_label='bitfinex',
        ), SwapEvent(
            timestamp=TimestampMS(1606986000000),
            location=Location.BITFINEX,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_WBTC,
            amount=FVal('10000.0'),
            event_identifier=create_event_identifier_from_unique_id(
                location=Location.BITFINEX,
                unique_id='4',
            ),
            location_label='bitfinex',
        ), SwapEvent(
            timestamp=TimestampMS(1606986000000),
            location=Location.BITFINEX,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_USD,
            amount=FVal('0.500000'),
            event_identifier=create_event_identifier_from_unique_id(
                location=Location.BITFINEX,
                unique_id='4',
            ),
            location_label='bitfinex',
        ), SwapEvent(
            timestamp=TimestampMS(1606986000000),
            location=Location.BITFINEX,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_BTC,
            amount=FVal('20.0'),
            event_identifier=create_event_identifier_from_unique_id(
                location=Location.BITFINEX,
                unique_id='4',
            ),
            location_label='bitfinex',
        )]


@pytest.mark.freeze_time(datetime.datetime(2020, 12, 3, 12, 0, 0, tzinfo=datetime.UTC))
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
            f'[{trade_1},{TRADE_2}]',
            f'[{trade_1},{TRADE_2}]',  # repeated line
            f'[{TRADE_2},{TRADE_3}]',  # contains repeated
            f'[{trade_4}]',
        ]
        yield from results

    def mock_api_query_response(endpoint, options):  # pylint: disable=unused-argument
        if endpoint == 'trades':
            return MockResponse(HTTPStatus.OK, next(get_response))

        return MockResponse(HTTPStatus.OK, '[]')

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
        events, actual_end_ts = mock_bitfinex.query_online_history_events(
            start_ts=Timestamp(0),
            end_ts=(end_ts := Timestamp(int(datetime.datetime.now(tz=datetime.UTC).timestamp()))),
        )
        assert end_ts == actual_end_ts
        assert events == [SwapEvent(
            timestamp=TimestampMS(1606899600000),
            location=Location.BITFINEX,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_USDT,
            amount=FVal('49.3425179516'),
            event_identifier=create_event_identifier_from_unique_id(
                location=Location.BITFINEX,
                unique_id='1',
            ),
            location_label='bitfinex',
        ), SwapEvent(
            timestamp=TimestampMS(1606899600000),
            location=Location.BITFINEX,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ETH,
            amount=FVal('0.26334268'),
            event_identifier=create_event_identifier_from_unique_id(
                location=Location.BITFINEX,
                unique_id='1',
            ),
            location_label='bitfinex',
        ), SwapEvent(
            timestamp=TimestampMS(1606899600000),
            location=Location.BITFINEX,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_USDT,
            amount=FVal('0.09868591'),
            event_identifier=create_event_identifier_from_unique_id(
                location=Location.BITFINEX,
                unique_id='1',
            ),
            location_label='bitfinex',
        ), SwapEvent(
            timestamp=TimestampMS(1606901400000),
            location=Location.BITFINEX,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            amount=FVal('0.26334268'),
            event_identifier=create_event_identifier_from_unique_id(
                location=Location.BITFINEX,
                unique_id='2',
            ),
            location_label='bitfinex',
        ), SwapEvent(
            timestamp=TimestampMS(1606901400000),
            location=Location.BITFINEX,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_USDT,
            amount=FVal('49.3425179516'),
            event_identifier=create_event_identifier_from_unique_id(
                location=Location.BITFINEX,
                unique_id='2',
            ),
            location_label='bitfinex',
        ), SwapEvent(
            timestamp=TimestampMS(1606901400000),
            location=Location.BITFINEX,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.09868591'),
            event_identifier=create_event_identifier_from_unique_id(
                location=Location.BITFINEX,
                unique_id='2',
            ),
            location_label='bitfinex',
        ), SwapEvent(
            timestamp=TimestampMS(1606932000000),
            location=Location.BITFINEX,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_USD,
            amount=FVal('0.500000'),
            event_identifier=create_event_identifier_from_unique_id(
                location=Location.BITFINEX,
                unique_id='3',
            ),
            location_label='bitfinex',
        ), SwapEvent(
            timestamp=TimestampMS(1606932000000),
            location=Location.BITFINEX,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_WBTC,
            amount=FVal('10000.0'),
            event_identifier=create_event_identifier_from_unique_id(
                location=Location.BITFINEX,
                unique_id='3',
            ),
            location_label='bitfinex',
        ), SwapEvent(
            timestamp=TimestampMS(1606932000000),
            location=Location.BITFINEX,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_USD,
            amount=FVal('20.0'),
            event_identifier=create_event_identifier_from_unique_id(
                location=Location.BITFINEX,
                unique_id='3',
            ),
            location_label='bitfinex',
        ), SwapEvent(
            timestamp=TimestampMS(1606986000000),
            location=Location.BITFINEX,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_WBTC,
            amount=FVal('10000.0'),
            event_identifier=create_event_identifier_from_unique_id(
                location=Location.BITFINEX,
                unique_id='4',
            ),
            location_label='bitfinex',
        ), SwapEvent(
            timestamp=TimestampMS(1606986000000),
            location=Location.BITFINEX,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_USD,
            amount=FVal('0.500000'),
            event_identifier=create_event_identifier_from_unique_id(
                location=Location.BITFINEX,
                unique_id='4',
            ),
            location_label='bitfinex',
        ), SwapEvent(
            timestamp=TimestampMS(1606986000000),
            location=Location.BITFINEX,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_WBTC,
            amount=FVal('20.0'),
            event_identifier=create_event_identifier_from_unique_id(
                location=Location.BITFINEX,
                unique_id='4',
            ),
            location_label='bitfinex',
        )]


def test_deserialize_asset_movement_deposit(mock_bitfinex: 'Bitfinex') -> None:
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
    expected_asset_movement = [AssetMovement(
        timestamp=TimestampMS(1569348774000),
        location=Location.BITFINEX,
        location_label=mock_bitfinex.name,
        event_type=HistoryEventType.DEPOSIT,
        asset=fee_asset,
        amount=FVal('0.26300954'),
        unique_id='13105603',
        extra_data={
            'reference': '13105603',
            'address': 'DESTINATION_ADDRESS',
            'transaction_id': 'TRANSACTION_ID',
        },
    ), AssetMovement(
        timestamp=TimestampMS(1569348774000),
        location=Location.BITFINEX,
        location_label=mock_bitfinex.name,
        event_type=HistoryEventType.DEPOSIT,
        asset=fee_asset,
        amount=FVal('0.00135'),
        unique_id='13105603',
        is_fee=True,
    )]
    asset_movement = mock_bitfinex._deserialize_asset_movement(raw_result=raw_result)
    assert asset_movement == expected_asset_movement


def test_deserialize_asset_movement_withdrawal(mock_bitfinex: 'Bitfinex') -> None:
    """Test also both 'address' and 'transaction_id' are None for fiat
    movements.
    """
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
    expected_asset_movement = [AssetMovement(
        timestamp=TimestampMS(1569348774000),
        location=Location.BITFINEX,
        location_label=mock_bitfinex.name,
        event_type=HistoryEventType.WITHDRAWAL,
        asset=fee_asset,
        amount=FVal('0.26300954'),
        unique_id='13105603',
        extra_data={'reference': '13105603'},
    ), AssetMovement(
        timestamp=TimestampMS(1569348774000),
        location=Location.BITFINEX,
        location_label=mock_bitfinex.name,
        event_type=HistoryEventType.WITHDRAWAL,
        asset=fee_asset,
        amount=FVal('0.00135'),
        unique_id='13105603',
        is_fee=True,
    )]
    asset_movement = mock_bitfinex._deserialize_asset_movement(raw_result=raw_result)
    assert asset_movement == expected_asset_movement


@pytest.mark.freeze_time(datetime.datetime(2020, 12, 3, 12, 0, 0, tzinfo=datetime.UTC))
def test_query_online_deposits_withdrawals_case_1(mock_bitfinex: 'Bitfinex') -> None:
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
    mock_bitfinex.first_connection = MagicMock()  # type: ignore
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
        call(
            endpoint='trades',
            options={
                'start': 0,
                'end': 1606996800000,
                'limit': 2500,
                'sort': 1,
            },
        ),
    ]

    def get_paginated_response() -> Generator[str, None, None]:
        results = [
            f'[{movement_2},{movement_1}]',
            f'[{movement_4},{movement_3}]',
            f'[{movement_5}]',
        ]
        yield from results

    def mock_api_query_response(endpoint: str, options: dict[str, Any]) -> MockResponse:  # pylint: disable=unused-argument
        if endpoint == 'movements':
            return MockResponse(HTTPStatus.OK, next(get_response))

        return MockResponse(HTTPStatus.OK, '[]')

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
        asset_movements, _ = mock_bitfinex.query_online_history_events(
            start_ts=Timestamp(0),
            end_ts=Timestamp(int(datetime.datetime.now(tz=datetime.UTC).timestamp())),
        )
        assert api_query_mock.call_args_list == expected_calls

        wbtc_fee_asset = A_WBTC
        eur_fee_asset = A_EUR
        expected_asset_movements = [
            AssetMovement(
                timestamp=TimestampMS(1606899600000),
                location=Location.BITFINEX,
                location_label=mock_bitfinex.name,
                event_type=HistoryEventType.DEPOSIT,
                asset=wbtc_fee_asset,
                amount=FVal('0.26300954'),
                unique_id='1',
                extra_data={
                    'reference': '1',
                    'address': 'DESTINATION_ADDRESS',
                    'transaction_id': 'TRANSACTION_ID',
                },
            ),
            AssetMovement(
                timestamp=TimestampMS(1606899600000),
                location=Location.BITFINEX,
                location_label=mock_bitfinex.name,
                event_type=HistoryEventType.DEPOSIT,
                asset=wbtc_fee_asset,
                amount=FVal('0.00135'),
                unique_id='1',
                is_fee=True,
            ),
            AssetMovement(
                timestamp=TimestampMS(1606901400000),
                location=Location.BITFINEX,
                location_label=mock_bitfinex.name,
                event_type=HistoryEventType.WITHDRAWAL,
                asset=wbtc_fee_asset,
                amount=FVal('0.26300954'),
                unique_id='2',
                extra_data={
                    'reference': '2',
                    'address': 'DESTINATION_ADDRESS',
                    'transaction_id': 'TRANSACTION_ID',
                },
            ),
            AssetMovement(
                timestamp=TimestampMS(1606901400000),
                location=Location.BITFINEX,
                location_label=mock_bitfinex.name,
                event_type=HistoryEventType.WITHDRAWAL,
                asset=wbtc_fee_asset,
                amount=FVal('0.00135'),
                unique_id='2',
                is_fee=True,
            ),
            AssetMovement(
                timestamp=TimestampMS(1606986000000),
                location=Location.BITFINEX,
                location_label=mock_bitfinex.name,
                event_type=HistoryEventType.WITHDRAWAL,
                asset=eur_fee_asset,
                amount=FVal('0.26300954'),
                unique_id='4',
                extra_data={'reference': '4'},
            ),
            AssetMovement(
                timestamp=TimestampMS(1606986000000),
                location=Location.BITFINEX,
                location_label=mock_bitfinex.name,
                event_type=HistoryEventType.WITHDRAWAL,
                asset=eur_fee_asset,
                amount=FVal('0.00135'),
                unique_id='4',
                is_fee=True,
            ),
        ]
        assert asset_movements == expected_asset_movements


@pytest.mark.freeze_time(datetime.datetime(2020, 12, 3, 12, 0, 0, tzinfo=datetime.UTC))
def test_query_online_deposits_withdrawals_case_2(mock_bitfinex: 'Bitfinex') -> None:
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
    mock_bitfinex.first_connection = MagicMock()  # type: ignore
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

    def get_paginated_response() -> Generator[str, None, None]:
        results = [
            f'[{movement_2},{movement_1}]',
            f'[{movement_2},{movement_1}]',
            f'[{movement_3},{movement_2}]',
            f'[{movement_4}]',
        ]
        yield from results

    def mock_api_query_response(endpoint, options):  # pylint: disable=unused-argument
        if endpoint == 'movements':
            return MockResponse(HTTPStatus.OK, next(get_response))

        return MockResponse(HTTPStatus.OK, '[]')

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
        asset_movements, _ = mock_bitfinex.query_online_history_events(
            start_ts=Timestamp(0),
            end_ts=Timestamp(int(datetime.datetime.now(tz=datetime.UTC).timestamp())),
        )
        wbtc_fee_asset = A_WBTC
        eur_fee_asset = A_EUR
        expected_asset_movements = [
            AssetMovement(
                timestamp=TimestampMS(1606899600000),
                location=Location.BITFINEX,
                location_label=mock_bitfinex.name,
                event_type=HistoryEventType.DEPOSIT,
                asset=wbtc_fee_asset,
                amount=FVal('0.26300954'),
                unique_id='1',
                extra_data={
                    'reference': '1',
                    'address': 'DESTINATION_ADDRESS',
                    'transaction_id': 'TRANSACTION_ID',
                },
            ),
            AssetMovement(
                timestamp=TimestampMS(1606899600000),
                location=Location.BITFINEX,
                location_label=mock_bitfinex.name,
                event_type=HistoryEventType.DEPOSIT,
                asset=wbtc_fee_asset,
                amount=FVal('0.00135'),
                unique_id='1',
                is_fee=True,
            ),
            AssetMovement(
                timestamp=TimestampMS(1606901400000),
                location=Location.BITFINEX,
                location_label=mock_bitfinex.name,
                event_type=HistoryEventType.WITHDRAWAL,
                asset=wbtc_fee_asset,
                amount=FVal('0.26300954'),
                unique_id='2',
                extra_data={
                    'reference': '2',
                    'address': 'DESTINATION_ADDRESS',
                    'transaction_id': 'TRANSACTION_ID',
                },
            ),
            AssetMovement(
                timestamp=TimestampMS(1606901400000),
                location=Location.BITFINEX,
                location_label=mock_bitfinex.name,
                event_type=HistoryEventType.WITHDRAWAL,
                asset=wbtc_fee_asset,
                amount=FVal('0.00135'),
                unique_id='2',
                is_fee=True,
            ),
            AssetMovement(
                timestamp=TimestampMS(1606986000000),
                location=Location.BITFINEX,
                location_label=mock_bitfinex.name,
                event_type=HistoryEventType.WITHDRAWAL,
                asset=eur_fee_asset,
                amount=FVal('0.26300954'),
                unique_id='3',
                extra_data={'reference': '3'},
            ),
            AssetMovement(
                timestamp=TimestampMS(1606986000000),
                location=Location.BITFINEX,
                location_label=mock_bitfinex.name,
                event_type=HistoryEventType.WITHDRAWAL,
                asset=eur_fee_asset,
                amount=FVal('0.00135'),
                unique_id='3',
                is_fee=True,
            ),
            AssetMovement(
                timestamp=TimestampMS(1606996800000),
                location=Location.BITFINEX,
                location_label=mock_bitfinex.name,
                event_type=HistoryEventType.DEPOSIT,
                asset=wbtc_fee_asset,
                amount=FVal('0.26300954'),
                unique_id='4',
                extra_data={
                    'reference': '4',
                    'address': 'DESTINATION_ADDRESS',
                    'transaction_id': 'TRANSACTION_ID',
                },
            ),
            AssetMovement(
                timestamp=TimestampMS(1606996800000),
                location=Location.BITFINEX,
                location_label=mock_bitfinex.name,
                event_type=HistoryEventType.DEPOSIT,
                asset=wbtc_fee_asset,
                amount=FVal('0.00135'),
                unique_id='4',
                is_fee=True,
            ),
        ]
        assert asset_movements == expected_asset_movements


def test_partial_query_online_history_events(mock_bitfinex: 'Bitfinex') -> None:
    """Test that the logic for history events works as expected when there is an error
    causing only part of the range to be queried.
    """
    api_limit = 2
    mock_bitfinex.first_connection = MagicMock()  # type: ignore
    mock_bitfinex.pair_bfx_symbols_map = {'ETHUST': ('ETH', 'UST')}
    expected_calls = [
        call(
            endpoint='movements',
            options={
                'start': 0,
                'end': 1743533561000,
                'limit': 2,
            },
        ),
        call(
            endpoint='trades',
            options={
                'start': 0,
                'end': 1743533561000,
                'limit': 2,
                'sort': 1,
            },
        ),
        call(
            endpoint='trades',
            options={
                'start': 1606901400000,
                'end': 1743533561000,
                'limit': 2,
                'sort': 1,
            },
        ),
    ]

    def get_paginated_response() -> Generator[tuple[HTTPStatus, str], None, None]:
        results = [
            (HTTPStatus.OK, f'[{MOVEMENT_1}]'),
            (HTTPStatus.OK, f'[{TRADE_1},{TRADE_2}]'),
            (HTTPStatus.INTERNAL_SERVER_ERROR, 'xxxxxxx'),
        ]
        yield from results

    def mock_api_query_response(endpoint: str, options: dict[str, Any]) -> MockResponse:  # pylint: disable=unused-argument
        status, text = next(get_response)
        return MockResponse(status, text)

    get_response = get_paginated_response()
    with ExitStack() as stack:
        stack.enter_context(patch(
            target='rotkehlchen.exchanges.bitfinex.API_MOVEMENTS_MAX_LIMIT',
            new=api_limit,
        ))
        stack.enter_context(patch(
            target='rotkehlchen.exchanges.bitfinex.API_TRADES_MAX_LIMIT',
            new=api_limit,
        ))
        api_query_mock = stack.enter_context(patch.object(
            target=mock_bitfinex,
            attribute='_api_query',
            side_effect=mock_api_query_response,
        ))
        events, actual_end_ts = mock_bitfinex.query_online_history_events(
            start_ts=Timestamp(0),
            end_ts=(end_ts := Timestamp(1743533561)),
        )
        assert api_query_mock.call_args_list == expected_calls
        assert len(events) == 8  # withdrawal/fee from one movement, and spend/receive/fee from two trades.  # noqa: E501
        assert actual_end_ts == ts_ms_to_sec(events[-1].timestamp)
        assert actual_end_ts != end_ts  # There were errors and only part of the range was queried.
