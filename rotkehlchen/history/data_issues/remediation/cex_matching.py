import hashlib
import json
import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.concurrency import checkpoint
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.constants import HistoryEventLinkType
from rotkehlchen.db.filtering import DataIssuesFilterQuery, HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import InputError, NotFoundError, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.constants import ALL_SUPPORTED_EXCHANGES
from rotkehlchen.fval import FVal
from rotkehlchen.history.data_issues.bucket_checks import balances_match
from rotkehlchen.history.data_issues.constants import IssueKind, IssueState
from rotkehlchen.history.data_issues.manager import DataIssuesManager
from rotkehlchen.history.data_issues.remediation.base import (
    BaseRemediationStrategy,
    RemediationOutcome,
)
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.types import HistoryEventSubType
from rotkehlchen.locations.chains import BLOCKCHAIN_LOCATIONS
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.tasks.events import (
    MOVEMENT_MATCHING_BATCH_SIZE,
    MovementMatchingState,
    _build_movement_batch_possible_matches,
    _get_assets_in_collection,
    _get_movement_match_window,
    _process_movement_candidate_set,
    get_already_matched_event_ids,
    get_unmatched_asset_movements,
)
from rotkehlchen.tasks.historical_balances import process_historical_balances
from rotkehlchen.types import EventMetricKey, Timestamp, TimestampMS
from rotkehlchen.utils.misc import ts_now, ts_sec_to_ms

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.chain.aggregator import ChainsAggregator
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.sqlite import DBCursor
    from rotkehlchen.db.settings import DBSettings
    from rotkehlchen.history.data_issues.types import DataIssue
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

CEX_ONCHAIN_MATCHING: Final = 'cex_onchain_matching'
CEX_ONCHAIN_MATCHING_TIMEOUT: Final = 300
"""Seconds one issue's matching may take. Each candidate movement runs the matcher's candidate
search, and the matches and the attempt owing their verification commit together, so a cut-off
attempt leaves nothing behind and would time out again on every later run."""
ATTRIBUTION_MATCHED_DEPOSIT: Final = 'matched_to_cex_deposit'
ATTRIBUTION_MATCHED_WITHDRAWAL: Final = 'matched_to_cex_withdrawal'
ATTRIBUTION_REPROCESSING_PENDING: Final = 'reprocessing_pending'
ATTRIBUTIONS_KEEPING_VERIFICATION_PENDING: Final = frozenset({'timeout', 'strategy_failed'})
"""Attributions of attempts that end without concluding a pending verification."""
TRIAL_SNAPSHOT_KEYS: Final = (
    'amount_tolerance',
    'time_range',
    'movement_ids',
    'window_fingerprint',
)
REMEDIATED_ISSUE_KINDS: Final = (IssueKind.NEGATIVE_BALANCE, IssueKind.CURRENT_BALANCE_MISMATCH)

type AssetsInCollectionCache = dict[str, tuple[Asset, ...]]


def _is_on_exchange(issue: DataIssue) -> bool:
    return any(str(location) == issue.location for location in ALL_SUPPORTED_EXCHANGES)


def _get_issue_window(issue: DataIssue, time_range: int) -> tuple[TimestampMS, TimestampMS]:
    """The issue's time span widened on both sides by `time_range` seconds."""
    time_range_ms = ts_sec_to_ms(Timestamp(time_range))
    return (
        TimestampMS(max(issue.ts_start - time_range_ms, 0)),
        TimestampMS(issue.ts_end + time_range_ms),
    )


def get_pending_verification(issue: DataIssue) -> dict[str, Any] | None:
    """The attempt recording this strategy's matches whose balance verification is still owed.

    Matching records it in the transaction that creates the links, so it survives a run that
    is cancelled or crashes before the verification. It stays owed through operational
    failures and is settled by any other attempt of this strategy: a verification outcome,
    or a later trial of the matcher.
    """
    pending: dict[str, Any] | None = None
    for attempt in issue.auto_remediation_attempts:
        if attempt.get('strategy') != CEX_ONCHAIN_MATCHING:
            continue
        if attempt.get('attribution') == ATTRIBUTION_REPROCESSING_PENDING:
            pending = attempt
        elif attempt.get('attribution') not in ATTRIBUTIONS_KEEPING_VERIFICATION_PENDING:
            pending = None
    return pending


