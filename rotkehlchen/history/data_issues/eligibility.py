"""Whether a wallet bucket can be compared, and on what evidence.

The detector, the write-time revalidation and the read-side classification all ask this module,
so one bucket can't be comparable in one place and not in another. The only sources are the
database: observations written by the balance queries, the transaction query ranges and the
decoding state. Nothing here queries a chain.

Two properties are deliberately separate:

- Unsupported: no comparison can ever be made while the condition holds (disabled queries for
  the chain/address, a rebasing asset whose balance accrues without events, a non-EVM chain).
- Pending: the comparison could be made later (no observation covers the asset, the history has
  not been synced through the observation, transactions are not decoded yet, or a derived event
  is newer than the observation).

A missing observation is never turned into zero. A missing derived balance is only treated as a
verified history-free zero when the account's history is fully synced, nothing is pending
decoding, no processing stop exists and the bucket has no history events at all.
"""
from dataclasses import dataclass
from typing import TYPE_CHECKING

from rotkehlchen.assets.types import AssetFlag
from rotkehlchen.constants import ZERO
from rotkehlchen.db.cache import DBCacheDynamic
from rotkehlchen.db.constants import TX_DECODED
from rotkehlchen.db.evmtx import evm_tx_query_range_prefixes, intersect_evm_tx_query_ranges
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.data_issues.bucket_checks import (
    BucketReason,
    DerivedSnapshot,
    get_balance_checks,
)
from rotkehlchen.history.data_issues.bucket_state import (
    get_bucket_stops,
    make_bucket_key,
    wallet_bucket_assets,
)
from rotkehlchen.history.data_issues.observations import (
    ObservationSource,
    WalletObservation,
    get_wallet_observations_from_cursor,
)
from rotkehlchen.locations.chains import EVM_LOCATIONS, is_evm_location, location_to_chain
from rotkehlchen.types import SupportedBlockchain, Timestamp
from rotkehlchen.utils.misc import ts_sec_to_ms

if TYPE_CHECKING:
    from collections.abc import Mapping

    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.sqlite import DBCursor
    from rotkehlchen.history.data_issues.bucket_checks import BucketBalanceCheck, CheckKey


@dataclass(frozen=True)
class AccountSync:
    """How far the transaction history of an account was synced, in seconds.

    complete is False when any of the normal, internal or token transaction ranges is missing
    or starts after the genesis, since then earlier transactions were never queried.
    """
    synced_from: Timestamp | None
    synced_to: Timestamp | None
    complete: bool


@dataclass(frozen=True)
class WalletEvidence:
    """The facts behind one wallet bucket.

    amount is the covered observed amount. None means no successful query covered this asset,
    which is not the same as zero. observed_at and observation_id identify that observation.
    derived_snapshot is the input snapshot, or the synthetic zero of a verified history-free
    bucket so that callers don't have to build it (and can't build it when it isn't verified).
    """
    amount: FVal | None
    observed_at: Timestamp | None
    observation_id: int | None
    pending_reasons: tuple[BucketReason, ...]
    unsupported: tuple[BucketReason, ...]
    verified_history_free: bool
    history_synced_to: Timestamp | None
    derived_snapshot: DerivedSnapshot | None


@dataclass(frozen=True)
class WalletEvidenceContext:
    """The database state one read pass loaded, reused for every bucket of that pass."""
    observations: dict[tuple[str, str, str], WalletObservation]
    tracked: set[tuple[str, str]]
    disabled: set[tuple[str, str]]
    sync: dict[tuple[str, str], AccountSync]
    accounts_with_pending_decoding: set[tuple[str, str]]
    stopped_buckets: set[tuple[str, str, str, str]]
    rebasing_assets: frozenset[str]
    treat_eth2_as_eth: bool
    accounts_queried: set[tuple[str, str]]
    balance_checks: dict[CheckKey, BucketBalanceCheck]
    swapped_assets: frozenset[str]


def get_swapped_asset_ids() -> frozenset[str]:
    """Assets whose identity resolves to another one through `swapped_for`.

    `Bucket.from_event` applies that resolution while processing, so metrics, checks and
    observations stored under the source identifier would describe an identity the history no
    longer maps to. They are not refreshed until the next processing pass, so the read side must
    stop trusting them as soon as the global DB says the identity changed.
    """
    with GlobalDBHandler().conn.read_ctx() as cursor:
        return frozenset(row[0] for row in cursor.execute(
            'SELECT identifier FROM common_asset_details WHERE swapped_for IS NOT NULL',
        ))


