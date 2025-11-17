import warnings as test_warnings
from typing import TYPE_CHECKING, cast
from unittest.mock import patch

import pytest

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.converters import asset_from_poloniex
from rotkehlchen.constants.assets import A_BCH, A_BTC, A_ETH
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.poloniex import Poloniex, trade_from_poloniex
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.swap import SwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.history.events.utils import create_group_identifier_from_unique_id
from rotkehlchen.tests.utils.constants import A_AIR2
from rotkehlchen.tests.utils.exchanges import (
    POLONIEX_BALANCES_RESPONSE,
    POLONIEX_MOCK_DEPOSIT_WITHDRAWALS_RESPONSE,
    POLONIEX_TRADES_RESPONSE,
    get_exchange_asset_symbols,
)
from rotkehlchen.tests.utils.globaldb import is_asset_symbol_unsupported
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import Location, Timestamp, TimestampMS

if TYPE_CHECKING:
    from rotkehlchen.globaldb.handler import GlobalDBHandler
    from rotkehlchen.tests.fixtures.messages import MockRotkiNotifier


TEST_RATE_STR = '0.00022999'
TEST_AMOUNT_STR = '613.79427133'
TEST_FEE_STR = '0.920691406995'
TEST_POLO_TRADE = {
    'symbol': 'ETH_BTC',
    'id': 192167,
    'createTime': 1500758317000,
    'price': TEST_RATE_STR,
    'quantity': TEST_AMOUNT_STR,
    'feeCurrency': 'BTC',
    'feeAmount': TEST_FEE_STR,
    'side': 'SELL',
    'type': 'MARKET',
    'accountType': 'SPOT',
}


def test_name():
    exchange = Poloniex('poloniex1', 'a', b'a', object(), object())
    assert exchange.location == Location.POLONIEX
    assert exchange.name == 'poloniex1'


def test_trade_from_poloniex():
    assert trade_from_poloniex(exchange_name=(exchange_name := 'poloniex1'), poloniex_trade=TEST_POLO_TRADE) == [SwapEvent(  # noqa: E501
        timestamp=TimestampMS(1500758317000),
        location=Location.POLONIEX,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_ETH,
        amount=FVal(TEST_AMOUNT_STR),
        location_label=exchange_name,
        group_identifier=create_group_identifier_from_unique_id(
            location=Location.POLONIEX,
            unique_id='192167',
        ),
    ), SwapEvent(
        timestamp=TimestampMS(1500758317000),
        location=Location.POLONIEX,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_BTC,
        amount=FVal('0.1411665444631867'),
        location_label=exchange_name,
        group_identifier=create_group_identifier_from_unique_id(
            location=Location.POLONIEX,
            unique_id='192167',
        ),
    ), SwapEvent(
        timestamp=TimestampMS(1500758317000),
        location=Location.POLONIEX,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_BTC,
        amount=FVal(TEST_FEE_STR),
        location_label=exchange_name,
        group_identifier=create_group_identifier_from_unique_id(
            location=Location.POLONIEX,
            unique_id='192167',
        ),
    )]


def test_poloniex_trade_deserialization_errors():
    test_trade = TEST_POLO_TRADE.copy()
    test_trade['createTime'] = 'dsadsad'
    with pytest.raises(DeserializationError):
        trade_from_poloniex(poloniex_trade=test_trade, exchange_name=(exchange_name := 'poloniex1'))  # noqa: E501

    test_trade = TEST_POLO_TRADE.copy()
    test_trade['side'] = 'lololol'
    with pytest.raises(DeserializationError):
        trade_from_poloniex(poloniex_trade=test_trade, exchange_name=exchange_name)

    test_trade = TEST_POLO_TRADE.copy()
    test_trade['quantity'] = None
    with pytest.raises(DeserializationError):
        trade_from_poloniex(poloniex_trade=test_trade, exchange_name=exchange_name)

    test_trade = TEST_POLO_TRADE.copy()
    test_trade['price'] = None
    with pytest.raises(DeserializationError):
        trade_from_poloniex(poloniex_trade=test_trade, exchange_name=exchange_name)

    test_trade = TEST_POLO_TRADE.copy()
    test_trade['feeAmount'] = ['a']
    with pytest.raises(DeserializationError):
        trade_from_poloniex(poloniex_trade=test_trade, exchange_name=exchange_name)

    test_trade = TEST_POLO_TRADE.copy()
    del test_trade['price']
    with pytest.raises(DeserializationError):
        trade_from_poloniex(poloniex_trade=test_trade, exchange_name=exchange_name)


