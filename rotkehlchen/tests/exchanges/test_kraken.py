import warnings as test_warnings
from contextlib import ExitStack
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING, cast
from unittest.mock import _patch, patch
from uuid import uuid4

import gevent
import pytest
import requests

from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.api.v1.types import IncludeExcludeFilterData
from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.assets.asset import Asset, CustomAsset
from rotkehlchen.assets.converters import asset_from_kraken
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import (
    A_BTC,
    A_DOT,
    A_ETH,
    A_ETH2,
    A_GRT,
    A_KSM,
    A_USD,
    A_USDC,
    A_USDT,
)
from rotkehlchen.constants.limits import FREE_HISTORY_EVENTS_LIMIT
from rotkehlchen.constants.resolver import strethaddress_to_identifier
from rotkehlchen.db.custom_assets import DBCustomAssets
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import ModifiableDBSettings
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.kraken import Kraken
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.asset_movement import create_asset_movement_with_fee
from rotkehlchen.history.events.structures.base import HistoryBaseEntryType, HistoryEvent
from rotkehlchen.history.events.structures.swap import SwapEvent, create_swap_events
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.history.events.utils import create_event_identifier_from_unique_id
from rotkehlchen.serialization.deserialize import deserialize_timestamp_from_floatstr
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_sync_response_with_result,
)
from rotkehlchen.tests.utils.constants import (
    A_ADA,
    A_DAO,
    A_EUR,
    TEST_PREMIUM_HISTORY_EVENTS_LIMIT,
)
from rotkehlchen.tests.utils.exchanges import (
    get_exchange_asset_symbols,
    try_get_first_exchange,
)
from rotkehlchen.tests.utils.history import prices
from rotkehlchen.tests.utils.kraken import KRAKEN_DELISTED, MockKraken
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.tests.utils.pnl_report import query_api_create_and_get_report
from rotkehlchen.types import AssetAmount, Location, Timestamp, TimestampMS

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer


def _check_trade_history_events_order(db, expected):
    """Check that the history events for the trades have the expected order"""
    dbevents = DBHistoryEvents(db)
    with db.conn.read_ctx() as cursor:
        events = dbevents.get_history_events(cursor, HistoryEventFilterQuery.make(), True)
        assert len(events) == len(expected)
        for event in events:
            assert event.sequence_index == expected[event.sequence_index][0]
            assert event.event_type == expected[event.sequence_index][1]
            assert event.event_subtype == expected[event.sequence_index][2]


def _patch_ledger(kraken: 'MockKraken', ledger_data: str) -> _patch:
    kraken.random_trade_data = False
    kraken.random_ledgers_data = False
    kraken.cache_ttl_secs = 0
    return patch(
        target='rotkehlchen.tests.utils.kraken.KRAKEN_GENERAL_LEDGER_RESPONSE',
        new=ledger_data,
    )


def test_name():
    exchange = Kraken('kraken1', 'a', b'YQ==', object(), object())  # b'YQ==' is base64 for 'a'
    assert exchange.location == Location.KRAKEN
    assert exchange.name == 'kraken1'


@pytest.mark.asset_test
def test_coverage_of_kraken_balances():
    response = requests.get('https://api.kraken.com/0/public/Assets')
    got_assets = set(response.json()['result'].keys())
    expected_assets = get_exchange_asset_symbols(
        exchange=Location.KRAKEN,
        query_suffix=';',  # exclude false-positives of delisted assets
    )

    # Special/staking assets and which assets they should map to
    special_assets = {
        'XTZ.S': Asset('XTZ'),
        'DOT.S': A_DOT,
        'ATOM.S': Asset('ATOM'),
        'EUR.M': A_EUR,
        'USD.M': A_USD,
        'XBT.M': A_BTC,
        'KSM.S': A_KSM,
        'ETH2.S': A_ETH2,
        'KAVA.S': Asset('KAVA'),
        'EUR.HOLD': A_EUR,
        'USD.HOLD': A_USD,
        'FLOW.S': Asset('FLOW'),
        'FLOWH.S': Asset('FLOW'),
        'FLOWH': Asset('FLOW'),
        'ADA.S': A_ADA,
        'SOL.S': Asset('SOL'),
        'KSM.P': A_KSM,  # kusama bonded for parachains
        'ALGO.S': Asset('ALGO'),
        'DOT.P': A_DOT,
        'MINA.S': Asset('MINA'),
        'TRX.S': strethaddress_to_identifier('0x50327c6c5a14DCaDE707ABad2E27eB517df87AB5'),
        'LUNA.S': strethaddress_to_identifier('0xd2877702675e6cEb975b4A1dFf9fb7BAF4C91ea9'),
        'SCRT.S': Asset('SCRT'),
        'MATIC.S': strethaddress_to_identifier('0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeBB0'),
        'GBP.HOLD': Asset('GBP'),
        'CHF.HOLD': Asset('CHF'),
        'CAD.HOLD': Asset('CAD'),
        'AUD.HOLD': Asset('AUD'),
        'AED.HOLD': Asset('AED'),
        'USDC.M': A_USDC,
        'GRT.S': A_GRT,
        'FLR.S': Asset('FLR'),
        'USDT.M': A_USDT,
        'DOT28.S': A_DOT,
        'GRT28.S': A_GRT,
        'SCRT21.S': Asset('SCRT'),
        'KAVA21.S': Asset('KAVA'),
        'ATOM21.S': Asset('ATOM'),
        'SOL03.S': Asset('SOL'),
        'FLOW14.S': Asset('FLOW'),
        'MATIC04.S': strethaddress_to_identifier('0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeBB0'),
        'KSM07.S': A_KSM,
    }
    missing_assets = {
        'ZARS',  # doesn't appear yet in the platform
        'ZMXN',  # not listed yet in the platform
    }

    for kraken_asset in got_assets:
        if kraken_asset in special_assets:
            assert asset_from_kraken(kraken_asset) == special_assets[kraken_asset]
        elif kraken_asset not in KRAKEN_DELISTED:
            try:
                asset_from_kraken(kraken_asset)
            except (DeserializationError, UnknownAsset):
                if kraken_asset not in missing_assets:
                    test_warnings.warn(UserWarning(
                        f'Found unknown primary asset {kraken_asset} in kraken. '
                        f'Support for it has to be added',
                    ))

    delisted = expected_assets - got_assets - set(KRAKEN_DELISTED)
    if delisted:
        test_warnings.warn(UserWarning(
            f'Detected newly delisted assets from Kraken: {delisted}. '
            f'Please update KRAKEN_DELISTED constant.',
        ))


