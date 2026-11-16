import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.concurrency import checkpoint
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.constants import HistoryEventLinkType
from rotkehlchen.db.filtering import DataIssuesFilterQuery, HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import CachedSettings
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
from rotkehlchen.utils.misc import ts_sec_to_ms

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.chain.aggregator import ChainsAggregator
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.sqlite import DBCursor
    from rotkehlchen.db.settings import DBSettings
    from rotkehlchen.history.data_issues.types import DataIssue
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry

CEX_ONCHAIN_MATCHING: Final = 'cex_onchain_matching'
CEX_ONCHAIN_MATCHING_TIMEOUT: Final = 300
"""Seconds one issue's attempt may take. The matching itself is quick, but a match is only
known to resolve the issue after the balances are reprocessed from the start of the issue's
window, which for a long history takes far longer than the default strategy budget."""
ATTRIBUTION_MATCHED_DEPOSIT: Final = 'matched_to_cex_deposit'
ATTRIBUTION_MATCHED_WITHDRAWAL: Final = 'matched_to_cex_withdrawal'

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


def _get_linked_movements(database: DBHandler) -> list[AssetMovement]:
    """Load completed matches so an interrupted balance verification can be retried."""
    with database.conn.read_ctx() as cursor:
        identifiers = [row[0] for row in cursor.execute(
            'SELECT DISTINCT left_event_id FROM history_event_links WHERE link_type=?',
            (HistoryEventLinkType.ASSET_MOVEMENT_MATCH.serialize_for_db(),),
        )]
        if len(identifiers) == 0:
            return []
        return [
            event for event in DBHistoryEvents(database).get_history_events_internal(
                cursor=cursor,
                filter_query=HistoryEventFilterQuery.make(identifiers=identifiers),
            ) if isinstance(event, AssetMovement)
        ]


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
        all_unmatched_movements: list[AssetMovement],
        fee_events: dict[str, AssetMovement],
        assets_in_collection_cache: AssetsInCollectionCache,
) -> list[AssetMovement]:
    """Run the asset movement matcher on just the given movements and return the matched ones.

    This drives the matcher's own per-movement step, so the candidate search, the amount
    tolerance, the match window and the event edits are exactly those of a full matching run.
    Ambiguous movements are retried once another match narrows their candidates, like there.
    """
    events_db = DBHistoryEvents(database)
    movements_by_asset: defaultdict[Asset, list[AssetMovement]] = defaultdict(list)
    for movement in all_unmatched_movements:
        movements_by_asset[movement.asset].append(movement)

    with database.conn.read_ctx() as cursor:
        blockchain_accounts = database.get_blockchain_accounts(cursor=cursor)
        matching_state = MovementMatchingState(
            already_matched_event_ids=get_already_matched_event_ids(cursor=cursor),
        )
        pending, from_retry = list(movements), False
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
        if movement.identifier in matching_state.already_matched_event_ids
    ]


def _get_latest_strategy_attempt(issue: DataIssue, strategy_name: str) -> dict[str, Any] | None:
    latest_attempt: dict[str, Any] | None = None
    for attempt in issue.auto_remediation_attempts:
        if attempt.get('strategy') == strategy_name:
            latest_attempt = attempt
    return latest_attempt


def _is_retrying_verification(issue: DataIssue, strategy_name: str) -> bool:
    """Whether an interrupted prior attempt for `strategy_name` still needs verification."""
    if issue.state == IssueState.UNRESOLVED and len(issue.auto_remediation_attempts) == 0:
        return True

    if (latest_attempt := _get_latest_strategy_attempt(issue, strategy_name)) is None:
        return False
    return latest_attempt.get('attribution') in {
        'timeout',
        'strategy_failed',
        'reprocessing_pending',
    }


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
    return (
        attempt.get('amount_tolerance') == snapshot['amount_tolerance'] and
        attempt.get('time_range') == snapshot['time_range'] and
        attempt.get('movement_ids') == snapshot['movement_ids'] and
        attempt.get('window_fingerprint') == snapshot['window_fingerprint']
    )


