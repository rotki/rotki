"""Reusable setup for the bucket reconciliation read side.

The helpers here write exactly the rows the report reads (balance metrics, saved checks,
processing stops, wallet observations and transaction sync ranges), so API tests, the parent's
fixture server and the performance benchmark can build the same representative states without
mocking any reader. Import this module from tests; nothing in it is used by production code.
"""
from typing import TYPE_CHECKING, cast

from rotkehlchen.chain.accounts import BlockchainAccountData
from rotkehlchen.constants.assets import A_ETH, A_ETH2
from rotkehlchen.db.cache import DBCacheDynamic, DBCacheStatic
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.data_issues.bucket_checks import BucketBalanceCheck, save_balance_check
from rotkehlchen.history.data_issues.bucket_state import make_bucket_key
from rotkehlchen.history.data_issues.constants import IssueKind
from rotkehlchen.history.data_issues.manager import DataIssuesManager
from rotkehlchen.history.data_issues.observations import (
    ObservationSource,
    record_wallet_observations,
)
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.locations.chains import EVM_LOCATIONS
from rotkehlchen.locations.constants import (
    LOCATION_ETHEREUM,
    LOCATION_KRAKEN,
    LOCATION_OPTIMISM,
)
from rotkehlchen.tests.utils.factories import make_evm_address, make_evm_tx_hash
from rotkehlchen.types import (
    BlockchainAddress,
    EventMetricKey,
    SupportedBlockchain,
    Timestamp,
)
from rotkehlchen.utils.misc import ts_now, ts_sec_to_ms

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.locations.types import LocationIdentifier


def track_blockchain_account(
        database: DBHandler,
        address: str,
        blockchain: SupportedBlockchain = SupportedBlockchain.ETHEREUM,
) -> None:
    """Track an account of any chain, as the account settings would."""
    with database.user_write() as write_cursor:
        database.add_blockchain_accounts(
            write_cursor=write_cursor,
            account_data=[BlockchainAccountData(
                chain=blockchain,
                address=cast('BlockchainAddress', address),
            )],
        )


def _add_event(
        database: DBHandler,
        address: str | None,
        ts: int,
        location: LocationIdentifier,
        asset: Asset,
        amount: FVal,
) -> int:
    """Add an event at the given location, of the concrete type its location accepts.

    `ts` is in seconds, like every timestamp these helpers take; events are stored in ms.
    """
    timestamp_ms = ts_sec_to_ms(Timestamp(ts))
    with database.user_write() as write_cursor:
        event = (
            EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=timestamp_ms,
                location=location,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=asset,
                amount=amount,
                location_label=address,
            ) if location in EVM_LOCATIONS else HistoryEvent(
                group_identifier=str(make_evm_tx_hash()),
                sequence_index=0,
                timestamp=timestamp_ms,
                location=location,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=asset,
                amount=amount,
                location_label=address,
            )
        )
        event_id = DBHistoryEvents(database).add_history_event(
            write_cursor=write_cursor,
            event=event,
        )
    assert event_id is not None
    return event_id


def add_balance_bucket(
        database: DBHandler,
        address: str | None,
        amount: str,
        ts: int,
        location: LocationIdentifier = LOCATION_ETHEREUM,
        protocol: str | None = None,
        asset: Asset = A_ETH,
        apply_stale_marker: bool = True,
) -> int:
    """Add an event plus the latest balance metric the processor would have written for it."""
    event_id = _add_event(
        database=database,
        address=address,
        ts=ts,
        location=location,
        asset=asset,
        amount=FVal(amount),
    )
    with database.user_write() as write_cursor:
        write_cursor.execute(
            'INSERT INTO event_metrics(event_identifier, location, location_label, protocol, '
            'metric_key, metric_value, asset, timestamp, sequence_index, sort_key) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?)',
            (
                event_id, location, address, protocol,
                EventMetricKey.BALANCE.serialize(), amount,
                asset.identifier, (timestamp_ms := ts_sec_to_ms(Timestamp(ts))), timestamp_ms,
            ),
        )
        if apply_stale_marker:
            write_cursor.execute(
                'DELETE FROM key_value_cache WHERE name IN (?, ?)',
                (
                    DBCacheStatic.STALE_BALANCES_FROM_TS.value,
                    DBCacheStatic.STALE_BALANCES_MODIFICATION_TS.value,
                ),
            )

    return event_id


def add_empty_event(
        database: DBHandler,
        address: str,
        ts: int,
        location: LocationIdentifier = LOCATION_ETHEREUM,
        asset: Asset = A_ETH,
) -> int:
    """Add a history event without a balance metric, like a pass stopped at its first event."""
    return _add_event(
        database=database,
        address=address,
        ts=ts,
        location=location,
        asset=asset,
        amount=FVal('1'),
    )


