from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_BTC, A_USDT
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.exchanges.bitmex import Bitmex
from rotkehlchen.exchanges.data_structures import Location, MarginPosition
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.types import HistoryEventType
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import Fee, Timestamp, TimestampMS
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


TEST_BITMEX_WITHDRAWAL = """[{
"transactID": "b6c6fd2c-4d0c-b101-a41c-fa5aa1ce7ef1", "account": 126541, "currency": "XBt",
 "transactType": "Withdrawal", "amount": 16960386, "fee": 800, "transactStatus": "Completed",
 "address": "", "tx": "", "text": "", "transactTime": "2018-09-15T12:30:56.475Z",
 "walletBalance": 103394923, "marginBalance": null,
 "timestamp": "2018-09-15T12:30:56.475Z"}]"""


def test_name():
    exchange = Bitmex('bitmex1', 'a', b'a', object(), object())
    assert exchange.location == Location.BITMEX
    assert exchange.name == 'bitmex1'


def test_bitmex_api_signature(mock_bitmex):
    # tests cases from here: https://www.bitmex.com/app/apiKeysUsage
    sig = mock_bitmex._generate_signature(
        'get',
        '/api/v1/instrument',
        1518064236,
    )
    assert sig == 'c7682d435d0cfe87c16098df34ef2eb5a549d4c5a3c2b1f0f77b8af73423bf00'
    sig = mock_bitmex._generate_signature(
        'get',
        '/api/v1/instrument?filter=%7B%22symbol%22%3A+%22XBTM15%22%7D',
        1518064237,
    )
    assert sig == 'e2f422547eecb5b3cb29ade2127e21b858b235b386bfa45e1c1756eb3383919f'
    sig = mock_bitmex._generate_signature(
        'post',
        '/api/v1/order',
        1518064238,
        data=(
            '{"symbol":"XBTM15","price":219.0,'
            '"clOrdID":"mm_bitmex_1a/oemUeQ4CAJZgP3fjHsA","orderQty":98}'
        ),
    )
    assert sig == '1749cd2ccae4aa49048ae09f0b95110cee706e0944e6a14ad0b3a8cb45bd336b'


def test_bitmex_api_withdrawals_deposit_and_query_after_subquery(
        database: 'DBHandler',
        sandbox_bitmex: Bitmex,
) -> None:
    """Test the happy case of bitmex withdrawals deposit query."""
    sandbox_bitmex.first_connection_made = True
    sandbox_bitmex.asset_to_decimals = {'XBt': 8, 'USDt': 6}
    sandbox_bitmex.query_history_events()
    with database.conn.read_ctx() as cursor:
        result = DBHistoryEvents(database).get_history_events(
            cursor,
            filter_query=HistoryEventFilterQuery.make(location=Location.BITMEX),
            has_premium=True,
        )

    expected_result = [AssetMovement(
        identifier=5,
        event_identifier='ccc9482b81ec668e8846054933f14426bb99fae1d31a1d753187962454544a1c',
        location=Location.BITMEX,
        location_label=sandbox_bitmex.name,
        event_type=HistoryEventType.DEPOSIT,
        timestamp=TimestampMS(1536486278000),
        asset=A_BTC,
        amount=FVal('0.46966992'),
    ), AssetMovement(
        identifier=3,
        event_identifier='e0f2ca47943d1769d568c8a7a5348ffdbd0ed11a98e3444eebc3370f1fc1f52d',
        location=Location.BITMEX,
        location_label=sandbox_bitmex.name,
        event_type=HistoryEventType.WITHDRAWAL,
        timestamp=TimestampMS(1536536707000),
        asset=A_BTC,
        amount=FVal('0.007'),
        extra_data={'address': 'mv4rnyY3Su5gjcDNzbMLKBQkBicCtHUtFB'},
    ), AssetMovement(
        identifier=4,
        event_identifier='e0f2ca47943d1769d568c8a7a5348ffdbd0ed11a98e3444eebc3370f1fc1f52d',
        location=Location.BITMEX,
        location_label=sandbox_bitmex.name,
        event_type=HistoryEventType.WITHDRAWAL,
        timestamp=TimestampMS(1536536707000),
        asset=A_BTC,
        amount=FVal('0.003'),
        is_fee=True,
    ), AssetMovement(
        identifier=2,
        event_identifier='290836ed7b44d7921bc7ab2f8d189f456e266769fa6517e6361e407f4ef4fbc9',
        location=Location.BITMEX,
        location_label=sandbox_bitmex.name,
        event_type=HistoryEventType.DEPOSIT,
        timestamp=TimestampMS(1536563759000),
        asset=A_BTC,
        amount=FVal('0.38474377'),
    ), AssetMovement(
        identifier=1,
        event_identifier='d4307315ea24915446578e8f8015a5ea95e30194769a62ce8f92f43c2b876bac',
        location=Location.BITMEX,
        location_label=sandbox_bitmex.name,
        event_type=HistoryEventType.DEPOSIT,
        timestamp=TimestampMS(1537014656000),
        asset=A_BTC,
        amount=FVal(0.16960386),
    )]
    assert result == expected_result
    # also make sure that asset movements contain Asset and not strings
    for movement in result:
        assert isinstance(movement.asset, Asset)


