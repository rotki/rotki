"""Tests for the notes rotki generates from event data instead of storing them"""
from typing import TYPE_CHECKING, Final

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH, A_SOL, A_USD, A_USDC
from rotkehlchen.db.constants import HISTORY_BASE_ENTRY_FIELDS
from rotkehlchen.db.filtering import (
    EthWithdrawalFilterQuery,
    EvmEventFilterQuery,
    HistoryEventFilterQuery,
)
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.auto_notes import AUTO_NOTES_SQL
from rotkehlchen.history.events.structures.base import HistoryBaseEntry, HistoryEvent
from rotkehlchen.history.events.structures.eth2 import (
    EthBlockEvent,
    EthDepositEvent,
    EthStakingEvent,
    EthWithdrawalEvent,
)
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.evm_swap import EvmSwapEvent
from rotkehlchen.history.events.structures.solana_event import SolanaEvent
from rotkehlchen.history.events.structures.swap import SwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.factories import make_evm_tx_hash, make_solana_signature
from rotkehlchen.types import ChecksumEvmAddress, Location, SolanaAddress, TimestampMS

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

USER: Final = string_to_evm_address('0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12')
OTHER: Final = string_to_evm_address('0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c')
SOL_USER: Final = SolanaAddress('JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4')
SOL_OTHER: Final = SolanaAddress('So11111111111111111111111111111111111111112')
TIMESTAMP: Final = TimestampMS(1700000000000)


def _evm(
        event_type: HistoryEventType,
        event_subtype: HistoryEventSubType,
        asset: Asset,
        amount: FVal,
        counterparty: str | None = None,
        address: ChecksumEvmAddress | None = None,
        location: Location = Location.ETHEREUM,
        notes: str | None = None,
) -> EvmEvent:
    return EvmEvent(
        tx_ref=make_evm_tx_hash(),
        sequence_index=0,
        timestamp=TIMESTAMP,
        location=location,
        location_label=USER,
        event_type=event_type,
        event_subtype=event_subtype,
        asset=asset,
        amount=amount,
        counterparty=counterparty,
        address=address,
        notes=notes,
    )


def _solana(
        event_type: HistoryEventType,
        event_subtype: HistoryEventSubType,
        asset: Asset,
        amount: FVal,
        counterparty: str | None = None,
        address: SolanaAddress | None = None,
) -> SolanaEvent:
    return SolanaEvent(
        tx_ref=make_solana_signature(),
        sequence_index=0,
        timestamp=TIMESTAMP,
        location_label=SOL_USER,
        event_type=event_type,
        event_subtype=event_subtype,
        asset=asset,
        amount=amount,
        counterparty=counterparty,
        address=address,
    )


