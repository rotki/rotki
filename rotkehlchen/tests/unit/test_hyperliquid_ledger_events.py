"""Convert the Hyperliquid Core ledger entries that only exist in Core to history events.

A Core `send` moves spot tokens between two Core accounts. It never touches HyperEVM, so
there is no transaction to decode and the Core ledger is the only place it appears. It was
logged as an unknown ledger event type and dropped, which left a received USDC transfer
missing from history.
"""
import logging
from typing import TYPE_CHECKING, Any

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_HYPE
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.externalapis.hyperliquid import HyperliquidAPI
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.locations.constants import LOCATION_HYPERLIQUID
from rotkehlchen.tests.utils.hyperliquid import query_history_events
from rotkehlchen.types import Timestamp

if TYPE_CHECKING:
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry
    from rotkehlchen.types import ChecksumEvmAddress

SENDER = string_to_evm_address('0x3Ba6eB0e4327B96aDe6D4f3b578724208a590CEF')
RECIPIENT = string_to_evm_address('0x09d3e31F5dbC0Aa13fE8640BFCADe46eB882e90d')
# Hyperliquid maps its USDC to the Arbitrum one, which is the asset Core uses.
HYPERLIQUID_USDC = Asset('eip155:42161/erc20:0xaf88d065e77c8cC2239327C5EDb3A432268e5831')
# A real send of 0.001 USDC that also paid the flat 1 USDC send fee. Both accounts get the
# same entry, so the same payload is served to the sender and to the recipient.
SEND_ENTRY: dict[str, Any] = {
    'time': 1792400354348,
    'hash': '0xb4d3b1bb00bf150bb64d0446e405920203c100a09bb233dd589c5d0dbfb2eef6',
    'delta': {
        'type': 'send',
        'user': '0x3ba6eb0e4327b96ade6d4f3b578724208a590cef',
        'destination': '0x09d3e31f5dbc0aa13fe8640bfcade46eb882e90d',
        'sourceDex': 'spot',
        'destinationDex': 'spot',
        'token': 'USDC',
        'amount': '0.001',
        'usdcValue': '0.001',
        'fee': '1.0',
        'nativeTokenFee': '0.0',
        'nonce': 1792400340220,
        'feeToken': 'USDC',
    },
}