def test_poloniex_trade_with_asset_needing_conversion():
    amount = FVal(613.79427133)
    rate = FVal(0.00022999)
    fee = FVal(0.001)
    poloniex_trade = {
        'id': 15,
        'symbol': 'BTC_AIR',
        'createTime': 1500758317000,
        'price': rate,
        'quantity': amount,
        'feeAmount': fee,
        'feeCurrency': 'AIR',
        'type': 'LIMIT',
        'side': 'SELL',
    }
    events = trade_from_poloniex(poloniex_trade=poloniex_trade, exchange_name=(exchange_name := 'poloniex'))  # noqa: E501
    assert events[0].asset == A_BTC
    assert events[1].asset == A_AIR2
    assert events[2].asset == A_AIR2
    assert events[0].location == Location.POLONIEX
    assert all(event.location_label == exchange_name for event in events)


def test_query_trade_history(poloniex: 'Poloniex'):
    """Happy path test for poloniex trade history querying"""
    def mock_api_return(url, **kwargs):  # pylint: disable=unused-argument
        if '/trades' in url:
            return MockResponse(200, POLONIEX_TRADES_RESPONSE)

        return MockResponse(200, '{"withdrawals": [], "deposits": []}')

    with patch.object(poloniex.session, 'get', side_effect=mock_api_return):
        events, _ = poloniex.query_online_history_events(
            start_ts=Timestamp(1500000000),
            end_ts=Timestamp(1565732120),
        )
        assert events == [SwapEvent(
            timestamp=TimestampMS(1539713117000),
            location=Location.POLONIEX,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_BCH,
            amount=FVal('1.40308443'),
            group_identifier=create_group_identifier_from_unique_id(
                location=Location.POLONIEX,
                unique_id='394131412',
            ),
            location_label=poloniex.name,
        ), SwapEvent(
            timestamp=TimestampMS(1539713117000),
            location=Location.POLONIEX,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_BTC,
            amount=FVal('0.0973073287465092'),
            group_identifier=create_group_identifier_from_unique_id(
                location=Location.POLONIEX,
                unique_id='394131412',
            ),
            location_label=poloniex.name,
        ), SwapEvent(
            timestamp=TimestampMS(1539713117000),
            location=Location.POLONIEX,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_BTC,
            amount=FVal('0.00009730732'),
            group_identifier=create_group_identifier_from_unique_id(
                location=Location.POLONIEX,
                unique_id='394131412',
            ),
            location_label=poloniex.name,
        ), SwapEvent(
            timestamp=TimestampMS(1539709423000),
            location=Location.POLONIEX,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_BTC,
            amount=FVal('0.1235704463578728'),
            group_identifier=create_group_identifier_from_unique_id(
                location=Location.POLONIEX,
                unique_id='13536350',
            ),
            location_label=poloniex.name,
        ), SwapEvent(
            timestamp=TimestampMS(1539709423000),
            location=Location.POLONIEX,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ETH,
            amount=FVal('3600.53748129'),
            group_identifier=create_group_identifier_from_unique_id(
                location=Location.POLONIEX,
                unique_id='13536350',
            ),
            location_label=poloniex.name,
        ), SwapEvent(
            timestamp=TimestampMS(1539709423000),
            location=Location.POLONIEX,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('7.20107496258'),
            group_identifier=create_group_identifier_from_unique_id(
                location=Location.POLONIEX,
                unique_id='13536350',
            ),
            location_label=poloniex.name,
        )]


