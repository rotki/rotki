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


def _write_tracked_address_transfer_issues(
        database: DBHandler,
        issues_manager: DataIssuesManager,
) -> None:
    """Write issues for plain transfers whose sender and receiver are tracked."""
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

    for candidate in candidates:
        event_id, _tx_hash, _chain_id, timestamp = candidate[:4]
        location, location_label, asset, _is_customized = candidate[4:]
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


class TrackedAddressTransferStrategy(BaseRemediationStrategy):
    """Redecode a plain transfer after both counterparties become tracked."""

    name: Final = 'redecode_tracked_address_transfer'

    def __init__(self, database: DBHandler, chains_aggregator: ChainsAggregator) -> None:
        self.database = database
        self.chains_aggregator = chains_aggregator
        self.candidates: dict[
            int,
            tuple[EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE, EVMTxHash],
        ] = {}

    def _get_candidate(
            self,
            issue: DataIssue,
    ) -> tuple[EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE, EVMTxHash] | None:
        if issue.kind != IssueKind.TRACKED_ADDRESS_TRANSFER:
            return None

        location = Location.deserialize_from_db(issue.location)
        if location not in EVM_LOCATIONS:
            return None
        chain_id = cast('EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE', ChainID(location.to_chain_id()))

        with self.database.conn.read_ctx() as cursor:
            row = cursor.execute(
                'SELECT C.tx_ref, T.chain_id, EXISTS('
                'SELECT 1 FROM history_events H2 JOIN history_events_mappings M '
                'ON M.parent_identifier = H2.identifier '
                'WHERE H2.group_identifier = H.group_identifier '
                'AND M.name = ? AND M.value = ?) FROM history_events H '
                'JOIN chain_events_info C ON C.identifier = H.identifier '
                'JOIN evm_transactions T ON T.tx_hash = C.tx_ref AND T.chain_id = ? '
                'WHERE H.identifier = ?',
                (
                    HISTORY_MAPPING_KEY_STATE,
                    HistoryMappingState.CUSTOMIZED.serialize_for_db(),
                    chain_id.serialize_for_db(),
                    issue.payload['event_identifier'],
                ),
            ).fetchone()
        if row is None or row[2]:
            return None

        return (
            chain_id,
            EVMTxHash(row[0]),
        )

    def applies_to(self, issue: DataIssue) -> bool:
        if (candidate := self._get_candidate(issue)) is None:
            return False

        self.candidates[issue.id] = candidate
        return True

    def attempt(self, issue: DataIssue) -> RemediationOutcome:
        chain_id, tx_hash = self.candidates.pop(issue.id)
        with self.database.conn.read_ctx() as cursor:
            original = cursor.execute(
                'SELECT H.type, H.amount, H.location_label, C.address FROM history_events H '
                'JOIN chain_events_info C ON C.identifier = H.identifier WHERE H.identifier = ?',
                (issue.payload['event_identifier'],),
            ).fetchone()
        if original is None:
            return RemediationOutcome(False, 'system', 'Original transfer is no longer available')
        event_type, amount, sender, receiver = original
        if event_type == HistoryEventType.RECEIVE.serialize():
            sender, receiver = receiver, sender

        self.chains_aggregator.get_evm_manager(
            chain_id,
        ).transactions_decoder.decode_transaction_hashes(
            ignore_cache=True,
            tx_hashes=[tx_hash],
        )
        with self.database.conn.read_ctx() as cursor:
            resolved = cursor.execute(
                'SELECT 1 FROM history_events H '
                'JOIN chain_events_info C ON C.identifier = H.identifier '
                'WHERE C.tx_ref = ? AND H.location = ? AND H.asset = ? AND H.amount = ? '
                'AND H.location_label = ? AND C.address = ? AND H.type = ? AND H.subtype = ?',
                (
                    tx_hash, issue.location, issue.asset, amount, sender, receiver,
                    HistoryEventType.TRANSFER.serialize(), HistoryEventSubType.NONE.serialize(),
                ),
            ).fetchone() is not None
        return RemediationOutcome(
            resolved=resolved,
            attribution='system',
            notes=(
                'Verified internal transfer after redecoding'
                if resolved else 'Redecoding did not produce the expected internal transfer'
            ),
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
        transactions: dict[EVMTxHash, list[EvmEvent]],
        treat_eth2_as_eth: bool,
        preview_cache: PreviewCache,
        reloaded_chains: set[EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE],
) -> RemediationOutcome:
    location = Location.deserialize_from_db(issue.location)
    chain_id = cast('EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE', ChainID(location.to_chain_id()))
    bucket = Bucket(
        location=issue.location,
        location_label=issue.location_label or None,
        protocol=issue.protocol or None,
        asset=issue.asset,
    )
    decoder = chains_aggregator.get_evm_manager(chain_id).transactions_decoder
    # TODO: Replace preview-only comparison with stale-marked production
    # reprocessing for the full issue window.
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
            attempt=attempt,
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
    """Compare customized negative-balance transactions with current decoder output."""

    name: Final = REDECODE_CUSTOMIZED_TRANSACTIONS

    def __init__(self, database: DBHandler, chains_aggregator: ChainsAggregator) -> None:
        self.database = database
        self.chains_aggregator = chains_aggregator
        self.issues_manager = DataIssuesManager(database)
        self.treat_eth2_as_eth = CachedSettings().get_entry('treat_eth2_as_eth') is True
        self.preview_cache: PreviewCache = {}
        self.reloaded_chains: set[EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE] = set()
        self.transactions: dict[int, dict[EVMTxHash, list[EvmEvent]]] = {}

    def applies_to(self, issue: DataIssue) -> bool:
        if issue.kind != IssueKind.NEGATIVE_BALANCE or issue.location_label == '':
            return False
        location = Location.deserialize_from_db(issue.location)
        if location not in EVM_LOCATIONS:
            return False

        chain_id = cast('EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE', ChainID(location.to_chain_id()))
        transactions = _get_customized_transactions_for_issue(
            database=self.database,
            issue=issue,
            chain_id=chain_id,
            location=location,
        )
        if len(transactions) == 0:
            return False

        self.transactions[issue.id] = transactions
        return True

    def attempt(self, issue: DataIssue) -> RemediationOutcome:
        return _check_issue(
            database=self.database,
            chains_aggregator=self.chains_aggregator,
            issues_manager=self.issues_manager,
            issue=issue,
            transactions=self.transactions.pop(issue.id),
            treat_eth2_as_eth=self.treat_eth2_as_eth,
            preview_cache=self.preview_cache,
            reloaded_chains=self.reloaded_chains,
        )