def test_querying_balances(kraken):
    result, error_or_empty = kraken.query_balances()
    assert error_or_empty == ''
    assert isinstance(result, dict)
    for asset, entry in result.items():
        assert isinstance(asset, Asset)
        assert isinstance(entry, Balance)


def test_querying_rate_limit_exhaustion(kraken, database):
    """Test that if kraken api rates limit us we don't get stuck in an infinite loop
    and also that we return what we managed to retrieve until rate limit occurred.

    Regression test for https://github.com/rotki/rotki/issues/3629
    """
    kraken.use_original_kraken = True
    kraken.reduction_every_secs = 0.05

    count = 0

    def mock_response(url, **kwargs):  # pylint: disable=unused-argument
        nonlocal count
        if 'Ledgers' in url:
            if count == 0:
                text = '{"result":{"ledger":{"L1":{"refid":"AOEXXV-61T63-AKPSJ0","time":1609950165.4497,"type":"trade","subtype":"","aclass":"currency","asset":"KFEE","amount":"0.00","fee":"1.145","balance":"0.00"},"L2":{"refid":"AOEXXV-61T63-AKPSJ0","time":1609950165.4492,"type":"trade","subtype":"","aclass":"currency","asset":"ZEUR","amount":"50","fee":"0.4429","balance":"500"},"L3":{"refid":"AOEXXV-61T63-AKPSJ0","time":1609950165.4486,"type":"trade","subtype":"","aclass":"currency","asset":"XETH","amount":"-0.1","fee":"0.0000000000","balance":1.1}},"count":4}}'  # noqa: E501
                count += 1
                return MockResponse(200, text)
            # else
            text = '{"result": "", "error": "EAPI Rate limit exceeded"}'
            count += 1
            return MockResponse(200, text)
        if 'AssetPairs' in url:
            dir_path = Path(__file__).resolve().parent.parent
            return MockResponse(200, (dir_path / 'data' / 'assets_kraken.json').read_text(encoding='utf8'))  # noqa: E501

        # else
        raise AssertionError(f'Unexpected url in kraken query: {url}')

    patch_kraken = patch.object(kraken.session, 'post', side_effect=mock_response)
    patch_retries = patch('rotkehlchen.exchanges.kraken.KRAKEN_QUERY_TRIES', new=2)
    patch_dividend = patch('rotkehlchen.exchanges.kraken.KRAKEN_BACKOFF_DIVIDEND', new=1)

    with ExitStack() as stack:
        stack.enter_context(gevent.Timeout(8))
        stack.enter_context(patch_retries)
        stack.enter_context(patch_dividend)
        stack.enter_context(patch_kraken)
        kraken.query_history_events()

    with database.conn.read_ctx() as cursor:
        assert len(DBHistoryEvents(database).get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(location=Location.KRAKEN),
        )) == 4  # spend, receive, fee, and kfee
        from_ts, to_ts = database.get_used_query_range(cursor, 'kraken_history_events_mockkraken')

    assert from_ts == 0
    assert to_ts == 1609950165, 'should have saved only until the last trades timestamp'


def test_querying_deposits_withdrawals(kraken):
    kraken.random_ledgers_data = False
    kraken.query_history_events()
    with kraken.db.conn.read_ctx() as cursor:
        result = DBHistoryEvents(kraken.db).get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(
                location=Location.KRAKEN,
                from_ts=Timestamp(1439994442),
                event_types=[HistoryEventType.DEPOSIT, HistoryEventType.WITHDRAWAL],
                entry_types=IncludeExcludeFilterData(
                    values=[HistoryBaseEntryType.ASSET_MOVEMENT_EVENT],
                ),
            ),
        )

    assert len(result) == 8
    assert len([event for event in result if event.event_subtype == HistoryEventSubType.FEE]) == 3


