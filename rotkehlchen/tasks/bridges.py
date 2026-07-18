"""Matching of the two legs of cross-chain bridge transfers.

The anchor of a match is always the source chain DEPOSIT/BRIDGE event. Its
counterpart is the destination chain WITHDRAWAL/BRIDGE event, or a plain
receive when the destination side is not decoded as a bridge (e.g. bridges
without a decoder). Matching happens in tiers:

1. Exact: same counterparty and same protocol transfer id in the structured
   ``extra_data['bridge']`` data written by the decoders.
2. Structured heuristic: destination chain/address recorded by the decoder plus
   asset-collection equality, amount tolerance and a time window.
3. Pure heuristic: asset-collection equality, amount tolerance and time window
   only (old events decoded before the structured data existed).

A confirmed match links the two events via ``history_event_links`` with
``HistoryEventLinkType.BRIDGE_MATCH`` and stamps both sides with a
``matched_bridge`` extra_data entry. No adjustment events are created: both
legs are real onchain flows so the amount difference between them simply IS the
bridge fee, recorded as ``fee_amount`` in the link metadata.
"""
import logging
from collections import defaultdict
from time import perf_counter
from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.chain.arbitrum_one.constants import CPT_ARBITRUM_ONE
from rotkehlchen.chain.ethereum.decoding.constants import CPT_GNOSIS_CHAIN
from rotkehlchen.chain.ethereum.modules.zksync.constants import CPT_ZKSYNC
from rotkehlchen.chain.evm.decoding.constants import CPT_BASE
from rotkehlchen.chain.evm.decoding.polygon.constants import CPT_POLYGON
from rotkehlchen.chain.optimism.constants import CPT_OPTIMISM
from rotkehlchen.chain.scroll.constants import CPT_SCROLL
from rotkehlchen.constants.timing import DAY_IN_SECONDS
from rotkehlchen.db.constants import HistoryEventLinkType, HistoryMappingState
from rotkehlchen.db.filtering import AssetMovementMatchFilterQuery, HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.base import HistoryBaseEntry, HistoryBaseEntryType
from rotkehlchen.history.events.structures.evm_event import BRIDGE_EXTRA_DATA_KEY
from rotkehlchen.history.events.structures.onchain_event import OnchainEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.tasks.events import (
    TIMESTAMP_TOLERANCE_MS,
    _match_amount,
    get_already_matched_event_ids,
)
from rotkehlchen.types import (
    EVM_CHAIN_IDS_WITH_TRANSACTIONS,
    EVM_LOCATIONS,
    ChainID,
    Location,
    Timestamp,
    TimestampMS,
)
from rotkehlchen.utils.misc import ts_sec_to_ms

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.sqlite import DBCursor
    from rotkehlchen.fval import FVal

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

MATCHED_BRIDGE_KEY: Final = 'matched_bridge'
# Entry types that can never be the destination leg of a bridge
ENTRY_TYPES_TO_EXCLUDE_FROM_BRIDGE_MATCHING: Final = [
    HistoryBaseEntryType.ETH_BLOCK_EVENT,
    HistoryBaseEntryType.ETH_DEPOSIT_EVENT,
    HistoryBaseEntryType.ETH_WITHDRAWAL_EVENT,
    HistoryBaseEntryType.SWAP_EVENT,
    HistoryBaseEntryType.EVM_SWAP_EVENT,
    HistoryBaseEntryType.SOLANA_SWAP_EVENT,
    HistoryBaseEntryType.ASSET_MOVEMENT_EVENT,
]
# Native/canonical bridges with challenge periods or manual claiming can take
# much longer than liquidity bridges, which settle in minutes.
SLOW_BRIDGE_MATCH_WINDOWS: Final[dict[str, int]] = {
    CPT_ARBITRUM_ONE: 14 * DAY_IN_SECONDS,  # 7 day challenge period + manual claim
    CPT_OPTIMISM: 14 * DAY_IN_SECONDS,  # 7 day challenge period + manual claim
    CPT_BASE: 14 * DAY_IN_SECONDS,  # 7 day challenge period + manual claim
    CPT_SCROLL: 7 * DAY_IN_SECONDS,  # manual claim on L1
    CPT_POLYGON: 30 * DAY_IN_SECONDS,  # checkpoint wait + manual exit
    CPT_ZKSYNC: 7 * DAY_IN_SECONDS,
    CPT_GNOSIS_CHAIN: 7 * DAY_IN_SECONDS,  # gnosis -> ethereum claims are manual
}


