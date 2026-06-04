import json
import warnings as test_warnings
from collections.abc import Callable
from http import HTTPStatus
from typing import Any
from unittest.mock import Mock, patch

import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.converters import asset_from_gate
from rotkehlchen.constants.assets import A_BTC, A_ETH, A_USDT
from rotkehlchen.constants.timing import DAY_IN_SECONDS
from rotkehlchen.db.constants import GATE_LOCATION_KEY
from rotkehlchen.db.ranges import DBQueryRanges
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.exchanges.gate import (
    GATE_BASE_URL,
    GATE_MAX_MOVEMENT_WINDOW,
    GATE_MOVEMENTS_PAGINATION_LIMIT,
    GATE_MOVEMENTS_QUERY_START_TS,
    Gate,
    GateLocation,
)
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.swap import SwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.history.events.utils import create_group_identifier_from_unique_id
from rotkehlchen.types import Location, Timestamp, TimestampMS
from rotkehlchen.utils.misc import ts_now


def test_gate_location_urls(gate_exchange: Gate) -> None:
    assert gate_exchange.uri == GATE_BASE_URL

    gate_exchange.edit_exchange_extras({GATE_LOCATION_KEY: GateLocation.EUROPE})
    assert gate_exchange.uri == 'https://api.gateeu.com/api/v4'

    gate_exchange.edit_exchange_extras({GATE_LOCATION_KEY: GateLocation.US})
    assert gate_exchange.uri == 'https://api.gate.us/api/v4'


def test_gate_signature_uses_full_api_path(gate_exchange: Gate) -> None:
    response = Mock()
    response.status_code = HTTPStatus.OK
    response.text = '[]'

    with patch.object(gate_exchange.session, 'request', return_value=response), \
            patch.object(gate_exchange, '_generate_signature', wraps=gate_exchange._generate_signature) as generate_signature:  # noqa: E501
        gate_exchange._api_query('/spot/accounts')

    assert generate_signature.call_args.kwargs['url_path'] == '/api/v4/spot/accounts'


def test_gate_deposit_withdrawal_queries_use_30_day_windows(gate_exchange: Gate) -> None:
    calls = []

    def mock_api_query(path: str, options: dict[str, Any] | None = None) -> list:
        calls.append((path, options))
        return []

    with patch.object(gate_exchange, '_api_query', side_effect=mock_api_query):
        gate_exchange._query_deposits_withdrawals(
            start_ts=Timestamp(ts_now() - 31 * 24 * 60 * 60),
            end_ts=Timestamp(ts_now()),
            query_for=HistoryEventType.DEPOSIT,
        )

    assert len(calls) == 2
    assert all(call[0] == '/wallet/deposits' for call in calls)
    assert all(call[1] is not None and call[1]['to'] - call[1]['from'] <= 30 * 24 * 60 * 60 for call in calls)  # noqa: E501


def test_gate_deposit_withdrawal_queries_handle_pagination(gate_exchange: Gate) -> None:
    calls = []

    def mock_api_query(path: str, options: dict[str, Any] | None = None) -> list:
        calls.append((path, options))
        if len(calls) == 1:
            return [{} for _ in range(GATE_MOVEMENTS_PAGINATION_LIMIT)]
        return []

    with patch.object(gate_exchange, '_api_query', side_effect=mock_api_query):
        gate_exchange._query_deposits_withdrawals(
            start_ts=Timestamp(ts_now() - 24 * 60 * 60),
            end_ts=Timestamp(ts_now()),
            query_for=HistoryEventType.DEPOSIT,
        )

    assert len(calls) == 2
    assert calls[0][1] is not None and calls[0][1]['offset'] == 0
    assert calls[1][1] is not None and calls[1][1]['offset'] == GATE_MOVEMENTS_PAGINATION_LIMIT