def _events_with_auto_notes() -> list[tuple[HistoryBaseEntry, str]]:
    """One event per auto notes template, paired with the text expected of it. The events
    carry no notes so that the DB write stores NULL and the SQL side has to rebuild them."""
    return [
        (_evm(event_type=HistoryEventType.SPEND, event_subtype=HistoryEventSubType.FEE, asset=A_ETH, amount=FVal('0.001'), counterparty=CPT_GAS), 'Burn 0.001 ETH for gas'),  # noqa: E501
        (_evm(event_type=HistoryEventType.FAIL, event_subtype=HistoryEventSubType.FEE, asset=A_ETH, amount=FVal('0.002'), counterparty=CPT_GAS), 'Burn 0.002 ETH for gas of a failed transaction'),  # noqa: E501
        (_evm(event_type=HistoryEventType.INFORMATIONAL, event_subtype=HistoryEventSubType.APPROVE, asset=A_USDC, amount=FVal('115'), address=OTHER), f'Set USDC spending approval of {USER} by {OTHER} to 115'),  # noqa: E501
        (_evm(event_type=HistoryEventType.INFORMATIONAL, event_subtype=HistoryEventSubType.APPROVE, asset=A_USDC, amount=FVal(0), address=OTHER), f'Revoke USDC spending approval of {USER} by {OTHER}'),  # noqa: E501
        (_evm(event_type=HistoryEventType.DEPLOY, event_subtype=HistoryEventSubType.NONE, asset=A_ETH, amount=FVal(0), address=OTHER), f'Deploy a new contract at {OTHER}'),  # noqa: E501
        (_evm(event_type=HistoryEventType.TRANSACTION_TO_SELF, event_subtype=HistoryEventSubType.NONE, asset=A_ETH, amount=FVal(0), address=USER), 'No value transaction to self'),  # noqa: E501
        (_evm(event_type=HistoryEventType.TRANSACTION_TO_SELF, event_subtype=HistoryEventSubType.NONE, asset=A_ETH, amount=FVal('1.5'), address=USER), 'Transaction to self of 1.5 ETH'),  # noqa: E501
        (_evm(event_type=HistoryEventType.SPEND, event_subtype=HistoryEventSubType.NONE, asset=A_ETH, amount=FVal('0.5'), address=OTHER), f'Send 0.5 ETH to {OTHER}'),  # noqa: E501
        (_evm(event_type=HistoryEventType.RECEIVE, event_subtype=HistoryEventSubType.NONE, asset=A_ETH, amount=FVal('0.5'), address=OTHER, location=Location.ARBITRUM_ONE), f'Receive 0.5 ETH from {OTHER}'),  # noqa: E501
        (_evm(event_type=HistoryEventType.WITHDRAWAL, event_subtype=HistoryEventSubType.REMOVE_ASSET, asset=A_ETH, amount=FVal('2'), address=OTHER, counterparty='kraken'), 'Withdraw 2 ETH from kraken'),  # noqa: E501
        (_evm(event_type=HistoryEventType.TRANSFER, event_subtype=HistoryEventSubType.NONE, asset=A_USDC, amount=FVal('10'), address=OTHER), f'Transfer 10 USDC from {USER} to {OTHER}'),  # noqa: E501
        (_evm(event_type=HistoryEventType.RECEIVE, event_subtype=HistoryEventSubType.NONE, asset=A_USDC, amount=FVal('10'), address=OTHER), f'Receive 10 USDC from {OTHER} to {USER}'),  # noqa: E501
        (_evm(event_type=HistoryEventType.DEPOSIT, event_subtype=HistoryEventSubType.DEPOSIT_ASSET, asset=A_USDC, amount=FVal('10'), address=OTHER, counterparty='binance'), f'Deposit 10 USDC from {USER} to binance'),  # noqa: E501
        (_solana(event_type=HistoryEventType.SPEND, event_subtype=HistoryEventSubType.FEE, asset=A_SOL, amount=FVal('0.000005'), counterparty=CPT_GAS), 'Spend 0.000005 SOL as transaction fee'),  # noqa: E501
        (_solana(event_type=HistoryEventType.SPEND, event_subtype=HistoryEventSubType.NONE, asset=A_SOL, amount=FVal('3'), address=SOL_OTHER), f'Send 3 SOL to {SOL_OTHER}'),  # noqa: E501
        (_solana(event_type=HistoryEventType.RECEIVE, event_subtype=HistoryEventSubType.NONE, asset=A_SOL, amount=FVal('3')), 'Receive 3 SOL'),  # noqa: E501
        (EthWithdrawalEvent(validator_index=42, timestamp=TIMESTAMP, amount=FVal('0.01'), withdrawal_address=USER, is_exit=False), 'Withdraw 0.01 ETH from validator 42'),  # noqa: E501
        (EthWithdrawalEvent(validator_index=43, timestamp=TIMESTAMP, amount=FVal('32'), withdrawal_address=USER, is_exit=True), 'Exit validator 43 with 32 ETH'),  # noqa: E501
        (EthBlockEvent(validator_index=42, timestamp=TIMESTAMP, amount=FVal('0.1'), fee_recipient=USER, fee_recipient_tracked=True, block_number=100, is_mev_reward=False), f'Validator 42 produced block 100 with 0.1 ETH going to {USER} as the block reward'),  # noqa: E501
        (EthBlockEvent(validator_index=42, timestamp=TIMESTAMP, amount=FVal('0.2'), fee_recipient=USER, fee_recipient_tracked=True, block_number=100, is_mev_reward=True), f'Validator 42 produced block 100. Relayer reported 0.2 ETH as the MEV reward going to {USER}'),  # noqa: E501
        (EthDepositEvent(tx_ref=make_evm_tx_hash(), validator_index=42, sequence_index=0, timestamp=TIMESTAMP, amount=FVal(32), depositor=USER), 'Deposit 32 ETH to validator 42'),  # noqa: E501
        (EthDepositEvent(tx_ref=make_evm_tx_hash(), validator_index=-1, sequence_index=0, timestamp=TIMESTAMP, amount=FVal(32), depositor=USER), 'Deposit 32 ETH to validator with a not yet known validator index'),  # noqa: E501
        (HistoryEvent(group_identifier='kraken1', sequence_index=0, timestamp=TIMESTAMP, location=Location.KRAKEN, event_type=HistoryEventType.STAKING, event_subtype=HistoryEventSubType.REWARD, asset=A_ETH, amount=FVal('0.3')), 'Gain 0.3 ETH from Kraken staking'),  # noqa: E501
        (HistoryEvent(group_identifier='kraken2', sequence_index=0, timestamp=TIMESTAMP, location=Location.KRAKEN, event_type=HistoryEventType.STAKING, event_subtype=HistoryEventSubType.FEE, asset=A_ETH, amount=FVal('0.01')), 'Spend 0.01 ETH as Kraken staking fee'),  # noqa: E501
        (SwapEvent(timestamp=TIMESTAMP, location=Location.BINANCE, event_subtype=HistoryEventSubType.SPEND, asset=A_ETH, amount=FVal(1), group_identifier='swap1'), 'Swap 1 ETH in Binance'),  # noqa: E501
        (SwapEvent(timestamp=TIMESTAMP, location=Location.BINANCE, event_subtype=HistoryEventSubType.RECEIVE, asset=A_USD, amount=FVal(3000), group_identifier='swap1'), 'Receive 3000 USD after a swap in Binance'),  # noqa: E501
        (SwapEvent(timestamp=TIMESTAMP, location=Location.BINANCE, event_subtype=HistoryEventSubType.FEE, asset=A_USD, amount=FVal(3), group_identifier='swap1'), 'Spend 3 USD as Binance swap fee'),  # noqa: E501
        (EvmSwapEvent(tx_ref=make_evm_tx_hash(), sequence_index=0, timestamp=TIMESTAMP, location=Location.ETHEREUM, event_subtype=HistoryEventSubType.SPEND, asset=A_ETH, amount=FVal(1)), 'Swap 1 ETH in Ethereum'),  # noqa: E501
        (AssetMovement(timestamp=TIMESTAMP, location=Location.BINANCEUS, event_subtype=HistoryEventSubType.RECEIVE, asset=A_ETH, amount=FVal(1), unique_id='m1'), 'Deposit 1 ETH to Binance US'),  # noqa: E501
        (AssetMovement(timestamp=TIMESTAMP, location=Location.BINANCEUS, event_subtype=HistoryEventSubType.SPEND, asset=A_ETH, amount=FVal(2), unique_id='m2'), 'Withdraw 2 ETH from Binance US'),  # noqa: E501
        (AssetMovement(timestamp=TIMESTAMP, location=Location.BINANCEUS, event_subtype=HistoryEventSubType.FEE, asset=A_ETH, amount=FVal('0.1'), unique_id='m2'), 'Pay 0.1 ETH as Binance US exchange transfer fee'),  # noqa: E501
    ]


