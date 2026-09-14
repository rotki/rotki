"""Matching of the two legs of cross-chain bridge transfers.

For automatic matching the anchor is always the source chain DEPOSIT/BRIDGE
event. Its counterpart is the destination chain WITHDRAWAL/BRIDGE event, or a
plain receive when the destination side is not decoded as a bridge (e.g.
bridges without a decoder). Manual matching via the API can also anchor on a
destination chain WITHDRAWAL/BRIDGE event, searching backward in time for the
source leg (a bridge deposit or a plain spend). Matching happens in tiers:

1. Exact: compatible counterparties and the same protocol transfer id in the
   structured ``extra_data['bridge']`` data written by the decoders. An aggregator
   and its underlying bridge (currently LI.FI and Relay) are compatible.
2. Structured heuristic: destination chain/address recorded by the decoder plus
   target asset (when available), asset-collection equality, amount tolerance and
   a time window. Cross-asset routes cannot use source/destination amounts.
3. Pure heuristic: asset-collection equality, amount tolerance and time window
   only (old events decoded before the structured data existed).

A confirmed match links the two events via ``history_event_links`` with
``HistoryEventLinkType.BRIDGE_MATCH`` and stamps both sides with a
``matched_bridge`` extra_data entry. No adjustment events are created: both
legs are real onchain flows. For economically equivalent assets the amount
difference is the bridge fee, recorded as ``fee_amount`` in the link metadata.

The one exception is legs whose counterpart can never be pulled because the
counterpart chain is no longer queryable (e.g. zksync lite after its API shut
down). For those a mirror counterpart event is manufactured from the leg's own
data — marked with the SYNTHETIC mapping state so the user can tell it apart —
and linked like any other match. This happens automatically for ZKsync Lite
sunset claims and on demand via the create-counterpart resolution of the API.
"""
import logging
from collections import defaultdict
from time import perf_counter
from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.arbitrum_one.constants import CPT_ARBITRUM_ONE
from rotkehlchen.chain.ethereum.decoding.constants import CPT_GNOSIS_CHAIN
from rotkehlchen.chain.ethereum.modules.zksync.constants import (
    CPT_ZKSYNC,
    ZKSYNC_LITE_SUNSET_CLAIM,
)
from rotkehlchen.chain.evm.constants import ETH_SPECIAL_ADDRESS, ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import CPT_BASE
from rotkehlchen.chain.evm.decoding.lifi.constants import CPT_LIFI
from rotkehlchen.chain.evm.decoding.polygon.constants import CPT_POLYGON
from rotkehlchen.chain.evm.decoding.relay.constants import CPT_RELAY
from rotkehlchen.chain.evm.decoding.socket_bridge.constants import CPT_SOCKET
from rotkehlchen.chain.optimism.constants import CPT_OPTIMISM
from rotkehlchen.chain.scroll.constants import CPT_SCROLL
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.constants.timing import DAY_IN_SECONDS
from rotkehlchen.db.constants import (
    HISTORY_MAPPING_KEY_STATE,
    HistoryEventLinkType,
    HistoryMappingState,
)
from rotkehlchen.db.filtering import AssetMovementMatchFilterQuery, HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.base import (
    HistoryBaseEntry,
    HistoryBaseEntryType,
    HistoryEvent,
)
from rotkehlchen.history.events.structures.evm_event import BRIDGE_EXTRA_DATA_KEY, EvmEvent
from rotkehlchen.history.events.structures.onchain_event import OnchainEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.tasks.calendar import acknowledge_matched_l2_bridge_calendar_entry
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
    SupportedBlockchain,
    Timestamp,
    TimestampMS,
)
from rotkehlchen.utils.misc import ts_sec_to_ms

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.sqlite import DBCursor
    from rotkehlchen.fval import FVal

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