def run_data_issue_remediation(
        database: DBHandler,
        chains_aggregator: ChainsAggregator,
) -> None:
    """Run registered remediation strategies for applicable data issues."""
    database.msg_aggregator.add_message(
        message_type=WSMessageType.PROGRESS_UPDATES,
        data={'subtype': str(ProgressUpdateSubType.DATA_ISSUE_REMEDIATION)},
    )
    issues_manager = DataIssuesManager(database)
    _write_tracked_address_transfer_issues(
        database=database,
        issues_manager=issues_manager,
    )
    pipeline = RemediationPipeline(
        manager=issues_manager,
        strategies=(
            TrackedAddressTransferStrategy(database, chains_aggregator),
            RedecodeCustomizedTransactionsStrategy(database, chains_aggregator),
        ),
    )
    for issue in issues_manager.list_issues(DataIssuesFilterQuery.make(
        kinds=[IssueKind.NEGATIVE_BALANCE, IssueKind.TRACKED_ADDRESS_TRANSFER],
        states=[IssueState.OPEN, IssueState.UNRESOLVED],
    )):
        if issue.state != IssueState.OPEN and _last_attempt_failed(issue) is False:
            continue

        pipeline.run(issue)
        checkpoint()

    with database.user_write() as write_cursor:
        database.set_static_cache(
            write_cursor=write_cursor,
            name=DBCacheStatic.LAST_DATA_ISSUE_REMEDIATION_TS,
            value=ts_now(),
        )


def _last_attempt_failed(issue: DataIssue) -> bool:
    """Retry operational failures, timeouts, and failed comparisons on the next scheduled run."""
    return (
        issue.state == IssueState.UNRESOLVED and
        len(issue.auto_remediation_attempts) != 0 and
        (
            (attempt := issue.auto_remediation_attempts[-1]).get('attribution') in {
                'timeout', 'strategy_failed',
            } or
            (
                attempt.get('strategy') == REDECODE_CUSTOMIZED_TRANSACTIONS and
                attempt.get('result') == 'redecoding_failed'
            )
        )
    )
