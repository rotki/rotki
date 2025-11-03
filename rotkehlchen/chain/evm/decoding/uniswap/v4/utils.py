import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from rotkehlchen.chain.decoding.types import get_versioned_counterparty_label
from rotkehlchen.chain.ethereum.utils import asset_normalized_value, asset_raw_value
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.uniswap.utils import get_uniswap_swap_amounts
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.errors.asset import WrongAssetType
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.history.events.structures.evm_event import EvmEvent

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def decode_uniswap_v4_like_swaps(
        transaction: 'EvmTransaction',
        decoded_events: list['EvmEvent'],
        all_logs: list['EvmTxReceiptLog'],
        base_tools: 'BaseEvmDecoderTools',
        swap_topics: tuple[bytes, ...],
        counterparty: str,
        router_address: ChecksumEvmAddress,
) -> list['EvmEvent']:
    """Decode Uniswap V4 like swaps."""
    amounts_received, amounts_sent, pools_used, possible_fees = set(), set(), set(), defaultdict(set)  # noqa: E501
    # Since tokens may be swapped multiple times before reaching the desired token, we must
    # check the amounts from multiple swap logs if present.
    for tx_log in all_logs:
        if tx_log.topics[0] in swap_topics:
            amount_received, amount_sent = get_uniswap_swap_amounts(tx_log=tx_log)
            amounts_received.add(amount_received)
            amounts_sent.add(amount_sent)
            pools_used.add(tx_log.address)
        elif (
            tx_log.topics[0] == ERC20_OR_ERC721_TRANSFER and
            ((from_addr := bytes_to_address(tx_log.topics[1])) == router_address or
            from_addr in pools_used) and
            not base_tools.is_tracked(bytes_to_address(tx_log.topics[2]))
        ):
            possible_fees[tx_log.address].add(int.from_bytes(tx_log.data[:32]))

    if len(internal_txs := DBEvmTx(base_tools.database).get_evm_internal_transactions(
        parent_tx_hash=transaction.tx_hash,
        blockchain=base_tools.evm_inquirer.blockchain,
    )) != 0:  # check internal txs for possible fees and use the wrapped native token to represent it.  # noqa: E501
        for internal_tx in internal_txs:
            if (
                    (internal_tx.to_address is not None and not base_tools.is_tracked(internal_tx.to_address)) and  # noqa: E501
                    internal_tx.from_address == router_address
            ):
                possible_fees[base_tools.evm_inquirer.wrapped_native_token.evm_address].add(internal_tx.value)

    if len(amounts_received) == 0:
        log.error(f'Could not find swap log in {transaction}')
        return decoded_events

    spend_event, receive_event, fee_event = None, None, None
    display_name = get_versioned_counterparty_label(counterparty)
    for event in decoded_events:
        if not (event.address == router_address or event.address in pools_used):
            continue

        if (
            ((
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE
            ) or (
                event.event_type == HistoryEventType.TRADE and
                event.event_subtype == HistoryEventSubType.SPEND
            )) and
            asset_raw_value(
                amount=event.amount,
                asset=(resolved_asset := event.asset.resolve_to_crypto_asset()),
            ) in amounts_sent
        ):
            event.counterparty = counterparty
            event.event_type = HistoryEventType.TRADE
            event.event_subtype = HistoryEventSubType.SPEND
            event.notes = f'Swap {event.amount} {resolved_asset.symbol} in {display_name}'
            spend_event = event
        elif ((
            event.event_type == HistoryEventType.RECEIVE and
            event.event_subtype == HistoryEventSubType.NONE
        ) or (
            event.event_type == HistoryEventType.TRADE and
            event.event_subtype == HistoryEventSubType.RECEIVE
        )):
            if (event_raw_amount := asset_raw_value(
                amount=event.amount,
                asset=(resolved_asset := event.asset.resolve_to_crypto_asset()),
            )) not in amounts_received:
                # In some cases a fee is deducted from the receive amount before it is sent to
                # the user. Check if this receive event actually has the right amount to match
                # this swap after adding the fee back on.
                try:  # First, get the received token's address
                    fee_token = (  # Fee will be in the wrapped version of the native currency.
                        event.asset.resolve_to_evm_token()
                        if event.asset != base_tools.evm_inquirer.native_token
                        else base_tools.evm_inquirer.wrapped_native_token
                    )
                except WrongAssetType:
                    log.error(
                        f'{display_name} swap receive asset {event.asset} is not the native '
                        f'currency or an EVM token in {transaction}. Should not happen.')
                    continue

                # Match against the amounts for possible fee transfers of this token
                if (raw_fee_amount := next((
                    amount for amount in possible_fees[fee_token.evm_address]
                    if event_raw_amount + amount in amounts_received
                ), None)) is None:
                    continue  # this receive is not related to this swap

                event.amount += (fee_amount := asset_normalized_value(
                    asset=resolved_asset,
                    amount=raw_fee_amount,
                ))
                fee_event = base_tools.make_event_next_index(
                    tx_ref=event.tx_ref,
                    timestamp=transaction.timestamp,
                    event_type=HistoryEventType.TRADE,
                    event_subtype=HistoryEventSubType.FEE,
                    asset=resolved_asset,
                    amount=fee_amount,
                    location_label=event.location_label,
                    notes=f'Spend {fee_amount} {resolved_asset.symbol} as a {display_name} fee',
                    counterparty=counterparty,
                    address=event.address,
                )

            event.counterparty = counterparty
            event.event_type = HistoryEventType.TRADE
            event.event_subtype = HistoryEventSubType.RECEIVE
            event.notes = f'Receive {event.amount} {resolved_asset.symbol} after a swap in {display_name}'  # noqa: E501
            receive_event = event

    if spend_event is None or receive_event is None:
        log.error(f'Failed to find both out and in events for {display_name} swap {transaction}')
        return decoded_events

    ordered_events = [spend_event, receive_event]
    if fee_event is not None:
        decoded_events.append(fee_event)
        ordered_events.append(fee_event)

    maybe_reshuffle_events(ordered_events=ordered_events, events_list=decoded_events)
    return decoded_events