MATCHED_BRIDGE_KEY: Final = 'matched_bridge'
SYNTHETIC_BRIDGE_GROUP_PREFIX: Final = 'synthbridge_'
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
# Legs rotki decodes without a counterparty. Their location is then the only thing saying
# which bridge, and so which settlement window, they belong to.
BRIDGE_COUNTERPARTY_BY_LOCATION: Final[dict[Location, str]] = {
    Location.ZKSYNC_LITE: CPT_ZKSYNC,
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


def get_bridge_match_window(event: HistoryBaseEntry, default_window: int) -> int:
    """Candidate search window in seconds for this bridge deposit.

    Which bridge a leg belongs to is normally read off its counterparty. The legs rotki
    decodes without one, such as a zksync lite exit, are recognized by their location.
    """
    if (counterparty := getattr(event, 'counterparty', None)) is None:
        counterparty = BRIDGE_COUNTERPARTY_BY_LOCATION.get(event.location)
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
        deposits.extend(events_db.get_history_events_internal(
            cursor=cursor,  # exits bridge out too, they just cannot state their amount yet
            filter_query=HistoryEventFilterQuery.make(
                location=Location.ZKSYNC_LITE,
                type_and_subtype_combinations=[
                    (HistoryEventType.INFORMATIONAL, HistoryEventSubType.NONE),
                ],
            ),
        ))
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

    if (to_address := deposit_data.get('to_address')) is None:
        return False

    candidate_to_address = candidate_data.get('to_address')
    return to_address != (
        candidate_to_address
        if candidate_to_address is not None
        else candidate.location_label
    )


def is_zksync_lite_exit(event: HistoryBaseEntry) -> bool:
    """Check whether the event is a zksync lite forced or full exit.

    Such an exit sweeps the account's whole balance of one token, so the amount is only
    settled when the rollup executes it and the zksync API never states it. rotki decodes
    it as an informational event with a zero amount, which is the only informational event
    it creates for that chain. It is a real bridging out though, so it is matched on asset
    and recipient alone and promoted to a proper bridge leg, taking its amount from the
    ethereum leg that paid it out, once that counterpart is found.
    """
    return (
        event.location == Location.ZKSYNC_LITE and
        event.event_type == HistoryEventType.INFORMATIONAL and
        event.event_subtype == HistoryEventSubType.NONE
    )


def _is_bridge_withdrawal(event: HistoryBaseEntry) -> bool:
    """Check whether the event is a decoded destination-side bridge leg."""
    return (
        event.event_type == HistoryEventType.WITHDRAWAL and
        event.event_subtype == HistoryEventSubType.BRIDGE
    )


def _bridge_counterparties_match(
        first_counterparty: str | None,
        second_counterparty: str | None,
) -> bool:
    """Return whether counterparties can describe the two legs of one bridge transfer."""
    counterparties = frozenset((first_counterparty, second_counterparty))
    return (
        first_counterparty == second_counterparty or
        counterparties == frozenset((CPT_LIFI, CPT_RELAY)) or
        CPT_SOCKET in counterparties
    )


def _have_exact_transfer_id_match(
        first_event: HistoryBaseEntry,
        second_event: HistoryBaseEntry,
) -> bool:
    """Return whether both events carry the same non-empty protocol transfer id."""
    return (
        (first_id := get_event_bridge_data(first_event).get('transfer_id')) is not None and
        first_id == get_event_bridge_data(second_event).get('transfer_id')
    )


def _is_socket_bridge_pair(
        first_event: HistoryBaseEntry,
        second_event: HistoryBaseEntry,
) -> bool:
    """Return whether Socket labels either side of a possible bridge pair."""
    return CPT_SOCKET in (
        getattr(first_event, 'counterparty', None),
        getattr(second_event, 'counterparty', None),
    )


def _get_bridge_target_asset(event: HistoryBaseEntry) -> Asset | None:
    """Resolve the target asset recorded on a source-side LI.FI bridge event."""
    if (
        _is_bridge_withdrawal(event) or
        getattr(event, 'counterparty', None) != CPT_LIFI
    ):
        return None

    bridge_data = get_event_bridge_data(event)
    if (
        not isinstance(to_chain := bridge_data.get('to_chain'), int) or
        not isinstance(to_asset := bridge_data.get('to_asset'), str)
    ):
        return None

    try:
        chain_id = ChainID.deserialize(to_chain)
        asset_address = deserialize_evm_address(to_asset)
    except DeserializationError:
        return None

    if chain_id not in EVM_CHAIN_IDS_WITH_TRANSACTIONS:
        return None
    if asset_address in (ZERO_ADDRESS, ETH_SPECIAL_ADDRESS):
        return Asset(chain_id.to_blockchain().get_native_token_id())
    return Asset(evm_address_to_identifier(address=asset_address, chain_id=chain_id))


def _bridge_candidate_tier(
        bridge_event: HistoryBaseEntry,
        candidate: HistoryBaseEntry,
        assets_in_collection: tuple[Asset, ...],
        tolerance: FVal,
        excluded_ids: set[int],
) -> str | None:
    """Classify a candidate event for the given bridge leg (deposit or withdrawal).

    Returns 'close' for counterpart bridge legs, 'other' for plain
    receives/spends that could be an undecoded counterpart leg, or None if the
    candidate cannot be the counterpart.
    """
    if is_zksync_lite_exit(bridge_event):
        # The exit states no amount, so only its asset and recipient can identify the
        # payout. Nothing weaker than an identified bridge leg is accepted, since the
        # match is what the exit's amount gets taken from.
        return 'close' if (
            candidate.identifier not in excluded_ids and
            candidate.location != bridge_event.location and
            _is_bridge_withdrawal(candidate) and
            candidate.asset == bridge_event.asset and
            candidate.location_label == bridge_event.location_label
        ) else None

    anchor_is_withdrawal = _is_bridge_withdrawal(bridge_event)
    deposit_side, withdrawal_side = (
        (candidate, bridge_event) if anchor_is_withdrawal else (bridge_event, candidate)
    )
    has_exact_transfer_id = (
        not _is_socket_bridge_pair(bridge_event, candidate) and
        _have_exact_transfer_id_match(bridge_event, candidate)
    )
    is_cross_asset_route = (
        anchor_is_withdrawal is False and
        _get_bridge_target_asset(bridge_event) is not None and
        bridge_event.asset not in assets_in_collection and
        candidate.asset in assets_in_collection
    )
    if (
        candidate.identifier in excluded_ids or
        candidate.location == bridge_event.location or  # bridging is always cross-chain
        (
            has_exact_transfer_id is False and
            is_cross_asset_route is False and
            not _match_amount(
                movement_amount=bridge_event.amount,
                event_amount=candidate.amount,
                tolerance=tolerance,
            )
        ) or
        _events_conflict_on_bridge_data(deposit=deposit_side, candidate=withdrawal_side)
    ):
        return None

    anchor_counterparty = getattr(bridge_event, 'counterparty', None)
    candidate_counterparty = getattr(candidate, 'counterparty', None)
    if (
        candidate.event_type == (
            HistoryEventType.DEPOSIT if anchor_is_withdrawal else HistoryEventType.WITHDRAWAL
        ) and candidate.event_subtype == HistoryEventSubType.BRIDGE
    ):
        if (
            anchor_counterparty is not None and
            candidate_counterparty is not None and
            not _bridge_counterparties_match(
                first_counterparty=anchor_counterparty,
                second_counterparty=candidate_counterparty,
            )
        ):
            return None  # different bridge protocols cannot be the two legs of one transfer
        return 'close'

    if (
        candidate.event_type == (
            HistoryEventType.SPEND if anchor_is_withdrawal else HistoryEventType.RECEIVE
        ) and
        candidate.event_subtype == HistoryEventSubType.NONE and
        candidate_counterparty is None
    ):
        return 'other'

    return None


def find_bridge_transaction_exact_matches(
        events_db: DBHistoryEvents,
        bridge_event: HistoryBaseEntry,
        cursor: DBCursor,
        excluded_ids: set[int],
) -> list[HistoryBaseEntry]:
    """Find non-Socket opposite bridge legs with the same exact protocol transfer id."""
    if get_event_bridge_data(bridge_event).get('transfer_id') is None:
        return []

    anchor_is_withdrawal = _is_bridge_withdrawal(bridge_event)
    candidates = events_db.get_history_events_internal(
        cursor=cursor,
        filter_query=HistoryEventFilterQuery.make(type_and_subtype_combinations=[(
            HistoryEventType.DEPOSIT if anchor_is_withdrawal else HistoryEventType.WITHDRAWAL,
            HistoryEventSubType.BRIDGE,
        )]),
    )
    matches: list[HistoryBaseEntry] = []
    for candidate in candidates:
        deposit_side, withdrawal_side = (
            (candidate, bridge_event) if anchor_is_withdrawal else (bridge_event, candidate)
        )
        if (
            _is_socket_bridge_pair(bridge_event, candidate) or
            candidate.identifier in excluded_ids or
            candidate.location == bridge_event.location or
            not _have_exact_transfer_id_match(bridge_event, candidate) or
            not _bridge_counterparties_match(
                first_counterparty=getattr(bridge_event, 'counterparty', None),
                second_counterparty=getattr(candidate, 'counterparty', None),
            ) or
            _events_conflict_on_bridge_data(deposit=deposit_side, candidate=withdrawal_side)
        ):
            continue
        matches.append(candidate)

    return matches


def _narrow_bridge_candidates(
        bridge_event: HistoryBaseEntry,
        candidates: list[HistoryBaseEntry],
) -> list[HistoryBaseEntry]:
    """Apply tie-breaking heuristics when multiple candidates match a bridge leg.

    Prefers, in order: candidates agreeing on the recorded destination address
    (held by the deposit-side event, whichever side that is), exact amount
    matches, exact asset matches, and finally the closest in time if it is
    strictly closer than the runner-up.
    """
    if len(candidates) <= 1:
        return candidates

    if len(transfer_id_matches := [
        candidate for candidate in candidates
        if _have_exact_transfer_id_match(bridge_event, candidate)
    ]) > 0:
        candidates = transfer_id_matches
    if _is_bridge_withdrawal(bridge_event):  # candidates are source legs carrying the address
        if bridge_event.location_label is not None and len(address_matches := [
            x for x in candidates
            if get_event_bridge_data(x).get('to_address') == bridge_event.location_label
        ]) > 0:
            candidates = address_matches
    elif (to_address := get_event_bridge_data(bridge_event).get('to_address')) is not None and len(
        address_matches := [x for x in candidates if x.location_label == to_address],
    ) > 0:
        candidates = address_matches
    if len(amount_matches := [x for x in candidates if x.amount == bridge_event.amount]) > 0:
        candidates = amount_matches
    if len(asset_matches := [x for x in candidates if x.asset == bridge_event.asset]) > 0:
        candidates = asset_matches

    if len(candidates) > 1:
        candidates = sorted(candidates, key=lambda x: abs(x.timestamp - bridge_event.timestamp))
        if abs(candidates[0].timestamp - bridge_event.timestamp) == abs(candidates[1].timestamp - bridge_event.timestamp):  # noqa: E501
            return candidates  # no unique closest candidate

        candidates = candidates[:1]

    return candidates


def find_bridge_transaction_matches(
        events_db: DBHistoryEvents,
        bridge_event: HistoryBaseEntry,
        cursor: DBCursor,
        assets_in_collection: tuple[Asset, ...],
        excluded_ids: set[int],
        tolerance: FVal,
        match_window: int,
        preloaded_possible_matches: list[HistoryBaseEntry] | None = None,
) -> list[HistoryBaseEntry]:
    """Find candidate counterpart events for the given bridge leg.

    A deposit anchor searches for destination-side candidates and a withdrawal
    anchor for source-side ones. Returns close matches (counterpart bridge
    legs) if any exist, otherwise plain receive/spend candidates, after
    tie-breaking heuristics.
    """
    if preloaded_possible_matches is None:
        from_ts_ms, to_ts_ms = get_bridge_leg_timestamp_range_ms(
            bridge_event=bridge_event,
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
            bridge_event=bridge_event,
            candidate=candidate,
            assets_in_collection=assets_in_collection,
            tolerance=tolerance,
            excluded_ids=excluded_ids,
        )
        if tier == 'close':
            close_matches.append(candidate)
        elif tier == 'other':
            other_matches.append(candidate)

    return _narrow_bridge_candidates(
        bridge_event=bridge_event,
        candidates=close_matches if len(close_matches) > 0 else other_matches,
    )


def get_bridge_leg_timestamp_range_ms(
        bridge_event: HistoryBaseEntry,
        match_window: int,
) -> tuple[TimestampMS, TimestampMS]:
    """The destination leg comes after the deposit, modulo a small clock tolerance,
    so a deposit anchor searches forward in time and a withdrawal anchor backward."""
    window_ms = ts_sec_to_ms(Timestamp(match_window))
    if _is_bridge_withdrawal(bridge_event):
        return (
            TimestampMS(bridge_event.timestamp - window_ms),
            TimestampMS(bridge_event.timestamp + TIMESTAMP_TOLERANCE_MS),
        )
    return (
        TimestampMS(bridge_event.timestamp - TIMESTAMP_TOLERANCE_MS),
        TimestampMS(bridge_event.timestamp + window_ms),
    )


def update_bridge_matched_event(
        events_db: DBHistoryEvents,
        bridge_event: HistoryBaseEntry,
        matched_event: HistoryBaseEntry,
) -> None:
    """Persist a confirmed bridge match between the given bridge leg and its counterpart.

    When the counterpart is not already decoded as the opposite bridge leg it is
    rewritten into one: a deposit anchor turns its match (a plain receive) into
    the destination withdrawal and a withdrawal anchor turns its match (a plain
    spend) into the source deposit. Both events get stamped with the
    matched_bridge metadata (including the implied bridge fee) and linked in the
    DB. A fee is inferred only when both legs use economically equivalent assets.
    Both edits keep backups so unlinking can restore them.
    """
    if is_zksync_lite_exit(bridge_event):  # promote it now that its payout is known
        bridge_event.amount = matched_event.amount
        bridge_event.event_type = HistoryEventType.DEPOSIT
        bridge_event.event_subtype = HistoryEventSubType.BRIDGE
        if isinstance(bridge_event, OnchainEvent):
            bridge_event.counterparty = CPT_ZKSYNC
        bridge_event.notes = (
            f'Bridge {bridge_event.amount} '
            f'{bridge_event.asset.resolve_to_asset_with_symbol().symbol} '
            f'from ZKSync Lite to Ethereum'
        )
        bridge_event.extra_data = (bridge_event.extra_data or {}) | {BRIDGE_EXTRA_DATA_KEY: {
            'from_chain': SupportedBlockchain.ZKSYNC_LITE.serialize(),
            'to_chain': ChainID.ETHEREUM.serialize(),
            'to_address': bridge_event.location_label,
        }}

    anchor_counterparty = getattr(bridge_event, 'counterparty', None)
    anchor_is_withdrawal = _is_bridge_withdrawal(bridge_event)
    expected_type = (
        HistoryEventType.DEPOSIT if anchor_is_withdrawal else HistoryEventType.WITHDRAWAL
    )
    if not (
        matched_event.event_type == expected_type and
        matched_event.event_subtype == HistoryEventSubType.BRIDGE
    ):
        matched_event.event_type = expected_type
        matched_event.event_subtype = HistoryEventSubType.BRIDGE
        if isinstance(matched_event, OnchainEvent) and anchor_counterparty is not None:
            matched_event.counterparty = anchor_counterparty

        symbol = matched_event.asset.resolve_to_asset_with_symbol().symbol
        if anchor_is_withdrawal:
            matched_event.notes = (
                f'Send {matched_event.amount} {symbol} '
                f'from {_location_chain_label(matched_event.location)} '
                f'bridged to {_location_chain_label(bridge_event.location)}'
            )
        else:
            matched_event.notes = (
                f'Receive {matched_event.amount} {symbol} '
                f'on {_location_chain_label(matched_event.location)} '
                f'bridged from {_location_chain_label(bridge_event.location)}'
            )

    deposit, withdrawal = (
        (matched_event, bridge_event) if anchor_is_withdrawal
        else (bridge_event, matched_event)
    )
    fee_amount = (
        deposit.amount - withdrawal.amount
        if withdrawal.asset in GlobalDBHandler.get_assets_in_same_collection(
            identifier=deposit.asset.identifier,
        )
        else None
    )
    for event, other in ((deposit, withdrawal), (withdrawal, deposit)):
        if event.extra_data is None:
            event.extra_data = {}
        matched_bridge_data = {
            'group_identifier': other.group_identifier,
            'location': other.location.serialize(),
        }
        if fee_amount is not None and fee_amount > 0:
            matched_bridge_data['fee_amount'] = str(fee_amount)
        event.extra_data[MATCHED_BRIDGE_KEY] = matched_bridge_data

    with events_db.db.conn.write_ctx() as write_cursor:
        for event in (deposit, withdrawal):
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
                withdrawal.identifier,
                HistoryEventLinkType.BRIDGE_MATCH.serialize_for_db(),
            ),
        )
        write_cursor.execute(  # the source leg is always the left side of the link
            'INSERT OR REPLACE INTO history_event_links('
            'left_event_id, right_event_id, link_type) VALUES(?, ?, ?)',
            (
                deposit.identifier,
                withdrawal.identifier,
                HistoryEventLinkType.BRIDGE_MATCH.serialize_for_db(),
            ),
        )

    if isinstance(deposit, EvmEvent):
        acknowledge_matched_l2_bridge_calendar_entry(
            database=events_db.db,
            bridge_event=deposit,
        )


