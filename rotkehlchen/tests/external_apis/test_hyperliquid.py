from typing import Any

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.externalapis import hyperliquid as hyperliquid_module
from rotkehlchen.externalapis.hyperliquid import HyperliquidAPI
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.swap import SwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import Location, Timestamp

DEAD_ADDRESS = string_to_evm_address('0x000000000000000000000000000000000000dEaD')


def test_hyperliquid_perp_history_mapping(monkeypatch) -> None:
    api = HyperliquidAPI()
    address = string_to_evm_address('0x000000000000000000000000000000000000dEaD')

    def fake_asset_from_hyperliquid(symbol: str) -> Asset:
        return Asset('USDC') if symbol == 'USDC' else Asset('BTC')

    def fake_post_info(payload: dict[str, Any]) -> Any:
        match payload['type']:
            case 'userNonFundingLedgerUpdates':
                return [
                    {
                        'time': 1700000000000,
                        'hash': '0xledger',
                        'delta': {'type': 'deposit', 'usdc': '10', 'coin': 'USDC'},
                    },
                ]
            case 'userFunding':
                return [
                    {
                        'time': 1700000001000,
                        'hash': '0xfund',
                        'delta': {'type': 'funding', 'usdc': '-1'},
                    },
                ]
            case 'userFillsByTime':
                return [
                    {
                        'time': 1700000002000,
                        'hash': '0xfill',
                        'coin': 'BTC',
                        'px': '100',
                        'sz': '2',
                        'side': 'B',
                        'dir': 'Open Long',
                        'fee': '0.5',
                        'feeToken': 'USDC',
                    },
                ]
            case 'spotMeta':
                return {'tokens': []}
            case _:
                return []

    monkeypatch.setattr(hyperliquid_module, 'asset_from_hyperliquid', fake_asset_from_hyperliquid)
    monkeypatch.setattr(api, '_post_info', fake_post_info)

    events = api.query_history_events(
        address=address,
        start_ts=Timestamp(0),
        end_ts=Timestamp(1700000003),
    )

    deposits = [event for event in events if isinstance(event, AssetMovement)]
    trade_events = [
        event
        for event in events
        if isinstance(event, HistoryEvent) and event.event_type == HistoryEventType.TRADE
    ]
    funding_events = [
        event
        for event in events
        if isinstance(event, HistoryEvent)
        and event.event_type == HistoryEventType.SPEND
        and event.event_subtype == HistoryEventSubType.NONE
    ]

    assert len(deposits) == 1
    assert deposits[0].event_type == HistoryEventType.EXCHANGE_TRANSFER
    assert deposits[0].event_subtype == HistoryEventSubType.RECEIVE
    assert str(deposits[0].amount) == '10'

    assert len(trade_events) == 3
    assert {event.event_subtype for event in trade_events} == {
        HistoryEventSubType.SPEND,
        HistoryEventSubType.RECEIVE,
        HistoryEventSubType.FEE,
    }

    assert len(funding_events) == 1


def test_hyperliquid_spot_fills_paginate(monkeypatch) -> None:
    api = HyperliquidAPI()
    address = string_to_evm_address('0x000000000000000000000000000000000000dEaD')
    requested_end_times: list[int] = []

    def fake_asset_from_hyperliquid(symbol: str) -> Asset:
        if symbol == 'USDC':
            return Asset('USDC')
        return Asset('BTC')

    def fake_post_info(payload: dict[str, Any]) -> Any:
        payload_type = payload['type']
        if payload_type in {'userNonFundingLedgerUpdates', 'userFunding'}:
            return []
        if payload_type == 'spotMeta':
            return {
                'tokens': [
                    {'index': 0, 'name': 'USDC'},
                    {'index': 1, 'name': 'BTC'},
                ],
                'universe': [
                    {'index': 1, 'tokens': [1, 0], 'name': 'BTC/USDC'},
                ],
            }
        if payload_type == 'userFillsByTime':
            end_time = int(payload['endTime'])
            requested_end_times.append(end_time)
            if end_time >= 1700000002000:
                return [
                    {
                        'time': 1700000002000,
                        'hash': '0xfill1',
                        'coin': '@1',
                        'px': '100',
                        'sz': '1',
                        'side': 'B',
                        'fee': '0.1',
                        'feeToken': 'USDC',
                    },
                ]

            if end_time >= 1700000001000:
                return [
                    {
                        'time': 1700000001000,
                        'hash': '0xfill2',
                        'coin': '@1',
                        'px': '110',
                        'sz': '1',
                        'side': 'S',
                        'fee': '0.1',
                        'feeToken': 'USDC',
                    },
                ]
        return []

    monkeypatch.setattr(hyperliquid_module, 'asset_from_hyperliquid', fake_asset_from_hyperliquid)
    monkeypatch.setattr(api, '_post_info', fake_post_info)

    events = api.query_history_events(
        address=address,
        start_ts=Timestamp(0),
        end_ts=Timestamp(1700000003),
    )
    swaps = [event for event in events if isinstance(event, SwapEvent)]
    assert len(swaps) == 6  # 2 spot fills -> spend/receive/fee
    assert len(requested_end_times) >= 2


