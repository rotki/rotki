from collections.abc import Callable, Hashable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from rotkehlchen.constants.assets import A_ETH, A_ETH2
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.data_issues.observations import delete_wallet_observations
from rotkehlchen.locations.chains import EVM_LOCATIONS, location_to_chain
from rotkehlchen.types import SupportedBlockchain, TimestampMS
from rotkehlchen.utils.misc import ts_now_in_ms

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from rotkehlchen.db.drivers.sqlite import DBCursor
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry

type BucketKey = tuple[str, str, str, str]
"""Location, location label, protocol and asset of a bucket, with '' for a missing label or
protocol. Buckets are keyed like this so the stops of a bucket can be found without a NULL
column in the primary key."""


def make_bucket_key(
        location: str,
        location_label: str | None,
        protocol: str | None,
        asset: str,
) -> BucketKey:
    return location, location_label or '', protocol or '', asset


@dataclass(frozen=True)
class BucketStop:
    """The event at which historical balance processing stopped for a bucket.

    The processor applies no further event to a bucket whose derived balance went negative, so
    the bucket is blocked for as long as this record exists, whatever its inbox issue says. The
    record is replaced only by a completed processing pass that reprocessed the event
    (see replace_bucket_stops), never by dismissing or remediating the negative balance issue.
    """
    event_identifier: int
    event_timestamp: TimestampMS
    derived_balance_before_event: FVal
    negative_amount: FVal


class BucketRunState[BucketT: Hashable]:
    """Where each bucket stands during one historical balance processing pass.

    A bucket is accumulating until an event drives it negative. It is then either stopped for
    good, or, for a rebasing token, waiting for an on-chain balance to reconcile it against. The
    on-chain query failing keeps it waiting and is reported once. Reconciling returns it to
    accumulating and clears the stop, the wait and the report together.

    Recording a stop is independent of waiting for reconciliation on purpose: a bucket that is
    waiting and then goes negative through an event of a non-rebasing asset has its stop
    overwritten but keeps waiting, so later events still reach it.
    """

    def __init__(self, make_key: Callable[[BucketT], BucketKey]) -> None:
        self._make_key = make_key
        self._awaiting_reconciliation: dict[BucketT, HistoryBaseEntry] = {}
        self._failure_reported: set[BucketT] = set()
        self._stops: dict[BucketKey, BucketStop] = {}

    @property
    def stops(self) -> Mapping[BucketKey, BucketStop]:
        return self._stops

    def is_awaiting_reconciliation(self, bucket: BucketT) -> bool:
        return bucket in self._awaiting_reconciliation

    def negative_event(self, bucket: BucketT) -> HistoryBaseEntry | None:
        """The event that drove the bucket negative, if it is awaiting reconciliation."""
        return self._awaiting_reconciliation.get(bucket)

    def record_stop(
            self,
            bucket: BucketT,
            event: HistoryBaseEntry,
            balance_before_event: FVal,
            negative_amount: FVal,
    ) -> None:
        """Remember the event at which the bucket stopped being processed, see BucketStop."""
        assert event.identifier is not None, 'Processed history events should have identifiers'
        self._stops[self._make_key(bucket)] = BucketStop(
            event_identifier=event.identifier,
            event_timestamp=event.timestamp,
            derived_balance_before_event=balance_before_event,
            negative_amount=negative_amount,
        )

    def await_reconciliation(
            self,
            bucket: BucketT,
            event: HistoryBaseEntry,
            balance_before_event: FVal,
            negative_amount: FVal,
    ) -> None:
        """Stop the bucket at the event, until an on-chain balance reconciles it."""
        self._awaiting_reconciliation[bucket] = event
        self.record_stop(bucket, event, balance_before_event, negative_amount)

    def report_failure_once(self, bucket: BucketT) -> bool:
        """Whether this is the first failed reconciliation attempt of the bucket."""
        if bucket in self._failure_reported:
            return False

        self._failure_reported.add(bucket)
        return True

    def reconcile(self, bucket: BucketT) -> None:
        """Return the bucket to accumulating."""
        del self._awaiting_reconciliation[bucket]
        self._stops.pop(self._make_key(bucket), None)
        self._failure_reported.discard(bucket)


def get_bucket_stops(cursor: DBCursor) -> dict[BucketKey, BucketStop]:
    """All the buckets that processing is stopped for."""
    return {
        (location, label, protocol, asset): BucketStop(
            event_identifier=event_identifier,
            event_timestamp=TimestampMS(event_timestamp),
            derived_balance_before_event=FVal(balance_before),
            negative_amount=FVal(negative_amount),
        ) for location, label, protocol, asset, event_identifier, event_timestamp, balance_before, negative_amount in cursor.execute(  # noqa: E501
            'SELECT location, location_label, protocol, asset, event_identifier, '
            'event_timestamp, derived_balance_before_event, negative_amount '
            'FROM bucket_processing_stops',
        )
    }


def replace_bucket_stops(
        write_cursor: DBCursor,
        stops: Mapping[BucketKey, BucketStop],
        from_ts: TimestampMS | None,
) -> None:
    """Settle the stops after a processing pass ran to completion.

    A pass from from_ts reprocessed every event at or after it, so the stops at or after it are
    dropped and the ones the pass found are written. A full pass (no from_ts) replaces all of
    them. Stops before from_ts were not reprocessed and stay. A pass that did not complete never
    gets here, which is what keeps a failed reprocessing from clearing a blockage.
    """
    if from_ts is None:
        write_cursor.execute('DELETE FROM bucket_processing_stops')
    else:
        write_cursor.execute(
            'DELETE FROM bucket_processing_stops WHERE event_timestamp >= ?',
            (from_ts,),
        )
    write_cursor.executemany(
        'INSERT OR REPLACE INTO bucket_processing_stops(location, location_label, protocol, '
        'asset, event_identifier, event_timestamp, derived_balance_before_event, '
        'negative_amount) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        [(
            *key,
            stop.event_identifier,
            stop.event_timestamp,
            str(stop.derived_balance_before_event),
            str(stop.negative_amount),
        ) for key, stop in stops.items()],
    )