def test_query_trade_history_unexpected_data(poloniex):
    """Test that poloniex trade history querying returning unexpected data is handled gracefully"""
    poloniex.cache_ttl_secs = 0

    def mock_poloniex_and_query(given_trades, expected_warnings_num, expected_errors_num, expected_trades_len=0):  # noqa: E501

        def mock_api_return(url, **kwargs):  # pylint: disable=unused-argument
            if '/trades' in url:
                return MockResponse(200, given_trades)

            return MockResponse(200, '{"withdrawals": [], "deposits": []}')

        with patch.object(poloniex.session, 'get', side_effect=mock_api_return):
            events, _ = poloniex.query_online_history_events(
                start_ts=Timestamp(1500000000),
                end_ts=Timestamp(1565732120),
            )

        assert len(events) == expected_trades_len
        warnings = poloniex.msg_aggregator.consume_warnings()
        assert len(warnings) == expected_warnings_num
        errors = poloniex.msg_aggregator.consume_errors()
        assert len(errors) == expected_errors_num

    input_trades = """[{
    "symbol": "ETH_BTC",
    "id": 13536350,
    "createTime": 1539709423000,
    "price": "0.00003432",
    "quantity": "3600.53748129",
    "feeAmount": "7.20107496258",
    "feeCurrency": "ETH",
    "side": "BUY",
    "type": "MARKET",
    "accountType": "SPOT"}]"""

    # First make sure it works with normal data
    mock_poloniex_and_query(input_trades, expected_warnings_num=0, expected_errors_num=0, expected_trades_len=3)  # noqa: E501

    # from here and on invalid data
    # invalid timestamp
    given_input = input_trades.replace('1539709423000', '"435345"')
    mock_poloniex_and_query(given_input, expected_warnings_num=0, expected_errors_num=1)

    # invalid symbol
    given_input = input_trades.replace('"ETH_BTC"', '"0"')
    mock_poloniex_and_query(given_input, expected_warnings_num=0, expected_errors_num=1)

    # symbol with unsupported asset
    given_input = input_trades.replace('"ETH_BTC"', '"ETH_BALLS"')
    mock_poloniex_and_query(given_input, expected_warnings_num=1, expected_errors_num=0)

    # invalid price
    given_input = input_trades.replace('"0.00003432"', 'null')
    mock_poloniex_and_query(given_input, expected_warnings_num=0, expected_errors_num=1)

    # invalid amount
    given_input = input_trades.replace('"3600.53748129"', '"dsadsd"')
    mock_poloniex_and_query(given_input, expected_warnings_num=0, expected_errors_num=1)

    # invalid fee
    given_input = input_trades.replace('"7.20107496258"', '"dasdsad"')
    mock_poloniex_and_query(given_input, expected_warnings_num=0, expected_errors_num=1)

    # invalid trade side
    given_input = input_trades.replace('"BUY"', '"dasdsdad"')
    mock_poloniex_and_query(given_input, expected_warnings_num=0, expected_errors_num=1)

    # invalid accountType
    given_input = input_trades.replace('"SPOT"', '"dsadsdsadd"')
    mock_poloniex_and_query(given_input, expected_warnings_num=0, expected_errors_num=0)


@pytest.mark.asset_test
def test_poloniex_assets_are_known(poloniex: 'Poloniex', globaldb: 'GlobalDBHandler'):
    for asset in get_exchange_asset_symbols(Location.POLONIEX):
        assert is_asset_symbol_unsupported(globaldb, Location.POLONIEX, asset) is False, f'Poloniex assets {asset} should not be unsupported'  # noqa: E501

    currencies = poloniex.api_query_list('/currencies')
    for asset_data in currencies:
        for poloniex_asset in asset_data:
            try:
                _ = asset_from_poloniex(poloniex_asset)
            except UnsupportedAsset:
                assert is_asset_symbol_unsupported(globaldb, Location.POLONIEX, poloniex_asset)
            except UnknownAsset as e:
                test_warnings.warn(UserWarning(
                    f'Found unknown asset {e.identifier} with symbol {poloniex_asset} in Poloniex. Support for it has to be added',  # noqa: E501
                ))


@pytest.mark.parametrize('function_scope_initialize_mock_rotki_notifier', [True])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_poloniex_query_balances_unknown_asset(poloniex):
    """Test that if a poloniex balance query returns unknown asset no exception
    is raised and a warning is generated. Same for unsupported assets"""

    def mock_unknown_asset_return(url, **kwargs):  # pylint: disable=unused-argument
        return MockResponse(200, POLONIEX_BALANCES_RESPONSE)

    with patch.object(poloniex.session, 'get', side_effect=mock_unknown_asset_return):
        # Test that after querying the assets only ETH and BTC are there
        balances, msg = poloniex.query_balances()

    assert msg == ''
    assert len(balances) == 2
    assert balances[A_BTC].amount == FVal('5.5')
    assert balances[A_BTC].usd_value == FVal('8.25')
    assert balances[A_ETH].amount == FVal('11.0')
    assert balances[A_ETH].usd_value == FVal('16.5')

    messages = poloniex.msg_aggregator.rotki_notifier.messages
    assert len(messages) == 2
    assert messages[0].message_type == WSMessageType.EXCHANGE_UNKNOWN_ASSET
    assert 'unsupported poloniex asset CNOTE' in messages[1].data['value']