def resolve_bridge_event_external(
        events_db: DBHistoryEvents,
        event: HistoryBaseEntry,
) -> bool:
    """Resolve an unmatched bridge leg as involving an external (untracked) counterpart.

    A deposit becomes a bridge spend (SPEND/BRIDGE, a payment to an untracked
    address) and a withdrawal becomes a bridge receive (RECEIVE/BRIDGE, income
    from an untracked source). The bridge subtype is kept so the event remains
    recognizable and filterable as a bridging event, while the spend/receive type
    makes the plain outgoing/incoming accounting treatment apply. The event keeps
    its bridge extra_data and is stamped with the external resolution and its
    original direction, and the edit saves a backup so unlinking restores the
    original bridge event. Returns False when the event is not a bridge leg.
    """
    if event.event_subtype != HistoryEventSubType.BRIDGE:
        return False

    symbol = event.asset.resolve_to_asset_with_symbol().symbol
    chain_label = _location_chain_label(event.location)
    if event.event_type == HistoryEventType.DEPOSIT:
        direction = 'deposit'
        event.event_type = HistoryEventType.SPEND
        event.notes = f'Send {event.amount} {symbol} from {chain_label} bridged to an external address'  # noqa: E501
    elif event.event_type == HistoryEventType.WITHDRAWAL:
        direction = 'withdrawal'
        event.event_type = HistoryEventType.RECEIVE
        event.notes = f'Receive {event.amount} {symbol} on {chain_label} bridged from an external address'  # noqa: E501
    else:
        return False

    if event.extra_data is None:
        event.extra_data = {}
    event.extra_data[MATCHED_BRIDGE_KEY] = {'resolution': 'external', 'direction': direction}
    with events_db.db.conn.write_ctx() as write_cursor:
        events_db.edit_history_event(
            write_cursor=write_cursor,
            event=event,
            mapping_state=HistoryMappingState.MATCHED,
            save_backup=True,
        )
        write_cursor.execute(
            'INSERT OR IGNORE INTO history_event_link_ignores(event_id, link_type) '
            'VALUES(?, ?)',
            (event.identifier, HistoryEventLinkType.BRIDGE_MATCH.serialize_for_db()),
        )

    return True