def get_event_bridge_data(event: HistoryBaseEntry) -> dict[str, Any]:
    """Return the structured bridge data of the event or an empty dict."""
    if event.extra_data is None:
        return {}
    return event.extra_data.get(BRIDGE_EXTRA_DATA_KEY) or {}


def _chain_matches_location(chain_value: int | str, location: Location) -> bool:
    """Check whether a bridge extra_data chain value refers to the given location."""
    if isinstance(chain_value, int):
        return location in EVM_LOCATIONS and location.to_chain_id() == chain_value
    return chain_value in (location.serialize(), location.name.lower())


def _location_chain_label(location: Location) -> str:
    """Human readable chain name for bridge notes."""
    if location in EVM_LOCATIONS:
        return ChainID(location.to_chain_id()).label()
    return str(location)


def get_bridge_match_window(counterparty: str | None, default_window: int) -> int:
    """Candidate search window in seconds for a bridge deposit of this counterparty."""
    if counterparty is not None and (slow_window := SLOW_BRIDGE_MATCH_WINDOWS.get(counterparty)) is not None:  # noqa: E501
        return max(slow_window, default_window)
    return default_window


def get_unmatched_bridge_events(
        database: DBHandler,
) -> tuple[list[HistoryBaseEntry], list[HistoryBaseEntry]]:
    """Return the (deposits, withdrawals) bridge events not yet linked or ignored."""
    events_db = DBHistoryEvents(database=database)
    with database.conn.read_ctx() as cursor:
        deposits = events_db.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(
                type_and_subtype_combinations=[
                    (HistoryEventType.DEPOSIT, HistoryEventSubType.BRIDGE),
                ],
            ),
        )
        withdrawals = events_db.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(
                type_and_subtype_combinations=[
                    (HistoryEventType.WITHDRAWAL, HistoryEventSubType.BRIDGE),
                ],
            ),
        )
        excluded_ids = get_already_matched_event_ids(
            cursor=cursor,
            link_type=HistoryEventLinkType.BRIDGE_MATCH,
        )
        excluded_ids.update(row[0] for row in cursor.execute(
            'SELECT event_id FROM history_event_link_ignores WHERE link_type=?',
            (HistoryEventLinkType.BRIDGE_MATCH.serialize_for_db(),),
        ))

    return (
        [x for x in deposits if x.identifier not in excluded_ids],
        [x for x in withdrawals if x.identifier not in excluded_ids],
    )


def _events_conflict_on_bridge_data(
        deposit: HistoryBaseEntry,
        candidate: HistoryBaseEntry,
) -> bool:
    """Return True when the structured bridge data of the two events contradict each other."""
    deposit_data, candidate_data = get_event_bridge_data(deposit), get_event_bridge_data(candidate)
    if (
        (deposit_id := deposit_data.get('transfer_id')) is not None and
        (candidate_id := candidate_data.get('transfer_id')) is not None and
        deposit_id != candidate_id
    ):
        return True

    if (
        (to_chain := deposit_data.get('to_chain')) is not None and
        not _chain_matches_location(chain_value=to_chain, location=candidate.location)
    ):
        return True

    if (
        (candidate_from_chain := candidate_data.get('from_chain')) is not None and
        not _chain_matches_location(chain_value=candidate_from_chain, location=deposit.location)
    ):
        return True

    return (
        (to_address := deposit_data.get('to_address')) is not None and
        candidate.location_label is not None and
        candidate.location_label != to_address
    )


def _bridge_candidate_tier(
        deposit: HistoryBaseEntry,
        candidate: HistoryBaseEntry,
        tolerance: FVal,
        excluded_ids: set[int],
) -> str | None:
    """Classify a candidate event for the given bridge deposit.

    Returns 'close' for destination bridge withdrawals, 'other' for plain
    receives that could be an undecoded destination leg, or None if the
    candidate cannot be the counterpart.
    """
    if (
        candidate.identifier in excluded_ids or
        candidate.location == deposit.location or  # bridging is always cross-chain
        not _match_amount(
            movement_amount=deposit.amount,
            event_amount=candidate.amount,
            tolerance=tolerance,
        ) or
        _events_conflict_on_bridge_data(deposit=deposit, candidate=candidate)
    ):
        return None

    deposit_counterparty = getattr(deposit, 'counterparty', None)
    candidate_counterparty = getattr(candidate, 'counterparty', None)
    if (
        candidate.event_type == HistoryEventType.WITHDRAWAL and
        candidate.event_subtype == HistoryEventSubType.BRIDGE
    ):
        if (
            deposit_counterparty is not None and
            candidate_counterparty is not None and
            deposit_counterparty != candidate_counterparty
        ):
            return None  # different bridge protocols cannot be the two legs of one transfer
        return 'close'

    if (
        candidate.event_type == HistoryEventType.RECEIVE and
        candidate.event_subtype == HistoryEventSubType.NONE and
        candidate_counterparty is None
    ):
        return 'other'

    return None