@pytest.mark.parametrize('function_scope_initialize_mock_rotki_notifier', [True])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_poloniex_deposits_withdrawal_unknown_asset(poloniex: 'Poloniex') -> None:
    """Test that if a poloniex asset movement query returns unknown asset no exception
    is raised and a warning is generated. Same for unsupported assets"""

    def mock_api_return(url, **kwargs):  # pylint: disable=unused-argument
        if '/trades' in url:
            return MockResponse(200, '[]')

        return MockResponse(200, POLONIEX_MOCK_DEPOSIT_WITHDRAWALS_RESPONSE)

    with patch.object(poloniex.session, 'get', side_effect=mock_api_return):
        # Test that after querying the api only ETH and BTC assets are there
        asset_movements, _ = poloniex.query_online_history_events(
            start_ts=Timestamp(0),
            end_ts=Timestamp(1488994442),
        )

    assert asset_movements == [AssetMovement(
        location=Location.POLONIEX,
        location_label=poloniex.name,
        event_type=HistoryEventType.WITHDRAWAL,
        timestamp=TimestampMS(1458994442000),
        asset=A_BTC,
        amount=FVal('4.5'),
        unique_id='withdrawal_1',
        extra_data={
            'address': '131rdg5Rzn6BFufnnQaHhVa5ZtRU1J2EZR',
            'transaction_id': '2d27ae26fa9c70d6709e27ac94d4ce2fde19b3986926e9f3bfcf3e2d68354ec5',
        },
    ), AssetMovement(
        location=Location.POLONIEX,
        location_label=poloniex.name,
        event_type=HistoryEventType.WITHDRAWAL,
        timestamp=TimestampMS(1458994442000),
        asset=A_BTC,
        amount=FVal('0.5'),
        unique_id='withdrawal_1',
        is_fee=True,
    ), AssetMovement(
        location=Location.POLONIEX,
        location_label=poloniex.name,
        event_type=HistoryEventType.WITHDRAWAL,
        timestamp=TimestampMS(1468994442000),
        asset=A_ETH,
        amount=FVal('9.9'),
        unique_id='withdrawal_2',
        extra_data={
            'address': '0xB7E033598Cb94EF5A35349316D3A2e4f95f308Da',
            'transaction_id': '0xbd4da74e1a0b81c21d056c6f58a5b306de85d21ddf89992693b812bb117eace4',
        },
    ), AssetMovement(
        location=Location.POLONIEX,
        location_label=poloniex.name,
        event_type=HistoryEventType.WITHDRAWAL,
        timestamp=TimestampMS(1468994442000),
        asset=A_ETH,
        amount=FVal('0.1'),
        unique_id='withdrawal_2',
        is_fee=True,
    ), AssetMovement(
        location=Location.POLONIEX,
        location_label=poloniex.name,
        event_type=HistoryEventType.DEPOSIT,
        timestamp=TimestampMS(1448994442000),
        asset=A_BTC,
        amount=FVal('50.0'),
        unique_id='deposit_1',
        extra_data={
            'address': '131rdg5Rzn6BFufnnQaHhVa5ZtRU1J2EZR',
            'transaction_id': 'b05bdec7430a56b5a5ed34af4a31a54859dda9b7c88a5586bc5d6540cdfbfc7a',
        },
    ), AssetMovement(
        location=Location.POLONIEX,
        location_label=poloniex.name,
        event_type=HistoryEventType.DEPOSIT,
        timestamp=TimestampMS(1438994442000),
        asset=A_ETH,
        amount=FVal('100.0'),
        unique_id='deposit_2',
        extra_data={
            'address': '0xB7E033598Cb94EF5A35349316D3A2e4f95f308Da',
            'transaction_id': '0xf7e7eeb44edcad14c0f90a5fffb1cbb4b80e8f9652124a0838f6906ca939ccd2',
        },
    )]

    messages = cast('MockRotkiNotifier', poloniex.msg_aggregator.rotki_notifier).messages
    assert len(messages) == 4
    assert messages[0].message_type == WSMessageType.EXCHANGE_UNKNOWN_ASSET
    assert 'Found withdrawal of unsupported poloniex asset BALLS' in messages[1].data['value']  # type: ignore
    assert messages[2].message_type == WSMessageType.EXCHANGE_UNKNOWN_ASSET
    assert 'Found deposit of unsupported poloniex asset EBT' in messages[3].data['value']  # type: ignore


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_poloniex_deposits_withdrawal_null_fee(poloniex: 'Poloniex'):
    """
    Test that if a poloniex asset movement query returns null for fee we don't crash.
    Regression test for issue #76
    """

    def mock_api_return(url, **kwargs):  # pylint: disable=unused-argument
        if '/trades' in url:
            return MockResponse(200, '[]')

        return MockResponse(
            200,
            '{"withdrawals": [{"currency": "FAC", "timestamp": 1478994442, '
            '"amount": "100.5", "fee": null, "withdrawalRequestsId": 1, "address": "131rdg5Rzn6BFufnnQaHhVa5ZtRU1J2EZR", "status": "COMPLETED"}], "deposits": []}',  # noqa: E501
        )

    with patch.object(poloniex.session, 'get', side_effect=mock_api_return):
        asset_movements, _ = poloniex.query_online_history_events(
            start_ts=Timestamp(0),
            end_ts=Timestamp(1488994442),
        )

    assert len(asset_movements) == 1
    assert asset_movements[0].event_type == HistoryEventType.WITHDRAWAL
    assert asset_movements[0].timestamp == TimestampMS(1478994442000)
    assert asset_movements[0].asset == Asset('FAIR')
    assert asset_movements[0].amount == FVal('100.5')

    warnings = poloniex.msg_aggregator.consume_warnings()
    assert len(warnings) == 0


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_poloniex_deposits_withdrawal_unexpected_data(poloniex):
    """
    Test that if a poloniex asset movement query returns unexpected data we handle it gracefully
    """
    poloniex.cache_ttl_secs = 0

    def mock_poloniex_and_query(given_movements, expected_warnings_num, expected_errors_num):

        def mock_api_return(url, **kwargs):  # pylint: disable=unused-argument
            if '/trades' in url:
                return MockResponse(200, '[]')

            return MockResponse(200, given_movements)

        with patch.object(poloniex.session, 'get', side_effect=mock_api_return):
            asset_movements, _ = poloniex.query_online_history_events(
                start_ts=0,
                end_ts=1488994442,
            )

        if expected_errors_num == 0 and expected_warnings_num == 0:
            if len(asset_movements) == 2:
                assert asset_movements[1].event_subtype == HistoryEventSubType.FEE
            else:
                assert len(asset_movements) == 1
        else:
            assert len(asset_movements) == 0
            warnings = poloniex.msg_aggregator.consume_warnings()
            assert len(warnings) == expected_warnings_num
            errors = poloniex.msg_aggregator.consume_errors()
            assert len(errors) == expected_errors_num

    def check_permutations_of_input_invalid_data(given_input):
        # First make sure it works with normal data
        mock_poloniex_and_query(given_input, expected_warnings_num=0, expected_errors_num=0)

        # From here and on test unexpected data
        # invalid timestamp
        movements = given_input.replace('1478994442', '"dasdsd"')
        mock_poloniex_and_query(movements, expected_warnings_num=0, expected_errors_num=1)

        # invalid amount
        movements = given_input.replace('"100.5"', 'null')
        mock_poloniex_and_query(movements, expected_warnings_num=0, expected_errors_num=1)

        # invalid fee
        if 'fee' in given_input:
            movements = given_input.replace('"0.1"', '"dasdsdsad"')
            mock_poloniex_and_query(movements, expected_warnings_num=0, expected_errors_num=1)

        # invalid currency type
        movements = given_input.replace('"FAC"', '[]')
        mock_poloniex_and_query(movements, expected_warnings_num=0, expected_errors_num=1)

        # missing key error
        movements = given_input.replace('"timestamp": 1478994442,', '')
        mock_poloniex_and_query(movements, expected_warnings_num=0, expected_errors_num=1)

    input_withdrawals = """
    {"withdrawals": [{"currency": "FAC", "timestamp": 1478994442,
    "amount": "100.5", "fee": "0.1", "withdrawalRequestsId": 1, "status": "COMPLETE", "address": "131rdg5Rzn6BFufnnQaHhVa5ZtRU1J2EZR"}], "deposits": []}"""  # noqa: E501
    check_permutations_of_input_invalid_data(input_withdrawals)
    input_deposits = """
    {"deposits": [{"currency": "FAC", "timestamp": 1478994442,
    "amount": "100.5", "depositNumber": 1, "txid": "0xfoo", "address": "0xboo"}], "withdrawals": []}"""  # noqa: E501
    check_permutations_of_input_invalid_data(input_deposits)
