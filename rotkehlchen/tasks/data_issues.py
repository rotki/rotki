import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Final, cast

from rotkehlchen.concurrency import checkpoint
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.constants import HistoryMappingState
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import EvmEventFilterQuery, EvmTransactionsFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.history.data_issues.constants import IssueKind, IssueState
from rotkehlchen.history.data_issues.manager import DataIssuesManager
from rotkehlchen.history.data_issues.types import (
    AutoRemediationAttempt,
    DataIssue,
    DataIssueFilters,
    RedecodeComparisonResult,
)
from rotkehlchen.history.events.structures.types import EventDirection
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.tasks.historical_balances import Bucket
from rotkehlchen.types import (
    EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE,
    EVM_LOCATIONS,
    ChainID,
    EVMTxHash,
    Location,
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

type BucketEffect = tuple[int, EventDirection, str]
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
                effects.append((event.sequence_index, direction, str(event.amount)))

    return effects


def _get_customized_transactions_affecting_issue(
        database: DBHandler,
        issue: DataIssue,
        bucket: Bucket,
        location: Location,
        treat_eth2_as_eth: bool,
) -> dict[EVMTxHash, list[EvmEvent]]:
    """Return customized transactions whose saved events affect the issue bucket."""
    dbevents = DBHistoryEvents(database)
    with database.conn.read_ctx() as cursor:
        customized_events = dbevents.get_history_events_internal(
            cursor=cursor,
            filter_query=EvmEventFilterQuery.make(
                location=location,
                state_markers=[HistoryMappingState.CUSTOMIZED],
                to_ts=ts_ms_to_sec(TimestampMS(issue.ts_end)),
            ),
        )
        if len(customized_events) == 0:
            return {}

        transaction_events = dbevents.get_history_events_internal(
            cursor=cursor,
            filter_query=EvmEventFilterQuery.make(
                location=location,
                group_identifiers=list({event.group_identifier for event in customized_events}),
            ),
        )

    events_by_transaction: defaultdict[EVMTxHash, list[EvmEvent]] = defaultdict(list)
    for event in transaction_events:
        if event.timestamp <= issue.ts_end:
            events_by_transaction[event.tx_ref].append(event)

    return {
        tx_hash: events
        for tx_hash, events in events_by_transaction.items()
        if len(_get_bucket_effects(events, bucket, treat_eth2_as_eth)) != 0
    }


def _preview_transaction(
        database: DBHandler,
        chains_aggregator: ChainsAggregator,
        chain_id: EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE,
        tx_hash: EVMTxHash,
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


def _check_issue(
        database: DBHandler,
        chains_aggregator: ChainsAggregator,
        issues_manager: DataIssuesManager,
        issue: DataIssue,
        treat_eth2_as_eth: bool,
        preview_cache: PreviewCache,
) -> None:
    location = Location.deserialize_from_db(issue.location)
    if location not in EVM_LOCATIONS:
        return

    chain_id = cast('EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE', ChainID(location.to_chain_id()))
    bucket = Bucket(
        location=issue.location,
        location_label=issue.location_label or None,
        protocol=issue.protocol or None,
        asset=issue.asset,
    )
    if len(transactions := _get_customized_transactions_affecting_issue(
        database=database,
        issue=issue,
        bucket=bucket,
        location=location,
        treat_eth2_as_eth=treat_eth2_as_eth,
    )) == 0:
        return

    issues_manager.update_state(issue.id, IssueState.AUTO_REMEDIATING)
    changed_transaction_count = 0
    try:
        for tx_hash, saved_events in transactions.items():
            if (preview_events := preview_cache.get((chain_id, tx_hash))) is None:
                preview_events = _preview_transaction(
                    database=database,
                    chains_aggregator=chains_aggregator,
                    chain_id=chain_id,
                    tx_hash=tx_hash,
                )
                preview_cache[chain_id, tx_hash] = preview_events
            if _get_bucket_effects(saved_events, bucket, treat_eth2_as_eth) != _get_bucket_effects(
                    preview_events,
                    bucket,
                    treat_eth2_as_eth,
            ):
                changed_transaction_count += 1
            checkpoint()
    except Exception as e:
        log.exception('Failed to preview customized transactions for data issue %s', issue.id)
        attempt = _make_comparison_attempt(
            result='redecoding_failed',
            customized_transaction_count=len(transactions),
            changed_transaction_count=changed_transaction_count,
            reason=str(e),
        )
    else:
        attempt = _make_comparison_attempt(
            result=(
                'redecoding_would_change_balance' if changed_transaction_count != 0 else
                'redecoding_would_not_change_balance'
            ),
            customized_transaction_count=len(transactions),
            changed_transaction_count=changed_transaction_count,
        )

    issues_manager.update_state(
        issue_id=issue.id,
        state=IssueState.UNRESOLVED,
        attempt=attempt,
    )


def run_data_issue_remediation(
        database: DBHandler,
        chains_aggregator: ChainsAggregator,
) -> None:
    """Check whether current decoders would change customized negative-balance transactions.

    Saved events are never removed or replaced. Each applicable issue receives a diagnostic
    timeline entry and remains unresolved for the user to review.
    """
    issues_manager = DataIssuesManager(database)
    treat_eth2_as_eth = CachedSettings().get_entry('treat_eth2_as_eth') is True
    preview_cache: PreviewCache = {}
    for issue in issues_manager.list_issues(DataIssueFilters(
        kind=IssueKind.NEGATIVE_BALANCE,
        state=IssueState.OPEN,
    )):
        _check_issue(
            database=database,
            chains_aggregator=chains_aggregator,
            issues_manager=issues_manager,
            issue=issue,
            treat_eth2_as_eth=treat_eth2_as_eth,
            preview_cache=preview_cache,
        )
        checkpoint()

    with database.user_write() as write_cursor:
        database.set_static_cache(
            write_cursor=write_cursor,
            name=DBCacheStatic.LAST_DATA_ISSUE_REMEDIATION_TS,
            value=ts_now(),
        )
