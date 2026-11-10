import json
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
from rotkehlchen.errors.misc import InputError, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
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
from rotkehlchen.locations.chains import (
    EVM_LOCATIONS,
    location_from_chain,
    location_to_chain_id,
)
from rotkehlchen.locations.types import LocationIdentifier
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.tasks.historical_balances import Bucket, process_historical_balances
from rotkehlchen.types import (
    CHAINS_WITH_TRANSACTIONS_TYPE,
    EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE,
    ChainID,
    EVMTxHash,
    TimestampMS,
    deserialize_evm_tx_hash,
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
DISCOVERY_BATCH_SIZE: Final = 500

type BucketEffect = tuple[TimestampMS, EventDirection, FVal]
type PreviewCache = dict[tuple[EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE, EVMTxHash], list[EvmEvent]]
type TrackedTransferIdentity = tuple[EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE, EVMTxHash, int]
type DecodedTransaction = tuple[
    dict[int, EvmEvent],  # the events before the redecode, by sequence index
    dict[int, EvmEvent],  # the events after the redecode, by sequence index
    bool,  # whether the transaction is customized, and so was not redecoded
]

_CHAIN_LOCATIONS: Final = tuple(
    (
        location,
        ChainID(location_to_chain_id(location)).to_blockchain().value,
        location_to_chain_id(location),
    )
    for location in EVM_LOCATIONS
)

TRACKED_ADDRESS_TRANSFER_CANDIDATES_QUERY: Final = (
    'WITH evm_chain_locations(location, blockchain, chain_id) AS ('
    f'VALUES {",".join("(?, ?, ?)" for _ in _CHAIN_LOCATIONS)}) '
    'SELECT H.identifier, C.tx_ref, L.chain_id, H.timestamp, H.location, '
    'H.location_label, H.asset, H.sequence_index FROM evm_chain_locations L '
    'JOIN blockchain_accounts S ON S.blockchain = L.blockchain '
    'CROSS JOIN history_events H INDEXED BY idx_history_events_location_label '
    'ON H.location = L.location AND H.location_label = S.account '
    'JOIN chain_events_info C ON C.identifier = H.identifier '
    'JOIN blockchain_accounts R ON R.blockchain = L.blockchain AND R.account = C.address '
    'JOIN evm_transactions T ON T.tx_hash = C.tx_ref AND T.chain_id = L.chain_id '
    'WHERE H.identifier > ? AND H.type IN (?, ?) AND H.subtype = ? AND NOT EXISTS('
    'SELECT 1 FROM history_events H2 JOIN history_events_mappings M '
    'ON M.parent_identifier = H2.identifier '
    'WHERE H2.group_identifier = H.group_identifier '
    'AND M.name = ? AND M.value = ?) '
    'ORDER BY H.identifier LIMIT ?'
)


def _tracked_address_transfer_candidates_bindings(
        after_identifier: int,
        limit: int,
) -> tuple[Any, ...]:
    return (
        *(value for chain_location in _CHAIN_LOCATIONS for value in chain_location),
        after_identifier,
        HistoryEventType.SPEND.serialize(),
        HistoryEventType.RECEIVE.serialize(),
        HistoryEventSubType.NONE.serialize(),
        HISTORY_MAPPING_KEY_STATE,
        HistoryMappingState.CUSTOMIZED.serialize_for_db(),
        limit,
    )


def _tracked_transfer_identity(payload: dict[str, Any]) -> TrackedTransferIdentity | None:
    """The stable identity of the transfer an issue was discovered from."""
    chain_id = payload.get('chain_id')
    tx_hash = payload.get('tx_hash')
    sequence_index = payload.get('sequence_index')
    if not (
        isinstance(chain_id, int) and
        isinstance(tx_hash, str) and
        isinstance(sequence_index, int)
    ):
        return None

    return (
        cast('EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE', ChainID(chain_id)),
        deserialize_evm_tx_hash(tx_hash),
        sequence_index,
    )


def _transaction_events_signature(
        events: dict[int, EvmEvent],
) -> tuple[tuple[Any, ...], ...]:
    """Every field of a transaction's events that a redecode could change."""
    return tuple(
        (
            sequence_index,
            event.identifier,
            event.event_type,
            event.event_subtype,
            event.asset.identifier,
            event.amount,
            event.location_label,
            event.address,
            event.notes,
        ) for sequence_index, event in sorted(events.items())
    )


def _write_tracked_address_transfer_issues(
        database: DBHandler,
        issues_manager: DataIssuesManager,
) -> None:
    """Write issues for plain transfers whose sender and receiver are tracked.

    Discovery is paged by event identifier so a large history is streamed in bounded
    batches, and every batch is written in one transaction by the manager. Rows that the
    scan describes exactly as they are stored are not rewritten. Issues whose event was
    replaced by a redecode that ran elsewhere are reconciled first, so the scan neither
    duplicates them nor leaves them dangling.
    """
    issues_manager.reconcile_dangling_tracked_address_transfer_issues()
    after_identifier = 0
    while True:
        with database.conn.read_ctx() as cursor:
            candidates = cursor.execute(
                TRACKED_ADDRESS_TRANSFER_CANDIDATES_QUERY,
                _tracked_address_transfer_candidates_bindings(
                    after_identifier=after_identifier,
                    limit=DISCOVERY_BATCH_SIZE,
                ),
            ).fetchall()
        if len(candidates) == 0:
            return

        issues_manager.write_tracked_address_transfer_issues([
            (
                event_identifier,
                chain_id,
                str(deserialize_evm_tx_hash(tx_ref)),
                sequence_index,
                location,
                label or '',
                asset,
                timestamp,
            ) for (
                event_identifier,
                tx_ref,
                chain_id,
                timestamp,
                location,
                label,
                asset,
                sequence_index,
            ) in candidates
        ])
        after_identifier = candidates[-1][0]
        checkpoint()


class TrackedAddressTransferStrategy(BaseRemediationStrategy):
    """Redecode a plain transfer after both counterparties become tracked.

    Force-redecoding replaces every event of a transaction, while these issues are scoped to
    a single event. The strategy therefore redecodes a transaction at most once per run and
    verifies every sibling issue against that single redecode, at its own sequence index.

    A transaction holding a customized event is never redecoded: its events are the user's
    data, and the strategy must not delete or reclassify them. The guard is evaluated again
    right before the redecode, even though discovery already skips customized transactions,
    because the user may customize the event after its issue was created.
    """

    name: Final = 'redecode_tracked_address_transfer'

    def __init__(self, database: DBHandler, chains_aggregator: ChainsAggregator) -> None:
        self.database = database
        self.chains_aggregator = chains_aggregator
        # (chain id, tx hash) -> snapshot or the failure to re-raise, so siblings share it
        self._decoded_transactions: dict[
            tuple[EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE, EVMTxHash],
            DecodedTransaction | Exception,
        ] = {}
        self.redecoded_transactions: list[
            tuple[EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE, EVMTxHash]
        ] = []
        self.earliest_redecoded_ts: TimestampMS | None = None

    def applies_to(self, issue: DataIssue) -> bool:
        return (
            issue.kind == IssueKind.TRACKED_ADDRESS_TRANSFER and
            LocationIdentifier(issue.location) in EVM_LOCATIONS
        )

    def _load_transaction_events(
            self,
            chain_id: EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE,
            tx_hash: EVMTxHash,
    ) -> tuple[dict[int, EvmEvent], dict[int, list[HistoryMappingState]]]:
        location = location_from_chain(
            cast('CHAINS_WITH_TRANSACTIONS_TYPE', chain_id.to_blockchain()),
        )
        checkpoint()
        with self.database.conn.read_ctx() as cursor:
            events = DBHistoryEvents(self.database).get_history_events_internal(
                cursor=cursor,
                filter_query=EvmEventFilterQuery.make(
                    location=location,
                    tx_hashes=[tx_hash],
                ),
            )
            mapping_states = DBHistoryEvents.get_event_mapping_states(
                cursor=cursor,
                location=location,
                entry_identifiers=[
                    event.identifier for event in events if event.identifier is not None
                ],
            )

        return (
            {event.sequence_index: event for event in events},
            mapping_states,
        )

    def _repoint_siblings(
            self,
            chain_id: EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE,
            tx_hash: EVMTxHash,
            after: dict[int, EvmEvent],
    ) -> None:
        """Move every issue of the transaction to the event that replaced its own row."""
        with self.database.conn.read_ctx() as cursor:
            rows = cursor.execute(
                'SELECT id, payload_json FROM data_issues WHERE kind = ? AND '
                "json_extract(payload_json, '$.chain_id') = ? AND "
                "json_extract(payload_json, '$.tx_hash') = ? AND event_identifier IS NOT NULL",
                (IssueKind.TRACKED_ADDRESS_TRANSFER, chain_id.serialize_for_db(), str(tx_hash)),
            ).fetchall()

        repoints: dict[int, int] = {}
        for issue_id, payload_json in rows:
            payload = json.loads(payload_json)
            if (
                (replacement := after.get(payload.get('sequence_index'))) is None or
                replacement.identifier is None or
                replacement.identifier == payload.get('event_identifier')
            ):
                continue
            repoints[issue_id] = replacement.identifier

        DataIssuesManager(self.database).repoint_tracked_address_transfer_issues(repoints)

    def _get_decoded_transaction(
            self,
            issue: DataIssue,
            chain_id: EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE,
            tx_hash: EVMTxHash,
    ) -> DecodedTransaction:
        key = (chain_id, tx_hash)
        if (cached := self._decoded_transactions.get(key)) is not None:
            if isinstance(cached, Exception):
                raise cached
            return cached

        before, mapping_states = self._load_transaction_events(chain_id=chain_id, tx_hash=tx_hash)
        if any(
            HistoryMappingState.CUSTOMIZED in states for states in mapping_states.values()
        ):
            # Never redecoding a customized transaction is what protects the user's edits.
            snapshot: DecodedTransaction = (before, before, True)
            self._decoded_transactions[key] = snapshot
            return snapshot

        decoder = self.chains_aggregator.get_evm_manager(chain_id).transactions_decoder
        try:
            decoder.decode_transaction_hashes(ignore_cache=True, tx_hashes=[tx_hash])
        except (RemoteError, DeserializationError, InputError) as e:
            self._decoded_transactions[key] = e
            raise

        after, _ = self._load_transaction_events(chain_id=chain_id, tx_hash=tx_hash)
        self._decoded_transactions[key] = (before, after, False)
        if _transaction_events_signature(before) == _transaction_events_signature(after):
            return before, after, False  # the redecode replaced nothing

        self.redecoded_transactions.append(key)
        if self.earliest_redecoded_ts is None or issue.ts_start < self.earliest_redecoded_ts:
            self.earliest_redecoded_ts = TimestampMS(issue.ts_start)
        self._repoint_siblings(chain_id=chain_id, tx_hash=tx_hash, after=after)
        return before, after, False

    def attempt(self, issue: DataIssue) -> RemediationOutcome:
        if (identity := _tracked_transfer_identity(issue.payload)) is None:
            return RemediationOutcome(
                resolved=False,
                attribution='not_applicable',
                notes='The issue has no transaction identity to verify its transfer against',
                record_attempt=False,
            )
        chain_id, tx_hash, sequence_index = identity
        before, after, customized = self._get_decoded_transaction(
            issue=issue,
            chain_id=chain_id,
            tx_hash=tx_hash,
        )
        if customized:
            return RemediationOutcome(
                resolved=False,
                attribution='not_applicable',
                notes='The transaction holds customized events and is left untouched',
                record_attempt=False,
            )
        if (original := before.get(sequence_index)) is None:
            return RemediationOutcome(
                resolved=False,
                attribution='not_applicable',
                notes='The original transfer event is no longer available',
                record_attempt=False,
            )

        expected_sender: str | None
        expected_receiver: str | None
        if original.event_type == HistoryEventType.RECEIVE:
            expected_sender, expected_receiver = original.address, original.location_label
        else:
            expected_sender, expected_receiver = original.location_label, original.address

        replacement = after.get(sequence_index)
        resolved = (
            replacement is not None and
            replacement.event_type == HistoryEventType.TRANSFER and
            replacement.event_subtype == HistoryEventSubType.NONE and
            replacement.asset == original.asset and
            replacement.amount == original.amount and
            replacement.location_label == expected_sender and
            replacement.address == expected_receiver
        )
        return RemediationOutcome(
            resolved=resolved,
            attribution='system',
            notes=(
                'Verified the internal transfer at its sequence index after redecoding'
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
        issues_manager: DataIssuesManager,
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
        self.issues_manager = DataIssuesManager(database)
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
                record_attempt=False,
            )

        return _check_issue(
            database=self.database,
            chains_aggregator=self.chains_aggregator,
            issues_manager=self.issues_manager,
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


def _reprocess_affected_balances(
        database: DBHandler,
        chains_aggregator: ChainsAggregator,
        earliest_redecoded_ts: TimestampMS | None,
) -> None:
    """Rerun the production historical-balance engine for the window a redecode changed.

    The forced redecode already marked the balances stale through the event delete/add path,
    so this only widens the run to that marker instead of duplicating it. The engine's own
    resolution path then settles negative-balance issues whose failing condition no longer
    holds.
    """
    with database.conn.read_ctx() as cursor:
        stale_from_ts = database.get_static_cache(
            cursor=cursor,
            name=DBCacheStatic.STALE_BALANCES_FROM_TS,
        )
    process_historical_balances(
        database=database,
        msg_aggregator=database.msg_aggregator,
        from_ts=(
            TimestampMS(int(stale_from_ts)) if stale_from_ts is not None
            else earliest_redecoded_ts
        ),
        chains_aggregator=chains_aggregator,
    )


def run_data_issue_remediation(
        database: DBHandler,
        chains_aggregator: ChainsAggregator,
) -> None:
    """Run registered remediation strategies for applicable data issues.

    Current balance mismatches are deliberately not handled. Re-decoding can't add the history
    they usually lack, so they are left to the user's on-demand divergence search.

    Data-changing remediation is limited to redecoding tracked-address transfers. A
    transaction holding a customized event is never touched, and the customized-transaction
    strategy is diagnostic only.
    """
    _send_remediation_phase(database, PHASE_RUNNING)
    try:
        issues_manager = DataIssuesManager(database)
        _write_tracked_address_transfer_issues(
            database=database,
            issues_manager=issues_manager,
        )
        transfer_strategy = TrackedAddressTransferStrategy(database, chains_aggregator)
        pipeline = RemediationPipeline(
            manager=issues_manager,
            strategies=(
                transfer_strategy,
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

        if len(transfer_strategy.redecoded_transactions) != 0:
            _reprocess_affected_balances(
                database=database,
                chains_aggregator=chains_aggregator,
                earliest_redecoded_ts=transfer_strategy.earliest_redecoded_ts,
            )

        with database.user_write() as write_cursor:
            database.set_static_cache(
                write_cursor=write_cursor,
                name=DBCacheStatic.LAST_DATA_ISSUE_REMEDIATION_TS,
                value=ts_now(),
            )
    finally:
        _send_remediation_phase(database, PHASE_COMPLETED)


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