@pytest.mark.parametrize('function_scope_initialize_mock_rotki_notifier', [True])
def test_kraken_query_balances_unknown_asset(kraken):
    """Test that if a kraken balance query returns unknown asset no exception
    is raised and a message is generated"""
    kraken.random_balance_data = False
    balances, msg = kraken.query_balances()

    assert msg == ''
    assert len(balances) == 2
    assert balances[A_BTC].amount == FVal('5.0')
    assert balances[A_BTC].usd_value == FVal('7.5')
    assert balances[A_ETH].amount == FVal('10.0')
    assert balances[A_ETH].usd_value == FVal('15.0')

    messages = kraken.msg_aggregator.rotki_notifier.messages
    assert len(messages) == 1
    assert messages[0].message_type == WSMessageType.EXCHANGE_UNKNOWN_ASSET
    assert messages[0].data['identifier'] == 'NOTAREALASSET'


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_kraken_query_deposit_withdrawals_unknown_asset(kraken):
    """Test that if a kraken deposits_withdrawals query returns unknown asset
    no exception is raised and a warning is generated and the deposits/withdrawals
    with valid assets are still returned"""
    input_ledger = """
    {
    "ledger": {
        "0": {
            "refid": "2",
            "time": 1439994442,
            "type": "withdrawal",
            "subtype": "",
            "aclass": "currency",
            "asset": "XETH",
            "amount": "-1.0000000000",
            "fee": "0.0035000000",
            "balance": "0.0000100000"
        },
        "L12382343902": {
            "refid": "0",
            "time": 1458994441.396,
            "type": "deposit",
            "subtype": "",
            "aclass": "currency",
            "asset": "EUR.HOLD",
            "amount": "4000000.0000",
            "fee": "1.7500",
            "balance": "3999998.25"
        },
        "L12382343903": {
            "refid": "3",
            "time": 1458994441.396,
            "type": "deposit",
            "subtype": "",
            "aclass": "currency",
            "asset": "YYYYYYYYYYYY",
            "amount": "4000000.0000",
            "fee": "1.7500",
            "balance": "3999998.25"
        }
    },
        "count": 3
    }
    """

    with _patch_ledger(kraken, input_ledger):
        kraken.query_history_events()

    with kraken.db.conn.read_ctx() as cursor:
        movements = DBHistoryEvents(kraken.db).get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(location=Location.KRAKEN),
        )

    # withdrawal and first normal deposit should have no problem
    assert len(movements) == 4
    assert movements[0].sequence_index == 0
    assert movements[0].timestamp == TimestampMS(1439994442000)
    assert movements[0].location == Location.KRAKEN
    assert movements[0].location_label == kraken.name
    assert movements[0].asset == A_ETH
    assert movements[0].amount == ONE
    assert movements[0].event_type == HistoryEventType.WITHDRAWAL
    assert movements[0].event_subtype == HistoryEventSubType.REMOVE_ASSET
    assert movements[1].event_identifier == movements[0].event_identifier
    assert movements[1].sequence_index == 1
    assert movements[1].timestamp == TimestampMS(1439994442000)
    assert movements[1].location == Location.KRAKEN
    assert movements[1].location_label == kraken.name
    assert movements[1].asset == A_ETH
    assert movements[1].amount == FVal('0.0035')
    assert movements[1].event_type == HistoryEventType.WITHDRAWAL
    assert movements[1].event_subtype == HistoryEventSubType.FEE
    assert movements[2].asset == A_EUR
    assert movements[2].amount == FVal('4000000')
    assert movements[2].event_type == HistoryEventType.DEPOSIT
    assert movements[3].event_subtype == HistoryEventSubType.FEE
    errors = kraken.msg_aggregator.consume_errors()
    assert len(errors) == 1


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_kraken_trade_with_spend_receive(kraken):
    """Test that trades based on spend/receive events are correctly processed.
    Also checks the multiple fees are properly handled.
    """
    test_trades = """{
        "ledger": {
            "L2": {
                "refid": "1",
                "time": 1636406000.8555,
                "type": "receive",
                "subtype": "",
                "aclass": "currency",
                "asset": "XETH",
                "amount": "1",
                "fee": "0.000123",
                "balance": "1001"
            },
            "L1": {
                "refid": "1",
                "time": 1636406000.8654,
                "type": "spend",
                "subtype": "",
                "aclass": "currency",
                "asset": "ZEUR",
                "amount": "-100",
                "fee": "0.4500",
                "balance": "30000000"
            }
        },
        "count": 2
    }"""

    with _patch_ledger(kraken, test_trades):
        kraken.query_history_events()

    with kraken.db.conn.read_ctx() as cursor:
        assert DBHistoryEvents(kraken.db).get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(location=Location.KRAKEN),
        ) == [SwapEvent(
            identifier=1,
            timestamp=(timestamp := TimestampMS(1636406000855)),
            location=Location.KRAKEN,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_EUR,
            amount=FVal('100'),
            event_identifier=(event_identifier := create_event_identifier_from_unique_id(
                location=Location.KRAKEN,
                unique_id='11636406000855',
            )),
            location_label=kraken.name,
        ), SwapEvent(
            identifier=2,
            timestamp=timestamp,
            location=Location.KRAKEN,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ETH,
            amount=FVal('1'),
            event_identifier=event_identifier,
            location_label=kraken.name,
        ), SwapEvent(
            identifier=3,
            timestamp=timestamp,
            location=Location.KRAKEN,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.000123'),
            event_identifier=event_identifier,
            location_label=kraken.name,
        ), SwapEvent(
            identifier=4,
            timestamp=timestamp,
            location=Location.KRAKEN,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_EUR,
            amount=FVal('0.4500'),
            event_identifier=event_identifier,
            location_label=kraken.name,
            sequence_index=3,
        )]

    errors = kraken.msg_aggregator.consume_errors()
    warnings = kraken.msg_aggregator.consume_warnings()
    assert len(errors) == 0
    assert len(warnings) == 0


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_kraken_trade_with_adjustment(kraken):
    """Test that trades based on adjustment events are processed"""

    test_trades = """{
        "ledger": {
            "L1": {
                "refid": "1",
                "time": 1636406000.8555,
                "type": "adjustment",
                "subtype": "",
                "aclass": "currency",
                "asset": "XDAO",
                "amount": "-0.0008854800",
                "fee": "0.0000000000",
                "balance": "1"
            },
            "L2": {
                "refid": "2",
                "time": 1636406000.8654,
                "type": "adjustment",
                "subtype": "",
                "aclass": "currency",
                "asset": "XETH",
                "amount": "0.0000088548",
                "fee": "0",
                "balance": "1"
            }
        },
        "count": 2
    }"""

    with _patch_ledger(kraken, test_trades):
        kraken.query_history_events()

        with kraken.db.conn.read_ctx() as cursor:
            assert DBHistoryEvents(kraken.db).get_history_events_internal(
                cursor=cursor,
                filter_query=HistoryEventFilterQuery.make(location=Location.KRAKEN),
            ) == [SwapEvent(
                identifier=1,
                timestamp=TimestampMS(1636406000855),
                location=Location.KRAKEN,
                event_subtype=HistoryEventSubType.SPEND,
                asset=A_DAO,
                amount=FVal('0.0008854800'),
                event_identifier=create_event_identifier_from_unique_id(
                    location=Location.KRAKEN,
                    unique_id='adjustment12',
                ),
                location_label=kraken.name,
            ), SwapEvent(
                identifier=2,
                timestamp=TimestampMS(1636406000855),
                location=Location.KRAKEN,
                event_subtype=HistoryEventSubType.RECEIVE,
                asset=A_ETH,
                amount=FVal('0.0000088548'),
                event_identifier=create_event_identifier_from_unique_id(
                    location=Location.KRAKEN,
                    unique_id='adjustment12',
                ),
                location_label=kraken.name,
            )]

    errors = kraken.msg_aggregator.consume_errors()
    warnings = kraken.msg_aggregator.consume_warnings()
    assert len(errors) == 0
    assert len(warnings) == 0


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_kraken_adjustment(kraken):
    """Test that a plain adjustment event (no associated trade) is handled correctly."""
    with _patch_ledger(
        kraken=kraken,
        ledger_data="""{"count": 1, "ledger": {"L1": {
            "aclass": "currency",
            "amount": "283.79600",
            "asset": "SYRUP",
            "balance": "283.79600",
            "fee": "0.00000",
            "refid": "xxxx",
            "time": 1731508592.028446,
            "type": "transfer",
            "subtype": "spotfromfutures"
        }}}""",
    ):
        kraken.query_history_events()

    with kraken.db.conn.read_ctx() as cursor:
        assert DBHistoryEvents(kraken.db).get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(location=Location.KRAKEN),
        ) == [HistoryEvent(
            identifier=1,
            event_identifier='xxxx',
            sequence_index=0,
            timestamp=TimestampMS(1731508592028),
            location=Location.KRAKEN,
            event_type=HistoryEventType.ADJUSTMENT,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:1/erc20:0x643C4E15d7d62Ad0aBeC4a9BD4b001aA3Ef52d66'),
            amount=FVal('283.79600'),
            location_label=kraken.name,
        )]


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_kraken_trade_no_counterpart(kraken):
    """Test that trades with no counterpart are processed properly"""
    test_trades = """{
        "ledger": {
            "L1": {
                "refid": "1",
                "time": 1636406000.8555,
                "type": "trade",
                "subtype": "",
                "aclass": "currency",
                "asset": "XETH",
                "amount": "-0.000001",
                "fee": "0.0000000000",
                "balance": "1"
            },
            "L2": {
                "refid": "2",
                "time": 1636406000.8654,
                "type": "trade",
                "subtype": "",
                "aclass": "currency",
                "asset": "XXBT",
                "amount": "0.0000001",
                "fee": "0",
                "balance": "1"
            }
        },
        "count": 2
    }"""

    with _patch_ledger(kraken, test_trades):
        kraken.query_history_events()

        with kraken.db.conn.read_ctx() as cursor:
            assert DBHistoryEvents(kraken.db).get_history_events_internal(
                cursor=cursor,
                filter_query=HistoryEventFilterQuery.make(location=Location.KRAKEN),
            ) == [SwapEvent(
                identifier=1,
                timestamp=TimestampMS(1636406000855),
                location=Location.KRAKEN,
                event_subtype=HistoryEventSubType.SPEND,
                asset=A_ETH,
                amount=FVal('0.000001'),
                event_identifier=create_event_identifier_from_unique_id(
                    location=Location.KRAKEN,
                    unique_id='11636406000855',
                ),
                location_label=kraken.name,
            ), SwapEvent(
                identifier=2,
                timestamp=TimestampMS(1636406000855),
                location=Location.KRAKEN,
                event_subtype=HistoryEventSubType.RECEIVE,
                asset=A_USD,
                amount=ZERO,
                event_identifier=create_event_identifier_from_unique_id(
                    location=Location.KRAKEN,
                    unique_id='11636406000855',
                ),
                location_label=kraken.name,
            ), SwapEvent(
                identifier=3,
                timestamp=TimestampMS(1636406000865),
                location=Location.KRAKEN,
                event_subtype=HistoryEventSubType.SPEND,
                asset=A_USD,
                amount=ZERO,
                event_identifier=create_event_identifier_from_unique_id(
                    location=Location.KRAKEN,
                    unique_id='21636406000865',
                ),
                location_label=kraken.name,
            ), SwapEvent(
                identifier=4,
                timestamp=TimestampMS(1636406000865),
                location=Location.KRAKEN,
                event_subtype=HistoryEventSubType.RECEIVE,
                asset=A_BTC,
                amount=FVal('0.0000001'),
                event_identifier=create_event_identifier_from_unique_id(
                    location=Location.KRAKEN,
                    unique_id='21636406000865',
                ),
                location_label=kraken.name,
            )]

    errors = kraken.msg_aggregator.consume_errors()
    warnings = kraken.msg_aggregator.consume_warnings()
    assert len(errors) == 0
    assert len(warnings) == 0


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_kraken_failed_withdrawals(kraken):
    """Test that failed withdrawals are processed properly"""
    test_events = """{
        "ledger": {
            "W1": {
                "refid": "1",
                "time": 1636406000.8555,
                "type": "withdrawal",
                "subtype": "",
                "aclass": "currency",
                "asset": "ZEUR",
                "amount": "-1000.0",
                "fee": "1.0",
                "balance": "1"
            },
            "W2": {
                "refid": "1",
                "time": 1636508000.8555,
                "type": "withdrawal",
                "subtype": "",
                "aclass": "currency",
                "asset": "ZEUR",
                "amount": "1000",
                "fee": "-1.0",
                "balance": "1"
            }
        },
        "count": 2
    }"""

    with _patch_ledger(kraken, test_events):
        kraken.query_history_events()
    with kraken.db.conn.read_ctx() as cursor:
        withdrawals = DBHistoryEvents(kraken.db).get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(location=Location.KRAKEN),
        )
    assert len(withdrawals) == 0


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_trade_from_kraken_unexpected_data(kraken):
    """Test that getting unexpected data from kraken leads to skipping the trade
    and does not lead to a crash"""
    # Important: Testing with a time floating point that has other than zero after decimal
    test_trades = """{
    "ledger": {
        "L343242342": {
            "refid": "1",
            "time": 1458994442.064,
            "type": "trade",
            "subtype": "",
            "aclass": "currency",
            "asset": "XXBT",
            "amount": "1",
            "fee": "0.0000000000",
            "balance": "0.0437477300"
            },
        "L5354645643": {
            "refid": "1",
            "time": 1458994442.063,
            "type": "trade",
            "subtype": "",
            "aclass": "currency",
            "asset": "ZEUR",
            "amount": "-100",
            "fee": "0.1",
            "balance": "200"
        }
    },
    "count": 2
}"""

    def query_kraken_and_test(input_trades, expected_warnings_num, expected_errors_num):
        # delete kraken history entries so they get requeried
        with kraken.history_events_db.db.user_write() as cursor:
            location = Location.KRAKEN
            cursor.execute(
                'DELETE FROM history_events WHERE location=?',
                (location.serialize_for_db(),),
            )
            cursor.execute(
                'DELETE FROM used_query_ranges WHERE name LIKE ?',
                (f'{location}_history_events_%',),
            )

        with _patch_ledger(kraken, input_trades):
            kraken.query_history_events()

        with kraken.db.conn.read_ctx() as cursor:
            events = DBHistoryEvents(kraken.db).get_history_events_internal(
                cursor=cursor,
                filter_query=HistoryEventFilterQuery.make(location=Location.KRAKEN),
            )

        if expected_warnings_num == 0 and expected_errors_num == 0:
            assert len(events) == 3
            assert events[0].asset == A_EUR
            assert events[1].asset == A_BTC
            assert events[2].asset == A_EUR
        else:
            assert len(events) == 0
        errors = kraken.msg_aggregator.consume_errors()
        warnings = kraken.msg_aggregator.consume_warnings()
        assert len(errors) == expected_errors_num
        assert len(warnings) == expected_warnings_num

    # First a normal trade should have no problems
    query_kraken_and_test(test_trades, expected_warnings_num=0, expected_errors_num=0)

    # Kraken also uses strings for timestamps, this should also work
    input_trades = test_trades
    input_trades = input_trades.replace('"time": 1458994442.063', '"time": "1458994442.063"')
    query_kraken_and_test(input_trades, expected_warnings_num=0, expected_errors_num=0)

    # From here and on let's check trades with unexpected data
    input_trades = test_trades
    input_trades = input_trades.replace('"asset": "XXBT"', '"asset": "lefty"')
    query_kraken_and_test(input_trades, expected_warnings_num=0, expected_errors_num=1)

    input_trades = test_trades
    input_trades = input_trades.replace('"time": 1458994442.063', '"time": "dsdsad"')
    query_kraken_and_test(input_trades, expected_warnings_num=0, expected_errors_num=1)

    input_trades = test_trades
    input_trades = input_trades.replace('"amount": "1"', '"amount": "dsdsad"')
    query_kraken_and_test(input_trades, expected_warnings_num=0, expected_errors_num=1)

    input_trades = test_trades
    input_trades = input_trades.replace('"amount": "-100"', '"amount": null')
    query_kraken_and_test(input_trades, expected_warnings_num=0, expected_errors_num=2)

    input_trades = test_trades
    input_trades = input_trades.replace('"fee": "0.1"', '"fee": "dsdsad"')
    query_kraken_and_test(input_trades, expected_warnings_num=0, expected_errors_num=2)

    # Also test key error
    input_trades = test_trades
    input_trades = input_trades.replace('"amount": "-100",', '')
    query_kraken_and_test(input_trades, expected_warnings_num=0, expected_errors_num=2)