def _movement_may_explain_issue(
        issue: DataIssue,
        movement: AssetMovement,
        assets_in_collection: tuple[Asset, ...],
        time_range: int,
) -> bool:
    """Whether matching the unmatched exchange movement could change the issue's bucket.

    The heuristic is deliberately loose, since the matcher itself decides what pairs up: the
    movement must fall in the issue's window and move the bucket's asset, or the same asset
    on another chain. For a bucket on an exchange it must also be a movement of that exchange
    account. For an onchain bucket any exchange qualifies: an unmatched movement of the asset
    that close to the failing event is the trace of a deposit or withdrawal whose onchain leg
    the wallet's history does not reflect yet, e.g. a withdrawal from the exchange that was
    decoded as an outflow of the wallet.
    """
    from_ts, to_ts = _get_issue_window(issue, time_range)
    return (
        from_ts <= movement.timestamp <= to_ts and
        any(asset.identifier == issue.asset for asset in assets_in_collection) and (
            _is_on_exchange(issue) is False or (
                movement.location == issue.location and
                (movement.location_label or '') == issue.location_label
            )
        )
    )


def _match_movements(
        database: DBHandler,
        settings: DBSettings,
        movements: list[AssetMovement],
        movements_by_asset: dict[Asset, list[AssetMovement]],
        fee_events: dict[str, AssetMovement],
        assets_in_collection_cache: AssetsInCollectionCache,
) -> tuple[list[AssetMovement], set[int]]:
    """Run the asset movement matcher on just the given movements.

    This drives the matcher's own per-movement step, so the candidate search, the amount
    tolerance, the match window and the event edits are exactly those of a full matching run.
    Ambiguous movements are retried once another match narrows their candidates, like there.
    A movement linked since the caller listed it as unmatched is left alone.

    Returns the movements this call matched and the ids of every event linked afterwards.
    """
    events_db = DBHistoryEvents(database)
    with database.conn.read_ctx() as cursor:
        blockchain_accounts = database.get_blockchain_accounts(cursor=cursor)
        initially_linked_ids = get_already_matched_event_ids(cursor=cursor)
        matching_state = MovementMatchingState(already_matched_event_ids=set(initially_linked_ids))
        pending, from_retry = [
            movement for movement in movements
            if movement.identifier not in initially_linked_ids
        ], False
        while len(pending) != 0:
            for movement in pending:
                checkpoint()
                _process_movement_candidate_set(
                    events_db=events_db,
                    asset_movement=movement,
                    fee_events=fee_events,
                    settings=settings,
                    assets_in_collection_cache=assets_in_collection_cache,
                    cursor=cursor,
                    blockchain_accounts=blockchain_accounts,
                    asset_movements_by_asset=movements_by_asset,
                    matching_state=matching_state,
                    from_retry=from_retry,
                )

            pending, from_retry = [
                matching_state.unresolved_ambiguous_movements[movement_id]
                for movement_id in matching_state.movements_to_retry
                if movement_id in matching_state.unresolved_ambiguous_movements
            ], True
            matching_state.movements_to_retry.clear()

    return [
        movement for movement in movements
        if movement.identifier not in initially_linked_ids and
        movement.identifier in matching_state.already_matched_event_ids
    ], matching_state.already_matched_event_ids


def _get_latest_strategy_attempt(issue: DataIssue, strategy_name: str) -> dict[str, Any] | None:
    latest_attempt: dict[str, Any] | None = None
    for attempt in issue.auto_remediation_attempts:
        if attempt.get('strategy') == strategy_name:
            latest_attempt = attempt
    return latest_attempt


def _get_tracked_accounts(cursor: DBCursor) -> list[tuple[str, str]]:
    return sorted(
        (str(row[0]), str(row[1]))
        for row in cursor.execute('SELECT blockchain, account FROM blockchain_accounts')
    )


