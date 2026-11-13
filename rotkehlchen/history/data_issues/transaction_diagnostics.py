"""Read-only diagnosis of one transaction and of one bridge leg's matching.

inspect_transaction compares what the decoders made of a transaction (its saved events and
their bucket effects) with what its saved receipt shows moved (ERC20 transfer logs, the
native value and internal transactions). explain_bridge_match runs the bridge matcher's own
candidate classification and reports why each candidate was accepted or rejected.

Both only read the database: receipts and internal transactions come from what was saved
when the transaction was pulled, and are reported as missing rather than queried.
"""
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ZERO
from rotkehlchen.db.constants import HistoryEventLinkType, HistoryMappingState
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import (
    AssetMovementMatchFilterQuery,
    EvmTransactionsFilterQuery,
    HistoryEventFilterQuery,
)
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.data_issues.diagnostics import (
    get_group_events,
    get_mapping_states,
    get_processing_state,
    serialize_bucket,
    serialize_effects,
    serialize_event_summary,
)
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import (
    EventDirection,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.locations.chains import EVM_LOCATIONS, location_to_chain
from rotkehlchen.tasks.bridges import (
    ENTRY_TYPES_TO_EXCLUDE_FROM_BRIDGE_MATCHING,
    classify_bridge_candidate,
    find_bridge_transaction_exact_matches,
    get_bridge_leg_timestamp_range_ms,
    get_bridge_match_assets_in_collection,
    get_bridge_match_window,
    get_event_bridge_data,
    is_zksync_lite_exit,
)
from rotkehlchen.tasks.events import get_already_matched_event_ids
from rotkehlchen.tasks.historical_balances import Bucket
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry
    from rotkehlchen.types import ChainID, ChecksumEvmAddress, EvmTransaction

MAX_LISTED_CANDIDATES: Final = 50
# Candidates up to this many match windows away are listed as outside the window, so a leg
# that settled late is told apart from one that never arrived.
NEAR_MISS_WINDOW_FACTOR: Final = 3
BRIDGE_METADATA_KEYS: Final = ('transfer_id', 'from_chain', 'to_chain', 'to_address', 'to_asset')

type AccountAsset = tuple[str, str]


def _token_amount(chain_id: ChainID, token_address: ChecksumEvmAddress, raw: int) -> tuple[str, FVal | None]:  # noqa: E501
    """The asset identifier and decimal amount of a token transfer, amount None if unknown."""
    if (token := GlobalDBHandler.get_evm_token(address=token_address, chain_id=chain_id)) is None:
        return f'eip155:{chain_id.serialize()}/erc20:{token_address}', None
    if token.decimals is None:
        return token.identifier, None
    return token.identifier, FVal(raw) / FVal(10 ** token.decimals)


def _receipt_transfers(
        database: DBHandler,
        transaction: EvmTransaction,
        tracked: set[ChecksumEvmAddress],
) -> tuple[dict[AccountAsset, FVal], list[dict[str, Any]], list[str]]:
    """Net movement per (tracked account, asset) that the saved receipt shows, the token
    transfers that could not be valued, and caveats about what the receipt can't show."""
    caveats: list[str] = []
    net: dict[AccountAsset, FVal] = defaultdict(lambda: ZERO)
    unvalued: list[dict[str, Any]] = []
    chain_id = transaction.chain_id
    dbevmtx = DBEvmTx(database)
    with database.conn.read_ctx() as cursor:
        receipt = dbevmtx.get_receipt(
            cursor=cursor,
            tx_hash=transaction.tx_hash,
            chain_id=chain_id,
        )
    internal_txs = dbevmtx.get_evm_internal_transactions(
        parent_tx_hash=transaction.tx_hash,
        blockchain=chain_id.to_blockchain(),
        parent_tx_id=transaction.db_id,
    )
    native = chain_id.to_blockchain().get_native_token_id()
    if receipt is None:
        caveats.append('receipt_missing')
        return net, unvalued, caveats

    if receipt.status is False:
        caveats.append('transaction_reverted')
    else:
        transfers = [(transaction.from_address, transaction.to_address, transaction.value)]
        transfers.extend((tx.from_address, tx.to_address, tx.value) for tx in internal_txs)
        for from_address, to_address, value in transfers:
            if value == 0:
                continue
            amount = FVal(value) / FVal(10 ** 18)
            if from_address in tracked:
                net[from_address, native] -= amount
            if to_address is not None and to_address in tracked:
                net[to_address, native] += amount

        for log in receipt.logs:
            if len(log.topics) != 3 or log.topics[0] != ERC20_OR_ERC721_TRANSFER:
                continue  # four topics is an ERC721 transfer, not a fungible amount
            from_address = bytes_to_address(log.topics[1])
            to_address = bytes_to_address(log.topics[2])
            if from_address not in tracked and to_address not in tracked:
                continue
            asset_identifier, token_amount = _token_amount(
                chain_id=chain_id,
                token_address=log.address,
                raw=int.from_bytes(log.data[:32]) if len(log.data) >= 32 else 0,
            )
            if token_amount is None:
                unvalued.append({'asset': asset_identifier, 'log_index': log.log_index})
                continue
            if from_address in tracked:
                net[from_address, asset_identifier] -= token_amount
            if to_address in tracked:
                net[to_address, asset_identifier] += token_amount

    if transaction.from_address in tracked:
        caveats.append('gas_fee_excluded_from_comparison')
    if len(internal_txs) == 0 and transaction.to_address is not None:
        caveats.append('internal_transactions_may_be_missing')
    return net, unvalued, caveats


def _bucket_asset(identifier: str, treat_eth2_as_eth: bool) -> str:
    """The asset a wallet bucket files the identifier under, itself if it is unknown."""
    try:
        asset = Asset(identifier).resolve_swapped_for()
    except (UnknownAsset, WrongAssetType):
        return identifier
    if treat_eth2_as_eth and asset.identifier == 'ETH2':
        return 'ETH'
    return asset.identifier


def _decoded_wallet_effects(
        events: list[HistoryBaseEntry],
        treat_eth2_as_eth: bool,
) -> dict[AccountAsset, FVal]:
    """Net wallet effect per (account, asset) of the decoded events, gas fees excluded."""
    net: dict[AccountAsset, FVal] = defaultdict(lambda: ZERO)
    for event in events:
        if event.event_subtype == HistoryEventSubType.FEE and event.event_type == HistoryEventType.SPEND:  # noqa: E501
            continue
        for bucket, direction in Bucket.from_event(event, treat_eth2_as_eth=treat_eth2_as_eth):
            if bucket.protocol is not None or bucket.location_label is None:
                continue
            net[bucket.location_label, bucket.asset] += (
                event.amount if direction == EventDirection.IN else -event.amount
            )
    return net


def inspect_transaction(database: DBHandler, group_identifier: str) -> dict[str, Any] | None:
    """The full event group with customization state, bucket effects and receipt evidence.

    Returns None when there is no such group. The receipt comparison is only made for EVM
    transactions; for other locations the decoded effects are all the evidence there is.
    """
    if len(events := get_group_events(database, group_identifier)) == 0:
        return None

    treat_eth2_as_eth = CachedSettings().get_entry('treat_eth2_as_eth') is True
    with database.conn.read_ctx() as cursor:
        mapping_states = get_mapping_states(cursor=cursor, events=events)
        processing_state = get_processing_state(cursor=cursor, database=database)

    serialized_events = []
    net_by_bucket: dict[Bucket, FVal] = defaultdict(lambda: ZERO)
    for event in events:
        effects = serialize_effects(event=event, treat_eth2_as_eth=treat_eth2_as_eth)
        serialized_events.append(serialize_event_summary(
            event=event,
            mapping_states=mapping_states.get(event.identifier or -1, ()),
        ) | effects | ({
            'bridge_metadata_present': sorted(bridge_data.keys()),
        } if len(bridge_data := get_event_bridge_data(event)) != 0 else {}))
        for bucket, direction in Bucket.from_event(event, treat_eth2_as_eth=treat_eth2_as_eth):
            net_by_bucket[bucket] += event.amount if direction == EventDirection.IN else -event.amount  # noqa: E501

    customized = any(HistoryMappingState.CUSTOMIZED in x for x in mapping_states.values())
    result: dict[str, Any] = {
        'group_identifier': group_identifier,
        'location': events[0].location,
        'processing': processing_state,
        'customized': customized,
        'events': serialized_events,
        'net_effects': [
            {'bucket': serialize_bucket(bucket), 'net_amount': str(amount)}
            for bucket, amount in net_by_bucket.items()
        ],
        'receipt_comparison': None,
    }
    if not isinstance(first := events[0], EvmEvent) or first.location not in EVM_LOCATIONS:
        return result

    chain_id = location_to_chain(first.location).to_chain_id()
    dbevmtx = DBEvmTx(database)
    with database.conn.read_ctx() as cursor:
        transactions = dbevmtx.get_transactions(
            cursor=cursor,
            filter_=EvmTransactionsFilterQuery.make(tx_hash=first.tx_ref, chain_id=chain_id),
        )
        tracked = {  # evm accounts are saved checksummed
            string_to_evm_address(address)
            for address in database.get_blockchain_accounts(cursor).get(
                location_to_chain(first.location),
            )
        }
    if len(transactions) != 1:
        result['receipt_comparison'] = {'available': False, 'caveats': ['transaction_missing']}
        return result

    observed_raw, unvalued, caveats = _receipt_transfers(
        database=database,
        transaction=transactions[0],
        tracked=tracked,
    )
    observed: dict[AccountAsset, FVal] = defaultdict(lambda: ZERO)
    for (account, asset), amount in observed_raw.items():  # match the bucket asset identity
        observed[account, _bucket_asset(asset, treat_eth2_as_eth)] += amount
    decoded = _decoded_wallet_effects(events=events, treat_eth2_as_eth=treat_eth2_as_eth)
    discrepancies = []
    for key in sorted({*observed, *decoded}):
        account, asset = key
        if (observed_amount := observed.get(key, ZERO)) != (decoded_amount := decoded.get(key, ZERO)):  # noqa: E501
            discrepancies.append({
                'account': account,
                'asset': asset,
                'observed_net': str(observed_amount),
                'decoded_net': str(decoded_amount),
                'difference': str(observed_amount - decoded_amount),
            })

    result['receipt_comparison'] = {
        'available': 'receipt_missing' not in caveats,
        'observed_net_by_account_asset': [
            {'account': account, 'asset': asset, 'net_amount': str(amount)}
            for (account, asset), amount in sorted(observed.items())
        ],
        'unvalued_token_transfers': unvalued,
        'discrepancies': discrepancies,
        'caveats': caveats,
        'interpretation': 'Discrepancies are evidence, not conclusions: wrapping, rebasing, '
                          'fee-on-transfer and spam tokens legitimately differ from the raw '
                          'transfers',
    }
    return result


def _link_state(database: DBHandler, event_identifier: int) -> dict[str, Any]:
    link_type = HistoryEventLinkType.BRIDGE_MATCH.serialize_for_db()
    with database.conn.read_ctx() as cursor:
        linked = cursor.execute(
            'SELECT left_event_id, right_event_id FROM history_event_links '
            'WHERE link_type = ? AND (left_event_id = ? OR right_event_id = ?)',
            (link_type, event_identifier, event_identifier),
        ).fetchone()
        ignored = cursor.execute(
            'SELECT 1 FROM history_event_link_ignores WHERE event_id = ? AND link_type = ?',
            (event_identifier, link_type),
        ).fetchone() is not None
    return {
        'linked_to_event_identifier': None if linked is None else (
            linked[1] if linked[0] == event_identifier else linked[0]
        ),
        'ignored': ignored,
    }


def _serialize_candidate(
        bridge_event: HistoryBaseEntry,
        candidate: HistoryBaseEntry,
        tier: str | None,
        rejection: str | None,
) -> dict[str, Any]:
    return {
        'event_identifier': candidate.identifier,
        'group_identifier': candidate.group_identifier,
        'location': candidate.location,
        'location_label': candidate.location_label,
        'event_type': candidate.event_type.serialize(),
        'event_subtype': candidate.event_subtype.serialize(),
        'asset': candidate.asset.identifier,
        'amount': str(candidate.amount),
        'amount_difference': str(candidate.amount - bridge_event.amount),
        'counterparty': getattr(candidate, 'counterparty', None),
        'timestamp_ms': candidate.timestamp,
        'seconds_from_anchor': (candidate.timestamp - bridge_event.timestamp) // 1000,
        'tier': tier,
        'rejection': rejection,
    }


def explain_bridge_match(database: DBHandler, event_identifier: int) -> dict[str, Any] | None:
    """Every candidate counterpart of a bridge leg, and why each was or wasn't eligible.

    ``conclusion`` distinguishes a leg that is already linked or ignored, one with a unique
    eligible candidate (which the automatic matcher would link), an ambiguous one and one with
    zero eligible candidates. Zero eligible candidates is not evidence that no counterpart
    exists: the counterpart may be on an untracked account, undecoded, or outside the window.

    Returns None when the event does not exist or is not a bridge leg.
    """
    events_db = DBHistoryEvents(database)
    with database.conn.read_ctx() as cursor:
        found = events_db.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(identifiers=[event_identifier]),
        )
    if len(found) != 1 or not (
        (found[0].event_type, found[0].event_subtype) in (
            (HistoryEventType.DEPOSIT, HistoryEventSubType.BRIDGE),
            (HistoryEventType.WITHDRAWAL, HistoryEventSubType.BRIDGE),
        ) or is_zksync_lite_exit(found[0])
    ):
        return None

    bridge_event = found[0]
    settings = CachedSettings().get_settings()
    is_withdrawal = bridge_event.event_type == HistoryEventType.WITHDRAWAL
    window = settings.bridge_match_time_range if is_withdrawal else get_bridge_match_window(
        event=bridge_event,
        default_window=settings.bridge_match_time_range,
    )
    assets_in_collection = get_bridge_match_assets_in_collection(deposit=bridge_event)
    link_state = _link_state(database, event_identifier)
    with database.conn.read_ctx() as cursor:
        excluded_ids = get_already_matched_event_ids(
            cursor=cursor,
            link_type=HistoryEventLinkType.BRIDGE_MATCH,
        )
        excluded_ids.discard(event_identifier)
        exact = find_bridge_transaction_exact_matches(
            events_db=events_db,
            bridge_event=bridge_event,
            cursor=cursor,
            excluded_ids=excluded_ids,
        )
        in_from, in_to = get_bridge_leg_timestamp_range_ms(
            bridge_event=bridge_event,
            match_window=window,
        )
        near_from, near_to = get_bridge_leg_timestamp_range_ms(
            bridge_event=bridge_event,
            match_window=window * NEAR_MISS_WINDOW_FACTOR,
        )
        pool = events_db.get_history_events_internal(
            cursor=cursor,
            filter_query=AssetMovementMatchFilterQuery.make(
                asset_timestamp_ranges=[(assets_in_collection, near_from, near_to)],
                entry_types_to_exclude=ENTRY_TYPES_TO_EXCLUDE_FROM_BRIDGE_MATCHING,
            ),
        )

    candidates: list[dict[str, Any]] = []
    rejection_counts: defaultdict[str, int] = defaultdict(int)
    eligible: list[HistoryBaseEntry] = []
    for candidate in pool:
        if candidate.identifier == event_identifier:
            continue
        tier, rejection = classify_bridge_candidate(
            bridge_event=bridge_event,
            candidate=candidate,
            assets_in_collection=assets_in_collection,
            tolerance=settings.bridge_match_amount_tolerance,
            excluded_ids=excluded_ids,
        )
        in_window = in_from <= candidate.timestamp <= in_to
        reason = rejection.value if rejection is not None else (
            None if in_window else 'outside_time_window'
        )
        if reason is not None:
            rejection_counts[reason] += 1
        elif tier is not None:
            eligible.append(candidate)
        candidates.append(_serialize_candidate(
            bridge_event=bridge_event,
            candidate=candidate,
            tier=tier if reason is None else None,
            rejection=reason,
        ) | {'within_window': in_window})

    close = [x for x in eligible if classify_bridge_candidate(
        bridge_event, x, assets_in_collection, settings.bridge_match_amount_tolerance, excluded_ids,  # noqa: E501
    )[0] == 'close']
    if link_state['linked_to_event_identifier'] is not None:
        conclusion = 'already_linked'
    elif link_state['ignored']:
        conclusion = 'ignored'
    elif len(exact) == 1 or len(close or eligible) == 1:
        conclusion = 'unique_eligible_candidate'
    elif len(eligible) > 1:
        conclusion = 'ambiguous'
    else:
        conclusion = 'zero_eligible_candidates'

    bridge_data = get_event_bridge_data(bridge_event)
    candidates.sort(key=lambda x: (x['rejection'] is not None, abs(x['seconds_from_anchor'])))
    with database.conn.read_ctx() as cursor:
        processing_state = get_processing_state(cursor=cursor, database=database)
    return {
        'bridge_event': serialize_event_summary(bridge_event),
        'direction': 'withdrawal' if is_withdrawal else 'deposit',
        'processing': processing_state,
        'link_state': link_state,
        'conclusion': conclusion,
        'search': {
            'window_s': window,
            'searched_from_ts_ms': near_from,
            'searched_to_ts_ms': near_to,
            'window_from_ts_ms': in_from,
            'window_to_ts_ms': in_to,
            'amount_tolerance': str(settings.bridge_match_amount_tolerance),
            'assets_considered': [asset.identifier for asset in assets_in_collection],
        },
        'missing_metadata': [key for key in BRIDGE_METADATA_KEYS if key not in bridge_data] + (
            ['counterparty'] if getattr(bridge_event, 'counterparty', None) is None else []
        ),
        'exact_transfer_id_matches': [x.identifier for x in exact],
        'eligible_count': len(eligible),
        'rejection_counts': dict(sorted(rejection_counts.items())),
        'candidates': candidates[:MAX_LISTED_CANDIDATES],
        'candidates_truncated': len(candidates) > MAX_LISTED_CANDIDATES,
        'interpretation': (
            'Zero eligible candidates means none of the saved events qualifies, not that no '
            'counterpart exists: it may be on an untracked account, not yet pulled or '
            'decoded, or settled outside the searched range'
        ) if conclusion == 'zero_eligible_candidates' else None,
    }