def are_queries_disabled(blockchain: SupportedBlockchain, address: str) -> bool:
    """Whether the balance queries of the address are skipped, on their own or with their chain."""
    return (skipped := CachedSettings().get_settings().disabled_chain_queries.get(
        blockchain,
    )) is not None and (len(skipped) == 0 or address in skipped)


def _get_account_sync(
        cursor: DBCursor,
        blockchain: SupportedBlockchain,
        addresses: set[str],
) -> dict[str, AccountSync]:
    """Intersect the normal, internal and token transaction query ranges of each address.

    Missing any of them means the history of that address is not complete. An empty range
    (both ends zero) means it was never synced. A start after the genesis means transactions
    before it were never queried, so the history can't be called complete either.
    """
    prefixes = evm_tx_query_range_prefixes(blockchain)  # type: ignore[arg-type]
    ranges: dict[str, dict[str, tuple[Timestamp, Timestamp]]] = {
        address: {} for address in addresses
    }
    address_list = list(addresses)
    for prefix in prefixes:
        for start_idx in range(0, len(address_list), 500):  # stay below SQLite variable limits
            wanted = [
                f'{prefix}_{address}'
                for address in address_list[start_idx:start_idx + 500]
            ]
            for name, start, end in cursor.execute(
                f'SELECT name, start_ts, end_ts FROM used_query_ranges '
                f'WHERE name IN ({",".join("?" * len(wanted))})',
                tuple(wanted),
            ):
                address = name[len(prefix) + 1:]
                if address in ranges:
                    ranges[address][prefix] = (Timestamp(start), Timestamp(end))

    result: dict[str, AccountSync] = {}
    for address, per_prefix in ranges.items():
        # Same reducer as DBEvmTx.get_queried_range, fed from one query for the whole account
        # set instead of three queries per account.
        synced_from, synced_to = intersect_evm_tx_query_ranges(
            [per_prefix.get(prefix) for prefix in prefixes],
        )
        result[address] = AccountSync(
            synced_from=synced_from,
            synced_to=synced_to,
            complete=(
                len(per_prefix) == len(prefixes) and synced_from == 0 and synced_to > 0
            ),
        )

    return result


def _get_accounts_with_pending_decoding(
        cursor: DBCursor,
        scope: set[tuple[SupportedBlockchain, str]],
) -> set[tuple[SupportedBlockchain, str]]:
    """Addresses whose mapped transactions of the chain have no decoded marker.

    Transactions without a receipt are included, unlike the receipt-backed pending-decoder
    query, since such a transaction may not be decoded and its events are missing from history.
    """
    if len(scope) == 0:
        return set()

    chain_of_serialized = {
        blockchain.to_chain_id().serialize_for_db(): blockchain
        for blockchain, _ in scope
    }
    pending: set[tuple[SupportedBlockchain, str]] = set()
    for chain_id, address in cursor.execute(
        'SELECT DISTINCT C.chain_id, M.address FROM evmtx_address_mappings AS M '
        'INNER JOIN evm_transactions AS C ON M.tx_id = C.identifier '
        f'WHERE C.chain_id IN ({",".join("?" * len(chain_of_serialized))}) AND NOT EXISTS ('
        'SELECT 1 FROM evm_tx_mappings AS D WHERE D.tx_id = M.tx_id AND D.value = ?)',
        (*chain_of_serialized, TX_DECODED),
    ):
        if (blockchain := chain_of_serialized.get(chain_id)) is not None:
            pending.add((blockchain, address))

    return pending


def _get_accounts_queried(
        cursor: DBCursor,
        tracked: set[tuple[str, str]],
        observations: Mapping[tuple[str, str, str], WalletObservation],
) -> set[tuple[str, str]]:
    """Which accounts have at least one successful asset query behind them."""
    queried = {(location, address) for location, address, _ in observations}
    wallet_by_stamp = {
        DBCacheDynamic.LAST_ADDRESS_BALANCES_QUERY_TS.get_db_key(
            blockchain=location_to_chain(location).serialize(),
            address=address,
        ): (location, address)
        for location, address in tracked
    }
    for (name,) in cursor.execute(
        'SELECT name FROM key_value_cache WHERE name LIKE ?',
        ('address_balances_query_ts_%',),
    ):
        if (wallet := wallet_by_stamp.get(name)) is not None:
            queried.add(wallet)

    return queried