def add_observation(
        database: DBHandler,
        address: str,
        asset: Asset,
        amount: str,
        observed_at: int,
        blockchain: SupportedBlockchain = SupportedBlockchain.ETHEREUM,
) -> None:
    with database.user_write() as write_cursor:
        record_wallet_observations(
            write_cursor=write_cursor,
            blockchain=blockchain,
            address=address,
            amounts={asset.identifier: FVal(amount)},
            observed_at=Timestamp(observed_at),
            source=ObservationSource.BALANCE_QUERY,
        )
        database.set_dynamic_cache(
            write_cursor=write_cursor,
            name=DBCacheDynamic.LAST_ADDRESS_BALANCES_QUERY_TS,
            value=Timestamp(observed_at),
            blockchain=blockchain.serialize(),
            address=address,
        )


def add_complete_sync(
        database: DBHandler,
        address: str,
        synced_to: int,
        synced_from: int = 0,
        blockchain: SupportedBlockchain = SupportedBlockchain.ETHEREUM,
) -> None:
    """Mark the normal, internal and token transaction ranges of an address as complete."""
    with database.user_write() as write_cursor:
        write_cursor.executemany(
            'INSERT OR REPLACE INTO used_query_ranges(name, start_ts, end_ts) VALUES (?, ?, ?)',
            [(
                f'{blockchain.to_range_prefix(prefix)}_{address}',
                synced_from,
                synced_to,
            ) for prefix in ('txs', 'internaltxs', 'tokentxs')],
        )


def add_check(
        database: DBHandler,
        address: str,
        asset: Asset = A_ETH,
        derived_balance: str = '5',
        observed_balance: str = '5',
        observed_at: int | None = None,
        compared_at: int | None = None,
        latest_event_identifier: int | None = None,
        observation_id: int | None = None,
        location: LocationIdentifier = LOCATION_ETHEREUM,
) -> None:
    now = ts_now()
    with database.user_write() as write_cursor:
        save_balance_check(write_cursor, BucketBalanceCheck(
            location=location,
            location_label=address,
            asset=asset.identifier,
            derived_balance=FVal(derived_balance),
            observed_balance=FVal(observed_balance),
            latest_event_identifier=latest_event_identifier,
            observed_at=Timestamp(now if observed_at is None else observed_at),
            compared_at=Timestamp(now if compared_at is None else compared_at),
            observation_id=observation_id,
        ))


def add_stop(
        database: DBHandler,
        address: str,
        event_identifier: int,
        event_timestamp: int,
        asset: Asset = A_ETH,
        location: LocationIdentifier = LOCATION_ETHEREUM,
        protocol: str | None = None,
        derived_balance_before_event: str = '1',
        negative_amount: str = '-2',
) -> None:
    with database.user_write() as write_cursor:
        write_cursor.execute(
            'INSERT OR REPLACE INTO bucket_processing_stops(location, location_label, protocol, '
            'asset, event_identifier, event_timestamp, derived_balance_before_event, '
            'negative_amount) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (
                *make_bucket_key(
                    location=location,
                    location_label=address,
                    protocol=protocol,
                    asset=asset.identifier,
                ),
                event_identifier,
                ts_sec_to_ms(Timestamp(event_timestamp)),
                derived_balance_before_event,
                negative_amount,
            ),
        )


def add_negative_balance_issue(
        database: DBHandler,
        address: str,
        event_identifier: int,
        asset: Asset = A_ETH,
        location: LocationIdentifier = LOCATION_ETHEREUM,
        protocol: str | None = None,
        dismiss: bool = False,
) -> int:
    manager = DataIssuesManager(database)
    issue_id = manager.write_issue(
        kind=IssueKind.NEGATIVE_BALANCE,
        location=location,
        location_label=address,
        protocol=protocol,
        asset=asset.identifier,
        payload={
            'event_identifier': event_identifier,
            'in_memory_negative_amount': '-2',
            'derived_balance_before_event': '1',
        },
        ts_start=1_000,
        ts_end=2_000,
    )
    if dismiss:
        manager.dismiss(issue_id)

    return issue_id


def add_mismatch_issue(
        database: DBHandler,
        address: str,
        asset: Asset = A_ETH,
        location: LocationIdentifier = LOCATION_ETHEREUM,
        derived_balance: str = '5',
        observed_balance: str = '7',
) -> int:
    return DataIssuesManager(database).write_issue(
        kind=IssueKind.CURRENT_BALANCE_MISMATCH,
        location=location,
        location_label=address,
        protocol=None,
        asset=asset.identifier,
        payload={
            'derived_balance': derived_balance,
            'observed_balance': observed_balance,
            'delta': str(FVal(observed_balance) - FVal(derived_balance)),
            'queried_at_ts': ts_now(),
            'latest_event_identifier': None,
        },
        ts_start=1_000,
        ts_end=2_000,
    )


def ignore_asset(database: DBHandler, asset: Asset) -> None:
    with database.user_write() as write_cursor:
        database.add_to_ignored_assets(write_cursor=write_cursor, asset=asset)