def _narrow_bridge_candidates(
        deposit: HistoryBaseEntry,
        candidates: list[HistoryBaseEntry],
) -> list[HistoryBaseEntry]:
    """Apply tie-breaking heuristics when multiple candidates match a deposit.

    Prefers, in order: candidates whose recorded destination address matches,
    exact amount matches, exact asset matches, and finally the closest in time
    if it is strictly closer than the runner-up.
    """
    if len(candidates) <= 1:
        return candidates

    deposit_data = get_event_bridge_data(deposit)
    if (to_address := deposit_data.get('to_address')) is not None and len(
        address_matches := [x for x in candidates if x.location_label == to_address],
    ) > 0:
        candidates = address_matches
    if len(amount_matches := [x for x in candidates if x.amount == deposit.amount]) > 0:
        candidates = amount_matches
    if len(asset_matches := [x for x in candidates if x.asset == deposit.asset]) > 0:
        candidates = asset_matches

    if len(candidates) > 1:
        candidates = sorted(candidates, key=lambda x: abs(x.timestamp - deposit.timestamp))
        if abs(candidates[0].timestamp - deposit.timestamp) == abs(candidates[1].timestamp - deposit.timestamp):  # noqa: E501
            return candidates  # no unique closest candidate

        candidates = candidates[:1]

    return candidates


def find_bridge_transaction_matches(
        events_db: DBHistoryEvents,
        deposit: HistoryBaseEntry,
        cursor: DBCursor,
        assets_in_collection: tuple[Asset, ...],
        excluded_ids: set[int],
        tolerance: FVal,
        match_window: int,
        preloaded_possible_matches: list[HistoryBaseEntry] | None = None,
) -> list[HistoryBaseEntry]:
    """Find candidate destination events for the given bridge deposit.

    Returns close matches (destination bridge withdrawals) if any exist,
    otherwise plain-receive candidates, after tie-breaking heuristics.
    """
    if preloaded_possible_matches is None:
        from_ts_ms, to_ts_ms = get_bridge_deposit_timestamp_range_ms(
            deposit=deposit,
            match_window=match_window,
        )
        possible_matches = events_db.get_history_events_internal(
            cursor=cursor,
            filter_query=AssetMovementMatchFilterQuery.make(
                asset_timestamp_ranges=[(assets_in_collection, from_ts_ms, to_ts_ms)],
                entry_types_to_exclude=ENTRY_TYPES_TO_EXCLUDE_FROM_BRIDGE_MATCHING,
            ),
        )
    else:
        possible_matches = preloaded_possible_matches

    close_matches: list[HistoryBaseEntry] = []
    other_matches: list[HistoryBaseEntry] = []
    for candidate in possible_matches:
        tier = _bridge_candidate_tier(
            deposit=deposit,
            candidate=candidate,
            tolerance=tolerance,
            excluded_ids=excluded_ids,
        )
        if tier == 'close':
            close_matches.append(candidate)
        elif tier == 'other':
            other_matches.append(candidate)

    return _narrow_bridge_candidates(
        deposit=deposit,
        candidates=close_matches if len(close_matches) > 0 else other_matches,
    )


def get_bridge_deposit_timestamp_range_ms(
        deposit: HistoryBaseEntry,
        match_window: int,
) -> tuple[TimestampMS, TimestampMS]:
    """The destination leg comes after the deposit, modulo a small clock tolerance."""
    return (
        TimestampMS(deposit.timestamp - TIMESTAMP_TOLERANCE_MS),
        TimestampMS(deposit.timestamp + ts_sec_to_ms(Timestamp(match_window))),
    )