def test_empty_kraken_balance_response():
    """Balance api query returns a response without a result

    Regression test for: https://github.com/rotki/rotki/issues/2443
    """
    kraken = Kraken('kraken1', 'a', b'YW55IGNhcm5hbCBwbGVhc3VyZS4=', object(), object())

    def mock_post(url, data, **kwargs):  # pylint: disable=unused-argument
        return MockResponse(200, '{"error":[]}')

    with patch.object(kraken.session, 'post', wraps=mock_post):
        result, msg = kraken.query_balances()
        assert msg == ''
        assert result == {}


def test_timestamp_deserialization():
    """Test the function that allows to deserialize timestamp from different types"""
    assert deserialize_timestamp_from_floatstr('1458994442.2353') == 1458994442
    assert deserialize_timestamp_from_floatstr(1458994442.2353) == 1458994442
    assert deserialize_timestamp_from_floatstr(1458994442) == 1458994442
    assert deserialize_timestamp_from_floatstr(FVal(1458994442.2353)) == 1458994442
    with pytest.raises(DeserializationError):
        deserialize_timestamp_from_floatstr('234a')
    with pytest.raises(DeserializationError):
        deserialize_timestamp_from_floatstr('')


@pytest.mark.parametrize('have_decoders', [True])
@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('added_exchanges', [(Location.KRAKEN,)])
@pytest.mark.parametrize('mocked_price_queries', [prices])
@pytest.mark.parametrize('start_with_valid_premium', [False, True])
@pytest.mark.parametrize('db_settings', [{  # to count the kraken ETH staking events in accounting
    'eth_staking_taxable_after_withdrawal_enabled': False,
}])
def test_kraken_staking(rotkehlchen_api_server_with_exchanges, start_with_valid_premium):
    """Test that kraken staking events are processed correctly"""
    server = rotkehlchen_api_server_with_exchanges
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    # The input has extra information to test that the filters work correctly.
    # The events related to staking are AAA, BBB and CCC, DDD
    input_ledger = """
    {
    "ledger":{
        "WWW": {
            "refid": "WWWWWWW",
            "time": 1640493376.4008,
            "type": "staking",
            "subtype": "",
            "aclass": "currency",
            "asset": "XTZ",
            "amount": "0.0000100000",
            "fee": "0.0000000000",
            "balance": "0.0000100000"
        },
        "AAA": {
            "refid": "XXXXXX",
            "time": 1640493374.4008,
            "type": "staking",
            "subtype": "",
            "aclass": "currency",
            "asset": "ETH2",
            "amount": "0.0000538620",
            "fee": "0.0000000000",
            "balance": "0.0003349820"
        },
        "BBB": {
            "refid": "YYYYYYYY",
            "time": 1636740198.9674,
            "type": "transfer",
            "subtype": "stakingfromspot",
            "aclass": "currency",
            "asset": "ETH2.S",
            "amount": "0.0600000000",
            "fee": "0.0000000000",
            "balance": "0.0600000000"
        },
        "CCC": {
            "refid": "ZZZZZZZZZ",
            "time": 1636738550.7562,
            "type": "transfer",
            "subtype": "spottostaking",
            "aclass": "currency",
            "asset": "XETH",
            "amount": "-0.0600000000",
            "fee": "0.0000000000",
            "balance": "0.0250477300"
        },
        "L12382343902": {
            "refid": "0",
            "time": 1458994441.396,
            "type": "deposit",
            "subtype": "",
            "aclass": "currency",
            "asset": "EUR.HOLD",
            "amount": "4000000.0000",
            "fee": "1.7500",
            "balance": "3999998.25"
        },
        "DDD": {
            "refid": "DDDDD",
            "time": 1628994441.4008,
            "type": "staking",
            "subtype": "",
            "aclass": "currency",
            "asset": "ETH2",
            "amount": "12",
            "fee": "0",
            "balance": "0.1000538620"
        }
    },
    "count": 6
    }
    """
    # Test that before populating we don't have any event
    response = requests.post(
        api_url_for(
            server,
            'stakingresource',
        ),
    )
    result = assert_proper_sync_response_with_result(response)
    assert len(result['entries']) == 0

    with rotki.data.db.user_write() as write_cursor:
        rotki.data.db.purge_exchange_data(write_cursor, Location.KRAKEN)
    kraken = try_get_first_exchange(rotki.exchange_manager, Location.KRAKEN)
    with _patch_ledger(kraken, input_ledger):
        kraken.query_history_events()

    response = requests.post(
        api_url_for(
            server,
            'stakingresource',
        ),
        json={
            'from_timestamp': 1636538550,
            'to_timestamp': 1640493378,
        },
    )

    result = assert_proper_sync_response_with_result(response)
    events = result['entries']

    assert len(events) == 3
    assert len(events) == result['entries_found']
    assert events[0]['event_type'] == 'reward'
    assert events[1]['event_type'] == 'reward'
    assert events[2]['event_type'] == 'deposit asset'
    assert events[0]['asset'] == 'XTZ'
    assert events[1]['asset'] == 'ETH2'
    assert events[2]['asset'] == 'ETH'
    if start_with_valid_premium:
        assert result['entries_limit'] == TEST_PREMIUM_HISTORY_EVENTS_LIMIT
    else:
        assert result['entries_limit'] == FREE_HISTORY_EVENTS_LIMIT
    assert result['entries_total'] == 4
    assert result['received'] == [
        {'asset': 'XTZ', 'amount': '0.0000100000', 'usd_value': '0.000046300000'},
        {'asset': 'ETH2', 'amount': '0.0000538620', 'usd_value': '0.219353533620'},
    ]

    # test that the correct number of entries is returned with pagination
    response = requests.post(
        api_url_for(
            server,
            'stakingresource',
        ),
        json={
            'from_timestamp': 1636738551,
            'to_timestamp': 1640493375,
            'limit': 1,
        },
    )
    result = assert_proper_sync_response_with_result(response)
    assert result['entries_found'] == 1
    assert set(result['assets']) == {'ETH', 'ETH2', 'XTZ'}

    # assert that filter by asset is working properly
    response = requests.post(
        api_url_for(
            server,
            'stakingresource',
        ),
        json={
            'from_timestamp': 1628994442,
            'to_timestamp': 1640493377,
            'asset': 'ETH2',
        },
    )
    result = assert_proper_sync_response_with_result(response)
    assert len(result['entries']) == 1
    assert len(result['received']) == 1

    # test that we can correctly query subtypes
    response = requests.post(
        api_url_for(
            server,
            'stakingresource',
        ),
        json={
            'from_timestamp': 1458994441,
            'to_timestamp': 1640493377,
            'event_subtypes': ['reward'],
        },
    )
    result = assert_proper_sync_response_with_result(response)
    assert len(result['entries']) == 3

    response = requests.post(
        api_url_for(
            server,
            'stakingresource',
        ),
        json={
            'from_timestamp': 1458994441,
            'to_timestamp': 1640493377,
            'event_subtypes': [
                'reward',
                'deposit asset',
            ],
        },
    )
    result = assert_proper_sync_response_with_result(response)
    assert len(result['entries']) == 4

    # test that sorting for a non-existing column is handled correctly
    response = requests.post(
        api_url_for(
            server,
            'stakingresource',
        ),
        json={
            'ascending': [False],
            'async_query': False,
            'limit': 10,
            'offset': 0,
            'only_cache': True,
            'order_by_attributes': ['random_column'],
        },
    )
    assert_error_response(
        response=response,
        contained_in_msg='Database query error retrieving missing prices no such column',
        status_code=HTTPStatus.CONFLICT,
    )

    # test that the event_type filter for order attribute
    response = requests.post(
        api_url_for(
            server,
            'stakingresource',
        ),
        json={
            'ascending': [False],
            'async_query': False,
            'limit': 10,
            'offset': 0,
            'only_cache': True,
            'order_by_attributes': ['event_type'],
        },
    )
    assert_proper_sync_response_with_result(response)

    _, without_eth2_staking_report_result, _ = query_api_create_and_get_report(
        server=rotkehlchen_api_server_with_exchanges,
        start_ts=0,
        end_ts=1640493377,
        prepare_mocks=False,
    )
    without_eth2_staking_overview = without_eth2_staking_report_result['entries'][0]['overview']
    assert FVal('39102.819423433620').is_close(
        FVal(without_eth2_staking_overview.get(str(AccountingEventType.STAKING))['taxable']),
    )
    with rotki.data.db.user_write() as cursor:
        rotki.data.db.set_settings(
            cursor,
            ModifiableDBSettings(eth_staking_taxable_after_withdrawal_enabled=True),
        )
    _, with_eth2_staking_report_result, _ = query_api_create_and_get_report(
        server=rotkehlchen_api_server_with_exchanges,
        start_ts=0,
        end_ts=1640493377,
        prepare_mocks=False,
    )
    with_eth2_staking_overview = with_eth2_staking_report_result['entries'][0]['overview']
    assert FVal('0.000069900000').is_close(
        FVal(with_eth2_staking_overview.get(str(AccountingEventType.STAKING))['taxable']),
    )


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_kraken_event_serialization_with_custom_asset(database):
    """Regression test for https://github.com/rotki/rotki/issues/9200"""
    custom_asset = CustomAsset.initialize(
        identifier=str(uuid4()),
        name='Gold Bar',
        custom_asset_type='inheritance',
    )
    DBCustomAssets(database).add_custom_asset(custom_asset)

    swap_events = create_swap_events(
        timestamp=TimestampMS(10000000000),
        location=Location.KRAKEN,
        spend=AssetAmount(asset=custom_asset, amount=ONE),
        receive=AssetAmount(asset=custom_asset, amount=ONE),
        fee=AssetAmount(asset=custom_asset, amount=ONE),
        event_identifier=create_event_identifier_from_unique_id(
            location=Location.KRAKEN,
            unique_id='UNIQUE_ID',
        ),
    )
    for idx, expected_notes in enumerate((
        'Swap 1 Gold Bar in Kraken',
        'Receive 1 Gold Bar after a swap in Kraken',
        'Spend 1 Gold Bar as Kraken swap fee',
    )):
        assert swap_events[idx].serialize()['auto_notes'] == expected_notes

    for event_type in {HistoryEventType.DEPOSIT, HistoryEventType.WITHDRAWAL}:
        asset_movements = create_asset_movement_with_fee(
            timestamp=TimestampMS(10000000000),
            location=Location.KRAKEN,
            event_type=event_type,
            asset=custom_asset,
            amount=ONE,
            fee=AssetAmount(asset=custom_asset, amount=ONE),
        )
        if event_type == HistoryEventType.DEPOSIT:
            assert asset_movements[0].serialize()['auto_notes'] == 'Deposit 1 Gold Bar to Kraken'
        else:
            assert asset_movements[0].serialize()['auto_notes'] == 'Withdraw 1 Gold Bar from Kraken'  # noqa: E501
        assert asset_movements[1].serialize()['auto_notes'] == f'Pay 1 Gold Bar as Kraken {event_type.name.lower()} fee'  # noqa: E501

    for event_type, event_subtype, expected_notes in (
            (HistoryEventType.STAKING, HistoryEventSubType.REWARD, 'Gain 1 Gold Bar from Kraken staking'),  # noqa: E501
            (HistoryEventType.STAKING, HistoryEventSubType.FEE, 'Spend 1 Gold Bar as Kraken staking fee'),  # noqa: E501
    ):
        event = HistoryEvent(
            event_identifier='foo',
            sequence_index=1,
            timestamp=TimestampMS(10000000000),
            location=Location.KRAKEN,
            event_type=event_type,
            event_subtype=event_subtype,
            asset=custom_asset,
            amount=ONE,
            location_label='my kraken',
        )
        assert event.serialize()['auto_notes'] == expected_notes


