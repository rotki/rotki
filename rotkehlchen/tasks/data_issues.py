import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Final, cast

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
from rotkehlchen.errors.misc import InputError
from rotkehlchen.fval import FVal
from rotkehlchen.history.data_issues.constants import IssueKind, IssueState
from rotkehlchen.history.data_issues.manager import DataIssuesManager
from rotkehlchen.history.data_issues.types import (
    AutoRemediationAttempt,
    DataIssue,
    RedecodeComparisonResult,
    TransactionDecodingComparison,
)
from rotkehlchen.history.events.structures.types import (
    EventDirection,
    HistoryEventSubType,
    HistoryEventType,
)
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

type BucketEffect = tuple[TimestampMS, EventDirection, FVal]
type PreviewCache = dict[tuple[EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE, EVMTxHash], list[EvmEvent]]


def _redecode_tracked_address_transfers(
        database: DBHandler,
        chains_aggregator: ChainsAggregator,
        issues_manager: DataIssuesManager,
) -> None:
    """Redecode plain transfers once both their addresses are tracked.

    A transaction with customized events must remain untouched, so its plain transfer is
    surfaced for review instead.
    """
    chain_locations = tuple(
        (
            location.serialize_for_db(),
            ChainID(location.to_chain_id()).to_blockchain().value,
            location.to_chain_id(),
        )
        for location in EVM_LOCATIONS
    )
    with database.conn.read_ctx() as cursor:
        candidates = cursor.execute(
            'WITH evm_chain_locations(location, blockchain, chain_id) AS ('
            f'VALUES {",".join("(?, ?, ?)" for _ in chain_locations)}) '
            'SELECT H.identifier, C.tx_ref, L.chain_id, H.timestamp, H.location, '
            'H.location_label, H.asset, EXISTS('
            'SELECT 1 FROM history_events H2 JOIN history_events_mappings M '
            'ON M.parent_identifier = H2.identifier '
            'WHERE H2.group_identifier = H.group_identifier '
            'AND M.name = ? AND M.value = ?) FROM evm_chain_locations L '
            'JOIN blockchain_accounts S ON S.blockchain = L.blockchain '
            'CROSS JOIN history_events H INDEXED BY idx_history_events_location_label '
            'ON H.location = L.location AND H.location_label = S.account '
            'JOIN chain_events_info C ON C.identifier = H.identifier '
            'JOIN blockchain_accounts R ON R.blockchain = L.blockchain AND R.account = C.address '
            'JOIN evm_transactions T ON T.tx_hash = C.tx_ref AND T.chain_id = L.chain_id '
            'WHERE H.type IN (?, ?) AND H.subtype = ?',
            (
                *(value for chain_location in chain_locations for value in chain_location),
                HISTORY_MAPPING_KEY_STATE,
                HistoryMappingState.CUSTOMIZED.serialize_for_db(),
                HistoryEventType.SPEND.serialize(),
                HistoryEventType.RECEIVE.serialize(),
                HistoryEventSubType.NONE.serialize(),
            ),
        ).fetchall()

    transactions_by_chain: defaultdict[
        EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE,
        set[EVMTxHash],
    ] = defaultdict(set)
    for candidate in candidates:
        event_id, tx_hash, chain_id_raw, timestamp = candidate[:4]
        location, location_label, asset, is_customized = candidate[4:]
        chain_id = cast('EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE', ChainID(chain_id_raw))

        if is_customized:
            issues_manager.write_issue(
                kind=IssueKind.TRACKED_ADDRESS_TRANSFER,
                location=location,
                location_label=location_label,
                protocol=None,
                asset=asset,
                payload={'event_identifier': event_id},
                ts_start=timestamp,
                ts_end=timestamp,
            )
        else:
            transactions_by_chain[chain_id].add(tx_hash)

    for chain_id, tx_hashes in transactions_by_chain.items():
        chains_aggregator.get_evm_manager(chain_id).transactions_decoder.decode_transaction_hashes(
            ignore_cache=True,
            tx_hashes=list(tx_hashes),
        )


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
        location: Location,
) -> dict[EVMTxHash, list[EvmEvent]]:
    """Return customized transactions associated with the issue account."""
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
                location.serialize_for_db(),
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
        issues_manager: DataIssuesManager,
        issue: DataIssue,
        treat_eth2_as_eth: bool,
        preview_cache: PreviewCache,
        reloaded_chains: set[EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE],
) -> None:
    location = Location.deserialize_from_db(issue.location)
    if location not in EVM_LOCATIONS or issue.location_label == '':
        return

    chain_id = cast('EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE', ChainID(location.to_chain_id()))
    bucket = Bucket(
        location=issue.location,
        location_label=issue.location_label or None,
        protocol=issue.protocol or None,
        asset=issue.asset,
    )
    if len(transactions := _get_customized_transactions_for_issue(
        database=database,
        issue=issue,
        chain_id=chain_id,
        location=location,
    )) == 0:
        return

    try:
        issues_manager.update_state(issue.id, IssueState.AUTO_REMEDIATING)
    except InputError:
        return

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
    except TaskCancelledError:
        attempt = _make_comparison_attempt(
            result='redecoding_failed',
            customized_transaction_count=customized_transaction_count,
            changed_transaction_count=changed_transaction_count,
            reason='Remediation was cancelled before the comparison finished',
        )
        issues_manager.update_state(
            issue_id=issue.id,
            state=IssueState.UNRESOLVED,
            attempt=None if _is_repeated_failure(issue, attempt) else attempt,
        )
        raise
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
    issues_manager.update_state(
        issue_id=issue.id,
        state=IssueState.UNRESOLVED,
        attempt=None if _is_repeated_failure(issue, attempt) else attempt,
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
    reloaded_chains: set[EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE] = set()
    _redecode_tracked_address_transfers(
        database=database,
        chains_aggregator=chains_aggregator,
        issues_manager=issues_manager,
    )
    for issue in issues_manager.list_issues(DataIssuesFilterQuery.make(
        kinds=[IssueKind.NEGATIVE_BALANCE],
        states=[IssueState.OPEN, IssueState.UNRESOLVED],
    )):
        if issue.state != IssueState.OPEN and _last_attempt_failed(issue) is False:
            continue

        _check_issue(
            database=database,
            chains_aggregator=chains_aggregator,
            issues_manager=issues_manager,
            issue=issue,
            treat_eth2_as_eth=treat_eth2_as_eth,
            preview_cache=preview_cache,
            reloaded_chains=reloaded_chains,
        )
        checkpoint()

    with database.user_write() as write_cursor:
        database.set_static_cache(
            write_cursor=write_cursor,
            name=DBCacheStatic.LAST_DATA_ISSUE_REMEDIATION_TS,
            value=ts_now(),
        )


def _last_attempt_failed(issue: DataIssue) -> bool:
    """Return whether a failed comparison should be retried on the next scheduled run."""
    return (
        issue.state == IssueState.UNRESOLVED and
        len(issue.auto_remediation_attempts) != 0 and
        issue.auto_remediation_attempts[-1].get('strategy') == REDECODE_CUSTOMIZED_TRANSACTIONS and
        issue.auto_remediation_attempts[-1].get('result') == 'redecoding_failed'
    )


def _is_repeated_failure(issue: DataIssue, attempt: AutoRemediationAttempt) -> bool:
    """Return whether the previous timeline entry records the same failure."""
    return (
        attempt.get('result') == 'redecoding_failed' and
        len(issue.auto_remediation_attempts) != 0 and
        {key: value for key, value in issue.auto_remediation_attempts[-1].items()
         if key != 'timestamp'} ==
        {key: value for key, value in attempt.items() if key != 'timestamp'}
    )