def seed_reconciliation_scenarios(
        database: DBHandler,
        accounts: tuple[str, ...],
        now: int | None = None,
) -> dict[str, dict]:
    """Build the reportable states, spread over several accounts, and return their identifiers.

    Accounts must be the tracked ethereum accounts of the fixture. The result maps a case name to
    the identifiers the API assertions need (account, asset, event, issue, amounts).

    The states live on different accounts on purpose: with ETH2 treated as ETH, a bucket of one
    account aggregates both identifiers, so the ETH and ETH2 cases would otherwise share a key.
    """
    now = ts_now() if now is None else now
    address = accounts[0]
    other = accounts[1] if len(accounts) > 1 else make_evm_address()
    observed_at = now - 60
    event_ts = now - 3_600
    seeded: dict[str, dict] = {}

    # Reconciled: a fresh saved match backed by a covered observation and complete sync.
    event_id = add_balance_bucket(database, address, '5', event_ts)
    add_observation(database, address, A_ETH, '5', observed_at)
    add_check(
        database=database,
        address=address,
        derived_balance='5',
        observed_balance='5',
        observed_at=observed_at,
        latest_event_identifier=event_id,
        observation_id=latest_observation_id(database, address, A_ETH),
    )
    add_complete_sync(database, address, now)
    seeded['reconciled'] = {'account': address, 'asset': A_ETH.identifier}

    # Mismatch: saved comparison differs and is still fresh.
    if other not in accounts:
        track_blockchain_account(database, other)
    mismatch_event = add_balance_bucket(database, other, '5', event_ts, asset=A_ETH2)
    add_observation(database, other, A_ETH2, '7', observed_at)
    add_check(
        database=database,
        address=other,
        asset=A_ETH2,
        derived_balance='5',
        observed_balance='7',
        observed_at=observed_at,
        latest_event_identifier=mismatch_event,
        observation_id=latest_observation_id(database, other, A_ETH2),
    )
    add_complete_sync(database, other, now)
    seeded['mismatch'] = {'account': other, 'asset': A_ETH2.identifier, 'delta': '2'}

    # Blocked: a stop with a dismissed negative-balance issue and no metric for the bucket.
    track_blockchain_account(database, address, SupportedBlockchain.OPTIMISM)
    stop_event = add_empty_event(database, address, event_ts, location=LOCATION_OPTIMISM)
    add_stop(
        database=database,
        address=address,
        event_identifier=stop_event,
        event_timestamp=event_ts,
        location=LOCATION_OPTIMISM,
    )
    issue_id = add_negative_balance_issue(
        database=database,
        address=address,
        event_identifier=stop_event,
        location=LOCATION_OPTIMISM,
        dismiss=True,
    )
    seeded['blocked'] = {
        'account': address,
        'asset': A_ETH.identifier,
        'event_identifier': stop_event,
        'event_ts': event_ts,
        'issue_id': issue_id,
    }

    # Not compared: a protocol bucket, which v1 does not compare.
    add_balance_bucket(
        database=database,
        address=address,
        amount='3',
        ts=event_ts,
        protocol='aave-v3',
    )
    seeded['protocol'] = {'account': address, 'asset': A_ETH.identifier, 'protocol': 'aave-v3'}

    # Exchange bucket: informational, never compared with a wallet observation.
    add_balance_bucket(
        database=database,
        address='kraken account',
        amount='4',
        ts=event_ts,
        location=LOCATION_KRAKEN,
    )
    seeded['exchange'] = {'account': 'kraken account'}

    # Pending / never compared on its own account, so grouping is exercised too.
    pending_account = make_evm_address()
    track_blockchain_account(database, pending_account)
    add_balance_bucket(database, pending_account, '2', event_ts)
    add_observation(database, pending_account, A_ETH, '2', observed_at)
    add_complete_sync(database, pending_account, now)
    seeded['never_compared'] = {'account': pending_account, 'asset': A_ETH.identifier}

    mark_processing_completed(database, now)
    return seeded


def latest_observation_id(
        database: DBHandler,
        address: str,
        asset: Asset,
) -> int | None:
    with database.conn.read_ctx() as cursor:
        row = cursor.execute(
            'SELECT observation_id FROM wallet_balance_observations '
            'WHERE address = ? AND asset = ?',
            (address, asset.identifier),
        ).fetchone()
    return None if row is None else row[0]


def mark_processing_completed(database: DBHandler, ts: int) -> None:
    """Record a completed processing pass, so the report does not call the events pending."""
    with database.user_write() as write_cursor:
        database.set_static_cache(
            write_cursor=write_cursor,
            name=DBCacheStatic.LAST_HISTORICAL_BALANCE_PROCESSING_TS,
            value=Timestamp(ts),
        )


def set_stale_marker(database: DBHandler, from_ts: int) -> None:
    with database.user_write() as write_cursor:
        database.set_static_cache(
            write_cursor=write_cursor,
            name=DBCacheStatic.STALE_BALANCES_FROM_TS,
            value=str(ts_sec_to_ms(Timestamp(from_ts))),  # an event timestamp, so in ms
        )


def clear_stale_marker(database: DBHandler) -> None:
    with database.user_write() as write_cursor:
        write_cursor.execute(
            'DELETE FROM key_value_cache WHERE name = ?',
            (DBCacheStatic.STALE_BALANCES_FROM_TS.value,),
        )