def get_retained_stops(cursor: DBCursor, from_ts: TimestampMS) -> dict[BucketKey, BucketStop]:
    """The stops a pass from from_ts leaves untouched, so it must keep their buckets stopped."""
    return {
        key: stop for key, stop in get_bucket_stops(cursor).items()
        if stop.event_timestamp < from_ts
    }


def delete_balance_checks(
        write_cursor: DBCursor,
        accounts: Iterable[tuple[str, str]] = (),
        assets: Iterable[str] = (),
) -> None:
    """Drop the saved comparisons of the given (location, location_label) accounts and assets.

    Used by the lifecycle operations that make a saved comparison describe something other
    than what it was taken for. It touches neither issues nor stops: invalidating evidence is
    not evidence of a match, and only reprocessing clears a blockage.
    """
    write_cursor.executemany(
        'DELETE FROM bucket_balance_checks WHERE location = ? AND location_label = ?',
        list(accounts),
    )
    write_cursor.executemany(
        'DELETE FROM bucket_balance_checks WHERE asset = ?',
        [(asset,) for asset in assets],
    )


def get_evm_location_code(blockchain: SupportedBlockchain) -> str | None:
    """The location code of the wallet buckets of an EVM chain, None for any other chain."""
    return next((
        location for location in EVM_LOCATIONS if location_to_chain(location) == blockchain
    ), None)


def delete_balance_checks_of_cleared_accounts(
        write_cursor: DBCursor,
        accounts: Iterable[tuple[str, str | None]],
) -> None:
    """Drop the saved comparisons of the accounts that no longer have any history event.

    That is a history reset, as opposed to deleting an event or two, which the staleness checks
    already cover: a comparison against a derived balance that no longer exists has nothing
    left to be compared to. An account with remaining events keeps its comparisons.
    """
    cleared = [
        (location, label) for location, label in accounts
        if label is not None and location in EVM_LOCATIONS
    ]
    write_cursor.executemany(
        'DELETE FROM bucket_balance_checks WHERE location = ? AND location_label = ? '
        'AND NOT EXISTS (SELECT 1 FROM history_events WHERE location = ? AND location_label = ?)',
        [(location, label, location, label) for location, label in cleared],
    )
    # The observations of an account reset to no events describe history that no longer exists.
    delete_wallet_observations(
        write_cursor=write_cursor,
        accounts=tuple(
            (location, label) for location, label in cleared
            if write_cursor.execute(
                'SELECT 1 FROM history_events WHERE location = ? AND location_label = ? LIMIT 1',
                (location, label),
            ).fetchone() is None
        ),
    )


def wallet_bucket_assets(asset: str, treat_eth2_as_eth: bool) -> tuple[str, ...]:
    """The asset identifiers whose derived balances and stops make up a wallet bucket's asset.

    With ETH2 treated as ETH, both are aggregated under ETH when read. A stop recorded by a pass
    that ran with the setting off is still filed under ETH2, so it has to be looked up too.
    """
    return (
        (A_ETH.identifier, A_ETH2.identifier)
        if treat_eth2_as_eth and asset == A_ETH else (asset,)
    )


def invalidate_swapped_asset_identities(
        write_cursor: DBCursor,
) -> bool:
    """Invalidate the reconciliation evidence of assets whose identity resolves elsewhere.

    `Bucket.from_event` resolves `swapped_for` when it maps an event to a bucket, so when an
    asset update sets that field, events already processed under the old identifier would still
    have metrics under it, and a saved comparison or stop would describe the old identity. The
    event rows themselves are not rewritten by an asset update.

    Every affected asset has its metrics, observations, checks and stops dropped, and a full
    reprocessing is requested with the stale marker. Stops are not merged into the target
    identity: the bucket never existed under it. Returns whether anything was invalidated, in
    which case the caller must process the whole history, not a scoped range.

    Only the global DB's swapped assets are examined, so this stays cheap: normally the set is
    empty or tiny.
    """
    with GlobalDBHandler().conn.read_ctx() as cursor:
        swapped = [
            row[0] for row in cursor.execute(
                'SELECT identifier FROM common_asset_details WHERE swapped_for IS NOT NULL',
            )
        ]
    affected = [
        asset for asset in swapped
        if write_cursor.execute(
            'SELECT 1 FROM event_metrics WHERE asset = ? LIMIT 1',
            (asset,),
        ).fetchone() is not None or write_cursor.execute(
            'SELECT 1 FROM history_events WHERE asset = ? LIMIT 1',
            (asset,),
        ).fetchone() is not None
    ]
    if len(affected) == 0:
        return False

    for statement in (
        'DELETE FROM event_metrics WHERE asset = ?',
        'DELETE FROM bucket_processing_stops WHERE asset = ?',
        'DELETE FROM bucket_balance_checks WHERE asset = ?',
        'DELETE FROM wallet_balance_observations WHERE asset = ?',
    ):
        write_cursor.executemany(statement, [(asset,) for asset in affected])

    write_cursor.executemany(
        'INSERT OR REPLACE INTO key_value_cache(name, value) VALUES (?, ?)',
        [
            (DBCacheStatic.STALE_BALANCES_FROM_TS.value, '0'),
            (DBCacheStatic.STALE_BALANCES_MODIFICATION_TS.value, str(ts_now_in_ms())),
        ],
    )
    return True