def _load_possible_matches_for_movements(
        events_db: DBHistoryEvents,
        movements: list[AssetMovement],
        settings: DBSettings,
        assets_in_collection_cache: AssetsInCollectionCache,
        cursor: DBCursor,
) -> dict[int, list[HistoryBaseEntry]]:
    possible_matches_by_movement_id: dict[int, list[HistoryBaseEntry]] = {}
    for idx in range(0, len(movements), MOVEMENT_MATCHING_BATCH_SIZE):
        chunk = movements[idx:idx + MOVEMENT_MATCHING_BATCH_SIZE]
        possible_matches_by_movement_id.update(_build_movement_batch_possible_matches(
            events_db=events_db,
            asset_movements=chunk,
            settings=settings,
            assets_in_collection_cache=assets_in_collection_cache,
            cursor=cursor,
        ))
    return possible_matches_by_movement_id


def _build_trial_snapshot(
        movements: list[AssetMovement],
        all_movements_by_asset: Mapping[Asset, Sequence[AssetMovement]],
        fee_events: Mapping[str, AssetMovement],
        possible_matches_by_movement_id: Mapping[int, Sequence[HistoryBaseEntry]],
        already_matched_event_ids: set[int],
        tracked_accounts: list[tuple[str, str]],
        settings: DBSettings,
) -> dict[str, Any]:
    """Build a deterministic snapshot of the inputs that govern matching `movements`."""
    sorted_movements = sorted(
        (movement for movement in movements if movement.identifier is not None),
        key=lambda entry: entry.identifier or 0,
    )
    serialized_movements: list[dict[str, Any]] = []
    for movement in sorted_movements:
        assert movement.identifier is not None
        match_window_ms = _get_movement_match_window(
            asset_movement=movement,
            default_match_window=settings.asset_movement_time_range,
        ) * 1000
        fee_event = fee_events.get(movement.group_identifier)
        related_movements = [
            {
                'identifier': other.identifier,
                'timestamp': other.timestamp,
                'amount': str(other.amount),
            }
            for other in sorted(
                all_movements_by_asset.get(movement.asset, ()),
                key=lambda entry: entry.identifier or 0,
            )
            if (
                other.identifier is not None and
                other.identifier != movement.identifier and
                abs(other.timestamp - movement.timestamp) <= match_window_ms
            )
        ]
        candidates = [
            {
                'identifier': event.identifier,
                'entry_type': event.entry_type.value,
                'timestamp': event.timestamp,
                'location': event.location,
                'location_label': event.location_label,
                'asset': event.asset.identifier,
                'amount': str(event.amount),
                'event_type': event.event_type.serialize(),
                'event_subtype': event.event_subtype.serialize(),
                'counterparty': getattr(event, 'counterparty', None),
                'tx_ref': (
                    str(tx_ref)
                    if (tx_ref := getattr(event, 'tx_ref', None)) is not None
                    else None
                ),
                'address': (
                    str(addr)
                    if (addr := getattr(event, 'address', None)) is not None
                    else None
                ),
                'already_matched': event.identifier in already_matched_event_ids,
            }
            for event in sorted(
                possible_matches_by_movement_id.get(movement.identifier, ()),
                key=lambda entry: entry.identifier or 0,
            )
        ]
        serialized_movements.append({
            'identifier': movement.identifier,
            'timestamp': movement.timestamp,
            'location': movement.location,
            'location_label': movement.location_label,
            'asset': movement.asset.identifier,
            'amount': str(movement.amount),
            'event_subtype': movement.event_subtype.serialize(),
            'extra_data': movement.extra_data,
            'fee_event': (
                {
                    'identifier': fee_event.identifier,
                    'asset': fee_event.asset.identifier,
                    'amount': str(fee_event.amount),
                }
                if fee_event is not None else None
            ),
            'related_movements': related_movements,
            'candidates': candidates,
        })

    canonical_payload = json.dumps(
        {
            'tracked_accounts': tracked_accounts,
            'movements': serialized_movements,
        },
        sort_keys=True,
        separators=(',', ':'),
        default=str,
    )
    return {
        'amount_tolerance': str(settings.asset_movement_amount_tolerance),
        'time_range': settings.asset_movement_time_range,
        'movement_ids': [
            movement.identifier for movement in sorted_movements
            if movement.identifier is not None
        ],
        'window_fingerprint': hashlib.blake2b(
            canonical_payload.encode('utf-8'),
            digest_size=16,
        ).hexdigest(),
    }