def update_bridge_matched_event(
        events_db: DBHistoryEvents,
        deposit: HistoryBaseEntry,
        matched_event: HistoryBaseEntry,
) -> None:
    """Persist a confirmed bridge match between the deposit and the matched event.

    Rewrites a plain receive into a proper bridge withdrawal, stamps both events
    with the matched_bridge metadata (including the implied bridge fee) and links
    them in the DB. Both edits keep backups so unlinking can restore them.
    """
    deposit_counterparty = getattr(deposit, 'counterparty', None)
    if not (
        matched_event.event_type == HistoryEventType.WITHDRAWAL and
        matched_event.event_subtype == HistoryEventSubType.BRIDGE
    ):
        matched_event.event_type = HistoryEventType.WITHDRAWAL
        matched_event.event_subtype = HistoryEventSubType.BRIDGE
        if isinstance(matched_event, OnchainEvent) and deposit_counterparty is not None:
            matched_event.counterparty = deposit_counterparty

        matched_event.notes = (
            f'Bridge {matched_event.amount} '
            f'{matched_event.asset.resolve_to_asset_with_symbol().symbol} '
            f'from {_location_chain_label(deposit.location)} '
            f'to {_location_chain_label(matched_event.location)}'
        )

    fee_amount = deposit.amount - matched_event.amount
    for event, other in ((deposit, matched_event), (matched_event, deposit)):
        if event.extra_data is None:
            event.extra_data = {}
        matched_bridge_data = {
            'group_identifier': other.group_identifier,
            'location': other.location.serialize(),
        }
        if fee_amount > 0:
            matched_bridge_data['fee_amount'] = str(fee_amount)
        event.extra_data[MATCHED_BRIDGE_KEY] = matched_bridge_data

    with events_db.db.conn.write_ctx() as write_cursor:
        for event in (deposit, matched_event):
            events_db.edit_history_event(
                write_cursor=write_cursor,
                event=event,
                mapping_state=HistoryMappingState.MATCHED,
                save_backup=True,
            )
        write_cursor.execute(
            'DELETE FROM history_event_link_ignores WHERE event_id IN (?, ?) AND link_type=?',
            (
                deposit.identifier,
                matched_event.identifier,
                HistoryEventLinkType.BRIDGE_MATCH.serialize_for_db(),
            ),
        )
        write_cursor.execute(
            'INSERT OR REPLACE INTO history_event_links('
            'left_event_id, right_event_id, link_type) VALUES(?, ?, ?)',
            (
                deposit.identifier,
                matched_event.identifier,
                HistoryEventLinkType.BRIDGE_MATCH.serialize_for_db(),
            ),
        )


def _should_auto_resolve_external(deposit: HistoryBaseEntry) -> bool:
    """Bridges to chains rotki cannot query will never find a destination leg."""
    to_chain = get_event_bridge_data(deposit).get('to_chain')
    if isinstance(to_chain, int):
        return to_chain not in {chain_id.value for chain_id in EVM_CHAIN_IDS_WITH_TRANSACTIONS}
    return False  # str chains (zksync lite) are queryable; unknown destinations stay unmatched


def _get_deposit_assets_in_collection(
        deposit: HistoryBaseEntry,
        cache: dict[str, tuple[Asset, ...]],
) -> tuple[Asset, ...]:
    """Get all assets economically equivalent to the deposit asset, using a cache."""
    identifier = deposit.asset.identifier
    if (assets := cache.get(identifier)) is None:
        cache[identifier] = assets = GlobalDBHandler.get_assets_in_same_collection(
            identifier=identifier,
        )
    return assets


