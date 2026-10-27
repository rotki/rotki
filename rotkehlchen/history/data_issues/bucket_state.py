from dataclasses import dataclass
from typing import TYPE_CHECKING

from rotkehlchen.constants.assets import A_ETH, A_ETH2
from rotkehlchen.fval import FVal
from rotkehlchen.types import EVM_LOCATIONS, SupportedBlockchain, TimestampMS

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from rotkehlchen.db.drivers.sqlite import DBCursor

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
        location.serialize_for_db() for location in EVM_LOCATIONS
        if SupportedBlockchain.from_location(location) == blockchain
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
    write_cursor.executemany(
        'DELETE FROM bucket_balance_checks WHERE location = ? AND location_label = ? '
        'AND NOT EXISTS (SELECT 1 FROM history_events WHERE location = ? AND location_label = ?)',
        [(location, label, location, label) for location, label in accounts if label is not None],
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