def test_hyperliquid_query_history_raises_on_failed_endpoint(monkeypatch) -> None:
    api = HyperliquidAPI()
    address = string_to_evm_address('0x000000000000000000000000000000000000dEaD')

    def fake_post_info(payload: dict[str, Any]) -> Any:
        if payload['type'] == 'userFunding':
            raise RemoteError('boom')
        return []

    monkeypatch.setattr(api, '_post_info', fake_post_info)

    with pytest.raises(RemoteError):
        api.query_history_events(
            address=address,
            start_ts=Timestamp(0),
            end_ts=Timestamp(2),
        )


def test_hyperliquid_query_balances(monkeypatch) -> None:
    """Test that both spot and perp balances are queried and aggregated correctly."""
    api = HyperliquidAPI()

    def fake_asset_from_hyperliquid(symbol: str) -> Asset:
        return Asset('USDC') if symbol == 'USDC' else Asset('ETH')

    def fake_post_info(payload: dict[str, Any]) -> Any:
        if payload['type'] == 'spotClearinghouseState':
            return {
                'balances': [
                    {'coin': 'USDC', 'total': '500.5'},
                    {'coin': 'ETH', 'total': '2.0'},
                    {'coin': 'USDC', 'total': '0'},  # zero balance should be skipped
                ],
            }
        if payload['type'] == 'clearinghouseState':
            return {
                'crossMarginSummary': {'accountValue': '1000.25'},
            }
        return {}

    monkeypatch.setattr(hyperliquid_module, 'asset_from_hyperliquid', fake_asset_from_hyperliquid)
    monkeypatch.setattr(api, '_post_info', fake_post_info)
    balances = api.query_balances(address=DEAD_ADDRESS)

    assert balances[Asset('ETH')] == FVal('2.0')
    # spot USDC (500.5) should exist, plus perp account value (1000.25) on arb_usdc
    assert balances[Asset('USDC')] == FVal('500.5')
    assert balances[api.arb_usdc] == FVal('1000.25')


def test_hyperliquid_query_balances_handles_spot_failure(monkeypatch) -> None:
    """When the spot endpoint fails, perp balances should still be returned."""
    api = HyperliquidAPI()
    call_count = 0

    def fake_post_info(payload: dict[str, Any]) -> Any:
        nonlocal call_count
        call_count += 1
        if payload['type'] == 'spotClearinghouseState':
            raise RemoteError('spot endpoint down')
        if payload['type'] == 'clearinghouseState':
            return {'crossMarginSummary': {'accountValue': '100'}}
        return {}

    monkeypatch.setattr(api, '_post_info', fake_post_info)
    balances = api.query_balances(address=DEAD_ADDRESS)

    assert balances[api.arb_usdc] == FVal('100')
    assert call_count == 2  # both endpoints called


def test_hyperliquid_query_balances_handles_malformed_spot_response(monkeypatch) -> None:
    """When spot response shape is invalid, perp balances should still be returned."""
    api = HyperliquidAPI()

    def fake_post_info(payload: dict[str, Any]) -> Any:
        if payload['type'] == 'spotClearinghouseState':
            return []
        if payload['type'] == 'clearinghouseState':
            return {'crossMarginSummary': {'accountValue': '100'}}
        return {}

    monkeypatch.setattr(api, '_post_info', fake_post_info)
    balances = api.query_balances(address=DEAD_ADDRESS)

    assert balances[api.arb_usdc] == FVal('100')