def _sql_notes(database: DBHandler) -> dict[int, str | None]:
    """The auto notes SQLite rebuilds for every event in the DB, keyed by identifier"""
    with database.conn.read_ctx() as cursor:
        return dict(cursor.execute(
            f'SELECT history_events_identifier, COALESCE(notes, {AUTO_NOTES_SQL}) '
            f'FROM (SELECT {HISTORY_BASE_ENTRY_FIELDS} FROM history_events)',
        ))


def test_auto_notes_match_between_python_and_sql(database: DBHandler) -> None:
    """Every template is rendered identically by the event class and by the SQL expression
    the notes filter uses, apart from the asset symbol which SQL leaves out. The staking
    templates spell ETH out as text, so it stays. Also checks that events without notes are
    stored with NULL notes.
    """
    events_and_notes = _events_with_auto_notes()
    with database.user_write() as write_cursor:
        assert DBHistoryEvents(database).add_history_events(
            write_cursor=write_cursor,
            history=[event for event, _ in events_and_notes],
        ) == len(events_and_notes)

    sql_notes = _sql_notes(database)
    for identifier, (event, expected) in enumerate(events_and_notes, start=1):
        assert event.auto_notes() == expected
        assert event.serialize()['auto_notes'] == expected
        assert 'user_notes' not in event.serialize()
        if isinstance(event, EthStakingEvent):
            assert sql_notes[identifier] == expected
        else:
            assert sql_notes[identifier] == expected.replace(f' {event.asset.symbol_or_name()}', '', 1)  # noqa: E501