def _bridge_counterpart_location(bridge_event: HistoryBaseEntry) -> Location | None:
    """Derive the chain of the missing counterpart leg from the event's bridge data.

    Returns None when the bridge data has no chain entry or the chain does not
    correspond to a location rotki knows.
    """
    chain_value = get_event_bridge_data(bridge_event).get(
        'from_chain' if _is_bridge_withdrawal(bridge_event) else 'to_chain',
    )
    if isinstance(chain_value, int):
        try:
            chain_id = ChainID(chain_value)
        except ValueError:
            return None
        if chain_id not in EVM_CHAIN_IDS_WITH_TRANSACTIONS:
            return None  # from_chain_id silently falls back to polygon for other chains

        return Location.from_chain_id(chain_id)

    if isinstance(chain_value, str):
        try:
            return Location.deserialize(chain_value)
        except DeserializationError:
            return None

    return None


def create_bridge_counterpart_event(
        events_db: DBHistoryEvents,
        bridge_event: HistoryBaseEntry,
) -> HistoryBaseEntry:
    """Create a synthetic counterpart leg for a bridge event whose real counterpart
    cannot exist in the DB (e.g. a chain whose API has shut down) and link the two.

    The counterpart is a plain history event on the other chain mirroring the leg:
    same asset, amount and timestamp, opposite bridge direction. It is marked with
    the SYNTHETIC mapping state so it is clearly shown as an event manufactured by
    rotki rather than pulled from a chain, and linked to the leg like any other
    bridge match. Returns the created event.

    Idempotent under redecoding: when the anchor is deleted and re-decoded (single
    transaction redecode and the DB upgrade decoded-events reset preserve only
    customized events) the link dies with it while the synthetic counterpart
    survives as an orphan. Re-synthesis then reuses that orphan — refreshing its
    mirrored fields — instead of colliding with it.

    May raise:
        - InputError if the event is not a bridge leg, is already matched, its bridge
          data contains no usable counterpart chain, or the counterpart slot is
          occupied by an event that is not a synthetic counterpart.
    """
    if not (
        bridge_event.event_subtype == HistoryEventSubType.BRIDGE and
        bridge_event.event_type in (HistoryEventType.DEPOSIT, HistoryEventType.WITHDRAWAL)
    ):
        raise InputError(
            f'Event with identifier {bridge_event.identifier} is not a bridge deposit or withdrawal',  # noqa: E501
        )

    with events_db.db.conn.read_ctx() as cursor:
        if cursor.execute(
            'SELECT COUNT(*) FROM history_event_links WHERE link_type=? AND '
            '(left_event_id=? OR right_event_id=?)',
            (
                HistoryEventLinkType.BRIDGE_MATCH.serialize_for_db(),
                bridge_event.identifier,
                bridge_event.identifier,
            ),
        ).fetchone()[0] != 0:
            raise InputError(
                f'Event with identifier {bridge_event.identifier} is already matched '
                'to a counterpart event',
            )

    if (location := _bridge_counterpart_location(bridge_event)) is None:
        raise InputError(
            f'The bridge data of event with identifier {bridge_event.identifier} does not '
            'contain a known counterpart chain to create the counterpart event on',
        )

    bridge_data = get_event_bridge_data(bridge_event)
    symbol = bridge_event.asset.resolve_to_asset_with_symbol().symbol
    if _is_bridge_withdrawal(bridge_event):
        event_type = HistoryEventType.DEPOSIT
        location_label = bridge_data.get('from_address', bridge_event.location_label)
        notes = (
            f'Send {bridge_event.amount} {symbol} from {_location_chain_label(location)} '
            f'bridged to {_location_chain_label(bridge_event.location)}'
        )
    else:
        event_type = HistoryEventType.WITHDRAWAL
        location_label = bridge_data.get('to_address', bridge_event.location_label)
        notes = (
            f'Receive {bridge_event.amount} {symbol} on {_location_chain_label(location)} '
            f'bridged from {_location_chain_label(bridge_event.location)}'
        )

    counterpart = HistoryEvent(
        group_identifier=f'{SYNTHETIC_BRIDGE_GROUP_PREFIX}{bridge_event.group_identifier}',
        sequence_index=bridge_event.sequence_index,
        timestamp=bridge_event.timestamp,
        location=location,
        event_type=event_type,
        event_subtype=HistoryEventSubType.BRIDGE,
        asset=bridge_event.asset,
        amount=bridge_event.amount,
        location_label=location_label,
        notes=notes,
        extra_data={BRIDGE_EXTRA_DATA_KEY: dict(bridge_data)} if len(bridge_data) != 0 else None,
    )
    with events_db.db.conn.write_ctx() as write_cursor:
        identifier = events_db.add_history_event(
            write_cursor=write_cursor,
            event=counterpart,
            mapping_values={HISTORY_MAPPING_KEY_STATE: HistoryMappingState.SYNTHETIC},
        )
        if identifier is None:  # reuse an orphaned counterpart from a previous synthesis
            existing = write_cursor.execute(
                'SELECT identifier FROM history_events WHERE group_identifier=? AND '
                'sequence_index=? AND identifier IN (SELECT parent_identifier FROM '
                'history_events_mappings WHERE name=? AND value=?)',
                (
                    counterpart.group_identifier,
                    counterpart.sequence_index,
                    HISTORY_MAPPING_KEY_STATE,
                    HistoryMappingState.SYNTHETIC.serialize_for_db(),
                ),
            ).fetchone()
            if existing is None:
                raise InputError(
                    f'A non-synthetic event already occupies the counterpart slot of '
                    f'bridge event with group identifier {bridge_event.group_identifier}',
                )

            identifier = existing[0]
            counterpart.identifier = identifier
            events_db.edit_history_event(  # refresh the mirrored fields from the anchor
                write_cursor=write_cursor,
                event=counterpart,
                mapping_state=HistoryMappingState.SYNTHETIC,
            )

    counterpart.identifier = identifier
    update_bridge_matched_event(
        events_db=events_db,
        bridge_event=bridge_event,
        matched_event=counterpart,
    )
    return counterpart


