import logging
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest

from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_HYPE
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.externalapis.hyperliquid import HyperliquidAPI
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.history.events.utils import create_group_identifier_from_unique_id
from rotkehlchen.tasks.historical_balances import process_historical_balances
from rotkehlchen.tests.utils.hyperliquid import query_staking_history_events
from rotkehlchen.types import Location, Timestamp, TimestampMS

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.user_messages import MessagesAggregator

# The ValiDAO validator, which stakes and delegates HYPE to itself
STAKER = string_to_evm_address('0x000000000056f99d36B6F2e0c51FD41496BbacB8')
ZERO_HASH = '0x0000000000000000000000000000000000000000000000000000000000000000'


def _staking_event(
        unique_id: str,
        timestamp: int,
        event_type: HistoryEventType,
        event_subtype: HistoryEventSubType,
        amount: str,
        notes: str,
        extra_data: dict[str, Any] | None = None,
) -> HistoryEvent:
    return HistoryEvent(
        group_identifier=create_group_identifier_from_unique_id(
            location=Location.HYPERLIQUID,
            unique_id=unique_id,
        ),
        sequence_index=0,
        timestamp=TimestampMS(timestamp),
        location=Location.HYPERLIQUID,
        event_type=event_type,
        event_subtype=event_subtype,
        asset=A_HYPE,
        amount=FVal(amount),
        location_label=STAKER,
        notes=notes,
        extra_data=extra_data,
    )


@pytest.mark.vcr(match_on=['uri', 'method', 'body'])
def test_query_staking_balance_sums_the_whole_staking_account() -> None:
    """The staking balance is the delegated, undelegated and pending withdrawal HYPE."""
    assert HyperliquidAPI().query_staking_balance(address=STAKER) == FVal('10118.67358863')


@pytest.mark.vcr(match_on=['uri', 'method', 'body'])
@pytest.mark.usefixtures('globaldb')
def test_query_staking_history_events() -> None:
    api = HyperliquidAPI()
    assert query_staking_history_events(
        api=api,
        address=STAKER,
        start_ts=Timestamp(1735385000),
        end_ts=Timestamp(1735400000),
    ) == [
        _staking_event(
            unique_id=f'delegatorHistory_{STAKER}_1735385151376_0x5333fea0d2277c67af0f041a233c3a01c800881fb2b562e92e1196317c5ef989',
            timestamp=1735385151376,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            amount='10060',
            notes='Deposit 10060 HYPE to Hyperliquid staking',
        ), _staking_event(
            unique_id=f'delegatorHistory_{STAKER}_1735396594483_0x1b8d1dfa1e053a447741041a252e9301ac00c21f511e67ac9c4a82b70b8aec68',
            timestamp=1735396594483,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.DELEGATE,
            amount='10060',
            notes=f'Delegate 10060 HYPE to validator {STAKER}',
            extra_data={'validator': STAKER},
        ),
    ]
    assert query_staking_history_events(
        api=api,
        address=STAKER,
        start_ts=Timestamp(1791380000),
        end_ts=Timestamp(1791431000),
    ) == [
        _staking_event(
            unique_id=f'delegatorHistory_{STAKER}_1791380530774_0x656c707c3c5846e866e604460ab1e00207850061d75b65ba09351bcefb5c20d3',
            timestamp=1791380530774,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.DELEGATE,
            amount='50',
            notes=f'Undelegate 50 HYPE from validator {STAKER}',
            extra_data={'validator': STAKER},
        ), _staking_event(
            unique_id=f'delegatorHistory_{STAKER}_1791380544008_0xdd964b3f3ea0002cdf1004460ab297020e1f0024d9a31efe815ef691fda3da17',
            timestamp=1791380544008,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            amount='50',
            notes='Request withdrawal of 50 HYPE from Hyperliquid staking',
        ), _staking_event(
            unique_id=f'delegatorRewards_{STAKER}_1791417600062_delegation',
            timestamp=1791417600062,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            amount='0.589916',
            notes='Receive 0.589916 HYPE as Hyperliquid staking reward',
        ), _staking_event(
            unique_id=f'delegatorRewards_{STAKER}_1791417600062_commission',
            timestamp=1791417600062,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            amount='15.71236952',
            notes='Receive 15.71236952 HYPE as Hyperliquid validator commission',
        ), _staking_event(
            unique_id=f'delegatorHistory_{STAKER}_1791430048033_{ZERO_HASH}',
            timestamp=1791430048033,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            amount='100',
            notes='Withdraw 100 HYPE from Hyperliquid staking',
        ),
    ]