def load_wallet_evidence(database: DBHandler) -> WalletEvidenceContext:
    """Load, in one read pass, everything the per-bucket evidence needs."""
    with database.conn.read_ctx() as cursor:
        observations = get_wallet_observations_from_cursor(cursor)
        stopped_buckets = set(get_bucket_stops(cursor))
        balance_checks = get_balance_checks(cursor)
        location_of_chain = {
            location_to_chain(location).value: location
            for location in EVM_LOCATIONS
        }
        tracked: set[tuple[str, str]] = set()
        disabled: set[tuple[str, str]] = set()
        scope: set[tuple[SupportedBlockchain, str]] = set()
        for blockchain, account in cursor.execute(
            'SELECT blockchain, account FROM blockchain_accounts',
        ):
            if (location := location_of_chain.get(blockchain)) is None:
                continue

            tracked.add(wallet := (location, account))
            chain = SupportedBlockchain(blockchain)
            if are_queries_disabled(chain, account):
                disabled.add(wallet)
            scope.add((chain, account))

        sync: dict[tuple[str, str], AccountSync] = {}
        pending_decoding: set[tuple[str, str]] = set()
        for blockchain in {chain for chain, _ in scope}:
            addresses = {address for chain, address in scope if chain == blockchain}
            location = location_of_chain[blockchain.value]
            for address, account_sync in _get_account_sync(
                cursor=cursor,
                blockchain=blockchain,
                addresses=addresses,
            ).items():
                sync[location, address] = account_sync

            pending_decoding.update(
                (location, address)
                for _, address in _get_accounts_with_pending_decoding(
                    cursor=cursor,
                    scope={(blockchain, address) for address in addresses},
                )
            )

        accounts_queried = _get_accounts_queried(
            cursor=cursor,
            tracked=tracked,
            observations=observations,
        )

    return WalletEvidenceContext(
        observations=observations,
        tracked=tracked,
        disabled=disabled,
        sync=sync,
        accounts_with_pending_decoding=pending_decoding,
        stopped_buckets=stopped_buckets,
        rebasing_assets=frozenset(GlobalDBHandler.get_asset_ids_with_flag(AssetFlag.REBASING)),
        treat_eth2_as_eth=CachedSettings().get_entry('treat_eth2_as_eth') is True,
        accounts_queried=accounts_queried,
        balance_checks=balance_checks,
        swapped_assets=get_swapped_asset_ids(),
    )


def _get_observation(
        location: str,
        address: str,
        asset: str,
        observations: Mapping[tuple[str, str, str], WalletObservation],
        treat_eth2_as_eth: bool,
) -> WalletObservation | None:
    """The latest observation covering the asset of a wallet bucket.

    With ETH2 treated as ETH, the wallet bucket aggregates both identifiers. The native ETH row
    is the one the address balance query writes, so take the latest of them.
    """
    found = [
        observation
        for candidate in wallet_bucket_assets(asset=asset, treat_eth2_as_eth=treat_eth2_as_eth)
        if (observation := observations.get((location, address, candidate))) is not None
    ]
    if len(found) == 0:
        return None

    return max(found, key=lambda observation: observation.observation_id)


def _has_history_events(
        cursor: DBCursor,
        location: str,
        address: str,
        assets: tuple[str, ...],
) -> bool:
    return cursor.execute(
        'SELECT 1 FROM history_events WHERE location = ? AND location_label = ? '
        f'AND asset IN ({",".join("?" * len(assets))}) LIMIT 1',
        (location, address, *assets),
    ).fetchone() is not None


def _has_stop(
        cursor: DBCursor,
        location: str,
        address: str,
        assets: tuple[str, ...],
) -> bool:
    return cursor.execute(
        'SELECT 1 FROM bucket_processing_stops WHERE location = ? AND location_label = ? '
        f"AND protocol = '' AND asset IN ({",".join("?" * len(assets))}) LIMIT 1",
        (location, address, *assets),
    ).fetchone() is not None


