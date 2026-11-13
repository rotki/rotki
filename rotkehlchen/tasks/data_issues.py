import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Final, cast

from rotkehlchen.api.websockets.typedefs import ProgressUpdateSubType, WSMessageType
from rotkehlchen.concurrency import TaskCancelledError, checkpoint
from rotkehlchen.constants import ZERO
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.constants import HISTORY_MAPPING_KEY_STATE, HistoryMappingState
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import (
    DataIssuesFilterQuery,
    EvmEventFilterQuery,
    EvmTransactionsFilterQuery,
)
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.fval import FVal
from rotkehlchen.history.data_issues.constants import IssueKind, IssueState
from rotkehlchen.history.data_issues.manager import DataIssuesManager
from rotkehlchen.history.data_issues.remediation.base import (
    BaseRemediationStrategy,
    RemediationOutcome,
    RemediationPipeline,
)
from rotkehlchen.history.data_issues.types import (
    AutoRemediationAttempt,
    DataIssue,
    RedecodeComparisonResult,
    TransactionDecodingComparison,
)
from rotkehlchen.history.events.structures.types import EventDirection
from rotkehlchen.locations.chains import (
    EVM_LOCATIONS,
    location_to_chain_id,
)
from rotkehlchen.locations.types import LocationIdentifier
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.tasks.historical_balances import Bucket
from rotkehlchen.types import (
    EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE,
    ChainID,
    EVMTxHash,
    TimestampMS,
)
from rotkehlchen.utils.misc import ts_ms_to_sec, ts_now

if TYPE_CHECKING:
    from collections.abc import Sequence

    from rotkehlchen.chain.aggregator import ChainsAggregator
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.history.events.structures.evm_event import EvmEvent

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

REDECODE_CUSTOMIZED_TRANSACTIONS: Final = 'redecode_customized_transactions'

type BucketEffect = tuple[TimestampMS, EventDirection, FVal]
type PreviewCache = dict[tuple[EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE, EVMTxHash], list[EvmEvent]]


def _get_bucket_effects(
        events: Sequence[EvmEvent],
        bucket: Bucket,
        treat_eth2_as_eth: bool,
) -> list[BucketEffect]:
    effects: list[BucketEffect] = []
    for event in sorted(events, key=lambda entry: entry.sequence_index):
        for event_bucket, direction in Bucket.from_event(
            event=event,
            treat_eth2_as_eth=treat_eth2_as_eth,
        ):
            if event_bucket == bucket:
                effects.append((event.timestamp, direction, event.amount))

    return effects


def _get_customized_transactions_for_issue(
        database: DBHandler,
        issue: DataIssue,
        chain_id: EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE,
        location: LocationIdentifier,
) -> dict[EVMTxHash, list[EvmEvent]]:
    """Return customized transactions associated with the issue account."""
    checkpoint()  # loading runs inside the cancellable budget, like the comparison
    dbevents = DBHistoryEvents(database)
    with database.conn.read_ctx() as cursor:
        customized_group_identifiers = [row[0] for row in cursor.execute(
            'SELECT DISTINCT H.group_identifier FROM history_events_mappings M '
            'JOIN history_events H ON H.identifier = M.parent_identifier '
            'JOIN chain_events_info C ON C.identifier = H.identifier '
            'JOIN evm_transactions T ON T.tx_hash = C.tx_ref AND T.chain_id = ? '
            'JOIN evmtx_address_mappings A ON A.tx_id = T.identifier AND A.address = ? '
            'WHERE M.name = ? AND M.value = ? AND H.location = ? AND T.timestamp <= ?',
            (
                chain_id.serialize_for_db(),
                issue.location_label,
                HISTORY_MAPPING_KEY_STATE,
                HistoryMappingState.CUSTOMIZED.serialize_for_db(),
                location,
                ts_ms_to_sec(TimestampMS(issue.ts_end)),
            ),
        )]
        if len(customized_group_identifiers) == 0:
            return {}

        transaction_events = dbevents.get_history_events_internal(
            cursor=cursor,
            filter_query=EvmEventFilterQuery.make(
                location=location,
                group_identifiers=customized_group_identifiers,
            ),
        )

    events_by_transaction: defaultdict[EVMTxHash, list[EvmEvent]] = defaultdict(list)
    for event in transaction_events:
        events_by_transaction[event.tx_ref].append(event)

    return dict(events_by_transaction)