def _is_zksync_lite_sunset_claim(event: HistoryBaseEntry) -> bool:
    """Check whether the event is a decoded ZKsync Lite sunset claim leg.

    Such a leg can never find a counterpart: the claim exists only on Ethereum and
    the zksync lite API is shut down, so no L2 exit event can ever be pulled."""
    return (
        _is_bridge_withdrawal(event) and
        getattr(event, 'counterparty', None) == CPT_ZKSYNC and
        getattr(event, 'address', None) == ZKSYNC_LITE_SUNSET_CLAIM
    )


def _should_auto_ignore_external(deposit: HistoryBaseEntry) -> bool:
    """Bridges to chains rotki cannot query will never find a destination leg.

    Such deposits are only removed from the unmatched pool (ignored); the event
    itself is deliberately not rewritten -- resolving a leg as external changes
    its accounting treatment, so that rewrite stays an explicit user action.
    """
    to_chain = get_event_bridge_data(deposit).get('to_chain')
    if isinstance(to_chain, int):
        return to_chain not in {chain_id.value for chain_id in EVM_CHAIN_IDS_WITH_TRANSACTIONS}
    # str chains (zksync lite) stay unmatched: their history may have been pulled before
    # the API shut down, and legs without a counterpart can be resolved manually (e.g.
    # by creating a synthetic counterpart event).
    return False