def _assemble_evidence(
        *,
        location: str,
        address: str,
        asset: str,
        derived: DerivedSnapshot | None,
        observation: WalletObservation | None,
        account_sync: AccountSync,
        pending_decoding: bool,
        is_disabled: bool,
        is_queried: bool,
        has_stop: bool,
        has_history_events: bool,
        rebasing_assets: frozenset[str],
        is_swapped_identity: bool,
        treat_eth2_as_eth: bool,
) -> WalletEvidence:
    if is_evm_location(location) is False:
        return WalletEvidence(
            amount=None,
            observed_at=None,
            observation_id=None,
            pending_reasons=(),
            unsupported=(BucketReason.NON_EVM_CHAIN,),
            verified_history_free=False,
            history_synced_to=None,
            derived_snapshot=derived,
        )

    unsupported: list[BucketReason] = []
    if is_disabled:
        unsupported.append(BucketReason.QUERIES_DISABLED)
    if asset in rebasing_assets:
        unsupported.append(BucketReason.REBASING)

    if is_swapped_identity:
        # The bucket's identity now resolves elsewhere. Nothing saved under the old identifier
        # is evidence for it, and no new comparison is made until processing rebuilds it.
        observation = None
        has_history_events = True  # never call it history-free

    derived_latest_ts = None if derived is None else derived.latest_ts
    pending: list[BucketReason] = [BucketReason.DERIVED_SNAPSHOT_CHANGED] if is_swapped_identity else []  # noqa: E501
    if observation is None:
        pending.append(
            BucketReason.ASSET_COVERAGE_MISSING
            if is_queried else
            BucketReason.OBSERVATION_MISSING,
        )
    elif (
        derived_latest_ts is not None and
        ts_sec_to_ms(observation.observed_at) < derived_latest_ts
    ):
        pending.append(BucketReason.OBSERVATION_STALE)

    if (
        account_sync.complete is False or
        (
            observation is not None and
            (account_sync.synced_to is None or account_sync.synced_to < observation.observed_at)
        )
    ):
        pending.append(BucketReason.HISTORY_NOT_SYNCED)
    if pending_decoding:
        pending.append(BucketReason.HISTORY_PENDING_DECODING)

    verified_history_free = (
        derived is None and
        account_sync.complete and
        pending_decoding is False and
        is_disabled is False and
        has_stop is False and
        has_history_events is False
    )
    snapshot = derived
    if snapshot is None and verified_history_free:
        snapshot = DerivedSnapshot(
            balance=ZERO,
            latest_event_identifier=None,
            latest_ts=None,
            is_history_free=True,
        )

    return WalletEvidence(
        amount=None if observation is None else observation.amount,
        observed_at=None if observation is None else observation.observed_at,
        observation_id=None if observation is None else observation.observation_id,
        pending_reasons=tuple(pending),
        unsupported=tuple(unsupported),
        verified_history_free=verified_history_free,
        history_synced_to=account_sync.synced_to,
        derived_snapshot=snapshot,
    )


def _get_bucket_evidence(
        context: WalletEvidenceContext,
        cursor: DBCursor,
        location: str,
        address: str,
        asset: str,
        derived: DerivedSnapshot | None,
) -> WalletEvidence:
    if is_evm_location(location) is False:
        return _assemble_evidence(
            location=location,
            address=address,
            asset=asset,
            derived=derived,
            observation=None,
            account_sync=AccountSync(None, None, False),
            pending_decoding=False,
            is_disabled=False,
            is_queried=False,
            has_stop=False,
            has_history_events=False,
            rebasing_assets=context.rebasing_assets,
            is_swapped_identity=asset in context.swapped_assets,
            treat_eth2_as_eth=context.treat_eth2_as_eth,
        )

    wallet = (location, address)
    bucket_assets = wallet_bucket_assets(
        asset=asset,
        treat_eth2_as_eth=context.treat_eth2_as_eth,
    )
    return _assemble_evidence(
        location=location,
        address=address,
        asset=asset,
        derived=derived,
        observation=_get_observation(
            location=location,
            address=address,
            asset=asset,
            observations=context.observations,
            treat_eth2_as_eth=context.treat_eth2_as_eth,
        ),
        account_sync=context.sync.get(wallet, AccountSync(None, None, False)),
        pending_decoding=wallet in context.accounts_with_pending_decoding,
        is_disabled=wallet in context.disabled,
        is_queried=wallet in context.accounts_queried,
        has_stop=any(
            make_bucket_key(
                location=location,
                location_label=address,
                protocol=None,
                asset=stopped_asset,
            ) in context.stopped_buckets
            for stopped_asset in bucket_assets
        ),
        has_history_events=_has_history_events(
            cursor=cursor,
            location=location,
            address=address,
            assets=bucket_assets,
        ) if derived is None else False,
        rebasing_assets=context.rebasing_assets,
        is_swapped_identity=asset in context.swapped_assets,
        treat_eth2_as_eth=context.treat_eth2_as_eth,
    )