def _preview_transaction(
        database: DBHandler,
        chains_aggregator: ChainsAggregator,
        chain_id: EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE,
        tx_hash: EVMTxHash,
        reload: bool,
) -> list[EvmEvent]:
    dbtx = DBEvmTx(database)
    with database.conn.read_ctx() as cursor:
        transactions = dbtx.get_transactions(
            cursor=cursor,
            filter_=EvmTransactionsFilterQuery.make(tx_hash=tx_hash, chain_id=chain_id),
        )
        receipt = dbtx.get_receipt(cursor=cursor, tx_hash=tx_hash, chain_id=chain_id)

    if len(transactions) != 1 or receipt is None:
        raise RuntimeError(
            f'Missing transaction data needed to preview {tx_hash!s} on {chain_id!s}',
        )

    decoder = chains_aggregator.get_evm_manager(chain_id).transactions_decoder
    return decoder.decode_transaction_without_persistence(
        transaction=transactions[0],
        tx_receipt=receipt,
        reload=reload,
    )


def _make_comparison_attempt(
        result: RedecodeComparisonResult,
        customized_transaction_count: int,
        changed_transaction_count: int,
        reason: str | None = None,
) -> AutoRemediationAttempt:
    attempt = AutoRemediationAttempt(
        attribution='system',
        strategy=REDECODE_CUSTOMIZED_TRANSACTIONS,
        timestamp=ts_now(),
        result=result,
        customized_transaction_count=customized_transaction_count,
        changed_transaction_count=changed_transaction_count,
    )
    if reason is not None:
        attempt['reason'] = reason
    return attempt


def _serialize_comparison_events(
        events: Sequence[EvmEvent],
        bucket: Bucket,
        treat_eth2_as_eth: bool,
        customized_ids: set[int],
) -> list[dict[str, Any]]:
    """Snapshot all transaction events, including their effect on the issue's balance."""
    return [event.serialize() | {
        'customized': event.identifier in customized_ids,
        'balance_effect': str(sum((
            event.amount if direction == EventDirection.IN else -event.amount
            for event_bucket, direction in Bucket.from_event(event, treat_eth2_as_eth)
            if event_bucket == bucket
        ), start=ZERO)),
    } for event in sorted(events, key=lambda entry: entry.sequence_index)]


