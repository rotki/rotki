import logging
from collections import defaultdict
from dataclasses import dataclass
from operator import itemgetter
from typing import TYPE_CHECKING, Final, Literal

from rotkehlchen.api.v1.types import IncludeExcludeFilterData
from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.chain.accounts import BlockchainAccounts
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.constants import EXCHANGES_CPT
from rotkehlchen.chain.evm.decoding.monerium.constants import CPT_MONERIUM
from rotkehlchen.constants import HOUR_IN_SECONDS
from rotkehlchen.constants.assets import A_DAI, A_SAI
from rotkehlchen.constants.resolver import SOLANA_CHAIN_DIRECTIVE, identifier_to_evm_chain
from rotkehlchen.constants.timing import SAI_DAI_MIGRATION_TS
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.constants import (
    CHAIN_EVENT_FIELDS,
    HISTORY_BASE_ENTRY_FIELDS,
    HISTORY_MAPPING_KEY_STATE,
    HistoryEventLinkType,
    HistoryMappingState,
)
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.db.utils import get_query_chunks
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.base import (
    HistoryBaseEntry,
    HistoryBaseEntryType,
    HistoryEvent,
    get_event_direction,
)
from rotkehlchen.history.events.structures.onchain_event import OnchainEvent
from rotkehlchen.history.events.structures.types import (
    EventDirection,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import (
    BLOCKCHAIN_LOCATIONS,
    CHAINS_WITH_TRANSACTIONS,
    EVM_CHAIN_IDS_WITH_TRANSACTIONS,
    Location,
    SupportedBlockchain,
    Timestamp,
)
from rotkehlchen.utils.misc import is_valid_ethereum_tx_hash, ts_ms_to_sec, ts_now

if TYPE_CHECKING:
    from collections.abc import Iterable

    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.chain.aggregator import ChainsAggregator
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.db.settings import DBSettings

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

NATIVE_TOKEN_IDS_OF_CHAINS_WITH_TXS: Final = {
    x.get_native_token_id() for x in CHAINS_WITH_TRANSACTIONS
}
# Various entry types that should never be the matched event for an asset movement and can
# safely be excluded from the possible matches.
ENTRY_TYPES_TO_EXCLUDE_FROM_MATCHING: Final = [
    HistoryBaseEntryType.ETH_BLOCK_EVENT,
    HistoryBaseEntryType.ETH_DEPOSIT_EVENT,
    HistoryBaseEntryType.ETH_WITHDRAWAL_EVENT,
    HistoryBaseEntryType.SWAP_EVENT,
]
# Tolerance for the matched event to be on the wrong side of an asset movement during auto matching
TIMESTAMP_TOLERANCE: Final = HOUR_IN_SECONDS
LEGACY_EXCHANGE_MATCH_CUTOFF_TS: Final = Timestamp(1514764800)  # 2018-01-01 00:00:00 UTC
LEGACY_EXCHANGE_MATCH_WINDOW: Final = HOUR_IN_SECONDS * 100


@dataclass(frozen=True)
class CustomizedEventCandidate:
    """Represents a history event row used for customized duplicate detection."""
    identifier: int
    group_identifier: str
    sequence_index: int
    timestamp: int
    location: str
    location_label: str | None
    asset: str
    amount: str
    notes: str | None
    event_type: str
    event_subtype: str
    extra_data: str | None
    entry_type: int
    counterparty: str | None
    address: str | None
    customized: bool

    def signature(self) -> tuple:
        return (
            self.timestamp,
            self.location,
            self.location_label,
            self.asset,
            self.amount,
            self.notes,
            self.event_type,
            self.event_subtype,
            self.extra_data,
            self.counterparty,
            self.address,
            self.entry_type,
        )

    def direction(self) -> EventDirection | None:
        try:
            return get_event_direction(
                event_type=HistoryEventType.deserialize(self.event_type),
                event_subtype=HistoryEventSubType.deserialize(self.event_subtype),
                location=Location.deserialize_from_db(self.location),
                for_balance_tracking=True,
            )
        except DeserializationError:
            return None


@dataclass
class MovementMatchingState:
    """Shared mutable state for asset movement matching and retry processing."""
    already_matched_event_ids: set[int]
    unresolved_ambiguous_movements: dict[int, AssetMovement]
    ambiguous_movement_candidate_ids: dict[int, set[int]]
    candidate_to_ambiguous_movement_ids: dict[int, set[int]]
    movements_to_retry: set[int]
    movement_ids_to_ignore: list[int]
    unmatched_asset_movements: list[AssetMovement]


def process_eth2_events(
        chains_aggregator: 'ChainsAggregator',
        database: 'DBHandler',
) -> None:
    """Process ETH2 events and maybe modify or combine them with corresponding tx events."""
    if (eth2 := chains_aggregator.get_module('eth2')) is not None:
        eth2.combine_block_with_tx_events()
        eth2.refresh_activated_validators_deposits()

    with database.user_write() as write_cursor:
        database.set_static_cache(  # update last eth2 event processing timestamp
            write_cursor=write_cursor,
            name=DBCacheStatic.LAST_ETH2_EVENTS_PROCESSING_TS,
            value=ts_now(),
        )


def process_asset_movements(database: 'DBHandler') -> None:
    with database.match_asset_movements_lock:
        match_asset_movements(database)


def _load_customized_event_candidates(
        database: 'DBHandler',
        group_identifiers: list[str] | None = None,
) -> dict[str, list[CustomizedEventCandidate]]:
    """Load customized and related non-customized EVM/Solana events grouped by group identifier.

    Query outline:
    - Select base history event fields plus chain metadata (counterparty/address).
    - LEFT JOIN chain_events_info for EVM/Solana-specific columns.
    - LEFT JOIN history_events_mappings to mark customized rows.
    - Restrict to group identifiers that include at least one customized event (EXISTS).
    - Filter to EVM/Solana entry types and order by group/sequence for stable ordering.
    """
    group_events: dict[str, list[CustomizedEventCandidate]] = defaultdict(list)
    entry_type_values = [entry_type.serialize_for_db() for entry_type in (
        HistoryBaseEntryType.EVM_EVENT,
        HistoryBaseEntryType.EVM_SWAP_EVENT,
        HistoryBaseEntryType.SOLANA_EVENT,
        HistoryBaseEntryType.SOLANA_SWAP_EVENT,
    )]
    entry_type_placeholders = ', '.join(['?'] * len(entry_type_values))
    query = (
        'SELECT he.identifier, he.group_identifier, he.sequence_index, he.timestamp, '
        'he.location, he.location_label, he.asset, he.amount, he.notes, he.type, '
        'he.subtype, he.extra_data, he.entry_type, '
        'cei.counterparty, cei.address, '
        'CASE WHEN hm.parent_identifier IS NULL THEN 0 ELSE 1 END AS customized '
        'FROM history_events he '
        'LEFT JOIN chain_events_info cei ON he.identifier=cei.identifier '
        'LEFT JOIN history_events_mappings hm ON hm.parent_identifier=he.identifier '
        'AND hm.name=? AND hm.value=? '
        'WHERE EXISTS ('
        'SELECT 1 FROM history_events he2 '
        'JOIN history_events_mappings hm2 ON hm2.parent_identifier=he2.identifier '
        'AND hm2.name=? AND hm2.value=? '
        'WHERE he2.group_identifier=he.group_identifier '
        f'AND he2.entry_type IN ({entry_type_placeholders})) '
        f'AND he.entry_type IN ({entry_type_placeholders}) '
    )
    bindings_base = (
        HISTORY_MAPPING_KEY_STATE,
        HistoryMappingState.CUSTOMIZED.serialize_for_db(),
        HISTORY_MAPPING_KEY_STATE,
        HistoryMappingState.CUSTOMIZED.serialize_for_db(),
        *entry_type_values,
        *entry_type_values,
    )
    with database.conn.read_ctx() as cursor:
        if group_identifiers:
            for group_id_chunk, group_id_placeholders in get_query_chunks(group_identifiers):
                for entry in cursor.execute(
                    f'{query} AND he.group_identifier IN ({group_id_placeholders}) '
                    'ORDER BY he.group_identifier, he.sequence_index',
                    (*bindings_base, *group_id_chunk),
                ):
                    event = CustomizedEventCandidate(
                        identifier=entry[0],
                        group_identifier=entry[1],
                        sequence_index=entry[2],
                        timestamp=entry[3],
                        location=entry[4],
                        location_label=entry[5],
                        asset=entry[6],
                        amount=entry[7],
                        notes=entry[8],
                        event_type=entry[9],
                        event_subtype=entry[10],
                        extra_data=entry[11],
                        entry_type=entry[12],
                        counterparty=entry[13],
                        address=entry[14],
                        customized=bool(entry[15]),
                    )
                    group_events[event.group_identifier].append(event)
        else:
            for entry in cursor.execute(
                f'{query} ORDER BY he.group_identifier, he.sequence_index',
                bindings_base,
            ):
                event = CustomizedEventCandidate(
                    identifier=entry[0],
                    group_identifier=entry[1],
                    sequence_index=entry[2],
                    timestamp=entry[3],
                    location=entry[4],
                    location_label=entry[5],
                    asset=entry[6],
                    amount=entry[7],
                    notes=entry[8],
                    event_type=entry[9],
                    event_subtype=entry[10],
                    extra_data=entry[11],
                    entry_type=entry[12],
                    counterparty=entry[13],
                    address=entry[14],
                    customized=bool(entry[15]),
                )
                group_events[event.group_identifier].append(event)

    return group_events


def find_customized_event_duplicate_groups(
        database: 'DBHandler',
        group_identifiers: list[str] | None = None,
) -> tuple[list[str], list[str], list[int]]:
    """Return group identifiers for auto-fixable duplicates and manual review groups.

    Auto-fixable groups are exact matches (same fields except sequence_index/identifier)
    between at least one customized event and at least one non-customized event for EVM/Solana.
    Manual review groups are same-asset/same-direction pairs between customized and
    non-customized EVM/Solana events that are not exact matches.
    The returned exact_duplicate_ids are the non-customized event identifiers eligible for removal.
    When group_identifiers is provided, results are limited to those groups.
    """
    log.debug('Detecting duplicate customized EVM events')
    group_events = _load_customized_event_candidates(
        database=database,
        group_identifiers=group_identifiers,
    )

    auto_fix_group_ids: set[str] = set()  # groups with exact customized/non-customized matches
    manual_review_group_ids: set[str] = set()  # groups with asset+direction matches
    exact_duplicate_ids: set[int] = set()  # non-customized event identifiers to delete

    target_group_ids: set[str] | None = set(group_identifiers) if group_identifiers is not None else None  # noqa: E501
    group_iter: Iterable[tuple[str, list[CustomizedEventCandidate]]]
    if target_group_ids is None:
        group_iter = group_events.items()
    else:
        group_iter = (
            (group_id, group_events[group_id])
            for group_id in group_events
            if group_id in target_group_ids
        )

    for group_id, events in group_iter:
        # Index by signature to spot exact customized/non-customized duplicates.
        # Also track if there's a customized gas event for manual review detection.
        signatures: dict[tuple, tuple[set[int], set[int]]] = defaultdict(
            lambda: (set(), set()),
        )
        has_customized_gas = False
        for event in events:
            customized_ids, non_customized_ids = signatures[event.signature()]
            if event.customized:
                customized_ids.add(event.identifier)
                if event.counterparty == CPT_GAS:
                    has_customized_gas = True
            else:
                non_customized_ids.add(event.identifier)

        # Collect non-customized duplicates where a customized event shares the same signature.
        group_exact_ids: set[int] = set()
        for customized_ids, non_customized_ids in signatures.values():
            if customized_ids and non_customized_ids:
                group_exact_ids.update(non_customized_ids)

        # Auto-fixable groups have at least one exact customized/non-customized pair.
        if len(group_exact_ids) > 0:
            auto_fix_group_ids.add(group_id)
            exact_duplicate_ids.update(group_exact_ids)

        # build asset+direction+event_type pairs for manual review detection.
        # gas events can only be duplicates of other gas events
        # and not of events in the same direction
        customized_pairs: set[tuple[str, EventDirection, str]] = set()
        non_customized_pairs: set[tuple[str, EventDirection, str]] = set()
        for event in events:
            if (direction := event.direction()) is None:
                continue
            pair = (event.asset, direction, event.event_type)
            if event.customized:
                customized_pairs.add(pair)
            elif (
                event.identifier not in group_exact_ids and
                (event.counterparty != CPT_GAS or has_customized_gas)
            ):
                non_customized_pairs.add(pair)

        # Flag groups where customized/non-customized share asset+direction but are not exact.
        shared_pairs = customized_pairs & non_customized_pairs
        if len(customized_pairs) > 0 and len(non_customized_pairs) > 0 and len(shared_pairs) > 0:
            manual_review_group_ids.add(group_id)

    return (
        list(auto_fix_group_ids - manual_review_group_ids),  # Don't include groups in auto fix if they also have pairs that need manual review  # noqa: E501
        list(manual_review_group_ids),
        sorted(exact_duplicate_ids),
    )


def _should_auto_ignore_movement(asset_movement: AssetMovement) -> bool:
    """Check if the given asset movement should be auto ignored.
    Returns True if the asset movement has a fiat asset, or if it is a movement to/from a
    blockchain that we will not have txs for. Otherwise returns False.
    To determine if the chain is supported, first check if it is specified in the extra data.
    If not, check if the event's asset (or any asset in its collection) is from a supported chain.
    """
    if asset_movement.asset.is_fiat():
        return True

    if (
        (extra_data := asset_movement.extra_data) is not None and
        (blockchain_str := extra_data.get('blockchain')) is not None
    ):
        try:
            return SupportedBlockchain.deserialize(blockchain_str) not in CHAINS_WITH_TRANSACTIONS
        except DeserializationError:
            return True  # not even a valid SupportedBlockchain

    return False


def _get_assets_in_collection(
        asset_movement: AssetMovement,
        assets_in_collection_cache: dict[str, tuple['Asset', ...]],
) -> tuple['Asset', ...]:
    """Get assets in collection for movement asset, using cache."""
    asset_identifier = asset_movement.asset.identifier
    assets_in_collection = assets_in_collection_cache.get(asset_identifier)
    if assets_in_collection is None:
        assets_in_collection = GlobalDBHandler.get_assets_in_same_collection(
            identifier=asset_identifier,
        )
        if (
            asset_movement.asset in {A_DAI, A_SAI} and
            ts_ms_to_sec(asset_movement.timestamp) >= SAI_DAI_MIGRATION_TS
        ):
            assets_in_collection = tuple(set(assets_in_collection) | {A_DAI, A_SAI})
        assets_in_collection_cache[asset_identifier] = assets_in_collection

    return assets_in_collection


def _get_movement_match_window(asset_movement: AssetMovement, default_match_window: int) -> int:
    """Get match window for movement, with legacy exchange override."""
    if (
        default_match_window < LEGACY_EXCHANGE_MATCH_WINDOW and
        ts_ms_to_sec(asset_movement.timestamp) < LEGACY_EXCHANGE_MATCH_CUTOFF_TS
    ):
        # Some exchanges had unusually long credit windows for certain events in 2017.
        return LEGACY_EXCHANGE_MATCH_WINDOW

    return default_match_window


def _assets_are_only_unsupported_chains(assets_in_collection: tuple['Asset', ...]) -> bool:
    """Return True if none of the assets belong to chains we can query txs for."""
    return not any(
        (
            asset.identifier in NATIVE_TOKEN_IDS_OF_CHAINS_WITH_TXS or
            asset.identifier.startswith(f'{SOLANA_CHAIN_DIRECTIVE}/') or
            identifier_to_evm_chain(asset.identifier) in EVM_CHAIN_IDS_WITH_TRANSACTIONS
        ) for asset in assets_in_collection
    )


def _clear_ambiguous_candidate_mappings(
        movement_id: int,
        ambiguous_movement_candidate_ids: dict[int, set[int]],
        candidate_to_ambiguous_movement_ids: dict[int, set[int]],
) -> None:
    """Remove reverse mappings for an ambiguous movement's candidate ids."""
    for event_id in ambiguous_movement_candidate_ids.pop(movement_id, set()):
        candidate_to_ambiguous_movement_ids[event_id].discard(movement_id)


def _set_ambiguous_candidate_mappings(
        movement_id: int,
        matched_events: list[HistoryBaseEntry],
        ambiguous_movement_candidate_ids: dict[int, set[int]],
        candidate_to_ambiguous_movement_ids: dict[int, set[int]],
) -> None:
    """Set reverse mappings for an ambiguous movement's current candidate ids."""
    new_candidate_ids = {
        event_id
        for match in matched_events
        if (event_id := match.identifier) is not None
    }
    old_candidate_ids = ambiguous_movement_candidate_ids.get(movement_id, set())

    for event_id in old_candidate_ids - new_candidate_ids:
        candidate_to_ambiguous_movement_ids[event_id].discard(movement_id)
    for event_id in new_candidate_ids - old_candidate_ids:
        candidate_to_ambiguous_movement_ids[event_id].add(movement_id)

    if len(new_candidate_ids) == 0:
        ambiguous_movement_candidate_ids.pop(movement_id, None)
    else:
        ambiguous_movement_candidate_ids[movement_id] = new_candidate_ids


def _remove_unresolved_movement(
        movement_id: int | None,
        unresolved_ambiguous_movements: dict[int, AssetMovement],
        ambiguous_movement_candidate_ids: dict[int, set[int]],
        candidate_to_ambiguous_movement_ids: dict[int, set[int]],
) -> None:
    """Remove unresolved movement and its candidate mappings if present."""
    if movement_id is None:
        return

    unresolved_ambiguous_movements.pop(movement_id, None)
    _clear_ambiguous_candidate_mappings(
        movement_id=movement_id,
        ambiguous_movement_candidate_ids=ambiguous_movement_candidate_ids,
        candidate_to_ambiguous_movement_ids=candidate_to_ambiguous_movement_ids,
    )


def _process_movement_candidate_set(
        events_db: DBHistoryEvents,
        asset_movement: AssetMovement,
        fee_events: dict[str, AssetMovement],
        settings: 'DBSettings',
        assets_in_collection_cache: dict[str, tuple['Asset', ...]],
        cursor: 'DBCursor',
        blockchain_accounts: BlockchainAccounts,
        all_asset_movements: list[AssetMovement],
        matching_state: MovementMatchingState,
        from_retry: bool,
) -> None:
    """Process one movement and update retry/ignore/unmatched collections."""
    movement_id = asset_movement.identifier
    if _should_auto_ignore_movement(asset_movement=asset_movement):
        _remove_unresolved_movement(
            movement_id=movement_id,
            unresolved_ambiguous_movements=matching_state.unresolved_ambiguous_movements,
            ambiguous_movement_candidate_ids=matching_state.ambiguous_movement_candidate_ids,
            candidate_to_ambiguous_movement_ids=matching_state.candidate_to_ambiguous_movement_ids,
        )
        if movement_id is not None:
            matching_state.movement_ids_to_ignore.append(movement_id)
        return

    assets_in_collection = _get_assets_in_collection(
        asset_movement=asset_movement,
        assets_in_collection_cache=assets_in_collection_cache,
    )
    match_window = _get_movement_match_window(
        asset_movement=asset_movement,
        default_match_window=settings.asset_movement_time_range,
    )

    matched_events = find_asset_movement_matches(
        events_db=events_db,
        asset_movement=asset_movement,
        is_deposit=(is_deposit := asset_movement.event_subtype == HistoryEventSubType.RECEIVE),
        fee_event=(fee_event := fee_events.get(asset_movement.group_identifier)),
        match_window=match_window,
        cursor=cursor,
        assets_in_collection=assets_in_collection,
        blockchain_accounts=blockchain_accounts,
        already_matched_event_ids=matching_state.already_matched_event_ids,
        tolerance=settings.asset_movement_amount_tolerance,
    )
    if len(matched_events) > 1 and _has_related_movement(
        asset_movement=asset_movement,
        other_movements=all_asset_movements,
        match_window_ms=match_window * 1000,
        tolerance=settings.asset_movement_amount_tolerance,
    ):
        # Heuristic: if multiple related movements exist, pick the closest amount match.
        matched_events = _pick_closest_amount_match(
            asset_movement=asset_movement,
            matches=matched_events,
            is_deposit=is_deposit,
            fee_event=fee_event,
        )

    match_count = len(matched_events)
    if from_retry and movement_id is not None and match_count != 1:
        _set_ambiguous_candidate_mappings(
            movement_id=movement_id,
            matched_events=matched_events,
            ambiguous_movement_candidate_ids=matching_state.ambiguous_movement_candidate_ids,
            candidate_to_ambiguous_movement_ids=matching_state.candidate_to_ambiguous_movement_ids,
        )

    if match_count == 1:
        matched_event = matched_events[0]
        update_asset_movement_matched_event(
            events_db=events_db,
            asset_movement=asset_movement,
            fee_event=fee_event,
            matched_event=matched_event,
            is_deposit=is_deposit,
        )
        _remove_unresolved_movement(
            movement_id=movement_id,
            unresolved_ambiguous_movements=matching_state.unresolved_ambiguous_movements,
            ambiguous_movement_candidate_ids=matching_state.ambiguous_movement_candidate_ids,
            candidate_to_ambiguous_movement_ids=matching_state.candidate_to_ambiguous_movement_ids,
        )
        if (matched_event_id := matched_event.identifier) is not None:
            matching_state.already_matched_event_ids.add(matched_event_id)
            matching_state.movements_to_retry.update(
                matching_state.candidate_to_ambiguous_movement_ids[matched_event_id],
            )
        return

    if match_count > 1:
        if movement_id is not None:
            matching_state.unresolved_ambiguous_movements[movement_id] = asset_movement
            if not from_retry:
                _set_ambiguous_candidate_mappings(
                    movement_id=movement_id,
                    matched_events=matched_events,
                    ambiguous_movement_candidate_ids=matching_state.ambiguous_movement_candidate_ids,
                    candidate_to_ambiguous_movement_ids=matching_state.candidate_to_ambiguous_movement_ids,
                )
        return

    if _assets_are_only_unsupported_chains(assets_in_collection):
        _remove_unresolved_movement(
            movement_id=movement_id,
            unresolved_ambiguous_movements=matching_state.unresolved_ambiguous_movements,
            ambiguous_movement_candidate_ids=matching_state.ambiguous_movement_candidate_ids,
            candidate_to_ambiguous_movement_ids=matching_state.candidate_to_ambiguous_movement_ids,
        )
        if movement_id is not None:
            matching_state.movement_ids_to_ignore.append(movement_id)
        return

    if not from_retry:
        matching_state.unmatched_asset_movements.append(asset_movement)
    return


def match_asset_movements(database: 'DBHandler') -> None:
    """Analyze asset movements and find corresponding onchain events, then update those onchain
    events with proper event_type, counterparty, etc and cache the matched identifiers.
    """
    log.debug('Analyzing asset movements for corresponding onchain events...')
    events_db = DBHistoryEvents(database=database)
    asset_movements, fee_events = get_unmatched_asset_movements(database)
    settings = CachedSettings().get_settings()
    assets_in_collection_cache: dict[str, tuple[Asset, ...]] = {}
    with events_db.db.conn.read_ctx() as cursor:
        blockchain_accounts = events_db.db.get_blockchain_accounts(cursor=cursor)
        matching_state = MovementMatchingState(
            already_matched_event_ids=get_already_matched_event_ids(cursor=cursor),
            unresolved_ambiguous_movements={},
            ambiguous_movement_candidate_ids={},
            candidate_to_ambiguous_movement_ids=defaultdict(set),
            movements_to_retry=set(),
            movement_ids_to_ignore=[],
            unmatched_asset_movements=[],
        )
        for asset_movement in asset_movements:
            _process_movement_candidate_set(
                events_db=events_db,
                asset_movement=asset_movement,
                fee_events=fee_events,
                settings=settings,
                assets_in_collection_cache=assets_in_collection_cache,
                cursor=cursor,
                blockchain_accounts=blockchain_accounts,
                all_asset_movements=asset_movements,
                matching_state=matching_state,
                from_retry=False,
            )

        # Retry previously ambiguous movements when any of their candidate events gets matched.
        while len(matching_state.movements_to_retry) > 0:
            movement_id = matching_state.movements_to_retry.pop()
            if movement_id not in matching_state.unresolved_ambiguous_movements:
                continue

            asset_movement = matching_state.unresolved_ambiguous_movements[movement_id]
            _process_movement_candidate_set(
                events_db=events_db,
                asset_movement=asset_movement,
                fee_events=fee_events,
                settings=settings,
                assets_in_collection_cache=assets_in_collection_cache,
                cursor=cursor,
                blockchain_accounts=blockchain_accounts,
                all_asset_movements=asset_movements,
                matching_state=matching_state,
                from_retry=True,
            )

        matching_state.unmatched_asset_movements.extend(
            matching_state.unresolved_ambiguous_movements.values(),
        )

    if len(matching_state.movement_ids_to_ignore) > 0:
        with events_db.db.conn.write_ctx() as write_cursor:
            write_cursor.executemany(
                'INSERT OR IGNORE INTO history_event_link_ignores(event_id, link_type) '
                'VALUES(?, ?)',
                [
                    (movement_id, HistoryEventLinkType.ASSET_MOVEMENT_MATCH.serialize_for_db())
                    for movement_id in matching_state.movement_ids_to_ignore
                ],
            )

    if (unmatched_count := len(matching_state.unmatched_asset_movements)) > 0:
        log.warning(f'Failed to match {unmatched_count} asset movements')
        database.msg_aggregator.add_message(
            message_type=WSMessageType.UNMATCHED_ASSET_MOVEMENTS,
            data={'count': unmatched_count},
        )


def get_unmatched_asset_movements(
        database: 'DBHandler',
) -> tuple[list[AssetMovement], dict[str, AssetMovement]]:
    """Get all asset movements that have not been matched yet. Returns a tuple containing the list
    of asset movements and a dict of the corresponding fee events keyed by their group_identifier.
    """
    asset_movements: list[AssetMovement] = []
    fee_events: dict[str, AssetMovement] = {}
    with database.conn.read_ctx() as cursor:
        for entry in cursor.execute(
                f'SELECT {HISTORY_BASE_ENTRY_FIELDS}, {CHAIN_EVENT_FIELDS} FROM history_events '
                'LEFT JOIN chain_events_info ON history_events.identifier=chain_events_info.identifier '  # noqa: E501
                'LEFT JOIN history_event_links ON '
                'history_events.identifier=history_event_links.left_event_id AND '
                'history_event_links.link_type=? '
                'LEFT JOIN history_event_link_ignores ON '
                'history_events.identifier=history_event_link_ignores.event_id AND '
                'history_event_link_ignores.link_type=? '
                'WHERE history_events.entry_type=? AND '
                'history_event_links.left_event_id IS NULL AND '
                'history_event_link_ignores.event_id IS NULL '
                'ORDER BY timestamp DESC, sequence_index',
                (
                    HistoryEventLinkType.ASSET_MOVEMENT_MATCH.serialize_for_db(),
                    HistoryEventLinkType.ASSET_MOVEMENT_MATCH.serialize_for_db(),
                    HistoryBaseEntryType.ASSET_MOVEMENT_EVENT.serialize_for_db(),
                ),
        ):
            if (asset_movement := AssetMovement.deserialize_from_db(entry[1:])).event_subtype == HistoryEventSubType.FEE:  # noqa: E501
                fee_events[asset_movement.group_identifier] = asset_movement
            else:
                asset_movements.append(asset_movement)

    return asset_movements, fee_events


def _maybe_add_adjustment_event(
        events_db: DBHistoryEvents,
        asset_movement: AssetMovement,
        fee_event: AssetMovement | None,
        matched_event: HistoryBaseEntry,
        is_deposit: bool,
) -> None:
    """Add an event to cover the difference between the amounts of the movement and its match.
    Takes no action if the amounts match or if existing events already cover the difference.
    """
    # Include the fee amount only for deposits since for withdrawals the matched event happens
    # after the fee has already been deducted.
    movement_amount_with_fee = asset_movement.amount - fee_event.amount if (
        is_deposit and
        fee_event is not None and
        fee_event.asset == asset_movement.asset
    ) else asset_movement.amount
    if matched_event.amount in (movement_amount_with_fee, asset_movement.amount):
        return  # Don't add an adjustment if the amount is an exact match

    # Get any existing events
    with events_db.db.conn.read_ctx() as cursor:
        amount_diff = abs(movement_amount_with_fee - matched_event.amount)
        has_correct_adjustment_event, events_to_delete = False, []
        for adjustment_id, adjustment_amount in cursor.execute(
            'SELECT identifier, amount FROM history_events WHERE entry_type=? '
            'AND group_identifier IN (?,?) AND asset=? AND type=? AND subtype IN (?,?)',
            (
                HistoryBaseEntryType.HISTORY_EVENT.serialize_for_db(),
                asset_movement.group_identifier,
                matched_event.group_identifier,  # include the matched event since it may also be an asset movement.  # noqa: E501
                asset_movement.asset.identifier,
                HistoryEventType.EXCHANGE_ADJUSTMENT.serialize(),
                HistoryEventSubType.SPEND.serialize(),
                HistoryEventSubType.RECEIVE.serialize(),
            ),
        ):
            if adjustment_amount == str(amount_diff) and has_correct_adjustment_event is False:
                # An existing adjustment already covers the amount difference. May happen
                # when a user manually unlinks a match but then re-matches them, or when
                # processing the second movement when matching a movement with another movement.
                has_correct_adjustment_event = True
                continue

            events_to_delete.append(adjustment_id)

    with events_db.db.conn.write_ctx() as write_cursor:
        # Remove any existing uncustomized adjustment events present for this match pair (if this
        # movement was matched before but then unlinked it may have an existing adjustment event).
        if len(events_to_delete) > 0:
            events_db.delete_events_and_track(
                write_cursor=write_cursor,
                where_clause=(
                    f'WHERE identifier IN ({",".join("?" for _ in events_to_delete)}) '
                    'AND identifier NOT IN (SELECT parent_identifier FROM history_events_mappings '
                    'WHERE name=? AND value=?)'
                ),
                where_bindings=(
                    *events_to_delete,
                    HISTORY_MAPPING_KEY_STATE,
                    HistoryMappingState.CUSTOMIZED.serialize_for_db(),
                ),
            )

        if has_correct_adjustment_event:
            return  # An existing adjustment already covers the amount difference.

    # Get the next open sequence index for the adjustment event
    with events_db.db.conn.read_ctx() as cursor:
        next_sequence_index = cursor.execute(
            'SELECT MAX(sequence_index) FROM history_events WHERE group_identifier = ?',
            (asset_movement.group_identifier,),
        ).fetchone()[0] + 1

    # Create the movement's adjustment event
    with events_db.db.conn.write_ctx() as write_cursor:
        events_db.add_history_event(
            write_cursor=write_cursor,
            event=HistoryEvent(
                group_identifier=asset_movement.group_identifier,
                sequence_index=next_sequence_index,
                timestamp=asset_movement.timestamp,
                location=asset_movement.location,
                event_type=HistoryEventType.EXCHANGE_ADJUSTMENT,
                event_subtype=HistoryEventSubType.SPEND if (
                    (is_deposit and movement_amount_with_fee > matched_event.amount) or
                    (not is_deposit and movement_amount_with_fee < matched_event.amount)
                ) else HistoryEventSubType.RECEIVE,
                asset=asset_movement.asset,
                amount=amount_diff,
                location_label=asset_movement.location_label,
                notes=(
                    f'Adjustment of {amount_diff} {asset_movement.asset.resolve_to_asset_with_symbol().symbol} '  # noqa: E501
                    f'to account for the difference between exchange and onchain amounts.'
                ),
            ),
            mapping_values={HISTORY_MAPPING_KEY_STATE: HistoryMappingState.AUTO_MATCHED},
        )


def update_asset_movement_matched_event(
        events_db: DBHistoryEvents,
        asset_movement: AssetMovement,
        fee_event: AssetMovement | None,
        matched_event: HistoryBaseEntry,
        is_deposit: bool,
        allow_adding_adjustments: bool = True,
) -> None:
    """Update the given matched event with proper event_type, counterparty, etc and cache the
    event identifiers.
    """
    should_edit_notes = True
    if isinstance(matched_event, OnchainEvent):
        # This could also be a plain history event (i.e. a btc event, or custom event)
        # so only check/update the counterparty if the event supports it.
        if matched_event.counterparty == CPT_MONERIUM:
            should_edit_notes = False  # Monerium event notes contain important info.

        matched_event.counterparty = asset_movement.location.name.lower()
    elif isinstance(matched_event, AssetMovement):
        should_edit_notes = False  # Asset movement notes are autogenerated.

    # Modify the matched event
    if is_deposit:
        matched_event.event_type = HistoryEventType.EXCHANGE_TRANSFER
        matched_event.event_subtype = HistoryEventSubType.SPEND
        notes = 'Send {amount} {asset}'
        address_hint = ' from {location_label}'
        exchange_hint = ' to {exchange}'
    else:
        matched_event.event_type = HistoryEventType.EXCHANGE_TRANSFER
        matched_event.event_subtype = HistoryEventSubType.RECEIVE
        notes = 'Receive {amount} {asset}'
        address_hint = ' in {location_label}'
        exchange_hint = ' from {exchange}'

    if should_edit_notes:
        format_args = {
            'amount': matched_event.amount,
            'asset': matched_event.asset.resolve_to_asset_with_symbol().symbol,
        }
        if matched_event.location_label is not None:
            notes += address_hint
            format_args['location_label'] = matched_event.location_label
        if asset_movement.location_label is not None:
            format_args['exchange'] = asset_movement.location_label
            notes += exchange_hint

        matched_event.notes = notes.format(**format_args)

    if matched_event.extra_data is None:
        matched_event.extra_data = {}

    matched_event.extra_data['matched_asset_movement'] = {
        'group_identifier': asset_movement.group_identifier,
        'exchange': asset_movement.location.serialize(),
        'exchange_name': asset_movement.location_label,
    }

    if allow_adding_adjustments:
        _maybe_add_adjustment_event(
            events_db=events_db,
            asset_movement=asset_movement,
            fee_event=fee_event,
            matched_event=matched_event,
            is_deposit=is_deposit,
        )

    # Save the event and cache the matched identifiers
    with events_db.db.conn.write_ctx() as write_cursor:
        events_db.edit_history_event(
            write_cursor=write_cursor,
            event=matched_event,
            mapping_state=HistoryMappingState.AUTO_MATCHED,
            save_backup=True,
        )
        write_cursor.execute(
            'DELETE FROM history_event_link_ignores WHERE event_id=? AND link_type=?',
            (asset_movement.identifier, HistoryEventLinkType.ASSET_MOVEMENT_MATCH.serialize_for_db()),  # noqa: E501
        )
        write_cursor.execute(
            'INSERT OR REPLACE INTO history_event_links('
            'left_event_id, right_event_id, link_type) VALUES(?, ?, ?)',
            (
                asset_movement.identifier,
                matched_event.identifier,
                HistoryEventLinkType.ASSET_MOVEMENT_MATCH.serialize_for_db(),
            ),
        )
        log.debug(
            'MATCH_DEBUG: cached match movement_id='
            f'{asset_movement.identifier} matched_id={matched_event.identifier}',
        )


def should_exclude_possible_match(
        asset_movement: AssetMovement,
        event: HistoryBaseEntry,
        blockchain_accounts: BlockchainAccounts,
        already_matched_event_ids: set[int],
        exclude_unexpected_direction: bool = False,
) -> bool:
    """Check if the given event should be excluded from being a possible match.
    Returns True in the following cases:
    - Event is from the same exchange as the asset movement
    - Event is an INFORMATIONAL/APPROVE event
    - Event is a TRANSFER/NONE between tracked accounts.
    - exclude_unexpected_direction is True and the event direction opposes the expected direction
       for the movement type. Used for close matches only (allows manually matching edge cases).
       Uses accounting direction instead of balance tracking direction, since the onchain match
       for a withdrawal could have been customized to also be a withdrawal for instance (NEUTRAL
       accounting direction vs OUT balance tracking direction). But if there are multiple close
       matches, the match will be narrowed by the balance tracking direction later.
    - Event identifier is in the list of already matched ids.
    - Gas events
    """
    if (
        asset_movement.location in {Location.COINBASE, Location.COINBASEPRO} and
        asset_movement.notes is not None and
        asset_movement.notes.startswith('Transfer funds') and
        asset_movement.notes.endswith('CoinbasePro') and
        event.location not in {Location.COINBASE, Location.COINBASEPRO}
    ):
        return True  # Coinbase/CoinbasePro transfer should only match between those exchanges

    if event.location == asset_movement.location:
        return True  # only allow exchange-to-exchange between different exchanges

    is_deposit = asset_movement.event_subtype == HistoryEventSubType.RECEIVE

    if isinstance(event, OnchainEvent):
        if (
            event.event_type == HistoryEventType.SPEND and
            event.event_subtype == HistoryEventSubType.FEE and
            getattr(event, 'counterparty', None) == CPT_GAS
        ):
            return True

        if event.counterparty in EXCHANGES_CPT and (
            event.extra_data is None or
            event.extra_data.get('matched_asset_movement') is None
        ) and (
            (
                is_deposit and
                (
                    (
                        event.event_type == HistoryEventType.EXCHANGE_TRANSFER and
                        event.event_subtype == HistoryEventSubType.RECEIVE
                    ) or (
                        event.event_type == HistoryEventType.WITHDRAWAL and
                        event.event_subtype == HistoryEventSubType.REMOVE_ASSET
                    )
                )
            ) or (
                not is_deposit and
                (
                    (
                        event.event_type == HistoryEventType.EXCHANGE_TRANSFER and
                        event.event_subtype == HistoryEventSubType.SPEND
                    ) or (
                        event.event_type == HistoryEventType.DEPOSIT and
                        event.event_subtype == HistoryEventSubType.DEPOSIT_ASSET
                    )
                )
            )
        ):
            return True

    if (
        event.event_type == HistoryEventType.INFORMATIONAL and
        event.event_subtype == HistoryEventSubType.APPROVE
    ):
        return True

    if (
        event.event_type == HistoryEventType.TRANSFER and
        event.event_subtype == HistoryEventSubType.NONE and
        event.location in BLOCKCHAIN_LOCATIONS and
        (chain_accounts := blockchain_accounts.get(SupportedBlockchain.from_location(
            location=event.location,  # type: ignore[arg-type]  # checked `in BLOCKCHAIN_LOCATIONS` above
        ))) is not None and
        event.location_label in chain_accounts and
        ((  # btc/bch don't have the address attribute so can only go by a tracked location label.
            (addr := getattr(event, 'address', None)) is None and
            event.location in (Location.BITCOIN, Location.BITCOIN_CASH)
        ) or addr in chain_accounts)
    ):
        return True

    if exclude_unexpected_direction:
        expected_direction = (
            EventDirection.OUT
            if is_deposit
            else EventDirection.IN
        )
        if event.maybe_get_direction() not in {EventDirection.NEUTRAL, expected_direction}:
            return True

    return event.identifier in already_matched_event_ids


def _match_amount(
        movement_amount: FVal,
        event_amount: FVal,
        tolerance: FVal,
) -> bool:
    """Check for matching amounts with the given tolerance."""
    return (
        movement_amount == event_amount or
        abs(movement_amount - event_amount) <= movement_amount * tolerance
    )


def get_already_matched_event_ids(
        cursor: 'DBCursor',
) -> set[int]:
    """Get the ids of events that are already matched with asset movements."""
    return {int(row[0]) for row in cursor.execute(
        'SELECT right_event_id FROM history_event_links WHERE link_type=?;',
        (HistoryEventLinkType.ASSET_MOVEMENT_MATCH.serialize_for_db(),),
    )}


def find_asset_movement_matches(
        events_db: DBHistoryEvents,
        asset_movement: AssetMovement,
        is_deposit: bool,
        fee_event: AssetMovement | None,
        match_window: int,
        cursor: 'DBCursor',
        assets_in_collection: tuple['Asset', ...],
        blockchain_accounts: BlockchainAccounts,
        already_matched_event_ids: set[int],
        tolerance: FVal | None = None,
) -> list[HistoryBaseEntry]:
    """Find events that closely match what the corresponding event for the given asset movement
    should look like. Returns a list of events that match.
    """
    asset_movement_timestamp = ts_ms_to_sec(asset_movement.timestamp)
    if is_deposit:
        from_ts = asset_movement_timestamp - match_window
        to_ts = asset_movement_timestamp + TIMESTAMP_TOLERANCE
    else:
        from_ts = asset_movement_timestamp - TIMESTAMP_TOLERANCE
        to_ts = asset_movement_timestamp + match_window

    if tolerance is None:
        tolerance = CachedSettings().get_settings().asset_movement_amount_tolerance

    possible_matches = events_db.get_history_events_internal(
        cursor=cursor,
        filter_query=HistoryEventFilterQuery.make(
            assets=assets_in_collection,
            from_ts=Timestamp(from_ts),
            to_ts=Timestamp(to_ts),
            entry_types=IncludeExcludeFilterData(
                values=ENTRY_TYPES_TO_EXCLUDE_FROM_MATCHING,
                operator='NOT IN',
            ),
        ),
    )
    log.debug(
        f'MATCH_DEBUG: possible_matches={len(possible_matches)} '
        f'movement_id={asset_movement.identifier} is_deposit={is_deposit} '
        f'movement_amount={asset_movement.amount}',
    )

    expected_amounts = _get_expected_amounts(
        asset_movement=asset_movement,
        is_deposit=is_deposit,
        fee_event=fee_event,
    )

    onchain_candidates: list[HistoryBaseEntry] = []
    exchange_candidates: list[HistoryBaseEntry] = []
    for event in possible_matches:
        (exchange_candidates if isinstance(event, AssetMovement) else onchain_candidates).append(event)  # noqa: E501

    close_matches = _find_close_matches(
        candidates=onchain_candidates,
        label='onchain',
        asset_movement=asset_movement,
        is_deposit=is_deposit,
        fee_event=fee_event,
        expected_amounts=expected_amounts,
        tolerance=tolerance,
        blockchain_accounts=blockchain_accounts,
        already_matched_event_ids=already_matched_event_ids,
    )
    if len(close_matches) == 0:
        close_matches = _find_close_matches(
            candidates=exchange_candidates,
            label='exchange',
            asset_movement=asset_movement,
            is_deposit=is_deposit,
            fee_event=fee_event,
            expected_amounts=expected_amounts,
            tolerance=tolerance,
            blockchain_accounts=blockchain_accounts,
            already_matched_event_ids=already_matched_event_ids,
        )

    if len(close_matches) == 0:
        log.debug(
            f'No close matches found for asset movement {asset_movement.group_identifier} '
            f'({asset_movement.event_type.name} {asset_movement.amount} {asset_movement.asset} '
            f'from/to {asset_movement.location})',
        )

    return close_matches


def _get_expected_amounts(
        asset_movement: AssetMovement,
        is_deposit: bool,
        fee_event: AssetMovement | None,
) -> list[FVal]:
    """Build candidate amounts to compare against when matching movements."""
    expected_amounts: list[FVal] = [asset_movement.amount]
    if is_deposit and fee_event is not None and fee_event.asset == asset_movement.asset:
        expected_amounts.append(asset_movement.amount + fee_event.amount)
    if (
        not is_deposit and
        fee_event is not None and
        fee_event.asset == asset_movement.asset
    ):
        expected_amounts.append(asset_movement.amount - fee_event.amount)

    return expected_amounts


def _find_close_matches(
        candidates: list[HistoryBaseEntry],
        label: Literal['onchain', 'exchange'],
        asset_movement: AssetMovement,
        is_deposit: bool,
        fee_event: AssetMovement | None,
        expected_amounts: list[FVal],
        tolerance: FVal,
        blockchain_accounts: BlockchainAccounts,
        already_matched_event_ids: set[int],
) -> list[HistoryBaseEntry]:
    """Return candidate matches that pass amount checks and heuristics."""
    close_matches: list[HistoryBaseEntry] = []
    for event in candidates:
        if should_exclude_possible_match(
            asset_movement=asset_movement,
            event=event,
            blockchain_accounts=blockchain_accounts,
            already_matched_event_ids=already_matched_event_ids,
            exclude_unexpected_direction=True,
        ):
            log.debug(
                f'MATCH_DEBUG: excluded {label} id={event.identifier} '
                f'type={event.event_type.name} subtype={event.event_subtype.name} '
                f'amount={event.amount} location={event.location}',
            )
            continue

        # Check for matching amount, or matching amount + fee for deposits. The fee doesn't need  # noqa: E501
        # to be included for withdrawals since the onchain event will happen after the fee is
        # already deducted and the amount should always match the main asset movement amount.
        # Also allow a small tolerance as long as the received amount is less
        # than the sent amount. A fee event will be added later to account for the difference.
        if not any(
            _match_amount(
                movement_amount=expected_amount,
                event_amount=event.amount,
                tolerance=tolerance,
            )
            for expected_amount in expected_amounts
        ):
            log.debug(
                f'MATCH_DEBUG: amount mismatch {label} id={event.identifier} '
                f'movement={asset_movement.amount} event={event.amount} '
                f'fee={fee_event.amount if fee_event is not None else None}',
            )
            log.debug(
                f'Excluding possible match for asset movement {asset_movement.group_identifier} '
                f'due to differing amount. Expected {asset_movement.amount} got {event.amount}',
            )
            continue

        log.debug(
            f'MATCH_DEBUG: close match {label} id={event.identifier} '
            f'type={event.event_type.name} amount={event.amount}',
        )
        close_matches.append(event)

    if len(close_matches) == 0:
        return close_matches

    if len(close_matches) > 1:  # Multiple close matches. Prefer expected direction, then other heuristics.  # noqa: E501
        expected_direction = (
            EventDirection.OUT
            if is_deposit
            else EventDirection.IN
        )
        direction_matches = [
            match for match in close_matches
            if match.maybe_get_direction(for_balance_tracking=True) == expected_direction
        ]
        if len(direction_matches) > 0:
            close_matches = direction_matches

        asset_matches: list[HistoryBaseEntry] = []
        tx_ref_matches: list[HistoryBaseEntry] = []
        counterparty_matches: list[HistoryBaseEntry] = []
        event_type_matches: list[HistoryBaseEntry] = []
        tx_ref = None if asset_movement.extra_data is None else asset_movement.extra_data.get('transaction_id')  # noqa: E501
        # Some exchanges occasionally store tx hashes without the 0x prefix.
        if tx_ref is not None and not tx_ref.startswith('0x') and is_valid_ethereum_tx_hash(prefixed_tx_ref := f'0x{tx_ref}'):  # noqa: E501
            tx_ref = prefixed_tx_ref

        for match in close_matches:
            # Maybe match by exact asset match (matched events can have any asset in the collection)  # noqa: E501
            if match.asset == asset_movement.asset:
                asset_matches.append(match)

            if (  # Maybe match by balance tracking event direction
                (match_direction := match.maybe_get_direction(
                    for_balance_tracking=True,
                )) != EventDirection.NEUTRAL and
                ((is_deposit and match_direction == EventDirection.OUT) or
                (not is_deposit and match_direction == EventDirection.IN))
            ):
                event_type_matches.append(match)

            if isinstance(match, OnchainEvent):
                if tx_ref is not None and str(match.tx_ref) == tx_ref:  # Maybe match by tx ref
                    tx_ref_matches.append(match)

                if match.counterparty is None or match.counterparty == CPT_MONERIUM:
                    # Events with a counterparty are usually not the correct match since they are  # noqa: E501
                    # part of a properly decoded onchain operation. Monerium is an exception.
                    counterparty_matches.append(match)

        for match_list in (tx_ref_matches, asset_matches, counterparty_matches, event_type_matches):  # noqa: E501
            if len(match_list) == 1:
                return match_list

        log.debug(
            f'Multiple close matches found for '
            f'asset movement {asset_movement.group_identifier}.',
        )

    return close_matches


def _has_related_movement(
        asset_movement: AssetMovement,
        other_movements: list[AssetMovement],
        match_window_ms: int,
        tolerance: FVal,
) -> bool:
    """Check if there is another movement close in time and amount for the same asset."""
    movement_ts = asset_movement.timestamp
    for other in other_movements:
        if other is asset_movement or other.asset != asset_movement.asset:
            continue
        if abs(other.timestamp - movement_ts) > match_window_ms:
            continue
        if abs(other.amount - asset_movement.amount) <= asset_movement.amount * tolerance:
            return True

    return False


def _pick_closest_amount_match(
        asset_movement: AssetMovement,
        matches: list[HistoryBaseEntry],
        is_deposit: bool,
        fee_event: AssetMovement | None,
) -> list[HistoryBaseEntry]:
    """Pick the closest amount match if it's strictly closer than the others."""
    expected_amounts = _get_expected_amounts(
        asset_movement=asset_movement,
        is_deposit=is_deposit,
        fee_event=fee_event,
    )

    amount_differences = [
        (min(abs(match.amount - expected) for expected in expected_amounts), match)
        for match in matches
    ]
    amount_differences.sort(key=itemgetter(0))
    # Only collapse to a single candidate when there is a unique best amount match.
    # If the top two candidates have the same difference, keep all candidates and let
    # the caller handle the ambiguity with additional matching rules.
    if (
        len(amount_differences) >= 2 and
        amount_differences[0][0] < amount_differences[1][0]
    ):
        return [amount_differences[0][1]]

    return matches