def wallet_evidence_for_bucket(
        context: WalletEvidenceContext,
        cursor: DBCursor,
        location: str,
        address: str,
        asset: str,
        derived: DerivedSnapshot | None,
) -> WalletEvidence:
    """Evidence for a bucket of an already loaded read pass."""
    return _get_bucket_evidence(
        context=context,
        cursor=cursor,
        location=location,
        address=address,
        asset=asset,
        derived=derived,
    )


def get_wallet_evidence(
        database: DBHandler,
        location: str,
        address: str,
        asset: str,
        derived: DerivedSnapshot | None,
        swapped_assets: frozenset[str] | None = None,
) -> WalletEvidence:
    """Fresh evidence for one bucket, read inside the caller's write transaction.

    Used to revalidate a comparison right before writing it, so an account removal, a history
    reset or an identity change that happened during the run can't be undone by the write.
    """
    if is_evm_location(location) is False:
        return _assemble_evidence(
            location=location,
            address=address,
            asset=asset,
            derived=derived,
            observation=None,
            account_sync=AccountSync(None, None, False),
            pending_decoding=False,
            is_disabled=False,
            is_queried=False,
            has_stop=False,
            has_history_events=False,
            rebasing_assets=frozenset(),
            is_swapped_identity=False,
            treat_eth2_as_eth=False,
        )

    chain = location_to_chain(location)
    treat_eth2_as_eth = CachedSettings().get_entry('treat_eth2_as_eth') is True
    asset_candidates = wallet_bucket_assets(
        asset=asset,
        treat_eth2_as_eth=treat_eth2_as_eth,
    )
    with database.conn.read_ctx() as cursor:
        observations = {
            (location, address_key, row_asset): WalletObservation(
                amount=FVal(amount),
                observed_at=Timestamp(observed_at),
                observation_id=identifier,
                source=ObservationSource(source),
            )
            for identifier, address_key, row_asset, amount, observed_at, source in cursor.execute(
                'SELECT observation_id, address, asset, amount, observed_at, source '
                'FROM wallet_balance_observations WHERE blockchain = ? AND address = ? '
                f'AND asset IN ({",".join("?" * len(asset_candidates))})',
                (chain.serialize(), address, *asset_candidates),
            )
        }
        account_sync = _get_account_sync(
            cursor=cursor,
            blockchain=chain,
            addresses={address},
        ).get(address, AccountSync(None, None, False))
        pending_decoding = len(_get_accounts_with_pending_decoding(
            cursor=cursor,
            scope={(chain, address)},
        )) != 0
        is_queried = len(observations) != 0 or database.get_dynamic_cache(
            cursor=cursor,
            name=DBCacheDynamic.LAST_ADDRESS_BALANCES_QUERY_TS,
            blockchain=chain.serialize(),
            address=address,
        ) is not None
        has_stop = _has_stop(cursor, location, address, asset_candidates)
        has_history_events = _has_history_events(cursor, location, address, asset_candidates)

    return _assemble_evidence(
        location=location,
        address=address,
        asset=asset,
        derived=derived,
        observation=_get_observation(
            location=location,
            address=address,
            asset=asset,
            observations=observations,
            treat_eth2_as_eth=treat_eth2_as_eth,
        ),
        account_sync=account_sync,
        pending_decoding=pending_decoding,
        is_disabled=are_queries_disabled(chain, address),
        is_queried=is_queried,
        has_stop=has_stop,
        has_history_events=has_history_events,
        rebasing_assets=frozenset(GlobalDBHandler.get_asset_ids_with_flag(AssetFlag.REBASING)),
        is_swapped_identity=asset in (
            get_swapped_asset_ids() if swapped_assets is None else swapped_assets
        ),
        treat_eth2_as_eth=treat_eth2_as_eth,
    )


def get_wallet_evidence_bulk(
        database: DBHandler,
        derived: Mapping[CheckKey, DerivedSnapshot | None],
        context: WalletEvidenceContext | None = None,
) -> dict[CheckKey, WalletEvidence]:
    """Evidence for several wallet buckets, from one database read.

    Returns exactly the given keys. A key for an account that is no longer tracked or whose
    chain is not an EVM one still gets an entry, with the matching unsupported reason, so the
    caller doesn't need a second scope check.
    """
    if context is None:
        context = load_wallet_evidence(database)

    with database.conn.read_ctx() as cursor:
        return {
            (location, address, asset): wallet_evidence_for_bucket(
                context=context,
                cursor=cursor,
                location=location,
                address=address,
                asset=asset,
                derived=snapshot,
            ) for (location, address, asset), snapshot in derived.items()
        }