def test_bitmex_api_withdrawals_deposit_unexpected_data(sandbox_bitmex: 'Bitmex') -> None:
    """Test getting unexpected data in bitmex withdrawals deposit query is handled gracefully"""
    original_input = TEST_BITMEX_WITHDRAWAL
    now = ts_now()
    sandbox_bitmex.first_connection_made = True
    sandbox_bitmex.asset_to_decimals = {'XBt': 8, 'USDt': 6}

    def query_bitmex_and_test(
            input_str: str,
            expected_warnings_num: int,
            expected_errors_num: int,
    ) -> None:
        def mock_get_history_events(url, **kwargs):  # pylint: disable=unused-argument
            return MockResponse(200, input_str)

        with patch.object(sandbox_bitmex.session, 'get', side_effect=mock_get_history_events):
            movements, _ = sandbox_bitmex.query_online_history_events(
                start_ts=Timestamp(0),
                end_ts=now,
            )

        if expected_warnings_num == 0 and expected_errors_num == 0:
            assert len(movements) == 1 if '"fee": null' in input_str else 2
        else:
            assert len(movements) == 0
            errors = sandbox_bitmex.msg_aggregator.consume_errors()
            warnings = sandbox_bitmex.msg_aggregator.consume_warnings()
            assert len(errors) == expected_errors_num
            assert len(warnings) == expected_warnings_num

    # First try with correct data to make sure everything works
    query_bitmex_and_test(original_input, expected_warnings_num=0, expected_errors_num=0)

    # From here and on present unexpected data
    # invalid timestamp
    given_input = original_input.replace('"2018-09-15T12:30:56.475Z"', '"dasd"')
    query_bitmex_and_test(given_input, expected_warnings_num=0, expected_errors_num=1)

    # invalid asset
    given_input = original_input.replace('"XBt"', '"XYX"')
    query_bitmex_and_test(given_input, expected_warnings_num=0, expected_errors_num=0)

    # invalid amount
    given_input = original_input.replace('16960386', 'null')
    query_bitmex_and_test(given_input, expected_warnings_num=0, expected_errors_num=0)

    # make sure that fee null/none works
    given_input = original_input.replace('800', 'null')
    query_bitmex_and_test(given_input, expected_warnings_num=0, expected_errors_num=0)

    # invalid fee
    given_input = original_input.replace('800', '"dadsdsa"')
    query_bitmex_and_test(given_input, expected_warnings_num=0, expected_errors_num=1)

    # missing key error
    given_input = original_input.replace('"amount": 16960386,', '')
    query_bitmex_and_test(given_input, expected_warnings_num=0, expected_errors_num=1)

    # check that if 'transactType` key is missing things still work
    given_input = original_input.replace('"transactType": "Withdrawal",', '')
    query_bitmex_and_test(given_input, expected_warnings_num=0, expected_errors_num=1)