def test_hyperliquid_ledger_withdraw_and_transfer(monkeypatch) -> None:
    """Test that withdrawals and internal transfers produce correct event types."""
    api = HyperliquidAPI()

    def fake_asset(symbol: str) -> Asset:
        return Asset('USDC')

    def fake_post_info(payload: dict[str, Any]) -> Any:
        if payload['type'] == 'userNonFundingLedgerUpdates':
            return [
                {
                    'time': 1700000000000,
                    'hash': '0xwithdraw1',
                    'delta': {'type': 'withdraw', 'usdc': '-500', 'coin': 'USDC'},
                },
                {
                    'time': 1700000001000,
                    'hash': '0xtransfer1',
                    'delta': {'type': 'accountClassTransfer', 'usdc': '100', 'coin': 'USDC'},
                },
                {
                    'time': 1700000002000,
                    'hash': '0xliq1',
                    'delta': {'type': 'liquidation', 'usdc': '-200', 'coin': 'USDC'},
                },
            ]
        return []

    monkeypatch.setattr(hyperliquid_module, 'asset_from_hyperliquid', fake_asset)
    monkeypatch.setattr(api, '_post_info', fake_post_info)

    events = api._create_ledger_events(
        address=DEAD_ADDRESS,
        start_ts=Timestamp(0),
        end_ts=Timestamp(1700000003),
    )

    assert len(events) == 3
    # withdrawal
    assert isinstance(events[0], AssetMovement)
    assert events[0].event_subtype == HistoryEventSubType.SPEND
    assert events[0].amount == FVal('500')
    # transfer
    assert isinstance(events[1], HistoryEvent)
    assert events[1].event_type == HistoryEventType.TRANSFER
    assert events[1].amount == FVal('100')
    # liquidation
    assert isinstance(events[2], HistoryEvent)
    assert events[2].event_type == HistoryEventType.LOSS
    assert events[2].event_subtype == HistoryEventSubType.LIQUIDATE
    assert events[2].amount == FVal('200')


def test_hyperliquid_funding_positive_and_negative(monkeypatch) -> None:
    """Positive funding = RECEIVE/INTEREST, negative = SPEND/NONE."""
    api = HyperliquidAPI()

    def fake_asset(symbol: str) -> Asset:
        return Asset('USDC')

    def fake_post_info(payload: dict[str, Any]) -> Any:
        if payload['type'] == 'userFunding':
            return [
                {
                    'time': 1700000000000,
                    'hash': '0xpos',
                    'delta': {'usdc': '5.5'},
                },
                {
                    'time': 1700000001000,
                    'hash': '0xneg',
                    'delta': {'usdc': '-3.2'},
                },
                {
                    'time': 1700000002000,
                    'hash': '0xzero',
                    'delta': {'usdc': '0'},
                },
            ]
        return []

    monkeypatch.setattr(hyperliquid_module, 'asset_from_hyperliquid', fake_asset)
    monkeypatch.setattr(api, '_post_info', fake_post_info)

    events = api._create_funding_events(
        address=DEAD_ADDRESS,
        start_ts=Timestamp(0),
        end_ts=Timestamp(1700000003),
    )

    assert len(events) == 2  # zero-amount entry skipped
    # positive
    assert events[0].event_type == HistoryEventType.RECEIVE
    assert events[0].event_subtype == HistoryEventSubType.INTEREST
    assert events[0].amount == FVal('5.5')
    assert events[0].location == Location.HYPERLIQUID
    # negative
    assert events[1].event_type == HistoryEventType.SPEND
    assert events[1].event_subtype == HistoryEventSubType.NONE
    assert events[1].amount == FVal('3.2')