def get_bridge_match_assets_in_collection(
        deposit: HistoryBaseEntry,
        cache: dict[str, tuple[Asset, ...]] | None = None,
) -> tuple[Asset, ...]:
    """Get candidate assets, preferring the recorded destination asset when available."""
    identifier = (
        target_asset.identifier
        if (target_asset := _get_bridge_target_asset(deposit)) is not None
        else deposit.asset.identifier
    )
    if cache is None:
        return GlobalDBHandler.get_assets_in_same_collection(identifier=identifier)
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

    remaining_withdrawals = []
    for withdrawal in withdrawals:  # sunset claims get their L2 exit leg synthesized
        if not _is_zksync_lite_sunset_claim(withdrawal):
            remaining_withdrawals.append(withdrawal)
            continue

        try:
            create_bridge_counterpart_event(events_db=events_db, bridge_event=withdrawal)
        except InputError as e:
            log.error(
                'Failed to synthesize the zksync lite counterpart of sunset claim %s due to %s',
                withdrawal.group_identifier,
                e,
            )
            remaining_withdrawals.append(withdrawal)
    withdrawals = remaining_withdrawals

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
            withdrawals_by_transfer_id: dict[str, list[HistoryBaseEntry]] = defaultdict(list)
            for withdrawal in withdrawals:
                if (transfer_id := get_event_bridge_data(withdrawal).get('transfer_id')) is not None:  # noqa: E501
                    withdrawals_by_transfer_id[transfer_id].append(withdrawal)

            pending_deposits = []
            for deposit in deposits:
                if (transfer_id := get_event_bridge_data(deposit).get('transfer_id')) is not None and len(candidates := [  # noqa: E501
                    withdrawal for withdrawal in withdrawals_by_transfer_id[transfer_id]
                    if (
                        not _is_socket_bridge_pair(deposit, withdrawal) and
                        withdrawal.identifier not in excluded_ids and
                        withdrawal.location != deposit.location and
                        _bridge_counterparties_match(
                            first_counterparty=getattr(deposit, 'counterparty', None),
                            second_counterparty=getattr(withdrawal, 'counterparty', None),
                        ) and
                        not _events_conflict_on_bridge_data(
                            deposit=deposit,
                            candidate=withdrawal,
                        )
                    )
                ]) == 1:
                    matched_pairs.append((deposit, matched_event := candidates[0]))
                    excluded_ids.update((deposit.identifier, matched_event.identifier))  # type: ignore[arg-type]  # events from the db have identifiers
                    continue

                if _should_auto_ignore_external(deposit=deposit):
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
                        bridge_event=deposit,
                        cursor=cursor,
                        assets_in_collection=get_bridge_match_assets_in_collection(
                            deposit=deposit,
                            cache=assets_in_collection_cache,
                        ),
                        excluded_ids=excluded_ids,
                        tolerance=settings.bridge_match_amount_tolerance,
                        match_window=get_bridge_match_window(
                            event=deposit,
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
                bridge_event=deposit,
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