@pytest.mark.parametrize('function_scope_initialize_mock_rotki_notifier', [True])
def test_bitmex_api_withdrawals_deposit_unknown_asset(mock_bitmex: 'Bitmex') -> None:
    """Test getting unknown asset in bitmex withdrawals deposit query is handled gracefully"""

    def mock_get_response(method, url, **kwargs):  # pylint: disable=unused-argument
        return MockResponse(200, TEST_BITMEX_WITHDRAWAL.replace('"XBt"', '"dadsdsa"'))

    with patch.object(mock_bitmex.session, 'request', side_effect=mock_get_response):
        movements, _ = mock_bitmex.query_online_history_events(
            start_ts=Timestamp(0),
            end_ts=ts_now(),
        )

    assert len(movements) == 0
    assert len(mock_bitmex.msg_aggregator.rotki_notifier.messages) == 1  # type: ignore


@pytest.mark.vcr
def test_bitmex_margin_history(sandbox_bitmex: Bitmex) -> None:
    sandbox_bitmex.first_connection_made = True
    sandbox_bitmex.asset_to_decimals = {'XBt': 8, 'USDt': 6}
    result = sandbox_bitmex.query_margin_history(
        start_ts=Timestamp(1536492800),
        end_ts=Timestamp(1536492976),
    )
    assert len(result) == 0

    result = sandbox_bitmex.query_margin_history(
        start_ts=Timestamp(0),
        end_ts=Timestamp(1536615593),  # timestamp that returns 5 results
    )
    expected_result = [MarginPosition(
        location=Location.BITMEX,
        open_time=None,
        close_time=Timestamp(1536580800),
        profit_loss=FVal('0.00000683'),
        pl_currency=A_BTC,
        fee=Fee(ZERO),
        fee_currency=A_BTC,
        link='9ab9f275-9132-64aa-4aa6-8c6503418ac6',
        notes='ETHUSD',
    ), MarginPosition(
        location=Location.BITMEX,
        open_time=None,
        close_time=Timestamp(1536580800),
        profit_loss=FVal('0.00000183'),
        pl_currency=A_BTC,
        fee=Fee(ZERO),
        fee_currency=A_BTC,
        link='9c50e247-9bea-b10b-93c8-26845f202e9a',
        notes='XBTJPY',
    ), MarginPosition(
        location=Location.BITMEX,
        open_time=None,
        close_time=Timestamp(1536580800),
        profit_loss=FVal('0.0000004'),
        pl_currency=A_BTC,
        fee=Fee(ZERO),
        fee_currency=A_BTC,
        link='c74e6967-1411-0ad1-e3e3-6f97a04d7202',
        notes='XBTUSD',
    ), MarginPosition(
        location=Location.BITMEX,
        open_time=None,
        close_time=Timestamp(1536580800),
        profit_loss=FVal('0.00000003'),
        pl_currency=A_BTC,
        fee=Fee(ZERO),
        fee_currency=A_BTC,
        link='97402f76-828e-a8ea-5d26-920134924149',
        notes='XBTZ18',
    ), MarginPosition(
        location=Location.BITMEX,
        open_time=None,
        close_time=Timestamp(1536494400),
        profit_loss=FVal('-0.00007992'),
        pl_currency=A_BTC,
        fee=Fee(ZERO),
        fee_currency=A_BTC,
        link='df46338a-da5e-e16c-9753-3e863d83d92c',
        notes='ETHU18',
    )]
    assert result[:5] == expected_result


def test_bitmex_query_balances(sandbox_bitmex):
    mock_response = [
        {'currency': 'XBt', 'amount': 123456789},
        {'currency': 'USDt', 'amount': 31164180},
    ]
    sandbox_bitmex.first_connection_made = True
    sandbox_bitmex.asset_to_decimals = {'XBt': 8, 'USDt': 6}
    with patch.object(sandbox_bitmex, '_api_query', return_value=mock_response):
        balances, msg = sandbox_bitmex.query_balances()

    assert msg == ''
    assert len(balances) == 2
    assert balances[A_BTC].amount == FVal('1.23456789')
    assert balances[A_BTC].usd_value == FVal('1.851851835')
    assert balances[A_USDT].amount == FVal('31.164180')

    warnings = sandbox_bitmex.msg_aggregator.consume_warnings()
    assert len(warnings) == 0
