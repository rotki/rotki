from typing import TYPE_CHECKING, Literal

import pytest

from rotkehlchen.chain.solana.rpc import Signature
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_ETH, A_SOL
from rotkehlchen.history.events.structures.solana_swap import SolanaSwapEvent
from rotkehlchen.history.events.structures.swap import create_swap_events
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import AssetAmount, Location, Timestamp, TimestampMS

if TYPE_CHECKING:
    from rotkehlchen.accounting.accountant import Accountant
    from rotkehlchen.assets.asset import Asset


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('accountant_without_rules', [True])
@pytest.mark.parametrize(('event_type', 'event_subtype'), [
    (HistoryEventType.TRADE, HistoryEventSubType.RECEIVE),
    (HistoryEventType.TRADE, HistoryEventSubType.SPEND),
    (HistoryEventType.MULTI_TRADE, HistoryEventSubType.RECEIVE),
])
def test_missing_rule_warning_for_unpaired_trade(
        accountant: Accountant,
        event_type: Literal[HistoryEventType.TRADE, HistoryEventType.MULTI_TRADE],
        event_subtype: Literal[HistoryEventSubType.RECEIVE, HistoryEventSubType.SPEND],
) -> None:
    """Events without rules count as missing unless their spend was explicitly skipped."""
    accountant.process_history(
        start_ts=Timestamp(1735689600),
        end_ts=Timestamp(1767225599),
        events=[SolanaSwapEvent(
            identifier=1,
            tx_ref=Signature.default(),
            sequence_index=0,
            timestamp=TimestampMS(1735689600000),
            event_type=event_type,
            event_subtype=event_subtype,
            asset=A_SOL,
            amount=ONE,
            counterparty='jupiter',
        )],
    )
    assert accountant.pots[0].events_skipped_no_rule == 1
    assert accountant.pots[0].processed_events == []


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_missing_rule_warning_for_ignored_trade_spend(accountant: Accountant) -> None:
    """Only receives paired with an ignored spend are suppressed, for the current report."""
    events = create_swap_events(
        timestamp=TimestampMS(1735689600000),
        location=Location.EXTERNAL,
        group_identifier='ignored-spend',
        spend=AssetAmount(asset=A_SOL, amount=ONE),
        receive=AssetAmount(asset=A_ETH, amount=ONE),
    )
    with accountant.db.user_write() as write_cursor:
        accountant.db.add_to_ignored_assets(write_cursor, A_SOL)

    accountant.process_history(
        start_ts=Timestamp(1735689600),
        end_ts=Timestamp(1767225599),
        events=events,
    )
    assert accountant.pots[0].events_skipped_no_rule == 0
    assert accountant.pots[0].processed_events == []

    # Reusing the group in a new report must not retain the ignored-spend exemption.
    accountant.process_history(
        start_ts=Timestamp(1735689600),
        end_ts=Timestamp(1767225599),
        events=events[1:],
    )
    assert accountant.pots[0].events_skipped_no_rule == 1
    assert accountant.pots[0].processed_events == []


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_missing_rule_warning_for_lone_trade_receive(accountant: Accountant) -> None:
    """A receive with a missing, non-ignored spend must still warn with default rules."""
    events = create_swap_events(
        timestamp=TimestampMS(1735689600000),
        location=Location.EXTERNAL,
        group_identifier='missing-spend',
        spend=AssetAmount(asset=A_SOL, amount=ONE),
        receive=AssetAmount(asset=A_ETH, amount=ONE),
    )
    accountant.process_history(
        start_ts=Timestamp(1735689600),
        end_ts=Timestamp(1767225599),
        events=events[1:],
    )
    assert accountant.pots[0].events_skipped_no_rule == 1
    assert accountant.pots[0].processed_events == []


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_ignored_spend_does_not_hide_another_swap_receive(accountant: Accountant) -> None:
    """An ignored spend exempts only its paired receive within an onchain transaction."""
    swap_legs: list[tuple[
        int,
        Literal[HistoryEventSubType.SPEND, HistoryEventSubType.RECEIVE],
        Asset,
    ]] = [
        (0, HistoryEventSubType.SPEND, A_SOL),
        (1, HistoryEventSubType.RECEIVE, A_ETH),
        # The second swap's spend at index 2 is missing.
        (3, HistoryEventSubType.RECEIVE, A_ETH),
    ]
    events = [SolanaSwapEvent(
        identifier=sequence_index + 1,
        tx_ref=Signature.default(),
        sequence_index=sequence_index,
        timestamp=TimestampMS(1735689600000),
        event_subtype=event_subtype,
        asset=asset,
        amount=ONE,
        counterparty='jupiter',
    ) for sequence_index, event_subtype, asset in swap_legs]
    with accountant.db.user_write() as write_cursor:
        accountant.db.add_to_ignored_assets(write_cursor, A_SOL)

    accountant.process_history(
        start_ts=Timestamp(1735689600),
        end_ts=Timestamp(1767225599),
        events=events,
    )
    assert accountant.pots[0].events_skipped_no_rule == 1
    assert accountant.pots[0].processed_events == []