def _send_events(
        address: ChecksumEvmAddress,
        entry: dict[str, Any] = SEND_ENTRY,
        tracked_addresses: tuple[ChecksumEvmAddress, ...] = (),
) -> list[HistoryBaseEntry]:
    """Query the Core history of an account whose ledger holds only the given send."""
    def query_list(
            _api: HyperliquidAPI,
            payload: dict[str, Any],
            **_kwargs: Any,
    ) -> list[dict[str, Any]]:
        return [entry] if payload['type'] == 'userNonFundingLedgerUpdates' else []

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(HyperliquidAPI, '_query_list', query_list)
        return query_history_events(
            api=HyperliquidAPI(),
            address=address,
            start_ts=Timestamp(entry['time'] // 1000),
            end_ts=Timestamp(entry['time'] // 1000),
            tracked_addresses=tracked_addresses,
        )


def test_send_received_from_another_account(globaldb) -> None:
    """The reported case: the recipient gets the amount and does not pay the sender's fee."""
    assert [(event.event_type, event.event_subtype, event.asset, event.amount, event.notes) for event in _send_events(address=RECIPIENT)] == [  # noqa: E501
        (
            HistoryEventType.RECEIVE,
            HistoryEventSubType.NONE,
            HYPERLIQUID_USDC,
            FVal('0.001'),
            f'Hyperliquid spot send from {SENDER}',
        ),
    ]


def test_send_to_another_account_pays_the_fee(globaldb) -> None:
    """The sender spends the amount plus the flat send fee, charged in `feeToken`."""
    events = _send_events(address=SENDER)

    assert [(event.event_type, event.event_subtype, event.asset, event.amount) for event in events] == [  # noqa: E501
        (HistoryEventType.SPEND, HistoryEventSubType.NONE, HYPERLIQUID_USDC, FVal('0.001')),
        (HistoryEventType.SPEND, HistoryEventSubType.FEE, HYPERLIQUID_USDC, FVal('1')),
    ]
    assert [event.sequence_index for event in events] == [0, 1]
    assert events[0].notes == f'Hyperliquid spot send to {RECIPIENT}'
    assert events[1].notes == 'Hyperliquid spot send fee'
    assert {event.location_label for event in events} == {SENDER}
    assert {event.location for event in events} == {LOCATION_HYPERLIQUID}


def test_send_fee_paid_in_hype(globaldb) -> None:
    """The send fee can be paid in the native token instead of `feeToken`."""
    events = _send_events(
        address=SENDER,
        entry={**SEND_ENTRY, 'delta': {**SEND_ENTRY['delta'], 'fee': '0.0', 'nativeTokenFee': '0.01'}},  # noqa: E501
    )

    assert [(event.event_subtype, event.asset, event.amount) for event in events] == [
        (HistoryEventSubType.NONE, HYPERLIQUID_USDC, FVal('0.001')),
        (HistoryEventSubType.FEE, A_HYPE, FVal('0.01')),
    ]


def test_send_with_unresolvable_fee_asset_is_still_saved(globaldb, caplog) -> None:
    """A fee in an asset rotki can't resolve only drops the fee, not the send itself."""
    caplog.set_level(logging.WARNING)
    resolve_asset = HyperliquidAPI._asset_from_hyperliquid_token

    def resolve_unless_unknown(
            api: HyperliquidAPI,
            token: Any,
            prefer_spot_metadata: bool = False,
    ) -> Asset:
        if token == 'UNKNOWN':
            raise UnknownAsset('UNKNOWN')
        return resolve_asset(api, token=token, prefer_spot_metadata=prefer_spot_metadata)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(HyperliquidAPI, '_asset_from_hyperliquid_token', resolve_unless_unknown)
        events = _send_events(
            address=SENDER,
            entry={**SEND_ENTRY, 'delta': {**SEND_ENTRY['delta'], 'feeToken': 'UNKNOWN'}},
        )

    assert [(event.event_type, event.amount) for event in events] == [
        (HistoryEventType.SPEND, FVal('0.001')),
    ]
    assert 'Failed to parse the fee of hyperliquid send entry' in caplog.text


def test_send_of_an_entry_naming_another_account_is_skipped(globaldb, caplog) -> None:
    """Defensive: an entry where the queried address is neither side is skipped instead of
    being reported as a transfer of that account."""
    caplog.set_level(logging.ERROR)

    assert _send_events(address=string_to_evm_address('0x1234567890AbcdEF1234567890aBcdef12345678')) == []  # noqa: E501
    assert 'is neither from nor to' in caplog.text


def test_send_between_two_tracked_accounts_is_a_transfer_that_keeps_the_fee(globaldb) -> None:
    """When both sides are tracked the amount is a transfer on each, but the sender still
    spent the fee, so it must not be turned into part of the transfer or lost."""
    tracked = (SENDER, RECIPIENT)
    sent = _send_events(address=SENDER, tracked_addresses=tracked)
    received = _send_events(address=RECIPIENT, tracked_addresses=tracked)

    assert [(e.event_type, e.event_subtype, e.amount, e.location_label) for e in sent] == [
        (HistoryEventType.TRANSFER, HistoryEventSubType.NONE, FVal('0.001'), SENDER),
        (HistoryEventType.SPEND, HistoryEventSubType.FEE, FVal('1'), SENDER),
    ]
    assert [(e.event_type, e.event_subtype, e.amount, e.location_label) for e in received] == [
        (HistoryEventType.TRANSFER, HistoryEventSubType.NONE, FVal('0.001'), RECIPIENT),
    ]
    assert sent[0].notes == f'Hyperliquid spot send to {RECIPIENT}'
    assert received[0].notes == f'Hyperliquid spot send from {SENDER}'


def test_send_to_an_untracked_account_stays_a_spend(globaldb) -> None:
    """Only the counterparty being tracked makes it a transfer, the sender being tracked
    does not."""
    assert _send_events(address=SENDER, tracked_addresses=(SENDER,))[0].event_type == HistoryEventType.SPEND  # noqa: E501


def test_send_to_oneself_is_a_single_transfer_with_the_fee(globaldb) -> None:
    """A send from one dex to another of the same account must not read as a receive."""
    events = _send_events(
        address=SENDER,
        entry={**SEND_ENTRY, 'delta': {
            **(delta := SEND_ENTRY['delta']),
            'destination': delta['user'],
        }},
    )

    assert [(e.event_type, e.event_subtype, e.amount) for e in events] == [
        (HistoryEventType.TRANSFER, HistoryEventSubType.NONE, FVal('0.001')),
        (HistoryEventType.SPEND, HistoryEventSubType.FEE, FVal('1')),
    ]


def test_send_of_zero_still_keeps_the_fee(globaldb) -> None:
    events = _send_events(
        address=SENDER,
        entry={**SEND_ENTRY, 'delta': {**SEND_ENTRY['delta'], 'amount': '0.0'}},
    )

    assert [(e.event_subtype, e.amount) for e in events] == [
        (HistoryEventSubType.FEE, FVal('1')),
    ]


def test_send_between_two_tracked_accounts_is_saved_for_both(database) -> None:
    """Both accounts get the same ledger entry, so its hash alone gave their events the same
    group identifier and the second account's events were dropped as duplicates."""
    events = _send_events(address=SENDER) + _send_events(address=RECIPIENT)
    with database.user_write() as write_cursor:
        database.add_asset_identifiers(
            write_cursor=write_cursor,
            asset_identifiers=list({event.asset.identifier for event in events}),
        )
        assert DBHistoryEvents(database).add_history_events(
            write_cursor=write_cursor,
            history=events,
        ) == 3

    with database.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT location_label, type, subtype FROM history_events ORDER BY identifier',
        ).fetchall() == [
            (SENDER, 'spend', 'none'),
            (SENDER, 'spend', 'fee'),
            (RECIPIENT, 'receive', 'none'),
        ]