def _check_issue(
        database: DBHandler,
        chains_aggregator: ChainsAggregator,
        issue: DataIssue,
        transactions: dict[EVMTxHash, list[EvmEvent]],
        treat_eth2_as_eth: bool,
        preview_cache: PreviewCache,
        reloaded_chains: set[EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE],
) -> RemediationOutcome:
    location = LocationIdentifier(issue.location)
    chain_id = cast('EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE', ChainID(location_to_chain_id(location)))  # noqa: E501
    bucket = Bucket(
        location=issue.location,
        location_label=issue.location_label or None,
        protocol=issue.protocol or None,
        asset=issue.asset,
    )
    decoder = chains_aggregator.get_evm_manager(chain_id).transactions_decoder
    preview_exceptions: tuple[type[Exception], ...] = (
        RuntimeError,
        *decoder.possible_decoding_exceptions,
    )
    changed_transaction_count = 0
    customized_transaction_count = 0
    comparisons: list[TransactionDecodingComparison] = []
    with database.conn.read_ctx() as cursor:
        mapping_states = DBHistoryEvents.get_event_mapping_states(
            cursor=cursor,
            location=location,
            entry_identifiers=[
                event.identifier for events in transactions.values() for event in events
                if event.identifier is not None
            ],
        )
    customized_ids = {
        identifier for identifier, states in mapping_states.items()
        if HistoryMappingState.CUSTOMIZED in states
    }
    try:
        for tx_hash, saved_events in transactions.items():
            checkpoint()
            saved_effects = _get_bucket_effects(saved_events, bucket, treat_eth2_as_eth)
            if len(saved_effects) != 0:
                customized_transaction_count += 1
            if (preview_events := preview_cache.get((chain_id, tx_hash))) is None:
                preview_events = _preview_transaction(
                    database=database,
                    chains_aggregator=chains_aggregator,
                    chain_id=chain_id,
                    tx_hash=tx_hash,
                    reload=chain_id not in reloaded_chains,
                )
                reloaded_chains.add(chain_id)
                preview_cache[chain_id, tx_hash] = preview_events
            preview_effects = _get_bucket_effects(preview_events, bucket, treat_eth2_as_eth)
            if len(saved_effects) == 0 and len(preview_effects) == 0:
                continue

            if len(saved_effects) == 0:
                customized_transaction_count += 1
            if saved_effects != preview_effects:
                changed_transaction_count += 1
                comparisons.append(TransactionDecodingComparison(
                    tx_hash=str(tx_hash),
                    group_identifier=saved_events[0].group_identifier,
                    saved_events=_serialize_comparison_events(
                        events=saved_events,
                        bucket=bucket,
                        treat_eth2_as_eth=treat_eth2_as_eth,
                        customized_ids=customized_ids,
                    ),
                    decoded_events=_serialize_comparison_events(
                        events=preview_events,
                        bucket=bucket,
                        treat_eth2_as_eth=treat_eth2_as_eth,
                        customized_ids=set(),
                    ),
                ))
    except preview_exceptions as e:
        log.exception('Failed to preview customized transactions for data issue %s', issue.id)
        attempt = _make_comparison_attempt(
            result='redecoding_failed',
            customized_transaction_count=customized_transaction_count,
            changed_transaction_count=changed_transaction_count,
            reason=str(e),
        )
    else:
        attempt = _make_comparison_attempt(
            result=(
                'redecoding_would_change_balance' if changed_transaction_count != 0 else
                'redecoding_would_not_change_balance'
            ),
            customized_transaction_count=customized_transaction_count,
            changed_transaction_count=changed_transaction_count,
        )

    if comparisons:
        attempt['transactions'] = comparisons
    return RemediationOutcome(
        resolved=False,
        attribution=attempt['attribution'],
        notes=attempt.get('reason', attempt.get('result', '')),
        attempt_data={
            key: value for key, value in attempt.items()
            if key not in {'attribution', 'strategy', 'timestamp'}
        },
    )


class RedecodeCustomizedTransactionsStrategy(BaseRemediationStrategy):
    """Compare customized negative-balance transactions with current decoder output.

    This is diagnostic by design: a customized transaction holds the user's own edits, so the
    strategy only previews what the current decoder would produce without persisting it, and
    never overwrites, reclassifies or deletes the saved events. A balance mismatch it finds is
    reported to the user to review, not repaired automatically.
    """

    name: Final = REDECODE_CUSTOMIZED_TRANSACTIONS

    def __init__(self, database: DBHandler, chains_aggregator: ChainsAggregator) -> None:
        self.database = database
        self.chains_aggregator = chains_aggregator
        self.treat_eth2_as_eth = CachedSettings().get_entry('treat_eth2_as_eth') is True
        self.preview_cache: PreviewCache = {}
        self.reloaded_chains: set[EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE] = set()

    def applies_to(self, issue: DataIssue) -> bool:
        return (
            issue.kind == IssueKind.NEGATIVE_BALANCE and
            issue.location_label != '' and
            LocationIdentifier(issue.location) in EVM_LOCATIONS
        )

    def attempt(self, issue: DataIssue) -> RemediationOutcome:
        location = LocationIdentifier(issue.location)
        chain_id = cast('EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE', ChainID(location_to_chain_id(location)))  # noqa: E501
        transactions = _get_customized_transactions_for_issue(
            database=self.database,
            issue=issue,
            chain_id=chain_id,
            location=location,
        )
        if len(transactions) == 0:
            return RemediationOutcome(
                resolved=False,
                attribution='not_applicable',
                notes='The issue account has no customized transaction to compare',
                record_attempt=(
                    len(issue.auto_remediation_attempts) == 0 or
                    issue.auto_remediation_attempts[-1].get('attribution') != 'not_applicable'
                ),
            )

        return _check_issue(
            database=self.database,
            chains_aggregator=self.chains_aggregator,
            issue=issue,
            transactions=transactions,
            treat_eth2_as_eth=self.treat_eth2_as_eth,
            preview_cache=self.preview_cache,
            reloaded_chains=self.reloaded_chains,
        )


