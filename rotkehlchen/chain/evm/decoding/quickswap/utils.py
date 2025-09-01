from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.quickswap.constants import UNISWAP_QUICKSWAP_COUNTERPARTY_MAP
from rotkehlchen.chain.evm.decoding.types import get_versioned_counterparty_label
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.history.events.structures.evm_event import EvmEvent


def decode_quickswap_swap(
        tx_log: 'EvmTxReceiptLog',
        decoded_events: list['EvmEvent'],
) -> list['EvmEvent']:
    """Quickswap swaps are already decoded by the uniswap decoders since they use the same swap
    tx_log signature. Finds the decoded uniswap events and updates the counterparty and notes.
    """
    for event in decoded_events:
        if not (
                event.event_type == HistoryEventType.TRADE and
                event.address == tx_log.address and
                event.counterparty in UNISWAP_QUICKSWAP_COUNTERPARTY_MAP
        ):
            continue

        event.counterparty = UNISWAP_QUICKSWAP_COUNTERPARTY_MAP[event.counterparty]
        display_name = get_versioned_counterparty_label(event.counterparty)
        if event.event_subtype == HistoryEventSubType.SPEND:
            event.notes = f'Swap {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} in {display_name}'  # noqa: E501
        else:  # receive
            event.notes = f'Receive {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} as the result of a swap in {display_name}'  # noqa: E501

    return decoded_events