def test_hyperliquid_perp_fill_sell(monkeypatch) -> None:
    """Sell side perp fill should reverse spend/receive assets."""
    api = HyperliquidAPI()

    def fake_asset(symbol: str) -> Asset:
        return Asset('USDC') if symbol == 'USDC' else Asset('ETH')

    def fake_post_info(payload: dict[str, Any]) -> Any:
        if payload['type'] == 'userFillsByTime':
            return [
                {
                    'time': 1700000000000,
                    'hash': '0xsell1',
                    'coin': 'ETH',
                    'px': '2000',
                    'sz': '1.5',
                    'side': 'S',
                    'dir': 'Close Long',
                    'fee': '1.0',
                    'feeToken': 'USDC',
                    'closedPnl': '50.0',
                },
            ]
        return []

    monkeypatch.setattr(hyperliquid_module, 'asset_from_hyperliquid', fake_asset)
    monkeypatch.setattr(api, '_post_info', fake_post_info)

    events = api._create_fill_events(
        address=DEAD_ADDRESS,
        start_ts=Timestamp(0),
        end_ts=Timestamp(1700000001),
    )

    assert len(events) == 3  # spend + receive + fee
    spend = events[0]
    receive = events[1]
    fee = events[2]
    # sell: spend base (ETH), receive quote (USDC)
    assert spend.asset == Asset('ETH')
    assert spend.amount == FVal('1.5')
    assert receive.asset == Asset('USDC')
    assert receive.amount == FVal('3000')  # 2000 * 1.5
    assert fee.amount == FVal('1.0')
    # check extra_data includes closed_pnl
    assert spend.extra_data is not None
    assert spend.extra_data['closed_pnl'] == '50.0'
    assert spend.extra_data['direction'] == 'Close Long'


def test_hyperliquid_fill_zero_size_skipped(monkeypatch) -> None:
    """Fills with zero size should be silently skipped."""
    api = HyperliquidAPI()

    def fake_asset(symbol: str) -> Asset:
        return Asset('USDC')

    def fake_post_info(payload: dict[str, Any]) -> Any:
        if payload['type'] == 'userFillsByTime':
            return [
                {
                    'time': 1700000000000,
                    'hash': '0xzero',
                    'coin': 'BTC',
                    'px': '50000',
                    'sz': '0',
                    'side': 'B',
                    'fee': '0',
                    'feeToken': 'USDC',
                },
            ]
        return []

    monkeypatch.setattr(hyperliquid_module, 'asset_from_hyperliquid', fake_asset)
    monkeypatch.setattr(api, '_post_info', fake_post_info)

    events = api._create_fill_events(
        address=DEAD_ADDRESS,
        start_ts=Timestamp(0),
        end_ts=Timestamp(1700000001),
    )
    assert len(events) == 0


def test_hyperliquid_perp_fill_no_fee(monkeypatch) -> None:
    """Perp fill with zero fee should not produce a fee event."""
    api = HyperliquidAPI()

    def fake_asset(symbol: str) -> Asset:
        return Asset('USDC') if symbol == 'USDC' else Asset('BTC')

    def fake_post_info(payload: dict[str, Any]) -> Any:
        if payload['type'] == 'userFillsByTime':
            return [
                {
                    'time': 1700000000000,
                    'hash': '0xnofee',
                    'coin': 'BTC',
                    'px': '50000',
                    'sz': '0.1',
                    'side': 'B',
                    'dir': 'Open Long',
                    'fee': '0',
                    'feeToken': 'USDC',
                },
            ]
        return []

    monkeypatch.setattr(hyperliquid_module, 'asset_from_hyperliquid', fake_asset)
    monkeypatch.setattr(api, '_post_info', fake_post_info)

    events = api._create_fill_events(
        address=DEAD_ADDRESS,
        start_ts=Timestamp(0),
        end_ts=Timestamp(1700000001),
    )
    assert len(events) == 2  # spend + receive only, no fee


def test_hyperliquid_empty_history(monkeypatch) -> None:
    """All endpoints returning empty lists should produce zero events."""
    api = HyperliquidAPI()

    def fake_post_info(payload: dict[str, Any]) -> Any:
        return []

    monkeypatch.setattr(api, '_post_info', fake_post_info)

    events = api.query_history_events(
        address=DEAD_ADDRESS,
        start_ts=Timestamp(0),
        end_ts=Timestamp(100),
    )
    assert events == []


