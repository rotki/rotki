import datetime
import hashlib
import hmac
import os
import warnings as test_warnings
from contextlib import ExitStack
from typing import TYPE_CHECKING, cast
from unittest.mock import call, patch
from urllib.parse import urlencode

import pytest
import requests

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.converters import asset_from_binance
from rotkehlchen.constants.assets import A_ADA, A_BNB, A_BTC, A_DOT, A_ETH, A_EUR, A_USDT, A_WBTC
from rotkehlchen.constants.misc import ONE
from rotkehlchen.db.cache import DBCacheDynamic
from rotkehlchen.db.constants import BINANCE_MARKETS_KEY
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.exchanges.binance import (
    API_TIME_INTERVAL_CONSTRAINT_TS,
    BINANCE_ASSETS_STARTING_WITH_LD,
    BINANCE_LAUNCH_TS,
    RETRY_AFTER_LIMIT,
    Binance,
    trade_from_binance,
)
from rotkehlchen.exchanges.data_structures import Location
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.swap import SwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType
from rotkehlchen.tests.utils.constants import A_AXS, A_BUSD, A_LUNA, A_RDN
from rotkehlchen.tests.utils.exchanges import (
    BINANCE_DEPOSITS_HISTORY_RESPONSE,
    BINANCE_FIATBUY_RESPONSE,
    BINANCE_FIATDEPOSITS_RESPONSE,
    BINANCE_FIATSELL_RESPONSE,
    BINANCE_FIATWITHDRAWS_RESPONSE,
    BINANCE_MYTRADES_RESPONSE,
    BINANCE_WITHDRAWALS_HISTORY_RESPONSE,
    assert_binance_asset_movements_result,
    get_exchange_asset_symbols,
    mock_binance_balance_response,
)
from rotkehlchen.tests.utils.globaldb import is_asset_symbol_unsupported
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import ApiKey, ApiSecret, Timestamp, TimestampMS
from rotkehlchen.utils.misc import ts_now_in_ms

if TYPE_CHECKING:
    from rotkehlchen.history.events.structures.asset_movement import AssetMovement
    from rotkehlchen.history.price import PriceHistorian


def test_name():
    exchange = Binance('binance1', 'a', b'a', object(), object())
    assert exchange.location == Location.BINANCE
    assert exchange.name == 'binance1'