def test_gate_history_query_commits_30_day_chunks(gate_exchange: Gate) -> None:
    query_end = Timestamp(GATE_MOVEMENTS_QUERY_START_TS + 2 * GATE_MAX_MOVEMENT_WINDOW + DAY_IN_SECONDS)  # noqa: E501
    calls = []

    def mock_query_online_history_events(
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> tuple[list, Timestamp]:
        calls.append((start_ts, end_ts))
        return [], end_ts

    with patch('rotkehlchen.exchanges.gate.ts_now', return_value=query_end), \
            patch.object(gate_exchange, 'query_online_history_events', side_effect=mock_query_online_history_events):  # noqa: E501
        gate_exchange.query_history_events()

    assert calls == [
        (GATE_MOVEMENTS_QUERY_START_TS, Timestamp(GATE_MOVEMENTS_QUERY_START_TS + GATE_MAX_MOVEMENT_WINDOW)),  # noqa: E501
        (Timestamp(GATE_MOVEMENTS_QUERY_START_TS + GATE_MAX_MOVEMENT_WINDOW), Timestamp(GATE_MOVEMENTS_QUERY_START_TS + 2 * GATE_MAX_MOVEMENT_WINDOW)),  # noqa: E501
        (Timestamp(GATE_MOVEMENTS_QUERY_START_TS + 2 * GATE_MAX_MOVEMENT_WINDOW), query_end),
    ]

    with gate_exchange.db.conn.read_ctx() as cursor:
        ranges_to_query = DBQueryRanges(gate_exchange.db).get_location_query_ranges(
            cursor=cursor,
            location_string=f'{gate_exchange.location!s}_history_events_{gate_exchange.name}',
            start_ts=GATE_MOVEMENTS_QUERY_START_TS,
            end_ts=query_end,
        )
    assert ranges_to_query == []


def gate_account_mock(
        calls: dict[str, list[tuple[dict[str, Any] | None, Any]]],
) -> Callable[[str, dict[str, Any] | None], Any]:
    """
    Mock call to the Gate API.
    - calls is a map of a path to a list of (options, response) tuples consumed in order.
    """
    iterators = {key: iter(val) for key, val in calls.items()}

    def _mock_api_query(path: str, options: dict[str, Any] | None = None) -> Any:  # pylint: disable=unused-argument
        return next(iterators.get(path, iter([(None, {})])))[1]

    return _mock_api_query


@pytest.mark.parametrize('should_mock_current_price_queries', [True])
def test_query_balances(gate_exchange: Gate):
    balance_response = [
        {'currency': 'BTC', 'available': '1.5', 'locked': '0.5'},
        {'currency': 'ETH', 'available': '2.0', 'locked': '0'},
        {'currency': 'USDT', 'available': '100.0', 'locked': '50.0'},
        {'currency': 'UNKNOWN', 'available': '0.0', 'locked': '0.0'},
    ]

    mock_fn = gate_account_mock(calls={
        '/spot/accounts': [(None, balance_response)],
    })
    with patch.object(gate_exchange, '_api_query', side_effect=mock_fn):
        balances, _ = gate_exchange.query_balances()

    assert balances == {
        A_BTC: Balance(amount=FVal('2.0'), value=FVal('3.0')),
        A_ETH: Balance(amount=FVal('2.0'), value=FVal('3.0')),
        A_USDT: Balance(amount=FVal('150.0'), value=FVal('225.0')),
    }


def test_validate_api_key(gate_exchange: Gate):
    mock_fn = gate_account_mock(calls={
        '/spot/accounts': [(None, [{'currency': 'BTC', 'available': '1.0', 'locked': '0.0'}])],
    })
    with patch.object(gate_exchange, '_api_query', side_effect=mock_fn):
        result, msg = gate_exchange.validate_api_key()

    assert result is True
    assert msg == ''


def test_assets_are_known(gate_exchange: Gate):
    mock_fn = gate_account_mock(calls={
        '/spot/accounts': [(None, [])],
    })
    with patch.object(gate_exchange, '_api_query', side_effect=mock_fn):
        # We can't easily query all currencies from Gate without a public endpoint,
        # so we'll just validate the asset_from_gate function works for common symbols
        for symbol in ('BTC', 'ETH', 'USDT', 'GT', 'POINT'):
            try:
                asset_from_gate(symbol)
            except UnknownAsset as e:
                test_warnings.warn(UserWarning(
                    f'Found unknown asset {e.identifier} in Gate. '
                    f'Support for it has to be added',
                ))


def test_deposit_withdrawals(gate_exchange: Gate) -> None:
    """Test that withdrawals and deposits get correctly processed"""
    mock_fn = gate_account_mock(calls={
        '/wallet/deposits': [(
            None,
            json.loads('[{"id": "d123", "currency": "USDT", "address": "0x4838B106FCe9647Bdf1E7877BF73cE8B0BAD5f97", "amount": "100", "txid": "0xabc", "timestamp": "1626345819", "status": "DONE", "memo": ""}, {"id": "d124", "currency": "ETH", "address": "0x4838B106FCe9647Bdf1E7877BF73cE8B0BAD5f97", "amount": "5.5", "txid": "0xdef", "timestamp": "1626345900", "status": "DONE", "memo": ""}]'),  # noqa: E501
        )],
        '/wallet/withdrawals': [(
            None,
            json.loads('[{"id": "w456", "timestamp": "1626346000", "currency": "BTC", "address": "bc1abc", "txid": "tx123", "amount": "0.5", "fee": "0.0001", "memo": "", "status": "DONE"}]'),  # noqa: E501
        )],
        '/spot/my_trades': [(None, [])],
    })
    with patch.object(gate_exchange, '_api_query', side_effect=mock_fn):
        movements, _ = gate_exchange.query_online_history_events(
            start_ts=Timestamp(1626345000),
            end_ts=Timestamp(1626347000),
        )

    assert movements == [
        AssetMovement(
            location=Location.GATE,
            location_label=gate_exchange.name,
            event_subtype=HistoryEventSubType.RECEIVE,
            timestamp=TimestampMS(1626345819000),
            asset=A_USDT,
            amount=FVal('100'),
            unique_id='d123',
            extra_data={
                'address': '0x4838B106FCe9647Bdf1E7877BF73cE8B0BAD5f97',
                'transaction_id': '0xabc',
            },
        ), AssetMovement(
            location=Location.GATE,
            location_label=gate_exchange.name,
            event_subtype=HistoryEventSubType.RECEIVE,
            timestamp=TimestampMS(1626345900000),
            asset=A_ETH,
            amount=FVal('5.5'),
            unique_id='d124',
            extra_data={
                'address': '0x4838B106FCe9647Bdf1E7877BF73cE8B0BAD5f97',
                'transaction_id': '0xdef',
            },
        ), AssetMovement(
            location=Location.GATE,
            location_label=gate_exchange.name,
            event_subtype=HistoryEventSubType.SPEND,
            timestamp=TimestampMS(1626346000000),
            asset=A_BTC,
            amount=FVal('0.5'),
            unique_id='w456',
            extra_data={
                'address': 'bc1abc',
                'transaction_id': 'tx123',
            },
        ), AssetMovement(
            location=Location.GATE,
            location_label=gate_exchange.name,
            event_subtype=HistoryEventSubType.FEE,
            timestamp=TimestampMS(1626346000000),
            asset=A_BTC,
            amount=FVal('0.0001'),
            unique_id='w456',
        ),
    ]


@pytest.mark.freeze_time('2024-03-12 00:00:00 GMT')
def test_trades(gate_exchange: Gate) -> None:
    mock_fn = gate_account_mock(calls={
        '/wallet/deposits': [(None, [])],
        '/wallet/withdrawals': [(None, [])],
        '/spot/my_trades': [(
            None,
            json.loads('[{"id": "2876130500", "create_time": "1645464610", "create_time_ms": "1645464610777.399200", "currency_pair": "BTC_USDT", "side": "buy", "amount": "0.1", "price": "40000", "order_id": "125924049993", "fee": "0.5", "fee_currency": "USDT", "point_fee": "0", "gt_fee": "0"}, {"id": "2876130501", "create_time": "1645464620", "create_time_ms": "1645464620777.399200", "currency_pair": "ETH_USDT", "side": "sell", "amount": "2.0", "price": "3000", "order_id": "125924049994", "fee": "0.01", "fee_currency": "ETH", "point_fee": "0", "gt_fee": "0"}]'),  # noqa: E501
        )],
    })
    with patch.object(gate_exchange, '_api_query', side_effect=mock_fn):
        events, _ = gate_exchange.query_online_history_events(
            start_ts=Timestamp(1645464000),
            end_ts=Timestamp(1645465000),
        )

    group_id_1 = create_group_identifier_from_unique_id(
        location=Location.GATE,
        unique_id='2876130500',
    )
    group_id_2 = create_group_identifier_from_unique_id(
        location=Location.GATE,
        unique_id='2876130501',
    )
    assert events == [SwapEvent(
        timestamp=TimestampMS(1645464610777),
        location=Location.GATE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_USDT,
        amount=FVal('4000'),
        location_label='gate',
        group_identifier=group_id_1,
    ), SwapEvent(
        timestamp=TimestampMS(1645464610777),
        location=Location.GATE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_BTC,
        amount=FVal('0.1'),
        location_label='gate',
        group_identifier=group_id_1,
    ), SwapEvent(
        timestamp=TimestampMS(1645464610777),
        location=Location.GATE,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_USDT,
        amount=FVal('0.5'),
        location_label='gate',
        group_identifier=group_id_1,
        sequence_index=2,
    ), SwapEvent(
        timestamp=TimestampMS(1645464620777),
        location=Location.GATE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_ETH,
        amount=FVal('2.0'),
        location_label='gate',
        group_identifier=group_id_2,
    ), SwapEvent(
        timestamp=TimestampMS(1645464620777),
        location=Location.GATE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_USDT,
        amount=FVal('6000'),
        location_label='gate',
        group_identifier=group_id_2,
    ), SwapEvent(
        timestamp=TimestampMS(1645464620777),
        location=Location.GATE,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal('0.01'),
        location_label='gate',
        group_identifier=group_id_2,
        sequence_index=2,
    )]


def test_trades_pagination(gate_exchange: Gate) -> None:
    """Test that trade pagination stops when fewer results than limit are returned"""
    mock_fn = gate_account_mock(calls={
        '/wallet/deposits': [(None, [])],
        '/wallet/withdrawals': [(None, [])],
        '/spot/my_trades': [
            (
                None,
                json.loads('[{"id": "1", "create_time": "1645464610", "create_time_ms": "1645464610777.399200", "currency_pair": "BTC_USDT", "side": "buy", "amount": "0.1", "price": "40000", "order_id": "1", "fee": "0", "fee_currency": "USDT", "point_fee": "0", "gt_fee": "0"}]'),  # noqa: E501
            ),
        ],
    })
    with patch.object(gate_exchange, '_api_query', side_effect=mock_fn):
        events, _ = gate_exchange.query_online_history_events(
            start_ts=Timestamp(1645464000),
            end_ts=Timestamp(1645465000),
        )

    assert len(events) == 2  # spend + receive