def _make_attempt_data(
        resolved: bool,
        notes: str,
        trial_snapshot: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if trial_snapshot is None:
        return {}
    attempt_data: dict[str, Any] = {'success': resolved}
    if notes != '':
        attempt_data['reason'] = notes
    attempt_data.update(trial_snapshot)
    return attempt_data


@dataclass(frozen=True, slots=True)
class _MatchIssueResult:
    matched_movements: list[AssetMovement]
    had_candidates: bool
    trial_snapshot: dict[str, Any] | None = None
    unchanged_inputs: bool = False


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


def _issue_still_reproduces(database: DBHandler, issue: DataIssue, tolerance: FVal) -> bool:
    """Whether the freshly reprocessed balances still show what the issue reported.

    A negative balance is gone once its event got a balance in the bucket: the engine writes
    none for the event that takes a bucket below zero, nor for any event after it. A current
    balance mismatch is gone once the bucket's latest balance is within tolerance of the
    observed one.
    """
    bucket_filter = 'metric_key = ? AND location = ? AND location_label IS ? AND protocol IS ? AND asset = ?'  # noqa: E501
    bucket_bindings = (
        EventMetricKey.BALANCE.serialize(),
        issue.location,
        issue.location_label or None,
        issue.protocol or None,
        issue.asset,
    )
    with database.conn.read_ctx() as cursor:
        if database.get_static_cache(cursor, DBCacheStatic.STALE_BALANCES_FROM_TS) is not None:
            return True
        if issue.kind == IssueKind.NEGATIVE_BALANCE:
            return cursor.execute(
                f'SELECT COUNT(*) FROM event_metrics WHERE {bucket_filter} AND event_identifier = ?',  # noqa: E501
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


class CexOnchainMatchingStrategy(BaseRemediationStrategy):
    """Pair unmatched exchange deposits/withdrawals around an issue with their onchain leg.

    Uses the existing matcher's configured tolerance and time range without remote fetching.
    A match can reclassify an onchain leg and flip its balance effect. Success requires
    reprocessing balances and checking the original failing condition. Balance reprocessing
    can query configured archive nodes for unrelated rebasing assets, like a scheduled pass.
    """

    name: Final = CEX_ONCHAIN_MATCHING
    timeout: float = CEX_ONCHAIN_MATCHING_TIMEOUT

    def __init__(self, database: DBHandler, chains_aggregator: ChainsAggregator) -> None:
        self.database = database
        self.chains_aggregator = chains_aggregator
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
        self._linked_movements: list[tuple[AssetMovement, tuple[Asset, ...]]] | None = None
        self._retry_verification_issue_ids: set[int] = set()
        self._unresolved_issue_ids: set[int] = set()
        self._preloaded_possible_matches: dict[int, list[HistoryBaseEntry]] = {}
        self._preloaded_movement_ids: set[int] = set()
        self._already_matched_event_ids: set[int] | None = None
        self._tracked_accounts: list[tuple[str, str]] | None = None
        self._preload_unresolved_inputs()

    def _preload_unresolved_inputs(self) -> None:
        unresolved_issues = DataIssuesManager(self.database).list_issues(
            DataIssuesFilterQuery.make(
                kinds=[IssueKind.NEGATIVE_BALANCE, IssueKind.CURRENT_BALANCE_MISMATCH],
                states=[IssueState.UNRESOLVED],
            ),
        )
        movements_to_preload: dict[int, AssetMovement] = {}
        needs_linked_movements = False
        for issue in unresolved_issues:
            if _is_retrying_verification(issue, self.name):
                needs_linked_movements = True
                continue
            if _get_latest_strategy_attempt(issue, self.name) is None:
                continue
            if (
                _is_on_exchange(issue) is False and
                (issue.location not in BLOCKCHAIN_LOCATIONS or issue.location_label == '')
            ):
                continue
            for movement in self._get_candidate_movements(issue):
                if movement.identifier is not None:
                    movements_to_preload[movement.identifier] = movement

        if needs_linked_movements:
            self._get_linked_movements_with_assets()

        if len(movements_to_preload) != 0:
            self._preload_snapshot_data_for_movements(list(movements_to_preload.values()))

    def _preload_snapshot_data_for_movements(self, movements: list[AssetMovement]) -> None:
        events_db = DBHistoryEvents(self.database)
        with self.database.conn.read_ctx() as cursor:
            if self._already_matched_event_ids is None:
                self._already_matched_event_ids = get_already_matched_event_ids(cursor=cursor)
            if self._tracked_accounts is None:
                self._tracked_accounts = _get_tracked_accounts(cursor=cursor)
            if len(movements) != 0:
                self._preloaded_possible_matches.update(_load_possible_matches_for_movements(
                    events_db=events_db,
                    movements=movements,
                    settings=self.settings,
                    assets_in_collection_cache=self.assets_in_collection_cache,
                    cursor=cursor,
                ))
                for movement in movements:
                    if movement.identifier is not None:
                        self._preloaded_movement_ids.add(movement.identifier)

    def _get_or_compute_snapshot(
            self,
            candidate_movements: list[AssetMovement],
    ) -> dict[str, Any]:
        missing_movements = [
            movement for movement in candidate_movements
            if movement.identifier is not None and
            movement.identifier not in self._preloaded_movement_ids
        ]
        if (
            len(missing_movements) != 0 or
            self._already_matched_event_ids is None or
            self._tracked_accounts is None
        ):
            self._preload_snapshot_data_for_movements(missing_movements)
        assert self._already_matched_event_ids is not None
        assert self._tracked_accounts is not None
        return _build_trial_snapshot(
            movements=candidate_movements,
            all_movements_by_asset=self._unmatched_by_asset,
            fee_events=self.fee_events,
            possible_matches_by_movement_id=self._preloaded_possible_matches,
            already_matched_event_ids=self._already_matched_event_ids,
            tracked_accounts=self._tracked_accounts,
            settings=self.settings,
        )

    def _compute_fresh_snapshot(
            self,
            movements: list[AssetMovement],
            all_unmatched_movements: list[AssetMovement],
            fee_events: Mapping[str, AssetMovement],
    ) -> dict[str, Any]:
        movements_by_asset: defaultdict[Asset, list[AssetMovement]] = defaultdict(list)
        for movement in all_unmatched_movements:
            movements_by_asset[movement.asset].append(movement)

        events_db = DBHistoryEvents(self.database)
        with self.database.conn.read_ctx() as cursor:
            already_matched_event_ids = get_already_matched_event_ids(cursor=cursor)
            tracked_accounts = _get_tracked_accounts(cursor=cursor)
            possible_matches_by_movement_id = _load_possible_matches_for_movements(
                events_db=events_db,
                movements=movements,
                settings=self.settings,
                assets_in_collection_cache=self.assets_in_collection_cache,
                cursor=cursor,
            )

        return _build_trial_snapshot(
            movements=movements,
            all_movements_by_asset=movements_by_asset,
            fee_events=fee_events,
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

    def _get_linked_movements_with_assets(self) -> list[tuple[AssetMovement, tuple[Asset, ...]]]:
        if self._linked_movements is None:
            self._linked_movements = [
                (movement, _get_assets_in_collection(movement, self.assets_in_collection_cache))
                for movement in _get_linked_movements(self.database)
            ]
        return self._linked_movements

    def _should_retry_verification(self, issue: DataIssue) -> bool:
        return _is_retrying_verification(issue, self.name) or (
            issue.state == IssueState.AUTO_REMEDIATING and
            len(issue.auto_remediation_attempts) == 0 and
            issue.id in self._retry_verification_issue_ids
        )

    def applies_to(self, issue: DataIssue) -> bool:
        """Whether an unmatched exchange movement could be behind the issue.

        Exchange issues qualify by kind when open. Onchain issues additionally need a nearby
        unmatched movement as documented in `_movement_may_explain_issue`. An unresolved issue
        qualifies when a prior attempt was interrupted before balance verification completed,
        when this strategy has never run on it and a candidate movement exists, or when the
        candidate window inputs changed since its last attempt.
        """
        if issue.kind not in {IssueKind.NEGATIVE_BALANCE, IssueKind.CURRENT_BALANCE_MISMATCH}:
            return False
        is_on_exchange = _is_on_exchange(issue)
        if is_on_exchange is False and (
            issue.location not in BLOCKCHAIN_LOCATIONS or issue.location_label == ''
        ):
            return False

        retry_verification = _is_retrying_verification(issue, self.name)
        if retry_verification:
            self._retry_verification_issue_ids.add(issue.id)
        if issue.state == IssueState.UNRESOLVED:
            self._unresolved_issue_ids.add(issue.id)

        if issue.state != IssueState.UNRESOLVED or retry_verification:
            if is_on_exchange:
                return True
            if len(self._get_candidate_movements(issue)) != 0:
                return True
            return retry_verification and any(
                _movement_may_explain_issue(
                    issue, movement, assets_in_collection, self.settings.asset_movement_time_range,
                ) for movement, assets_in_collection in self._get_linked_movements_with_assets()
            )

        candidate_movements = self._get_candidate_movements(issue)
        if len(candidate_movements) == 0:
            return False

        if (latest_attempt := _get_latest_strategy_attempt(issue, self.name)) is None:
            return True

        snapshot = self._get_or_compute_snapshot(candidate_movements)
        return _attempt_matches_snapshot(latest_attempt, snapshot) is False

    def attempt(self, issue: DataIssue) -> RemediationOutcome:
        while self.database.match_asset_movements_lock.acquire(timeout=0.1) is False:
            checkpoint()
        try:
            checkpoint()
            result = self._match_issue(issue)
        finally:
            self.database.match_asset_movements_lock.release()

        if result.unchanged_inputs:
            return RemediationOutcome(
                resolved=False,
                attribution='unchanged_inputs',
                notes='Matching inputs have not changed since the last attempt',
                record_attempt=False,
            )
        if len(result.matched_movements) == 0:
            if result.had_candidates is False:
                return RemediationOutcome(
                    resolved=False,
                    attribution='not_applicable',
                    notes='No unmatched exchange movement in the issue window',
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
                    trial_snapshot=result.trial_snapshot,
                ),
            )
        return self._verify_matches(issue, result.matched_movements, result.trial_snapshot)

    def _match_issue(self, issue: DataIssue) -> _MatchIssueResult:
        unmatched_movements, fee_events = get_unmatched_asset_movements(self.database)
        movements = [
            movement for movement in unmatched_movements if _movement_may_explain_issue(
                issue, movement,
                _get_assets_in_collection(movement, self.assets_in_collection_cache),
                self.settings.asset_movement_time_range,
            )
        ]
        trial_snapshot: dict[str, Any] | None = None
        if len(movements) != 0:
            trial_snapshot = self._compute_fresh_snapshot(
                movements=movements,
                all_unmatched_movements=unmatched_movements,
                fee_events=fee_events,
            )
            if (
                (issue.state == IssueState.UNRESOLVED or issue.id in self._unresolved_issue_ids) and  # noqa: E501
                self._should_retry_verification(issue) is False and
                (latest_attempt := _get_latest_strategy_attempt(issue, self.name)) is not None and
                _attempt_matches_snapshot(latest_attempt, trial_snapshot)
            ):
                return _MatchIssueResult(
                    matched_movements=[],
                    had_candidates=True,
                    trial_snapshot=trial_snapshot,
                    unchanged_inputs=True,
                )

        newly_matched = _match_movements(
            database=self.database,
            settings=self.settings,
            movements=movements,
            all_unmatched_movements=unmatched_movements,
            fee_events=fee_events,
            assets_in_collection_cache=self.assets_in_collection_cache,
        ) if len(movements) != 0 else []
        if len(newly_matched) != 0:
            return _MatchIssueResult(
                matched_movements=newly_matched,
                had_candidates=True,
                trial_snapshot=trial_snapshot,
            )

        if self._should_retry_verification(issue):
            previously_matched = [
                movement for movement in _get_linked_movements(self.database)
                if _movement_may_explain_issue(
                    issue, movement,
                    _get_assets_in_collection(movement, self.assets_in_collection_cache),
                    self.settings.asset_movement_time_range,
                )
            ]
            if len(previously_matched) != 0:
                return _MatchIssueResult(
                    matched_movements=previously_matched,
                    had_candidates=len(movements) != 0,
                    trial_snapshot=trial_snapshot,
                )

        return _MatchIssueResult(
            matched_movements=[],
            had_candidates=len(movements) != 0,
            trial_snapshot=trial_snapshot,
        )

    def _verify_matches(
            self,
            issue: DataIssue,
            matched_movements: list[AssetMovement],
            trial_snapshot: Mapping[str, Any] | None,
    ) -> RemediationOutcome:
        """Reprocess from the earliest outstanding stale marker, not just this issue's edits."""
        checkpoint()
        from_ts = _get_issue_window(issue, self.settings.asset_movement_time_range)[0]
        with self.database.conn.read_ctx() as cursor:
            if (stale_from_ts := self.database.get_static_cache(
                cursor=cursor,
                name=DBCacheStatic.STALE_BALANCES_FROM_TS,
            )) is not None:
                from_ts = min(from_ts, TimestampMS(int(stale_from_ts)))

        pending_outcome = RemediationOutcome(
            resolved=False,
            attribution='reprocessing_pending',
            notes='Movements matched; balance reprocessing is still pending',
        )
        if process_historical_balances(
            database=self.database,
            msg_aggregator=self.database.msg_aggregator,
            from_ts=from_ts,
            chains_aggregator=self.chains_aggregator,
        ) is not True:
            return pending_outcome

        with self.database.conn.read_ctx() as cursor:
            if self.database.get_static_cache(
                cursor=cursor,
                name=DBCacheStatic.STALE_BALANCES_FROM_TS,
            ) is not None:
                return pending_outcome

        if _issue_still_reproduces(
            database=self.database,
            issue=issue,
            tolerance=self.settings.asset_movement_amount_tolerance,
        ):
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