def test_notes_equal_to_auto_notes_are_not_stored(database: DBHandler) -> None:
    """Decoders keep setting the generated notes on the event so that protocol decoders can
    extend them. Only the ones that were left untouched are dropped at DB write time."""
    plain = _evm(event_type=HistoryEventType.SPEND, event_subtype=HistoryEventSubType.NONE, asset=A_ETH, amount=FVal('0.5'), address=OTHER)  # noqa: E501
    plain.notes = plain.auto_notes()
    extended = _evm(event_type=HistoryEventType.SPEND, event_subtype=HistoryEventSubType.NONE, asset=A_ETH, amount=FVal('0.5'), address=OTHER)  # noqa: E501
    extended.notes = f'{extended.auto_notes()} on behalf of {USER}'
    edited_gas = _evm(event_type=HistoryEventType.SPEND, event_subtype=HistoryEventSubType.FEE, asset=A_ETH, amount=FVal('0.001'), counterparty=CPT_GAS, notes='My expensive transaction')  # noqa: E501
    dbevents = DBHistoryEvents(database)
    with database.user_write() as write_cursor:
        dbevents.add_history_events(write_cursor, [plain, extended, edited_gas])

    with database.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT notes FROM history_events ORDER BY identifier',
        ).fetchall() == [(None,), (extended.notes,), ('My expensive transaction',)]
        events = dbevents.get_history_events_internal(cursor=cursor, filter_query=HistoryEventFilterQuery.make(), aggregate_by_group_ids=False)  # noqa: E501

    assert events[0].notes is None
    assert events[0].serialize()['auto_notes'] == f'Send 0.5 ETH to {OTHER}'
    assert events[1].serialize()['user_notes'] == extended.notes
    assert events[2].notes_or_auto() == 'My expensive transaction'
    assert events[0].notes_or_auto() == f'Send 0.5 ETH to {OTHER}'
    assert _sql_notes(database) == {1: f'Send 0.5 to {OTHER}', 2: extended.notes, 3: 'My expensive transaction'}  # noqa: E501


def test_unknown_asset_keeps_notes() -> None:
    """The DB write must not turn the foreign key failure of an unknown asset into an
    UnknownAsset error raised while checking the notes"""
    event = _evm(event_type=HistoryEventType.SPEND, event_subtype=HistoryEventSubType.FEE, asset=Asset('NOTREAL'), amount=FVal('0.001'), counterparty=CPT_GAS, notes='Burn 0.001 NOTREAL for gas')  # noqa: E501
    assert event._notes_for_db() == 'Burn 0.001 NOTREAL for gas'


@pytest.mark.parametrize(('substring', 'expected_notes'), [
    ('for gas', {'Burn 0.001 ETH for gas', 'Burn 0.002 ETH for gas of a failed transaction'}),
    ('0.001 for gas', {'Burn 0.001 ETH for gas'}),
    ('0.001 ETH', set()),
    ('spending approval of', {f'Set USDC spending approval of {USER} by {OTHER} to 115', f'Revoke USDC spending approval of {USER} by {OTHER}'}),  # noqa: E501
    (f'to {OTHER}', {f'Send 0.5 ETH to {OTHER}', f'Transfer 10 USDC from {USER} to {OTHER}'}),
    ('ETH from validator 42', {'Withdraw 0.01 ETH from validator 42'}),
    ('to validator 42', {'Deposit 32 ETH to validator 42'}),
    ('Binance US', {'Deposit 1 ETH to Binance US', 'Withdraw 2 ETH from Binance US', 'Pay 0.1 ETH as Binance US exchange transfer fee'}),  # noqa: E501
    ('transaction fee', {'Spend 0.000005 SOL as transaction fee'}),
])
def test_notes_filter_searches_auto_notes(
        database: DBHandler,
        substring: str,
        expected_notes: set[str],
) -> None:
    """The notes substring filter finds events whose notes are not stored but generated. The
    generated text is matched without the asset symbol, which the asset filter is for."""
    dbevents = DBHistoryEvents(database)
    with database.user_write() as write_cursor:
        dbevents.add_history_events(write_cursor, [event for event, _ in _events_with_auto_notes()])  # noqa: E501

    with database.conn.read_ctx() as cursor:
        events = dbevents.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(notes_substring=substring),
            aggregate_by_group_ids=False,
        )
    assert {event.auto_notes() for event in events} == expected_notes


def test_notes_filter_in_joined_queries(database: DBHandler) -> None:
    """The filter also works for the query variants that join the chain and staking tables"""
    dbevents = DBHistoryEvents(database)
    with database.user_write() as write_cursor:
        dbevents.add_history_events(write_cursor, [event for event, _ in _events_with_auto_notes()])  # noqa: E501

    with database.conn.read_ctx() as cursor:
        evm_events = dbevents.get_history_events_internal(
            cursor=cursor,
            filter_query=EvmEventFilterQuery.make(notes_substring='for gas'),
            aggregate_by_group_ids=False,
        )
        withdrawals = dbevents.get_history_events_internal(
            cursor=cursor,
            filter_query=EthWithdrawalFilterQuery.make(notes_substring='Exit validator'),
            aggregate_by_group_ids=False,
        )

    assert {event.auto_notes() for event in evm_events} == {'Burn 0.001 ETH for gas', 'Burn 0.002 ETH for gas of a failed transaction'}  # noqa: E501
    assert [event.auto_notes() for event in withdrawals] == ['Exit validator 43 with 32 ETH']