PHASE_RUNNING: Final = 'running'
PHASE_COMPLETED: Final = 'completed'


def _send_remediation_phase(database: DBHandler, phase: str) -> None:
    database.msg_aggregator.add_message(
        message_type=WSMessageType.PROGRESS_UPDATES,
        data={
            'subtype': str(ProgressUpdateSubType.DATA_ISSUE_REMEDIATION),
            'phase': phase,
        },
    )


def run_data_issue_remediation(
        database: DBHandler,
        chains_aggregator: ChainsAggregator,
) -> None:
    """Run the diagnostic remediation pipeline for negative-balance data issues.

    Current balance mismatches are deliberately not handled. Re-decoding can't add the history
    they usually lack, so they are left to the user's on-demand divergence search.

    Remediation is diagnostic only: a transaction holding a customized event is never touched,
    and the customized-transaction strategy previews decoder output without persisting it.

    A run that aborts is recorded like one that finishes. Otherwise the scheduler would start
    it again on its next tick, behind the worker that made it abort and may still hold the
    decoder lock. Only a cancelled run is left unrecorded, since it did not get to do its work.
    """
    _send_remediation_phase(database, PHASE_RUNNING)
    cancelled = False
    try:
        issues_manager = DataIssuesManager(database)
        pipeline = RemediationPipeline(
            manager=issues_manager,
            strategies=(
                RedecodeCustomizedTransactionsStrategy(database, chains_aggregator),
            ),
        )
        for issue in issues_manager.list_issues(DataIssuesFilterQuery.make(
            kinds=[IssueKind.NEGATIVE_BALANCE],
            states=[IssueState.OPEN, IssueState.UNRESOLVED],
        )):
            if issue.state != IssueState.OPEN and _last_attempt_failed(issue) is False:
                continue

            pipeline.run(issue)
            checkpoint()
    except TaskCancelledError:
        cancelled = True
        raise
    finally:
        try:
            if cancelled is False:
                with database.user_write() as write_cursor:
                    database.set_static_cache(
                        write_cursor=write_cursor,
                        name=DBCacheStatic.LAST_DATA_ISSUE_REMEDIATION_TS,
                        value=ts_now(),
                    )
        finally:
            _send_remediation_phase(database, PHASE_COMPLETED)


def _last_attempt_failed(issue: DataIssue) -> bool:
    """Retry operational failures, timeouts, failed comparisons and attempts that know
    they cannot make progress, on the next scheduled run.

    An unresolved issue with no attempt at all is retried too: nothing else would ever
    advance it.
    """
    if issue.state != IssueState.UNRESOLVED:
        return False
    if len(issue.auto_remediation_attempts) == 0:
        return True

    attempt = issue.auto_remediation_attempts[-1]
    return (
        attempt.get('attribution') in {'timeout', 'strategy_failed', 'not_applicable'} or
        (
            attempt.get('strategy') == REDECODE_CUSTOMIZED_TRANSACTIONS and
            attempt.get('result') == 'redecoding_failed'
        )
    )
