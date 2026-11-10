"""Read-only reconciliation report: which buckets are trustworthy, which stopped, and why.

The report enumerates every bucket that is in scope for the reconciliation view, from the union
of the latest reduced balance metrics, the saved comparisons, the current processing stops and
the eligible observations. No request scans history events or reconstructs a stop from issues:
the stops are read from `bucket_processing_stops`, which the processor is the only writer of.

One ordered classifier (bucket_checks.classify_bucket) decides the status of every bucket, and
the same classification feeds the account summaries, the status filter and the bucket rows. That
is why a bucket can never be counted in one status and listed under another.

Accounting:
- Ignored assets are filtered before classification, like balance processing does.
- Wallet buckets of blockchain locations are limited to tracked accounts. Protocol buckets are
  not tied to a tracked wallet (a validator pubkey, for example, is not an account), so they are
  enumerated with their own not_compared reason instead of being filtered out.
- Exchange locations are enumerated in full and flagged as exchanges, so the view can present
  them as an informational note without applying wallet account filtering.
- Zero is never used for a missing side: a bucket without a balance metric has no derived
  balance, and a bucket without a covered observation has no observed balance.

Wallet observation and comparison eligibility is not computed here. It comes from
`history/data_issues/eligibility.py`, so the detector, the write-time revalidation and this read
side share exactly one set of facts.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from rotkehlchen.balances.historical import HistoricalBalancesManager
from rotkehlchen.constants.assets import A_ETH, A_ETH2
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.exchanges.constants import ALL_SUPPORTED_EXCHANGES
from rotkehlchen.fval import FVal
from rotkehlchen.history.data_issues.bucket_checks import (
    BucketBalanceCheck,
    BucketClassification,
    BucketReason,
    BucketStatus,
    DerivedSnapshot,
    classify_bucket,
    get_balance_checks,
)
from rotkehlchen.history.data_issues.bucket_state import (
    BucketStop,
    get_bucket_stops,
)
from rotkehlchen.history.data_issues.constants import IssueKind, IssueState
from rotkehlchen.history.data_issues.eligibility import (
    WalletEvidence,
    get_wallet_evidence_bulk,
)
from rotkehlchen.history.data_issues.observations import get_wallet_observations
from rotkehlchen.locations.chains import (
    BLOCKCHAIN_LOCATIONS,
    location_of_chain_balances,
)
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import (
    EventMetricKey,
    SupportedBlockchain,
    Timestamp,
    TimestampMS,
)
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Mapping, Sequence

    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.sqlite import DBCursor

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

DEFAULT_PAGE_SIZE: Final = 50
MAX_PAGE_SIZE: Final = 500

type BucketKey = tuple[str, str | None, str | None, str]
"""Location, account label, protocol and asset of a bucket, with None for a missing account
label or protocol. The same shape the processing stops use internally."""

type WalletKey = tuple[str, str, str]
"""Location, account label and asset of a wallet bucket."""

ZERO_STATUS_COUNTS: Final[dict[BucketStatus, int]] = dict.fromkeys(BucketStatus, 0)
_ETH_IDENTIFIER: Final = A_ETH.identifier


@dataclass(frozen=True)
class ReconciliationBucket:
    """One bucket of the report, after classification and normalization.

    derived_balance and observed_balance are the current values of each side, and check is the
    saved comparison that the reconciled/mismatch verdict comes from. A newer observation with an
    older verdict is reported as pending by the classifier and never blended into one check.
    """
    location: str
    location_label: str | None
    protocol: str | None
    asset: str
    status: BucketStatus
    reasons: tuple[BucketReason, ...]
    derived_balance: FVal | None
    observed_balance: FVal | None
    observed_at: Timestamp | None
    last_event_ts: TimestampMS | None
    issue_id: int | None
    check: BucketBalanceCheck | None
    stop: BucketStop | None

    @property
    def delta(self) -> FVal | None:
        """The signed difference of the saved comparison, None without one."""
        if self.check is None:
            return None

        return self.check.observed_balance - self.check.derived_balance


@dataclass(frozen=True)
class ReconciliationAccount:
    """One (location, account label) group of the report.

    counts always describes every bucket of the account, never just the filtered or paginated
    rows: the totals of the summary must not change because a status filter is applied.
    """
    location: str
    location_label: str | None
    is_exchange: bool
    counts: Mapping[BucketStatus, int]
    last_compared_at: Timestamp | None
    last_event_ts: TimestampMS | None
    history_synced_to: Timestamp | None
    buckets: tuple[ReconciliationBucket, ...] = ()


@dataclass(frozen=True)
class ReconciliationReport:
    """The reconciliation summary and, when an account is scoped, its paginated bucket rows."""
    stale: bool
    processing: bool
    totals: Mapping[BucketStatus, int]
    accounts: tuple[ReconciliationAccount, ...]
    entries: tuple[ReconciliationBucket, ...] = ()  # only for a scoped account
    entries_total: int = 0  # bucket rows of the scoped account, before the status filter
    entries_found: int = 0  # bucket rows matching the status filter
    limit: int = DEFAULT_PAGE_SIZE
    offset: int = 0
    scoped: bool = False


def _read_latest_metrics(
        cursor: DBCursor,
        treat_eth2_as_eth: bool,
        location_filter: str | None = None,
        label_filter: str | None = None,
        match_null_label: bool = False,
) -> dict[BucketKey, DerivedSnapshot]:
    """The latest balance metric of every in-scope bucket, whatever its protocol.

    Unlike HistoricalBalancesManager.get_balances this keeps zero balances and does not filter
    on a history timestamp, because the report must list buckets whose latest derived balance is
    exactly zero. Bare columns take their values from the row holding MAX(sort_key), see
    https://www.sqlite.org/lang_select.html#bareagg.

    The account filters are pushed into the largest table of the report. They never change the
    result, because the same filters are applied to the merged bucket identities afterwards.
    """
    filters, bindings = '', [EventMetricKey.BALANCE.serialize(), 'ignored_asset']
    if location_filter is not None:
        filters += ' AND location = ?'
        bindings.append(location_filter)
    if match_null_label is True:
        filters += ' AND location_label IS NULL'
    elif label_filter is not None:
        filters += ' AND location_label = ?'
        bindings.append(label_filter)

    metrics: dict[BucketKey, DerivedSnapshot] = {}
    for location, label, protocol, asset, value, event_identifier, timestamp, _sort_key in cursor.execute(  # noqa: E501
        'SELECT location, location_label, protocol, asset, metric_value, event_identifier, '
        'timestamp, MAX(sort_key) FROM event_metrics WHERE metric_key = ? AND asset NOT IN ('
        'SELECT value FROM multisettings WHERE name = ?) '
        f'{filters} GROUP BY location, location_label, protocol, asset',
        bindings,
    ):
        key: BucketKey = (location, label, protocol, asset)
        if treat_eth2_as_eth and protocol is None and asset == A_ETH2.identifier:
            key = (location, label, protocol, _ETH_IDENTIFIER)

        timestamp_ms = TimestampMS(timestamp)
        if (entry := metrics.get(key)) is None:
            metrics[key] = DerivedSnapshot(
                balance=FVal(value),
                latest_event_identifier=event_identifier,
                latest_ts=timestamp_ms,
            )
            continue

        latest_event_identifier, latest_ts = entry.latest_event_identifier, entry.latest_ts
        if latest_ts is None or timestamp_ms > latest_ts:
            latest_event_identifier, latest_ts = event_identifier, timestamp_ms

        metrics[key] = DerivedSnapshot(
            balance=entry.balance + FVal(value),
            latest_event_identifier=latest_event_identifier,
            latest_ts=latest_ts,
        )

    return metrics


def _normalize_wallet_asset(asset: str, treat_eth2_as_eth: bool) -> str:
    """The asset a wallet bucket is filed under, folding ETH2 into ETH when so configured."""
    if treat_eth2_as_eth is False or asset != A_ETH2.identifier:
        return asset

    return _ETH_IDENTIFIER


def _read_checks(
        cursor: DBCursor,
        treat_eth2_as_eth: bool,
        ignored_assets: set[str],
) -> dict[BucketKey, BucketBalanceCheck]:
    """The saved comparisons keyed by their full bucket key, with ETH2 folded like metrics.

    The ignored-asset filter applies to the raw asset, before folding: an ignored ETH2 must not
    sneak back into the ETH bucket because its saved comparison was filed under the other one.
    """
    checks: dict[BucketKey, BucketBalanceCheck] = {}
    for check in get_balance_checks(cursor).values():
        if check.asset in ignored_assets:
            continue
        key: BucketKey = (
            check.location,
            check.location_label,
            None,
            _normalize_wallet_asset(check.asset, treat_eth2_as_eth),
        )
        if (existing := checks.get(key)) is None or check.compared_at > existing.compared_at:
            checks[key] = check

    return checks


def _read_stops(
        cursor: DBCursor,
        treat_eth2_as_eth: bool,
        ignored_assets: set[str],
) -> dict[BucketKey, BucketStop]:
    """The current processing stops keyed by their full bucket key, normalized like metrics."""
    stops: dict[BucketKey, BucketStop] = {}
    for (location, label, protocol, asset), stop in get_bucket_stops(cursor).items():
        if asset in ignored_assets:
            continue
        # The stop table uses '' for a wallet bucket and for a missing label, not NULL.
        normalized_asset = (
            _normalize_wallet_asset(asset, treat_eth2_as_eth)
            if not protocol else asset
        )
        key: BucketKey = (location, label or None, protocol or None, normalized_asset)
        if (existing := stops.get(key)) is None or stop.event_timestamp > existing.event_timestamp:
            stops[key] = stop

    return stops


def _read_tracked_accounts(cursor: DBCursor) -> dict[str, set[str]]:
    """The tracked accounts of every blockchain location."""
    tracked: dict[str, set[str]] = defaultdict(set)
    for blockchain, account in cursor.execute(
        'SELECT blockchain, account FROM blockchain_accounts',
    ):
        try:
            chain = SupportedBlockchain(blockchain)
        except ValueError:
            continue

        try:
            location = location_of_chain_balances(chain)
        except KeyError:
            continue

        tracked[location].add(account)

    return tracked


def _read_issue_ids(
        cursor: DBCursor,
        treat_eth2_as_eth: bool,
) -> tuple[dict[WalletKey, int], dict[tuple[BucketKey, int], int]]:
    """The issue to link from a wallet bucket and from a stopped bucket.

    The mismatch links to the newest non-resolved issue of the exact wallet bucket, whatever
    other buckets of the same asset say. The stop links to the negative balance issue of its
    actual stopping event and full bucket, not to any issue of the asset. Its state is
    irrelevant: a dismissed issue still describes the stop that the processing state proves.
    Keying by the bucket matters because one event can stop a wallet bucket and a protocol
    bucket; each links only its own issue, and a stop without one is still blocked with no link.

    Returns (mismatch issues keyed by (location, label, asset), negative balance issues keyed by
    the full bucket key and the stopping event identifier).
    """
    mismatches: dict[WalletKey, int] = {}
    negatives: dict[tuple[BucketKey, int], int] = {}
    for issue_id, kind, location, label, protocol, asset, event_identifier, state in cursor.execute(  # noqa: E501
        'SELECT id, kind, location, location_label, protocol, asset, event_identifier, state '
        'FROM data_issues WHERE kind IN (?, ?)',
        (IssueKind.CURRENT_BALANCE_MISMATCH.value, IssueKind.NEGATIVE_BALANCE.value),
    ):
        issue_label = label or None
        issue_protocol = protocol or None
        issue_asset = (
            _normalize_wallet_asset(asset, treat_eth2_as_eth)
            if issue_protocol is None else asset
        )
        if kind == IssueKind.CURRENT_BALANCE_MISMATCH.value:
            if (
                state == IssueState.RESOLVED.value or
                issue_label is None or
                issue_protocol is not None
            ):
                continue
            wallet: WalletKey = (location, issue_label, issue_asset)
            if issue_id > mismatches.get(wallet, 0):  # no ORDER BY, pick the newest explicitly
                mismatches[wallet] = issue_id
        elif event_identifier is not None:
            negatives[(
                location,
                issue_label,
                issue_protocol,
                issue_asset,
            ), event_identifier] = issue_id

    return mismatches, negatives


def _unsupported_reasons(
        location: str,
        protocol: str | None,
) -> tuple[BucketReason, ...]:
    """The comparison-unsupported reasons that come from the bucket identity alone.

    Wallet facts (disabled queries, rebasing, non-EVM) come from the evidence reader, so they
    are not duplicated here.
    """
    if location in ALL_SUPPORTED_EXCHANGES:
        return (BucketReason.EXCHANGE,)
    if location not in BLOCKCHAIN_LOCATIONS:
        return (BucketReason.UNSUPPORTED_LOCATION,)
    if protocol is not None:
        return (BucketReason.PROTOCOL_BUCKET,)

    return ()


def _in_scope(
        key: BucketKey,
        ignored_assets: set[str],
        tracked_accounts: Mapping[str, set[str]],
        location: str | None,
        location_label: str | None,
        null_label: bool,
) -> bool:
    """Whether the bucket belongs to the requested scope.

    Ignored assets never appear. A wallet bucket of a blockchain location exists only for a
    tracked account. Protocol buckets and buckets of other locations are not tied to a tracked
    wallet, so they are not filtered by account.

    null_label selects the account whose label is missing, which is how a protocol bucket
    without an account is addressed: an empty location_label is an explicit request for it, while
    no location_label at all means no account filter.
    """
    bucket_location, label, protocol, asset = key
    if asset in ignored_assets:
        return False
    if location is not None and bucket_location != location:
        return False
    if null_label is True:
        if label is not None:
            return False
    elif location_label is not None and label != location_label:
        return False
    return not (
        protocol is None and
        label is not None and
        bucket_location in BLOCKCHAIN_LOCATIONS and
        label not in tracked_accounts.get(bucket_location, set())
    )


def _observed_wallet_keys(
        observations: Mapping[WalletKey, object],
        treat_eth2_as_eth: bool,
) -> set[BucketKey]:
    """The wallet bucket identities of every on-chain observation, ETH2 folded into ETH.

    This is only used to discover holdings that have no balance metric, check or stop yet; the
    facts themselves come from the evidence reader.
    """
    keys: set[BucketKey] = set()
    keys.update((
            location,
            address,
            None,
            _normalize_wallet_asset(asset, treat_eth2_as_eth),
        ) for location, address, asset in observations)

    return keys


def get_reconciliation_report(  # one branch per scope rule
        database: DBHandler,
        location: str | None = None,
        location_label: str | None = None,
        statuses: Collection[BucketStatus] | None = None,
        limit: int = DEFAULT_PAGE_SIZE,
        offset: int = 0,
        now: Timestamp | None = None,
) -> ReconciliationReport:
    """Build the reconciliation report. Pure read: no writes, no network, no event scans.

    location/location_label scope the accounts. Giving both also returns the bucket rows of that
    account. statuses filters those rows only; summary totals and per-account counts are always
    unfiltered. limit/offset page the filtered rows.
    """
    now = ts_now() if now is None else now
    treat_eth2_as_eth = CachedSettings().get_entry('treat_eth2_as_eth') is True
    tolerance = CachedSettings().get_settings().asset_movement_amount_tolerance
    scoped = location is not None and location_label is not None
    # An empty (or blank) location_label asks for the account whose label is missing. It is a
    # real scope, not the absence of one: protocol buckets without an account live there.
    null_label = location_label is not None and location_label.strip() == ''
    scope_label = None if null_label else location_label
    limit = min(max(limit, 1), MAX_PAGE_SIZE)
    offset = max(offset, 0)

    with database.conn.read_ctx() as cursor:
        ignored_assets = database.get_ignored_asset_ids(cursor)
        stale = database.get_static_cache(
            cursor=cursor,
            name=DBCacheStatic.STALE_BALANCES_FROM_TS,
        ) is not None
        tracked_accounts = _read_tracked_accounts(cursor)
        metrics = _read_latest_metrics(
            cursor=cursor,
            treat_eth2_as_eth=treat_eth2_as_eth,
            location_filter=location,
            label_filter=scope_label,
            match_null_label=null_label,
        )
        checks = _read_checks(cursor, treat_eth2_as_eth, ignored_assets)
        stops = _read_stops(cursor, treat_eth2_as_eth, ignored_assets)
        mismatch_issues, negative_issues = _read_issue_ids(cursor, treat_eth2_as_eth)

    observations = _observed_wallet_keys(
        observations={
            key: observation
            for key, observation in get_wallet_observations(database).items()
            if key[2] not in ignored_assets
        },
        treat_eth2_as_eth=treat_eth2_as_eth,
    )
    candidates = {
        key for key in (*metrics, *checks, *stops, *observations)
        if _in_scope(
            key=key,
            ignored_assets=ignored_assets,
            tracked_accounts=tracked_accounts,
            location=location,
            location_label=scope_label,
            null_label=null_label,
        )
    }
    wallet_keys = {
        (bucket_location, label, asset)
        for bucket_location, label, protocol, asset in candidates
        if protocol is None and label is not None and bucket_location in BLOCKCHAIN_LOCATIONS
    }
    evidence = get_wallet_evidence_bulk(
        database=database,
        derived={
            key: metrics.get((key[0], key[1], None, key[2]))
            for key in wallet_keys
        },
    )

    processing = HistoricalBalancesManager(database)._has_unprocessed_events(
        where_clause='1=1',
        bindings=(),
    )

    accounted: dict[BucketKey, ReconciliationBucket] = {}
    for key in candidates:
        bucket_location, label, protocol, asset = key
        wallet_key: WalletKey = (bucket_location, label, asset)  # type: ignore[assignment]
        wallet_evidence: WalletEvidence | None = (
            evidence.get(wallet_key) if protocol is None and label is not None else None
        )
        derived = (
            wallet_evidence.derived_snapshot
            if wallet_evidence is not None else metrics.get(key)
        )
        check = checks.get(key) if protocol is None and label is not None else None
        stop = stops.get(key)
        unsupported = tuple(dict.fromkeys((
            *_unsupported_reasons(location=bucket_location, protocol=protocol),
            *(wallet_evidence.unsupported if wallet_evidence is not None else ()),
        )))
        verdict = _classify(
            stop=stop,
            unsupported=unsupported,
            check=check,
            derived=derived,
            evidence=wallet_evidence,
            stale=stale,
            now=now,
            tolerance=tolerance,
        )
        accounted[key] = ReconciliationBucket(
            location=bucket_location,
            location_label=label,
            protocol=protocol,
            asset=asset,
            status=verdict.status,
            reasons=verdict.reasons,
            derived_balance=None if derived is None else derived.balance,
            observed_balance=None if wallet_evidence is None else wallet_evidence.amount,
            observed_at=None if wallet_evidence is None else wallet_evidence.observed_at,
            last_event_ts=None if derived is None else derived.latest_ts,
            issue_id=(
                negative_issues.get((key, stop.event_identifier))
                if stop is not None else (
                    mismatch_issues.get(wallet_key)
                    if protocol is None and label is not None else None
                )
            ),
            check=check,
            stop=stop,
        )

    totals: dict[BucketStatus, int] = dict(ZERO_STATUS_COUNTS)
    grouped: dict[tuple[str, str | None], list[ReconciliationBucket]] = defaultdict(list)
    for bucket in accounted.values():
        totals[bucket.status] += 1
        grouped[bucket.location, bucket.location_label].append(bucket)

    for tracked_location, tracked_labels in tracked_accounts.items():
        for tracked_account in tracked_labels:
            # A tracked account exists for the view even before it has any bucket: no metric,
            # no check and no observation is not the same as no account.
            grouped.setdefault((tracked_location, tracked_account), [])

    scoped_rows: list[ReconciliationBucket] = []
    scoped_page: list[ReconciliationBucket] = []
    scoped_found = 0
    if location is not None and location_label is not None:  # account scoped
        scoped_rows = sorted(
            grouped.get((location, scope_label), []),
            key=_bucket_sort_key,
        )
        wanted_statuses = set(statuses) if statuses is not None else set(BucketStatus)
        scoped_filtered = [row for row in scoped_rows if row.status in wanted_statuses]
        scoped_found = len(scoped_filtered)
        scoped_page = scoped_filtered[offset:offset + limit]

    accounts = [
        ReconciliationAccount(
            location=account_location,
            location_label=account_label,
            is_exchange=account_location in ALL_SUPPORTED_EXCHANGES,
            counts=_count_statuses(buckets=rows),
            last_compared_at=_max_timestamp(
                row.check.compared_at for row in rows if row.check is not None
            ),
            last_event_ts=_max_ts_ms(
                row.last_event_ts for row in rows if row.last_event_ts is not None
            ),
            history_synced_to=_history_synced_to(rows=rows, evidence=evidence),
            buckets=tuple(scoped_page) if scoped else (),
        )
        for (account_location, account_label), rows in sorted(
            grouped.items(),
            key=lambda item: (item[0][0], item[0][1] or ''),
        )
        if (location is None or account_location == location) and (
            (null_label is True and account_label is None) or
            (null_label is False and (
                location_label is None or account_label == location_label
            ))
        )
    ]

    if scoped is False:
        return ReconciliationReport(
            stale=stale,
            processing=processing,
            totals=totals,
            accounts=tuple(accounts),
        )

    return ReconciliationReport(
        stale=stale,
        processing=processing,
        totals=totals,
        accounts=tuple(accounts),
        entries=tuple(scoped_page),
        entries_total=len(scoped_rows),
        entries_found=scoped_found,
        limit=limit,
        offset=offset,
        scoped=True,
    )


def _classify(
        stop: BucketStop | None,
        unsupported: Collection[BucketReason],
        check: BucketBalanceCheck | None,
        derived: DerivedSnapshot | None,
        evidence: WalletEvidence | None,
        stale: bool,
        now: Timestamp,
        tolerance: FVal,
) -> BucketClassification:
    """Classify one bucket with the shared ordered classifier and its evidence facts."""
    return classify_bucket(
        is_blocked=stop is not None,
        unsupported=unsupported,
        check=check,
        derived=derived,
        is_derived_history_stale=stale,
        latest_observed_at=None if evidence is None else evidence.observed_at,
        now=now,
        tolerance=tolerance,
        latest_observation_id=None if evidence is None else evidence.observation_id,
        pending_reasons=() if evidence is None else evidence.pending_reasons,
    )


def _count_statuses(buckets: Sequence[ReconciliationBucket]) -> dict[BucketStatus, int]:
    counts: dict[BucketStatus, int] = dict(ZERO_STATUS_COUNTS)
    for bucket in buckets:
        counts[bucket.status] += 1

    return counts


def _max_timestamp(values: Iterable[Timestamp]) -> Timestamp | None:
    return max(values, default=None)


def _max_ts_ms(values: Iterable[TimestampMS]) -> TimestampMS | None:
    return max(values, default=None)


def _history_synced_to(
        rows: Sequence[ReconciliationBucket],
        evidence: Mapping[WalletKey, WalletEvidence],
) -> Timestamp | None:
    """The furthest transaction-sync coverage of the wallet buckets of one account."""
    return max((
        wallet_evidence.history_synced_to
        for row in rows
        if row.location_label is not None and
        (wallet_evidence := evidence.get((row.location, row.location_label, row.asset))) is not None and  # noqa: E501
        wallet_evidence.history_synced_to is not None
    ), default=None)


def _bucket_sort_key(bucket: ReconciliationBucket) -> tuple[str, str]:
    return bucket.protocol or '', bucket.asset