def match_bridge_transactions(
        database: DBHandler,
        should_auto_match: bool = True,
) -> None:
    """Match bridge deposits with their destination chain counterparts.

    Runs the exact transfer-id tier first, then the heuristic tiers, with a
    fixpoint retry so consuming a candidate can disambiguate other deposits.
    Emits a websocket message with the remaining unmatched count.
    """
    log.debug('Analyzing bridge transactions for cross-chain counterparts...')
    started_at = perf_counter()
    events_db = DBHistoryEvents(database=database)
    deposits, withdrawals = get_unmatched_bridge_events(database=database)
    if should_auto_match is False:
        if (unmatched_count := len(deposits) + len(withdrawals)) > 0:
            database.msg_aggregator.add_message(
                message_type=WSMessageType.UNMATCHED_BRIDGE_TRANSACTIONS,
                data={'count': unmatched_count},
            )
        return

    settings = CachedSettings().get_settings()
    assets_in_collection_cache: dict[str, tuple[Asset, ...]] = {}
    ignore_ids: list[int] = []
    matched_pairs: list[tuple[HistoryBaseEntry, HistoryBaseEntry]] = []
    try:
        with database.conn.read_ctx() as cursor:
            excluded_ids = get_already_matched_event_ids(
                cursor=cursor,
                link_type=HistoryEventLinkType.BRIDGE_MATCH,
            )

            # Tier 1: exact transfer id matches
            withdrawals_by_transfer_id: dict[tuple[str | None, str], list[HistoryBaseEntry]] = defaultdict(list)  # noqa: E501
            for withdrawal in withdrawals:
                if (transfer_id := get_event_bridge_data(withdrawal).get('transfer_id')) is not None:  # noqa: E501
                    withdrawals_by_transfer_id[getattr(withdrawal, 'counterparty', None), transfer_id].append(withdrawal)  # noqa: E501

            pending_deposits = []
            for deposit in deposits:
                if (transfer_id := get_event_bridge_data(deposit).get('transfer_id')) is not None and len(candidates := [  # noqa: E501
                    x for x in withdrawals_by_transfer_id[getattr(deposit, 'counterparty', None), transfer_id]  # noqa: E501
                    if (
                        x.identifier not in excluded_ids and
                        x.location != deposit.location and
                        not _events_conflict_on_bridge_data(deposit=deposit, candidate=x)
                    )
                ]) == 1:
                    matched_pairs.append((deposit, matched_event := candidates[0]))
                    excluded_ids.update((deposit.identifier, matched_event.identifier))  # type: ignore[arg-type]  # events from the db have identifiers
                    continue

                if _should_auto_resolve_external(deposit=deposit):
                    if deposit.identifier is not None:
                        ignore_ids.append(deposit.identifier)
                    continue

                pending_deposits.append(deposit)

            # Tiers 2/3 with a fixpoint loop: a consumed candidate can turn a
            # previously ambiguous deposit into a unique match.
            while True:
                still_pending: list[HistoryBaseEntry] = []
                progressed = False
                for deposit in pending_deposits:
                    matches = find_bridge_transaction_matches(
                        events_db=events_db,
                        deposit=deposit,
                        cursor=cursor,
                        assets_in_collection=_get_deposit_assets_in_collection(
                            deposit=deposit,
                            cache=assets_in_collection_cache,
                        ),
                        excluded_ids=excluded_ids,
                        tolerance=settings.bridge_match_amount_tolerance,
                        match_window=get_bridge_match_window(
                            counterparty=getattr(deposit, 'counterparty', None),
                            default_window=settings.bridge_match_time_range,
                        ),
                    )
                    if len(matches) == 1:
                        matched_pairs.append((deposit, matched_event := matches[0]))
                        excluded_ids.update((deposit.identifier, matched_event.identifier))  # type: ignore[arg-type]  # events from the db have identifiers
                        progressed = True
                    else:
                        still_pending.append(deposit)

                pending_deposits = still_pending
                if not progressed or len(pending_deposits) == 0:
                    break

        for deposit, matched_event in matched_pairs:
            update_bridge_matched_event(
                events_db=events_db,
                deposit=deposit,
                matched_event=matched_event,
            )

        if len(ignore_ids) > 0:
            with database.conn.write_ctx() as write_cursor:
                write_cursor.executemany(
                    'INSERT OR IGNORE INTO history_event_link_ignores(event_id, link_type) '
                    'VALUES(?, ?)',
                    [
                        (event_id, HistoryEventLinkType.BRIDGE_MATCH.serialize_for_db())
                        for event_id in ignore_ids
                    ],
                )

        matched_withdrawal_ids = {matched.identifier for _, matched in matched_pairs}
        unmatched_count = len(pending_deposits) + len([
            x for x in withdrawals if x.identifier not in matched_withdrawal_ids
        ])
        if unmatched_count > 0:
            log.debug('Failed to match %s bridge transactions', unmatched_count)
            database.msg_aggregator.add_message(
                message_type=WSMessageType.UNMATCHED_BRIDGE_TRANSACTIONS,
                data={'count': unmatched_count},
            )
    finally:
        log.debug(
            'Bridge transaction matching finished in %.4fs',
            perf_counter() - started_at,
        )


def process_bridge_transactions(
        database: DBHandler,
        should_auto_match: bool = True,
) -> None:
    with database.match_bridge_transactions_lock:
        match_bridge_transactions(database=database, should_auto_match=should_auto_match)