def test_trade_from_binance(function_scope_binance):
    binance = function_scope_binance
    binance_trades_list = [
        {
            'symbol': 'RDNETH',
            'id': 1,
            'orderId': 1,
            'price': FVal(0.0063213),
            'qty': FVal(5.0),
            'commission': FVal(0.005),
            'commissionAsset': 'RDN',
            'time': 1512561941000,
            'isBuyer': True,
            'isMaker': False,
            'isBestMatch': True,
        }, {
            'symbol': 'ETHUSDT',
            'id': 2,
            'orderId': 2,
            'price': FVal(481.0),
            'qty': FVal(0.505),
            'commission': FVal(0.242905),
            'commissionAsset': 'USDT',
            'time': 1531117990000,
            'isBuyer': False,
            'isMaker': True,
            'isBestMatch': True,
        }, {
            'symbol': 'BTCUSDT',
            'id': 3,
            'orderId': 3,
            'price': FVal(6376.39),
            'qty': FVal(0.051942),
            'commission': FVal(0.00005194),
            'commissionAsset': 'BTC',
            'time': 1531728338000,
            'isBuyer': True,
            'isMaker': False,
            'isBestMatch': True,
        }, {
            'symbol': 'ADAUSDT',
            'id': 4,
            'orderId': 4,
            'price': FVal(0.17442),
            'qty': FVal(285.2),
            'commission': FVal(0.00180015),
            'commissionAsset': 'BNB',
            'time': 1531871806000,
            'isBuyer': False,
            'isMaker': True,
            'isBestMatch': True,
        },
    ]
    our_expected_list = [
        [SwapEvent(
            timestamp=TimestampMS(1512561941000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            amount=FVal('0.03160650'),
            unique_id='1',
        ), SwapEvent(
            timestamp=TimestampMS(1512561941000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_RDN,
            amount=FVal('5.0'),
            unique_id='1',
        ), SwapEvent(
            timestamp=TimestampMS(1512561941000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_RDN,
            amount=FVal('0.005'),
            unique_id='1',
        )],
        [SwapEvent(
            timestamp=TimestampMS(1531117990000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            amount=FVal('0.505'),
            unique_id='2',
        ), SwapEvent(
            timestamp=TimestampMS(1531117990000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_USDT,
            amount=FVal('242.9050'),
            unique_id='2',
        ), SwapEvent(
            timestamp=TimestampMS(1531117990000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_USDT,
            amount=FVal('0.242905'),
            unique_id='2',
        )],
        [SwapEvent(
            timestamp=TimestampMS(1531728338000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_USDT,
            amount=FVal('331.20244938'),
            unique_id='3',
        ), SwapEvent(
            timestamp=TimestampMS(1531728338000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_BTC,
            amount=FVal('0.051942'),
            unique_id='3',
        ), SwapEvent(
            timestamp=TimestampMS(1531728338000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_BTC,
            amount=FVal('0.00005194'),
            unique_id='3',
        )],
        [SwapEvent(
            timestamp=TimestampMS(1531871806000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ADA,
            amount=FVal('285.2'),
            unique_id='4',
        ), SwapEvent(
            timestamp=TimestampMS(1531871806000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_USDT,
            amount=FVal('49.744584'),
            unique_id='4',
        ), SwapEvent(
            timestamp=TimestampMS(1531871806000),
            location=Location.BINANCE,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_BNB,
            amount=FVal('0.00180015'),
            unique_id='4',
        )],
    ]

    for idx, binance_trade in enumerate(binance_trades_list):
        _, events = trade_from_binance(binance_trade, binance.symbols_to_pair, location=Location.BINANCE)  # noqa: E501
        assert events == our_expected_list[idx]
        assert isinstance(events[2].asset, Asset)


@pytest.mark.skipif(
    'CI' in os.environ,
    reason='https://twitter.com/LefterisJP/status/1598107187184037888',
)
def test_binance_assets_are_known(inquirer, globaldb):  # pylint: disable=unused-argument
    for asset in get_exchange_asset_symbols(Location.BINANCE):
        assert is_asset_symbol_unsupported(globaldb, Location.BINANCE, asset) is False, f'Binance assets {asset} should not be unsupported'  # noqa: E501

    exchange_data = requests.get('https://api3.binance.com/api/v3/exchangeInfo').json()
    binance_assets = set()
    assets_starting_with_ld = set()
    for pair_symbol in exchange_data['symbols']:
        for atype in ('baseAsset', 'quoteAsset'):
            symbol = pair_symbol[atype]
            if symbol.startswith('LD'):
                assets_starting_with_ld.add(symbol)
            binance_assets.add(symbol)

    sorted_assets = sorted(binance_assets)
    for binance_asset in sorted_assets:
        try:
            _ = asset_from_binance(binance_asset)
        except UnsupportedAsset:
            assert is_asset_symbol_unsupported(globaldb, Location.BINANCE, binance_asset)
        except UnknownAsset as e:
            test_warnings.warn(UserWarning(
                f'Found unknown asset {e.identifier} with symbol {binance_asset} in binance. '
                f'Support for it has to be added',
            ))

    assert assets_starting_with_ld == set(BINANCE_ASSETS_STARTING_WITH_LD)


def test_binance_query_balances_include_features(function_scope_binance: Binance):
    """Test that querying binance balances includes the futures wallet"""
    binance = function_scope_binance
    with patch.object(
        target=binance.session,
        attribute='request',
        side_effect=mock_binance_balance_response,
    ):
        balances, msg = binance.query_balances()

    assert msg == ''
    assert len(balances) == 7
    assert balances[A_BTC].amount == FVal('4723849.39208129')
    assert balances[A_ETH].amount == FVal('4763368.68006011')
    assert balances[A_BUSD].amount == FVal('5.82211108')
    assert balances[A_USDT].amount == FVal('202.01000000')
    assert balances[A_DOT].amount == FVal('500.55')
    assert balances[A_WBTC].amount == FVal('2.1')
    assert balances[A_AXS].amount == FVal('122.09202928')


def test_binance_query_trade_history(function_scope_binance: 'Binance'):
    """Test that turning a binance trade as returned by the server to our format works"""
    binance = function_scope_binance

    def mock_my_trades(url, params, **kwargs):  # pylint: disable=unused-argument
        if 'myTrades' in url:
            if params.get('symbol') == 'BNBBTC':
                text = BINANCE_MYTRADES_RESPONSE
            else:
                text = '[]'
        elif 'fiat/payments' in url:
            from_ts, to_ts = params.get('startTime'), params.get('endTime')
            if params.get('transactionType') == 0:
                if from_ts < 1624529919000 < to_ts:
                    text = BINANCE_FIATBUY_RESPONSE
                else:
                    text = '[]'
            elif params.get('transactionType') == 1:
                if from_ts < 1628529919000 < to_ts:
                    text = BINANCE_FIATSELL_RESPONSE
                else:
                    text = '[]'
            else:
                raise AssertionError('Unexpected binance request in test')
        else:
            text = '[]'

        return MockResponse(200, text)

    with patch.object(binance.session, 'request', side_effect=mock_my_trades):
        events, _ = binance.query_online_history_events(
            start_ts=Timestamp(0),
            end_ts=Timestamp(1638529919),
        )

    with function_scope_binance.db.conn.read_ctx() as cursor:
        assert function_scope_binance.db.get_dynamic_cache(
            cursor=cursor,
            name=DBCacheDynamic.BINANCE_PAIR_LAST_ID,
            location=function_scope_binance.location.serialize(),
            location_name=function_scope_binance.name,
            queried_pair='BNBBTC',
        ) == 28457

    assert events == [SwapEvent(
        timestamp=TimestampMS(1499865549590),
        location=Location.BINANCE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_BTC,
        amount=FVal('48.0000120000000000'),
        unique_id='28457',
    ), SwapEvent(
        timestamp=TimestampMS(1499865549590),
        location=Location.BINANCE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_BNB,
        amount=FVal('12.00000000'),
        unique_id='28457',
    ), SwapEvent(
        timestamp=TimestampMS(1499865549590),
        location=Location.BINANCE,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_BNB,
        amount=FVal('10.10000000'),
        unique_id='28457',
    ), SwapEvent(
        timestamp=TimestampMS(1624529919000),
        location=Location.BINANCE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_EUR,
        amount=FVal('19.800000064'),
        location_label='binance',
        unique_id='353fca443f06466db0c4dc89f94f027a',
    ), SwapEvent(
        timestamp=TimestampMS(1624529919000),
        location=Location.BINANCE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_LUNA,
        amount=FVal('4.462'),
        location_label='binance',
        unique_id='353fca443f06466db0c4dc89f94f027a',
    ), SwapEvent(
        timestamp=TimestampMS(1624529919000),
        location=Location.BINANCE,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_EUR,
        amount=FVal('0.2'),
        location_label='binance',
        unique_id='353fca443f06466db0c4dc89f94f027a',
    ), SwapEvent(
        timestamp=TimestampMS(1628529919000),
        location=Location.BINANCE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_ETH,
        amount=FVal('4.462'),
        location_label='binance',
        unique_id='463fca443f06466db0c4dc89f94f027a',
    ), SwapEvent(
        timestamp=TimestampMS(1628529919000),
        location=Location.BINANCE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_EUR,
        amount=FVal('19.800000064'),
        location_label='binance',
        unique_id='463fca443f06466db0c4dc89f94f027a',
    ), SwapEvent(
        timestamp=TimestampMS(1628529919000),
        location=Location.BINANCE,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_EUR,
        amount=FVal('0.2'),
        location_label='binance',
        unique_id='463fca443f06466db0c4dc89f94f027a',
    )]


def test_binance_query_trade_history_unexpected_data(function_scope_binance):
    """Test that turning a binance trade that contains unexpected data is handled gracefully"""
    binance = function_scope_binance
    binance.cache_ttl_secs = 0

    def mock_my_trades(url, params, **kwargs):  # pylint: disable=unused-argument
        if params.get('symbol') == 'BNBBTC' or params.get('symbol') == 'doesnotexist':
            text = BINANCE_MYTRADES_RESPONSE
        else:
            text = '[]'

        return MockResponse(200, text)

    def query_binance_and_test(input_trade_str, query_specific_markets=None):
        patch_get = patch.object(binance.session, 'request', side_effect=mock_my_trades)
        patch_response = patch(
            'rotkehlchen.tests.exchanges.test_binance.BINANCE_MYTRADES_RESPONSE',
            new=input_trade_str,
        )
        binance.selected_pairs = query_specific_markets
        with patch_get, patch_response:
            events, _ = binance.query_online_history_events(
                start_ts=Timestamp(0),
                end_ts=Timestamp(1564301134),
            )

        assert len(events) == 0

    input_str = BINANCE_MYTRADES_RESPONSE.replace(
        '"qty": "12.00000000"',
        '"qty": "dsadsad"',
    )
    query_binance_and_test(input_str)

    input_str = BINANCE_MYTRADES_RESPONSE.replace(
        '"price": "4.00000100"',
        '"price": null',
    )
    query_binance_and_test(input_str)

    input_str = BINANCE_MYTRADES_RESPONSE.replace(
        '"symbol": "BNBBTC"',
        '"symbol": "nonexistingmarket"',
    )
    query_binance_and_test(
        input_str,
        query_specific_markets=['doesnotexist'],
    )

    input_str = BINANCE_MYTRADES_RESPONSE.replace(
        '"time": 1499865549590',
        '"time": "sadsad"',
    )
    query_binance_and_test(input_str)

    # Delete an entry
    input_str = BINANCE_MYTRADES_RESPONSE.replace('"isBuyer": true,', '')
    query_binance_and_test(input_str)

    input_str = BINANCE_MYTRADES_RESPONSE.replace(
        '"commission": "10.10000000"',
        '"commission": "fdfdfdsf"',
    )
    query_binance_and_test(input_str)

    # unsupported fee currency
    input_str = BINANCE_MYTRADES_RESPONSE.replace(
        '"commissionAsset": "BNB"',
        '"commissionAsset": "BTCB"',
    )
    query_binance_and_test(input_str)

    # unknown fee currency
    input_str = BINANCE_MYTRADES_RESPONSE.replace(
        '"commissionAsset": "BNB"',
        '"commissionAsset": "DSDSDS"',
    )
    query_binance_and_test(input_str)


def test_binance_query_deposits_withdrawals(function_scope_binance: 'Binance') -> None:
    """Test the happy case of binance deposit withdrawal query

    NB: set `start_ts` and `end_ts` with a difference less than 90 days to
    prevent requesting with a time delta.
    """
    start_ts = 1508022000  # 2017-10-15
    end_ts = 1636400907
    binance = function_scope_binance

    def mock_get_history_events(url, params, **kwargs):  # pylint: disable=unused-argument
        from_ts, to_ts = params.get('startTime'), params.get('endTime')
        if 'capital/deposit' in url:
            if from_ts >= 1508022000000 and to_ts <= 1515797999999:
                response_str = BINANCE_DEPOSITS_HISTORY_RESPONSE
            else:
                response_str = '[]'
        elif 'capital/withdraw' in url:
            if from_ts <= 1508198532000 <= to_ts:
                response_str = BINANCE_WITHDRAWALS_HISTORY_RESPONSE
            else:
                response_str = '[]'
        elif 'fiat/orders' in url:
            from_ts, to_ts = params.get('startTime'), params.get('endTime')
            if params.get('transactionType') == 0:
                if from_ts < 1626144956000 < to_ts:
                    response_str = BINANCE_FIATDEPOSITS_RESPONSE
                else:
                    response_str = '[]'
            elif params.get('transactionType') == 1:
                if from_ts < 1636144956000 < to_ts:
                    response_str = BINANCE_FIATWITHDRAWS_RESPONSE
                else:
                    response_str = '[]'
            else:
                raise AssertionError('Unexpected binance request in test')
        elif 'myTrades' in url or 'fiat/payments' in url:
            response_str = '[]'
        else:
            raise AssertionError('Unexpected binance request in test')

        return MockResponse(200, response_str)

    with patch.object(binance.session, 'request', side_effect=mock_get_history_events):
        movements, _ = binance.query_online_history_events(
            start_ts=Timestamp(start_ts),
            end_ts=Timestamp(end_ts),
        )

    errors = binance.msg_aggregator.consume_errors()
    warnings = binance.msg_aggregator.consume_warnings()
    assert len(errors) == 0
    assert len(warnings) == 0
    assert_binance_asset_movements_result(
        movements=cast('list[AssetMovement]', movements),
        location=Location.BINANCE,
        got_fiat=True,
    )


def test_binance_query_deposits_withdrawals_unexpected_data(function_scope_binance):
    """Test that we handle unexpected deposit withdrawal query data gracefully

    NB: set `start_ts` and `end_ts` with a difference less than 90 days to
    prevent requesting with a time delta.
    """
    start_ts = 1508022000  # 2017-10-15
    end_ts = 1508540400  # 2017-10-21 (less than 90 days since `start_ts`)
    binance = function_scope_binance

    def mock_binance_and_query(deposits, withdrawals, expected_warnings_num, expected_errors_num):

        def mock_get_history_events(url, **kwargs):  # pylint: disable=unused-argument
            if 'deposit' in url:
                response_str = deposits
            else:
                response_str = withdrawals

            return MockResponse(200, response_str)

        with patch.object(binance.session, 'request', side_effect=mock_get_history_events):
            movements, _ = binance.query_online_history_events(
                start_ts=Timestamp(start_ts),
                end_ts=Timestamp(end_ts),
            )

        if expected_errors_num == 0 and expected_warnings_num == 0:
            if len(movements) == 2:
                assert movements[1].event_subtype == HistoryEventSubType.FEE
            else:
                assert len(movements) == 1
        else:
            assert len(movements) == 0

    def check_permutations_of_input_invalid_data(deposits, withdrawals):
        # First make sure it works with normal data
        mock_binance_and_query(
            deposits,
            withdrawals,
            expected_warnings_num=0,
            expected_errors_num=0,
        )
        testing_deposits = 'amount' in deposits

        # From here and on test unexpected data
        # invalid timestamp
        if testing_deposits:
            new_deposits = deposits.replace('1508198532000', '"dasdd"')
            new_withdrawals = withdrawals
        else:
            new_deposits = deposits
            new_withdrawals = withdrawals.replace('"2017-10-17 00:02:12"', '"dasdd"')
        mock_binance_and_query(
            new_deposits,
            new_withdrawals,
            expected_warnings_num=0,
            expected_errors_num=1,
        )

        # invalid asset
        if testing_deposits:
            new_deposits = deposits.replace('"ETH"', '[]')
            new_withdrawals = withdrawals
        else:
            new_deposits = deposits
            new_withdrawals = withdrawals.replace('"ETH"', '[]')
        mock_binance_and_query(
            new_deposits,
            new_withdrawals,
            expected_warnings_num=0,
            expected_errors_num=1,
        )

        # Unknown asset
        if testing_deposits:
            new_deposits = deposits.replace('"ETH"', '"dasdsDSDSAD"')
            new_withdrawals = withdrawals
        else:
            new_deposits = deposits
            new_withdrawals = withdrawals.replace('"ETH"', '"dasdsDSDSAD"')
        mock_binance_and_query(
            new_deposits,
            new_withdrawals,
            expected_warnings_num=1,
            expected_errors_num=0,
        )

        # Unsupported Asset
        if testing_deposits:
            new_deposits = deposits.replace('"ETH"', '"BTCB"')
            new_withdrawals = withdrawals
        else:
            new_deposits = deposits
            new_withdrawals = withdrawals.replace('"ETH"', '"BTCB"')
        mock_binance_and_query(
            new_deposits,
            new_withdrawals,
            expected_warnings_num=1,
            expected_errors_num=0,
        )

        # Invalid amount
        if testing_deposits:
            new_deposits = deposits.replace('0.04670582', 'null')
            new_withdrawals = withdrawals
        else:
            new_deposits = deposits
            new_withdrawals = withdrawals.replace('0.04670582', 'null')
        mock_binance_and_query(
            new_deposits,
            new_withdrawals,
            expected_warnings_num=0,
            expected_errors_num=1,
        )

        # Missing Key Error
        if testing_deposits:
            new_deposits = deposits.replace('"amount": 0.04670582,', '')
            new_withdrawals = withdrawals
        else:
            new_deposits = deposits
            new_withdrawals = withdrawals.replace('"amount": 0.04670582,', '')
        mock_binance_and_query(
            new_deposits,
            new_withdrawals,
            expected_warnings_num=0,
            expected_errors_num=1,
        )

    # To make the test easy to write the values for deposit/withdrawal attributes
    # are the same in the two examples below
    empty_deposits = '[]'
    empty_withdrawals = '[]'
    input_withdrawals = """[{
        "id":"7213fea8e94b4a5593d507237e5a555b",
        "amount": 0.04670582,
        "transactionFee": 0.01,
        "address": "0x6915f16f8791d0a1cc2bf47c13a6b2a92000504b",
        "coin": "ETH",
        "txId": "0xdf33b22bdb2b28b1f75ccd201a4a4m6e7g83jy5fc5d5a9d1340961598cfcb0a1",
        "applyTime": "2017-10-17 00:02:12",
        "status": 4
        }]"""
    check_permutations_of_input_invalid_data(
        deposits=empty_deposits,
        withdrawals=input_withdrawals,
    )

    input_deposits = """[{
        "insertTime": 1508198532000,
        "amount": 0.04670582,
        "coin": "ETH",
        "address": "0x6915f16f8791d0a1cc2bf47c13a6b2a92000504b",
        "txId": "0xdf33b22bdb2b28b1f75ccd201a4a4m6e7g83jy5fc5d5a9d1340961598cfcb0a1",
        "status": 1
        }]"""
    check_permutations_of_input_invalid_data(
        deposits=input_deposits,
        withdrawals=empty_withdrawals,
    )


def test_binance_query_deposits_withdrawals_gte_90_days(function_scope_binance):
    """Test the not so happy case of binance deposit withdrawal query

    From `start_ts` to `end_ts` there is a difference gte 90 days, which forces
    to request using a time delta (from API_TIME_INTERVAL_CONSTRAINT_TS). As
    the `mock_get_deposit_withdrawal()` results are the same as in
    `test_binance_query_deposits_withdrawals`, we only assert the number of
    movements.

    NB: this test implementation must mock 8 requests instead of 4.
    """
    start_ts = 0  # Defaults to BINANCE_LAUNCH_TS
    end_ts = BINANCE_LAUNCH_TS + API_TIME_INTERVAL_CONSTRAINT_TS  # eq 90 days after
    binance = function_scope_binance

    def get_time_delta_deposit_result():
        results = [
            BINANCE_DEPOSITS_HISTORY_RESPONSE,
            '[]',
        ]
        yield from results

    def get_time_delta_withdraw_result():
        results = [
            '[]',
            BINANCE_WITHDRAWALS_HISTORY_RESPONSE,
        ]
        yield from results

    def get_fiat_deposit_result():
        results = [
            '[]',
            BINANCE_FIATDEPOSITS_RESPONSE,
        ]
        yield from results

    def get_fiat_withdraw_result():
        results = [
            BINANCE_FIATWITHDRAWS_RESPONSE,
            '[]',
        ]
        yield from results

    def mock_get_history_events(url, params, **kwargs):  # pylint: disable=unused-argument
        if 'capital/deposit' in url:
            response_str = next(get_deposit_result)
        elif 'capital/withdraw' in url:
            response_str = next(get_withdraw_result)
        elif 'fiat/orders' in url:
            if params.get('transactionType') == 0:
                response_str = next(get_fiat_deposit_result)
            elif params.get('transactionType') == 1:
                response_str = next(get_fiat_withdraw_result)
            else:
                raise AssertionError('Unexpected binance request in test')
        elif 'myTrades' in url or 'fiat/payments' in url:
            response_str = '[]'
        else:
            raise AssertionError('Unexpected binance request in test')

        return MockResponse(200, response_str)

    get_deposit_result = get_time_delta_deposit_result()
    get_withdraw_result = get_time_delta_withdraw_result()
    get_fiat_deposit_result = get_fiat_deposit_result()
    get_fiat_withdraw_result = get_fiat_withdraw_result()

    with patch.object(binance.session, 'request', side_effect=mock_get_history_events):
        movements, _ = binance.query_online_history_events(
            start_ts=Timestamp(start_ts),
            end_ts=Timestamp(end_ts),
        )

    errors = binance.msg_aggregator.consume_errors()
    warnings = binance.msg_aggregator.consume_warnings()
    assert len(errors) == 0
    assert len(warnings) == 0

    assert len(movements) == 9


@pytest.mark.freeze_time(datetime.datetime(2020, 11, 24, 3, 14, 15, tzinfo=datetime.UTC))
def test_api_query_list_calls_with_time_delta(function_scope_binance):
    """Test the `api_query_list()` arguments when deposit/withdraw history
    requests involve a time delta.

    From `start_ts` to `end_ts` there is a difference gte 90 days, which forces
    to request using a time delta (from API_TIME_INTERVAL_CONSTRAINT_TS).
    """
    now_ts_ms = int(datetime.datetime.now(tz=datetime.UTC).timestamp()) * 1000
    start_ts = 0  # Defaults to BINANCE_LAUNCH_TS
    end_ts = BINANCE_LAUNCH_TS + API_TIME_INTERVAL_CONSTRAINT_TS  # eq 90 days after
    expected_calls = [
        call(
            'sapi',
            'capital/deposit/hisrec',
            options={
                'timestamp': now_ts_ms,
                'startTime': 1500001200000,
                'endTime': 1507777199999,
            },
        ),
        call(
            'sapi',
            'capital/deposit/hisrec',
            options={
                'timestamp': now_ts_ms,
                'startTime': 1507777200000,
                'endTime': 1507777200000,
            },
        ),
        call(
            'sapi',
            'capital/withdraw/history',
            options={
                'timestamp': now_ts_ms,
                'startTime': 1500001200000,
                'endTime': 1507777199999,
            },
        ),
        call(
            'sapi',
            'capital/withdraw/history',
            options={
                'timestamp': now_ts_ms,
                'startTime': 1507777200000,
                'endTime': 1507777200000,
            },
        ),
        call(
            'sapi',
            'fiat/orders',
            options={
                'timestamp': now_ts_ms,
                'startTime': 1500001200000,
                'endTime': 1507777199999,
                'transactionType': 0,
            },
        ),
        call(
            'sapi',
            'fiat/orders',
            options={
                'timestamp': now_ts_ms,
                'startTime': 1507777200000,
                'endTime': 1507777200000,
                'transactionType': 0,
            },
        ),
        call(
            'sapi',
            'fiat/orders',
            options={
                'timestamp': now_ts_ms,
                'startTime': 1500001200000,
                'endTime': 1507777199999,
                'transactionType': 1,
            },
        ),
        call(
            'sapi',
            'fiat/orders',
            options={
                'timestamp': now_ts_ms,
                'startTime': 1507777200000,
                'endTime': 1507777200000,
                'transactionType': 1,
            },
        ),
    ]
    binance = function_scope_binance

    with patch.object(binance, 'api_query_list') as mock_api_query_list:
        binance.query_online_history_events(
            start_ts=Timestamp(start_ts),
            end_ts=Timestamp(end_ts),
        )
        assert mock_api_query_list.call_args_list[:8] == expected_calls


@pytest.mark.freeze_time(datetime.datetime(2020, 11, 24, 3, 14, 15, tzinfo=datetime.UTC))
def test_api_query_retry_on_status_code_429(function_scope_binance):
    """Test when Binance API returns 429 and the request is retried, the
    signature is not polluted by any attribute from the previous call.

    It also tests getting the `retry-after` seconds to backoff from the
    response header.

    NB: basically remove `call_options['signature']`.
    """
    binance = function_scope_binance
    offset_ms = 1000
    call_options = {
        'fromId': 0,
        'limit': 1000,
        'symbol': 'BUSDUSDT',
        'recvWindow': 10000,
        'timestamp': str(ts_now_in_ms() + offset_ms),
    }
    signature = hmac.new(
        binance.secret,
        urlencode(call_options).encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()
    call_options['signature'] = signature
    base_url = 'https://api.binance.com/api/v3/myTrades'

    # NB: all calls must have the same signature (time frozen)
    expected_calls = [
        call(method='GET', url=base_url, params=call_options, timeout=(30, 30)),
        call(method='GET', url=base_url, params=call_options, timeout=(30, 30)),
        call(method='GET', url=base_url, params=call_options, timeout=(30, 30)),
    ]

    def get_mocked_response():
        responses = [
            MockResponse(429, '[]', headers={'retry-after': '1'}),
            MockResponse(418, '[]', headers={'retry-after': '5'}),
            MockResponse(418, '[]', headers={'retry-after': str(RETRY_AFTER_LIMIT + 1)}),
        ]
        yield from responses

    def mock_response(url, timeout, *args, **kwargs):  # pylint: disable=unused-argument
        return next(get_response)

    get_response = get_mocked_response()
    offset_ms_patch = patch.object(binance, 'offset_ms', new=1000)
    binance_patch = patch.object(binance.session, 'request', side_effect=mock_response)

    with ExitStack() as stack:
        stack.enter_context(offset_ms_patch)
        binance_mock_get = stack.enter_context(binance_patch)
        with pytest.raises(RemoteError) as e:
            binance.api_query(
                api_type='api',
                method='myTrades',
                options={
                    'fromId': 0,
                    'limit': 1000,
                    'symbol': 'BUSDUSDT',
                },
            )
    assert 'myTrades failed with HTTP status code: 418' in str(e.value)
    assert binance_mock_get.call_args_list == expected_calls


def test_binance_query_trade_history_custom_markets(function_scope_binance):
    """Test that custom pairs are queried correctly"""
    binance_api_key = ApiKey('binance_api_key')
    binance_api_secret = ApiSecret(b'binance_api_secret')
    function_scope_binance.db.add_exchange(
        name='binance',
        location=Location.BINANCE,
        api_key=binance_api_key,
        api_secret=binance_api_secret,
    )
    binance = function_scope_binance

    markets = ['ETHBTC', 'BNBBTC', 'BTCUSDC']
    binance.edit_exchange_extras({BINANCE_MARKETS_KEY: markets})
    count = 0
    seen = set()

    def mock_my_trades(url, params, *args, **kwargs):  # pylint: disable=unused-argument
        nonlocal count
        if 'myTrades' in url:
            count += 1
            market = params.get('symbol')
            assert market in markets and market not in seen
            seen.add(market)
        text = '[]'
        return MockResponse(200, text)

    with patch.object(binance.session, 'request', side_effect=mock_my_trades):
        binance.query_online_history_events(start_ts=Timestamp(0), end_ts=Timestamp(1564301134))

    assert count == len(markets)


@pytest.mark.parametrize('default_mock_price_value', [ONE])
def test_binance_query_lending_interests_history(
        function_scope_binance: 'Binance',
        price_historian: 'PriceHistorian',
):
    binance_api_key = ApiKey('binance_api_key')
    binance_api_secret = ApiSecret(b'binance_api_secret')
    function_scope_binance.db.add_exchange(
        name='binance',
        location=Location.BINANCE,
        api_key=binance_api_key,
        api_secret=binance_api_secret,
    )
    binance = function_scope_binance

    def mock_my_lendings(url, params, *args, **kwargs):  # pylint: disable=unused-argument
        if 'simple-earn/flexible/history/rewardsRecord' in url:
            if (request_type := params.get('type')) == 'BONUS':
                return MockResponse(200, """{
                    "rows": [{
                        "asset": "BUSD",
                        "rewards": "0.00006408",
                        "projectId": "USDT001",
                        "type": "BONUS",
                        "time": 7775998000
                    }],
                    "total": 2
                }""")
            elif request_type == 'REALTIME':
                return MockResponse(200, """{
                    "rows": [{
                        "asset": "USDT",
                        "rewards": "0.00687654",
                        "projectId": "USDT001",
                        "type": "REALTIME",
                        "time": 7775999000
                    }],
                    "total": 2
                }""")
            else:
                return MockResponse(200, """{
                    "rows": [{
                        "asset": "USDT",
                        "rewards": "0.00687654",
                        "projectId": "USDT001",
                        "type": "REWARDS",
                        "time": 7776000000
                    }],
                    "total": 1
                }""")
        elif 'simple-earn/locked/history/rewardsRecord' in url:
            return MockResponse(200, """{
                "rows": [{
                    "positionId": "123123",
                    "time": 0,
                    "asset": "BNB",
                    "lockPeriod": "30",
                    "amount": "21312.23223"
                }],
                "total": 1
            }""")
        return MockResponse(200, '[]')

    with (
        patch.object(binance.session, 'request', side_effect=mock_my_lendings),
        binance.db.conn.read_ctx() as cursor,
    ):
        for count, location in [
            (0, Location.BINANCEUS),
            (4, Location.BINANCE),
        ]:
            binance.location = location
            assert binance.query_lending_interests_history(
                cursor=binance.db.conn.cursor(),
                start_ts=Timestamp(0),
                end_ts=Timestamp(API_TIME_INTERVAL_CONSTRAINT_TS),
            ) is False

            assert cursor.execute(
                'SELECT COUNT(*) FROM history_events WHERE subtype="reward" AND location=?;',
                (location.serialize_for_db(),),
            ).fetchone()[0] == count

    assert len(binance.msg_aggregator.consume_errors()) == 0
    assert len(binance.msg_aggregator.consume_warnings()) == 0