def test_hyperliquid_dedup_entries(monkeypatch) -> None:
    """Duplicate entries (same hash+time) should be deduplicated in pagination."""
    api = HyperliquidAPI()

    def fake_asset(symbol: str) -> Asset:
        return Asset('USDC')

    call_count = 0

    def fake_post_info(payload: dict[str, Any]) -> Any:
        nonlocal call_count
        if payload['type'] == 'userFunding':
            call_count += 1
            # always return the same entry to simulate duplicates
            return [
                {
                    'time': 1700000000000,
                    'hash': '0xdup',
                    'delta': {'usdc': '1'},
                },
            ]
        return []

    monkeypatch.setattr(hyperliquid_module, 'asset_from_hyperliquid', fake_asset)
    monkeypatch.setattr(api, '_post_info', fake_post_info)

    events = api._create_funding_events(
        address=DEAD_ADDRESS,
        start_ts=Timestamp(0),
        end_ts=Timestamp(1700000001),
    )
    # the same entry returned multiple pages should be deduplicated to 1
    assert len(events) == 1


def test_hyperliquid_ledger_zero_amount_skipped(monkeypatch) -> None:
    """Zero-amount ledger entries should be silently skipped."""
    api = HyperliquidAPI()

    def fake_asset(symbol: str) -> Asset:
        return Asset('USDC')

    def fake_post_info(payload: dict[str, Any]) -> Any:
        if payload['type'] == 'userNonFundingLedgerUpdates':
            return [
                {
                    'time': 1700000000000,
                    'hash': '0xzero',
                    'delta': {'type': 'deposit', 'usdc': '0', 'coin': 'USDC'},
                },
            ]
        return []

    monkeypatch.setattr(hyperliquid_module, 'asset_from_hyperliquid', fake_asset)
    monkeypatch.setattr(api, '_post_info', fake_post_info)

    events = api._create_ledger_events(
        address=DEAD_ADDRESS,
        start_ts=Timestamp(0),
        end_ts=Timestamp(1700000001),
    )
    assert len(events) == 0


def test_hyperliquid_ledger_invalid_timestamp_skipped(monkeypatch) -> None:
    api = HyperliquidAPI()

    def fake_asset(symbol: str) -> Asset:
        return Asset('USDC')

    def fake_post_info(payload: dict[str, Any]) -> Any:
        if payload['type'] == 'userNonFundingLedgerUpdates':
            return [
                {
                    'time': 'invalid-time',
                    'hash': '0xbadtime',
                    'delta': {'type': 'deposit', 'usdc': '1', 'coin': 'USDC'},
                },
                {
                    'time': 1700000000000,
                    'hash': '0xgoodtime',
                    'delta': {'type': 'deposit', 'usdc': '2', 'coin': 'USDC'},
                },
            ]
        return []

    monkeypatch.setattr(hyperliquid_module, 'asset_from_hyperliquid', fake_asset)
    monkeypatch.setattr(api, '_post_info', fake_post_info)

    events = api._create_ledger_events(
        address=DEAD_ADDRESS,
        start_ts=Timestamp(0),
        end_ts=Timestamp(1700000001),
    )
    assert len(events) == 1
    assert events[0].amount == FVal('2')


def test_hyperliquid_spot_token_resolution(monkeypatch) -> None:
    """Verify that @N spot markets resolve to the base token and are cached."""
    api = HyperliquidAPI()

    spot_meta_calls = 0

    def fake_post_info(payload: dict[str, Any]) -> Any:
        nonlocal spot_meta_calls
        if payload['type'] == 'spotMeta':
            spot_meta_calls += 1
            return {
                'tokens': [
                    {'index': 0, 'name': 'USDC'},
                    {'index': 5, 'name': 'PURR'},
                    {'index': 10, 'name': 'JEFF'},
                ],
                'universe': [
                    {'index': 100, 'tokens': [5, 0], 'name': 'PURR/USDC'},
                    {'index': 101, 'tokens': [10, 0], 'name': 'JEFF/USDC'},
                ],
            }
        return []

    monkeypatch.setattr(api, '_post_info', fake_post_info)

    assert api._resolve_fill_coin('@100') == 'PURR'
    assert api._resolve_fill_coin('@101') == 'JEFF'
    assert api._resolve_fill_coin('@99') is None  # unknown spot market id
    assert api._resolve_fill_coin('BTC') == 'BTC'  # non-@ passthrough
    assert spot_meta_calls == 1  # cached after first call