def _attempt_matches_snapshot(
        attempt: Mapping[str, Any],
        snapshot: Mapping[str, Any],
) -> bool:
    return all(attempt.get(key) == snapshot[key] for key in TRIAL_SNAPSHOT_KEYS)


def _make_attempt_data(
        resolved: bool,
        notes: str,
        trial_snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    attempt_data: dict[str, Any] = {'success': resolved}
    if notes != '':
        attempt_data['reason'] = notes
    attempt_data.update(trial_snapshot)
    return attempt_data


def _pick_causal_movement(
        database: DBHandler,
        issue: DataIssue,
        matched_movements: list[AssetMovement],
) -> AssetMovement:
    """Pick the movement linked to the negative-balance event, or fall back to the first match."""
    if issue.kind == IssueKind.NEGATIVE_BALANCE and len(matched_movements) > 1:
        movements_by_id = {
            movement.identifier: movement
            for movement in matched_movements
            if movement.identifier is not None
        }
        with database.conn.read_ctx() as cursor:
            row = cursor.execute(
                'SELECT left_event_id FROM history_event_links '
                'WHERE link_type = ? AND right_event_id = ?',
                (
                    HistoryEventLinkType.ASSET_MOVEMENT_MATCH.serialize_for_db(),
                    issue.payload['event_identifier'],
                ),
            ).fetchone()
        if row is not None and (causal := movements_by_id.get(row[0])) is not None:
            return causal

    return matched_movements[0]


def _issue_still_reproduces(cursor: DBCursor, issue: DataIssue, tolerance: FVal) -> bool:
    """Whether the up to date balances still show what the issue reported.

    A negative balance is gone once its event got a balance in the bucket: the engine writes
    none for the event that takes a bucket below zero, nor for any event after it. A current
    balance mismatch is gone once the bucket's latest balance is within tolerance of the
    observed one. Callers must first make sure no stale balances marker is pending.
    """
    bucket_filter = 'metric_key = ? AND location = ? AND location_label IS ? AND protocol IS ? AND asset = ?'  # noqa: E501
    bucket_bindings = (
        EventMetricKey.BALANCE.serialize(),
        issue.location,
        issue.location_label or None,
        issue.protocol or None,
        issue.asset,
    )
    if issue.kind == IssueKind.NEGATIVE_BALANCE:
        return cursor.execute(
            f'SELECT COUNT(*) FROM event_metrics WHERE {bucket_filter} AND event_identifier = ?',
            (*bucket_bindings, issue.payload['event_identifier']),
        ).fetchone()[0] == 0

    cutoff = ts_sec_to_ms(Timestamp(issue.payload['queried_at_ts']))
    if cursor.execute(
        'SELECT 1 FROM bucket_processing_stops WHERE location=? AND location_label=? '
        'AND protocol=? AND asset=? AND event_timestamp<=?',
        (issue.location, issue.location_label, issue.protocol, issue.asset, cutoff),
    ).fetchone() is not None:
        return True

    latest_balance = cursor.execute(
        f'SELECT metric_value FROM event_metrics WHERE {bucket_filter} AND timestamp<=? '
        'ORDER BY sort_key DESC LIMIT 1',
        (*bucket_bindings, cutoff),
    ).fetchone()
    return latest_balance is None or balances_match(
        derived=FVal(latest_balance[0]),
        observed=FVal(issue.payload['observed_balance']),
        tolerance=tolerance,
    ) is False


def reprocess_balances_for_pending_matches(
        database: DBHandler,
        chains_aggregator: ChainsAggregator,
        issues: Iterable[DataIssue],
) -> None:
    """Reprocess the balances once for all the issues whose matches await verification.

    Processing starts at the stale balances marker that the match edits set, which is where a
    scheduled pass would start too. A pass cut short keeps that marker, so the metrics it
    deleted are always rebuilt by the next one. Nothing is reprocessed while no issue owes a
    verification or no marker is pending.
    """
    if all(get_pending_verification(issue) is None for issue in issues):
        return

    with database.conn.read_ctx() as cursor:
        if (stale_from_ts := database.get_static_cache(
            cursor=cursor,
            name=DBCacheStatic.STALE_BALANCES_FROM_TS,
        )) is None:
            return

    try:
        process_historical_balances(
            database=database,
            msg_aggregator=database.msg_aggregator,
            from_ts=TimestampMS(int(stale_from_ts)),
            chains_aggregator=chains_aggregator,
        )
    except (RemoteError, DeserializationError) as e:
        log.error('Failed to reprocess balances for exchange movement matches: %s', e)


class CexOnchainMatchingStrategy(BaseRemediationStrategy):
    """Pair unmatched exchange deposits/withdrawals around an issue with their onchain leg.

    Uses the existing matcher's configured tolerance and time range without remote fetching.
    A match can reclassify an onchain leg and flip its balance effect, so it only owes a
    verification: the links and a `reprocessing_pending` attempt naming the matched movements
    commit together. `reprocess_balances_for_pending_matches` then reprocesses once for every
    issue of the run, and `CexOnchainMatchVerificationStrategy` checks each issue's condition.

    The unmatched movements are loaded once per run, and the ones a match consumes are dropped.
    A movement linked by someone else meanwhile is skipped by the matcher.
    """

    name: Final = CEX_ONCHAIN_MATCHING
    timeout: float = CEX_ONCHAIN_MATCHING_TIMEOUT

    def __init__(self, database: DBHandler) -> None:
        self.database = database
        self.settings = CachedSettings().get_settings()
        self.assets_in_collection_cache: AssetsInCollectionCache = {}
        unmatched, self.fee_events = get_unmatched_asset_movements(database)
        self.unmatched_movements = [
            (movement, _get_assets_in_collection(movement, self.assets_in_collection_cache))
            for movement in unmatched
        ]
        self._unmatched_by_asset: defaultdict[Asset, list[AssetMovement]] = defaultdict(list)
        for movement in unmatched:
            self._unmatched_by_asset[movement.asset].append(movement)
        self._unresolved_issue_ids: set[int] = set()
        self._preloaded_possible_matches: dict[int, list[HistoryBaseEntry]] = {}
        self._already_matched_event_ids: set[int] | None = None
        self._tracked_accounts: list[tuple[str, str]] | None = None
        self._preload_unresolved_inputs()

    def _preload_unresolved_inputs(self) -> None:
        """Load what `applies_to` compares against the last trial of each unresolved issue."""
        movements_to_preload: dict[int, AssetMovement] = {}
        for issue in DataIssuesManager(self.database).list_issues(DataIssuesFilterQuery.make(
            kinds=list(REMEDIATED_ISSUE_KINDS),
            states=[IssueState.UNRESOLVED],
        )):
            if (
                _get_latest_strategy_attempt(issue, self.name) is None or
                get_pending_verification(issue) is not None
            ):
                continue
            for movement in self._get_candidate_movements(issue):
                if movement.identifier is not None:
                    movements_to_preload[movement.identifier] = movement

        if len(movements_to_preload) == 0:
            return

        with self.database.conn.read_ctx() as cursor:
            self._already_matched_event_ids = get_already_matched_event_ids(cursor=cursor)
            self._tracked_accounts = _get_tracked_accounts(cursor=cursor)
            self._preloaded_possible_matches = _load_possible_matches_for_movements(
                events_db=DBHistoryEvents(self.database),
                movements=list(movements_to_preload.values()),
                settings=self.settings,
                assets_in_collection_cache=self.assets_in_collection_cache,
                cursor=cursor,
            )

    def _get_preloaded_snapshot(
            self,
            candidate_movements: list[AssetMovement],
    ) -> dict[str, Any] | None:
        """The trial snapshot from the preloaded inputs, or None if they do not cover it."""
        if (
            self._already_matched_event_ids is None or
            self._tracked_accounts is None or
            any(
                movement.identifier not in self._preloaded_possible_matches
                for movement in candidate_movements
            )
        ):
            return None
        return _build_trial_snapshot(
            movements=candidate_movements,
            all_movements_by_asset=self._unmatched_by_asset,
            fee_events=self.fee_events,
            possible_matches_by_movement_id=self._preloaded_possible_matches,
            already_matched_event_ids=self._already_matched_event_ids,
            tracked_accounts=self._tracked_accounts,
            settings=self.settings,
        )

    def _compute_fresh_snapshot(self, movements: list[AssetMovement]) -> dict[str, Any]:
        with self.database.conn.read_ctx() as cursor:
            already_matched_event_ids = get_already_matched_event_ids(cursor=cursor)
            tracked_accounts = _get_tracked_accounts(cursor=cursor)
            possible_matches_by_movement_id = _load_possible_matches_for_movements(
                events_db=DBHistoryEvents(self.database),
                movements=movements,
                settings=self.settings,
                assets_in_collection_cache=self.assets_in_collection_cache,
                cursor=cursor,
            )

        return _build_trial_snapshot(
            movements=movements,
            all_movements_by_asset=self._unmatched_by_asset,
            fee_events=self.fee_events,
            possible_matches_by_movement_id=possible_matches_by_movement_id,
            already_matched_event_ids=already_matched_event_ids,
            tracked_accounts=tracked_accounts,
            settings=self.settings,
        )

    def _get_candidate_movements(self, issue: DataIssue) -> list[AssetMovement]:
        return [
            movement for movement, assets_in_collection in self.unmatched_movements
            if _movement_may_explain_issue(
                issue=issue,
                movement=movement,
                assets_in_collection=assets_in_collection,
                time_range=self.settings.asset_movement_time_range,
            )
        ]

    def _forget_linked_movements(self, linked_ids: set[int]) -> None:
        """Drop the movements now part of a match from the movements loaded for this run."""
        self.unmatched_movements = [
            entry for entry in self.unmatched_movements if entry[0].identifier not in linked_ids
        ]
        for asset, movements in self._unmatched_by_asset.items():
            self._unmatched_by_asset[asset] = [
                movement for movement in movements if movement.identifier not in linked_ids
            ]
        if self._already_matched_event_ids is not None:
            self._already_matched_event_ids |= linked_ids

    def applies_to(self, issue: DataIssue) -> bool:
        """Whether an unmatched exchange movement could be behind the issue.

        The issue needs a nearby unmatched movement as documented in
        `_movement_may_explain_issue`, and no match of this strategy awaiting verification.
        An unresolved issue this strategy already tried qualifies again only once the inputs
        of its last trial changed. When those inputs were not preloaded, `attempt` decides.
        """
        if (
            issue.kind not in REMEDIATED_ISSUE_KINDS or
            get_pending_verification(issue) is not None or (
                _is_on_exchange(issue) is False and
                (issue.location not in BLOCKCHAIN_LOCATIONS or issue.location_label == '')
            ) or
            len(candidate_movements := self._get_candidate_movements(issue)) == 0
        ):
            return False

        if issue.state != IssueState.UNRESOLVED:
            return True

        self._unresolved_issue_ids.add(issue.id)
        if (
            (latest_attempt := _get_latest_strategy_attempt(issue, self.name)) is None or
            (snapshot := self._get_preloaded_snapshot(candidate_movements)) is None
        ):
            return True
        return _attempt_matches_snapshot(latest_attempt, snapshot) is False

    def attempt(self, issue: DataIssue) -> RemediationOutcome:
        while self.database.match_asset_movements_lock.acquire(timeout=0.1) is False:
            checkpoint()
        try:
            checkpoint()
            return self._match_issue(issue)
        finally:
            self.database.match_asset_movements_lock.release()

    def _match_issue(self, issue: DataIssue) -> RemediationOutcome:
        if len(movements := self._get_candidate_movements(issue)) == 0:
            return RemediationOutcome(
                resolved=False,
                attribution='not_applicable',
                notes='No unmatched exchange movement in the issue window',
                record_attempt=False,
            )

        trial_snapshot = self._compute_fresh_snapshot(movements)
        if (
            issue.id in self._unresolved_issue_ids and
            (latest_attempt := _get_latest_strategy_attempt(issue, self.name)) is not None and
            _attempt_matches_snapshot(latest_attempt, trial_snapshot)
        ):
            return RemediationOutcome(
                resolved=False,
                attribution='unchanged_inputs',
                notes='Matching inputs have not changed since the last attempt',
                record_attempt=False,
            )

        with self.database.conn.write_ctx():
            matched_movements, linked_ids = _match_movements(
                database=self.database,
                settings=self.settings,
                movements=movements,
                movements_by_asset=self._unmatched_by_asset,
                fee_events=self.fee_events,
                assets_in_collection_cache=self.assets_in_collection_cache,
            )
            if len(matched_movements) != 0:
                self._record_pending_verification(issue, matched_movements, trial_snapshot)

        self._forget_linked_movements(linked_ids)
        if len(matched_movements) != 0:
            return RemediationOutcome(
                resolved=False,
                attribution=ATTRIBUTION_REPROCESSING_PENDING,
                notes='Movements matched; balance reprocessing is still pending',
                record_attempt=False,
            )

        notes = 'No exchange movement in the issue window could be matched'
        return RemediationOutcome(
            resolved=False,
            attribution='no_match',
            notes=notes,
            attempt_data=_make_attempt_data(
                resolved=False,
                notes=notes,
                trial_snapshot=trial_snapshot,
            ),
        )

    def _record_pending_verification(
            self,
            issue: DataIssue,
            matched_movements: list[AssetMovement],
            trial_snapshot: Mapping[str, Any],
    ) -> None:
        """Record the matches owing a verification, inside the transaction that made them.

        An issue dismissed or deleted meanwhile rolls back its matches too. That is reported
        as an `InputError`, which the pipeline turns into skipping the changed issue.
        """
        notes = 'Movements matched; balance reprocessing is still pending'
        try:
            DataIssuesManager(self.database).append_auto_remediation_attempt(
                issue_id=issue.id,
                attempt={
                    'attribution': ATTRIBUTION_REPROCESSING_PENDING,
                    'strategy': self.name,
                    'timestamp': ts_now(),
                    **_make_attempt_data(
                        resolved=False,
                        notes=notes,
                        trial_snapshot=trial_snapshot,
                    ),
                    'matched_movement_ids': sorted(
                        movement.identifier for movement in matched_movements
                        if movement.identifier is not None
                    ),
                },
                expected_state=IssueState.AUTO_REMEDIATING,
            )
        except NotFoundError as e:
            raise InputError(str(e)) from e


class CexOnchainMatchVerificationStrategy(BaseRemediationStrategy):
    """Check whether the matches `CexOnchainMatchingStrategy` made resolved their issue.

    It only considers the movements named by the issue's pending verification, never other
    links in the issue window, and never reprocesses balances itself: while a stale balances
    marker is pending, the verification stays owed for a later run.
    """

    name: Final = CEX_ONCHAIN_MATCHING

    def __init__(self, database: DBHandler) -> None:
        self.database = database
        self.settings = CachedSettings().get_settings()

    def applies_to(self, issue: DataIssue) -> bool:
        return issue.kind in REMEDIATED_ISSUE_KINDS and get_pending_verification(issue) is not None

    def attempt(self, issue: DataIssue) -> RemediationOutcome:
        if (pending := get_pending_verification(issue)) is None:  # applies_to guarantees one
            return RemediationOutcome(
                resolved=False,
                attribution='not_applicable',
                notes='No exchange movement match awaits verification',
                record_attempt=False,
            )

        trial_snapshot: dict[str, Any] = {
            key: pending[key] for key in TRIAL_SNAPSHOT_KEYS if key in pending
        }
        with self.database.conn.read_ctx() as cursor:
            matched_movements = self._get_still_linked_movements(
                cursor=cursor,
                movement_ids=pending.get('matched_movement_ids', []),
            )
            if len(matched_movements) == 0:
                notes = 'The matched exchange movements were unlinked before their verification'
                return RemediationOutcome(
                    resolved=False,
                    attribution='matches_unlinked',
                    notes=notes,
                    attempt_data=_make_attempt_data(
                        resolved=False,
                        notes=notes,
                        trial_snapshot=trial_snapshot,
                    ),
                )

            if self.database.get_static_cache(
                cursor=cursor,
                name=DBCacheStatic.STALE_BALANCES_FROM_TS,
            ) is not None:
                return self._still_pending(issue, pending)

            still_reproduces = _issue_still_reproduces(
                cursor=cursor,
                issue=issue,
                tolerance=self.settings.asset_movement_amount_tolerance,
            )

        if still_reproduces:
            notes = 'Movements matched, but the original balance condition still reproduces'
            return RemediationOutcome(
                resolved=False,
                attribution='matched_without_resolving',
                notes=notes,
                attempt_data=_make_attempt_data(
                    resolved=False,
                    notes=notes,
                    trial_snapshot=trial_snapshot,
                ),
            )

        causal_movement = _pick_causal_movement(self.database, issue, matched_movements)
        is_deposit = causal_movement.event_subtype == HistoryEventSubType.RECEIVE
        notes = f'Matched {len(matched_movements)} exchange movements with their onchain events'
        return RemediationOutcome(
            resolved=True,
            attribution=ATTRIBUTION_MATCHED_DEPOSIT if is_deposit else ATTRIBUTION_MATCHED_WITHDRAWAL,  # noqa: E501
            notes=notes,
            attempt_data=_make_attempt_data(
                resolved=True,
                notes=notes,
                trial_snapshot=trial_snapshot,
            ),
        )

    def _get_still_linked_movements(
            self,
            cursor: DBCursor,
            movement_ids: list[int],
    ) -> list[AssetMovement]:
        if len(movement_ids) == 0:
            return []
        placeholders = ','.join('?' * len(movement_ids))
        if len(linked_ids := [row[0] for row in cursor.execute(
            'SELECT DISTINCT left_event_id FROM history_event_links '
            f'WHERE link_type=? AND left_event_id IN ({placeholders})',
            (HistoryEventLinkType.ASSET_MOVEMENT_MATCH.serialize_for_db(), *movement_ids),
        )]) == 0:
            return []
        return sorted(
            (
                event for event in DBHistoryEvents(self.database).get_history_events_internal(
                    cursor=cursor,
                    filter_query=HistoryEventFilterQuery.make(identifiers=linked_ids),
                ) if isinstance(event, AssetMovement)
            ),
            key=lambda movement: movement.identifier or 0,
        )

    def _still_pending(self, issue: DataIssue, pending: dict[str, Any]) -> RemediationOutcome:
        """Keep the verification owed until the balances are up to date.

        The pending attempt is recorded again once other attempts followed it, so the capped
        attempt history can never drop it while the verification is still owed.
        """
        notes = 'Movements matched; balance reprocessing is still pending'
        if issue.auto_remediation_attempts[-1] is pending:
            return RemediationOutcome(
                resolved=False,
                attribution=ATTRIBUTION_REPROCESSING_PENDING,
                notes=notes,
                record_attempt=False,
            )
        return RemediationOutcome(
            resolved=False,
            attribution=ATTRIBUTION_REPROCESSING_PENDING,
            notes=notes,
            attempt_data={
                key: value for key, value in pending.items()
                if key not in {'attribution', 'strategy', 'timestamp'}
            },
        )