@pytest.mark.vcr(match_on=['uri', 'method', 'body'])
@pytest.mark.usefixtures('globaldb')
def test_staking_history_range_includes_the_whole_end_second() -> None:
    """The next queried range starts at the second after `end_ts`, so the rewards paid
    62ms into the end second belong to this range or would never be stored."""
    events = query_staking_history_events(
        api=HyperliquidAPI(),
        address=STAKER,
        start_ts=Timestamp(1791417599),
        end_ts=Timestamp(1791417600),
    )
    assert sorted((event.timestamp, event.amount) for event in events) == [
        (TimestampMS(1791417600062), FVal('0.589916')),
        (TimestampMS(1791417600062), FVal('15.71236952')),
    ]


@pytest.mark.vcr(match_on=['uri', 'method', 'body'])
def test_staking_events_are_all_stored_and_only_rewards_change_historical_balance(
        database: DBHandler,
        messages_aggregator: MessagesAggregator,
) -> None:
    """The range has two finalized withdrawals sharing the zero hash and pairs of rewards
    with no hash at the same time, so this checks that none of them collapses into another
    when stored. Moving HYPE between spot and staking keeps it in the account, so only the
    12 rewards change the HYPE balance.
    """
    events = query_staking_history_events(
        api=HyperliquidAPI(),
        address=STAKER,
        start_ts=Timestamp(1790936000),
        end_ts=Timestamp(1791431000),
    )
    assert len(events) == 20
    with database.user_write() as write_cursor:
        assert DBHistoryEvents(database).add_history_events(
            write_cursor=write_cursor,
            history=events,
        ) == 20

    process_historical_balances(database, messages_aggregator)

    with database.conn.read_ctx() as cursor:
        metric_values = [FVal(row[0]) for row in cursor.execute(
            'SELECT metric_value FROM event_metrics WHERE location_label=? AND asset=?',
            (STAKER, A_HYPE.identifier),
        )]

    assert len(metric_values) == 12
    assert max(metric_values) == FVal('98.14114491')


@pytest.mark.vcr(match_on=['uri', 'method', 'body'])
@pytest.mark.usefixtures('globaldb')
def test_staking_transfer_ledger_entry_is_skipped_without_warning(caplog) -> None:
    """The ledger has a `cStakingTransfer` for the 100 HYPE finalized withdrawal that
    `delegatorHistory` already reports, so it must not turn it into a second event."""
    caplog.set_level(logging.WARNING)
    api = HyperliquidAPI()
    assert [api._create_ledger_events(address=STAKER, contexts=contexts) for contexts in api._iter_entry_pages(  # noqa: E501
        query_type='userNonFundingLedgerUpdates',
        address=STAKER,
        start_ts=Timestamp(1791430048),
        end_ts=Timestamp(1791430049),
    )] == [[]]
    assert 'Unknown hyperliquid ledger event type' not in caplog.text


def test_staking_entries_sharing_an_id_get_distinct_ids() -> None:
    """Withdrawals finalized at the same millisecond share the zero hash, so the later
    ones get a counter. Entries with neither hash nor source fall back to their content
    instead of a constant."""
    withdrawal = {'time': 1791430048033, 'hash': ZERO_HASH, 'delta': {'withdrawal': {'amount': '1.0', 'phase': 'finalized'}}}  # noqa: E501
    unknown = {'time': 1791430048034, 'delta': {'newAction': {}}}
    api = HyperliquidAPI()
    with patch.object(api, '_query_list', return_value=[withdrawal, withdrawal, unknown]):
        assert [context.unique_id for context in api._query_staking_entries(
            query_type='delegatorHistory',
            address=STAKER,
            start_ts=Timestamp(1791430048),
            end_ts=Timestamp(1791430049),
        )] == [
            f'delegatorHistory_{STAKER}_1791430048033_{ZERO_HASH}',
            f'delegatorHistory_{STAKER}_1791430048033_{ZERO_HASH}_1',
            f'delegatorHistory_{STAKER}_1791430048034_{HyperliquidAPI._entry_content_id(unknown)}',
        ]