@pytest.mark.parametrize('have_decoders', [True])
@pytest.mark.parametrize('added_exchanges', [(Location.KRAKEN,)])
def test_margin_trading_events(rotkehlchen_api_server_with_exchanges: 'APIServer'):
    """Test that we correctly handle margin trade events"""
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    with _patch_ledger(
        kraken=(kraken := cast('MockKraken', try_get_first_exchange(rotki.exchange_manager, Location.KRAKEN))),  # noqa: E501
        ledger_data="""{"ledger":{"x1": {
            "aclass": "currency",
            "amount": "1.0000",
            "asset": "ZEUR",
            "balance": "25",
            "fee": "0.0710",
            "refid": "xyz1",
            "time": 1636738100.0000,
            "type": "margin",
            "subtype": ""
        }, "x2": {
            "aclass": "currency",
            "amount": "0.0000000000",
            "asset": "XETH",
            "balance": "1.2345",
            "fee": "0.0003987600",
            "refid": "xyz2",
            "time": 1636738200.0000,
            "type": "rollover",
            "subtype": ""
        }, "x3": {
            "aclass": "currency",
            "amount": "-0.123",
            "asset": "XETH",
            "balance": "1.1115",
            "fee": "0.0710",
            "refid": "xyz3",
            "time": 1636738300.0000,
            "type": "settled",
            "subtype": ""
        }},
        "count": 3}""",
    ):
        kraken.query_history_events()

    with rotki.data.db.conn.read_ctx() as cursor:
        events = DBHistoryEvents(rotki.data.db).get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
            group_by_event_ids=False,
        )

    assert events == [HistoryEvent(
        identifier=1,
        event_identifier='xyz1',
        sequence_index=0,
        timestamp=TimestampMS(1636738100000),
        location=Location.KRAKEN,
        event_type=HistoryEventType.MARGIN,
        event_subtype=HistoryEventSubType.PROFIT,
        asset=A_EUR,
        amount=FVal('1.0000'),
        location_label='mockkraken',
        notes='Margin trade',
    ), HistoryEvent(
        identifier=2,
        event_identifier='xyz1',
        sequence_index=1,
        timestamp=TimestampMS(1636738100000),
        location=Location.KRAKEN,
        event_type=HistoryEventType.MARGIN,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_EUR,
        amount=FVal('0.0710'),
        location_label='mockkraken',
        notes='Margin trade',
    ), HistoryEvent(
        identifier=3,
        event_identifier='xyz2',
        sequence_index=1,
        timestamp=TimestampMS(1636738200000),
        location=Location.KRAKEN,
        event_type=HistoryEventType.MARGIN,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal('0.0003987600'),
        location_label='mockkraken',
        notes='Margin rollover',
    ), HistoryEvent(
        identifier=4,
        event_identifier='xyz3',
        sequence_index=0,
        timestamp=TimestampMS(1636738300000),
        location=Location.KRAKEN,
        event_type=HistoryEventType.MARGIN,
        event_subtype=HistoryEventSubType.LOSS,
        asset=A_ETH,
        amount=FVal('0.123'),
        location_label='mockkraken',
        notes='Margin settlement',
    ), HistoryEvent(
        identifier=5,
        event_identifier='xyz3',
        sequence_index=1,
        timestamp=TimestampMS(1636738300000),
        location=Location.KRAKEN,
        event_type=HistoryEventType.MARGIN,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal('0.0710'),
        location_label='mockkraken',
        notes='Margin settlement',
    )]