def test_hyperliquid_post_info_uses_query_retry_limit(monkeypatch) -> None:
    api = HyperliquidAPI()
    calls = 0

    class FakeResponse:
        def __init__(
                self,
                status_code: int,
                payload: Any,
                text: str = '',
                headers: dict[str, str] | None = None,
        ) -> None:
            self.status_code = status_code
            self._payload = payload
            self.text = text
            self.headers = headers if headers is not None else {}
            self.url = 'https://api.hyperliquid.xyz/info'

        def json(self) -> Any:
            return self._payload

    def fake_post(*args: Any, **kwargs: Any) -> FakeResponse:
        nonlocal calls
        calls += 1
        if calls == 1:
            return FakeResponse(status_code=429, payload={}, text='rate limited')
        return FakeResponse(status_code=200, payload={'ok': True})

    monkeypatch.setattr(
        hyperliquid_module.CachedSettings,
        'get_query_retry_limit',
        lambda _self: 2,
    )
    monkeypatch.setattr(api.session, 'post', fake_post)
    monkeypatch.setattr(hyperliquid_module.gevent, 'sleep', lambda _seconds: None)

    data = api._post_info({'type': 'meta'})
    assert data == {'ok': True}
    assert calls == 2


def test_hyperliquid_post_info_honors_retry_after_header(monkeypatch) -> None:
    api = HyperliquidAPI()
    calls = 0
    slept: list[int] = []

    class FakeResponse:
        def __init__(
                self,
                status_code: int,
                payload: Any,
                text: str = '',
                headers: dict[str, str] | None = None,
        ) -> None:
            self.status_code = status_code
            self._payload = payload
            self.text = text
            self.headers = headers if headers is not None else {}
            self.url = 'https://api.hyperliquid.xyz/info'

        def json(self) -> Any:
            return self._payload

    def fake_post(*args: Any, **kwargs: Any) -> FakeResponse:
        nonlocal calls
        calls += 1
        if calls == 1:
            return FakeResponse(status_code=429, payload={}, headers={'retry-after': '7'})
        return FakeResponse(status_code=200, payload={'ok': True})

    def fake_sleep(seconds: int) -> None:
        slept.append(seconds)

    monkeypatch.setattr(
        hyperliquid_module.CachedSettings,
        'get_query_retry_limit',
        lambda _self: 2,
    )
    monkeypatch.setattr(api.session, 'post', fake_post)
    monkeypatch.setattr(hyperliquid_module.gevent, 'sleep', fake_sleep)

    assert api._post_info({'type': 'meta'}) == {'ok': True}
    assert calls == 2
    assert slept == [7]


def test_hyperliquid_query_history_raises_on_malformed_endpoint_response(monkeypatch) -> None:
    api = HyperliquidAPI()

    def fake_post_info(payload: dict[str, Any]) -> Any:
        if payload['type'] == 'userNonFundingLedgerUpdates':
            return {'unexpected': 'shape'}
        return []

    monkeypatch.setattr(api, '_post_info', fake_post_info)

    with pytest.raises(RemoteError):
        api.query_history_events(
            address=DEAD_ADDRESS,
            start_ts=Timestamp(0),
            end_ts=Timestamp(2),
        )


def test_hyperliquid_events_sorted_by_timestamp(monkeypatch) -> None:
    """Verify that events from different sources are sorted by timestamp."""
    api = HyperliquidAPI()

    def fake_asset(symbol: str) -> Asset:
        return Asset('USDC')

    def fake_post_info(payload: dict[str, Any]) -> Any:
        match payload['type']:
            case 'userNonFundingLedgerUpdates':
                return [
                    {
                        'time': 1700000003000,
                        'hash': '0xlate',
                        'delta': {'type': 'deposit', 'usdc': '10', 'coin': 'USDC'},
                    },
                ]
            case 'userFunding':
                return [
                    {
                        'time': 1700000001000,
                        'hash': '0xearly',
                        'delta': {'usdc': '1'},
                    },
                ]
            case 'userFillsByTime':
                return []
            case _:
                return []

    monkeypatch.setattr(hyperliquid_module, 'asset_from_hyperliquid', fake_asset)
    monkeypatch.setattr(api, '_post_info', fake_post_info)

    events = api.query_history_events(
        address=DEAD_ADDRESS,
        start_ts=Timestamp(0),
        end_ts=Timestamp(1700000004),
    )
    assert len(events) == 2
    assert events[0].timestamp < events[1].timestamp
