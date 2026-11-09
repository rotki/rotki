"""Asset-specific observations of wallet balances, written by the successful balance queries.

A row exists only for an asset a successful query actually covered. Its amount may be zero:
that is a certified zero, not an absence. A missing row is unknown coverage, so a reader must
not turn it into zero. This is why the balance cache can't answer the question on its own: a
token without a cache row is either no longer held or was never queried, and the cache doesn't
say which.

Each write replaces the row and with it the observation identifier, which is a monotonic
integer, so a replacement is detectable even when both observations happened within the same
second. The identifier is what freshness checks compare, not only the observed_at timestamp.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from rotkehlchen.constants import ZERO
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.locations.chains import location_from_chain, location_to_chain
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import (
    CHAINS_WITH_TRANSACTIONS,
    SupportedBlockchain,
    Timestamp,
)

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping

    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.sqlite import DBCursor
    from rotkehlchen.locations.types import LocationIdentifier

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

type ObservationKey = tuple[str, str, str]
"""Location, address and asset of a wallet holding. The asset is the raw one stored by the
writer; readers fold ETH2 into ETH when the setting asks for it."""


class ObservationSource(StrEnum):
    """Which successful query produced an observation."""
    BALANCE_QUERY = 'balance_query'
    TOKEN_DETECTION = 'token_detection'


@dataclass(frozen=True)
class WalletObservation:
    """What a successful query saw for one asset of one wallet at one moment.

    amount is the actual amount, including an explicit zero. observed_at is when the query was
    issued, in seconds, never the time the row was written. observation_id identifies this
    query result among all the results for the same asset: a later row always has a greater
    identifier, even within the same second.
    """
    amount: FVal
    observed_at: Timestamp
    observation_id: int
    source: ObservationSource


def _location_of_chain(blockchain: SupportedBlockchain) -> LocationIdentifier | None:
    """The wallet location of a chain, None for a chain that is not a transaction EVM one."""
    if blockchain not in CHAINS_WITH_TRANSACTIONS:
        return None

    return location_from_chain(blockchain)


def record_wallet_observations(
        write_cursor: DBCursor,
        blockchain: SupportedBlockchain,
        address: str,
        amounts: Mapping[str, FVal],
        *,
        observed_at: Timestamp,
        source: ObservationSource,
) -> None:
    """Replace the observations of the given assets with what a successful query returned.

    Only the given assets are touched, so an address can have observations from several queries
    at different times. Writing a row for an amount of zero is how a query says the asset is
    not held; nothing is ever written from inference.

    The rows of one call share the observation identity of that query, taken from a monotonic
    counter. A replacement therefore always has a greater identity, even within the same second.
    """
    if len(amounts) == 0:
        return

    observation_id = _next_observation_id(write_cursor)
    write_cursor.executemany(
        'INSERT OR REPLACE INTO wallet_balance_observations('
        'blockchain, address, asset, amount, observed_at, source, observation_id) '
        'VALUES (?, ?, ?, ?, ?, ?, ?)',
        [
            (
                blockchain.serialize(), address, asset, str(amount), observed_at,
                source.value, observation_id,
            )
            for asset, amount in amounts.items()
        ],
    )


def _next_observation_id(write_cursor: DBCursor) -> int:
    """A monotonically increasing identity for one observation write.

    Kept in key_value_cache under this thread's write transaction so it survives restarts and
    never repeats, unlike a rowid after a deletion.
    """
    key = 'wallet_observation_sequence'
    write_cursor.execute(
        'UPDATE key_value_cache SET value = CAST(value AS INTEGER) + 1 WHERE name = ?',
        (key,),
    )
    if write_cursor.rowcount == 0:
        write_cursor.execute(
            'INSERT INTO key_value_cache(name, value) VALUES (?, ?)',
            (key, '1'),
        )

    return int(write_cursor.execute(
        'SELECT value FROM key_value_cache WHERE name = ?',
        (key,),
    ).fetchone()[0])


def get_wallet_observations(database: DBHandler) -> dict[ObservationKey, WalletObservation]:
    """Read every wallet observation, keyed by (location, address, asset).

    This is one query for the whole database, meant for callers that need many buckets at once.
    """
    with database.conn.read_ctx() as cursor:
        return get_wallet_observations_from_cursor(cursor)


def get_wallet_observations_from_cursor(
        cursor: DBCursor,
) -> dict[ObservationKey, WalletObservation]:
    observations: dict[ObservationKey, WalletObservation] = {}
    for identifier, blockchain, address, asset, amount, observed_at, source in cursor.execute(
        'SELECT observation_id, blockchain, address, asset, amount, observed_at, source '
        'FROM wallet_balance_observations',
    ):
        try:
            location = _location_of_chain(SupportedBlockchain.deserialize(blockchain))
        except DeserializationError:
            location = None
        if location is None:
            # a chain without a location is not a wallet one
            log.error('Ignoring wallet observation for unknown chain %s', blockchain)
            continue

        observations[location, address, asset] = WalletObservation(
            amount=FVal(amount),
            observed_at=Timestamp(observed_at),
            observation_id=identifier,
            source=ObservationSource(source),
        )

    return observations


def delete_wallet_observations(
        write_cursor: DBCursor,
        accounts: tuple[tuple[str, str], ...] = (),
        assets: tuple[str, ...] = (),
        blockchain: SupportedBlockchain | None = None,
        address: str | None = None,
) -> None:
    """Drop observations that a lifecycle operation made describe something else.

    Used when an account is removed, when its history is reset or when an asset identity is
    replaced. No reader may keep using the deleted rows as evidence.
    """
    if len(accounts) != 0:
        write_cursor.executemany(
            'DELETE FROM wallet_balance_observations WHERE blockchain = ? AND address = ?',
            [(location_to_chain(location).serialize(), account) for location, account in accounts],
        )
    if len(assets) != 0:
        write_cursor.executemany(
            'DELETE FROM wallet_balance_observations WHERE asset = ?',
            [(asset,) for asset in assets],
        )
    if blockchain is not None and address is not None:
        write_cursor.execute(
            'DELETE FROM wallet_balance_observations WHERE blockchain = ? AND address = ?',
            (blockchain.serialize(), address),
        )


def record_token_detection_observations(
        write_cursor: DBCursor,
        blockchain: SupportedBlockchain,
        address: str,
        amounts: Mapping[str, FVal],
        *,
        previous_assets: Collection[str],
        queried_assets: Collection[str],
        observed_at: Timestamp,
) -> None:
    """Record what a successful token detection run covered for one address.

    Detection queries the whole candidate list, so every candidate is covered. Writing a zero
    row for every candidate of every address would be thousands of rows, so zeros are kept for
    the assets that reconciliation can actually ask about: the tokens the address was detected
    to hold before, the ones present in its derived wallet buckets, and the ones already
    observed. A derived asset absent from all of them is not certified by this run and reads as
    missing coverage, which is conservative.

    Failed or partial detection runs never reach this function; the caller skips those
    addresses entirely, so no omission is ever turned into a zero.
    """
    amounts = dict(amounts)
    relevant: set[str] = set(previous_assets)
    if len(amounts) > 0 or len(previous_assets) > 0 or len(queried_assets) > 0:
        location = _location_of_chain(blockchain)
        if location is not None:
            with_db = write_cursor.execute(
                'SELECT DISTINCT asset FROM event_metrics WHERE location = ? AND '
                'location_label = ? AND protocol IS NULL '
                'UNION SELECT asset FROM bucket_balance_checks WHERE location = ? AND '
                'location_label = ? '
                'UNION SELECT asset FROM wallet_balance_observations WHERE blockchain = ? AND '
                'address = ?',
                (
                    location, address, location, address,
                    blockchain.serialize(), address,
                ),
            )
            relevant.update(row[0] for row in with_db)

    for asset in relevant.intersection(queried_assets):
        amounts.setdefault(asset, ZERO)

    record_wallet_observations(
        write_cursor=write_cursor,
        blockchain=blockchain,
        address=address,
        amounts=amounts,
        observed_at=observed_at,
        source=ObservationSource.TOKEN_DETECTION,
    )
