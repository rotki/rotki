import logging
from typing import TYPE_CHECKING

from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter

from .constants import CPT_ZAPPER, ZAPPER_CPT_DETAILS, ZAPPER_SWAP_CONTRACT

if TYPE_CHECKING:
    from collections.abc import Callable

    from rotkehlchen.chain.decoding.types import CounterpartyDetails
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class ZapperDecoder(EvmDecoderInterface):
    """Decoder for legacy Zapper.fi multi-exchange swaps.

    The swap contract pulls input assets from the user, routes intermediate swaps across
    underlying exchanges (Uniswap, Curve, Balancer, ...), and transfers the resulting assets
    back to the user without emitting its own swap event.
    """

    def _process_swap(
            self,
            transaction: EvmTransaction,
            decoded_events: list[EvmEvent],
            all_logs: list[EvmTxReceiptLog],
    ) -> list[EvmEvent]:
        out_events, in_events = [], []
        for event in decoded_events:
            if event.address != ZAPPER_SWAP_CONTRACT:
                continue

            if (
                (event.event_type == HistoryEventType.SPEND and event.event_subtype == HistoryEventSubType.NONE) or  # noqa: E501
                # Handle cases where an underlying DEX decoder already partially decoded the swap.
                (event.event_type == HistoryEventType.TRADE and event.event_subtype == HistoryEventSubType.SPEND)  # noqa: E501
            ):
                out_events.append(event)
            elif (
                (event.event_type == HistoryEventType.RECEIVE and event.event_subtype == HistoryEventSubType.NONE) or  # noqa: E501
                (event.event_type == HistoryEventType.TRADE and event.event_subtype == HistoryEventSubType.RECEIVE)  # noqa: E501
            ):
                in_events.append(event)

        if len(out_events) == 0 or len(in_events) == 0:
            log.debug(
                'Could not find both sides of the zapper swap',
                tx_hash=transaction.tx_hash.hex(),
            )
            return decoded_events

        for event in out_events:
            event.event_type = HistoryEventType.TRADE
            event.event_subtype = HistoryEventSubType.SPEND
            event.counterparty = CPT_ZAPPER
            event.notes = f'Swap {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} in Zapper'  # noqa: E501

        for event in in_events:
            event.event_type = HistoryEventType.TRADE
            event.event_subtype = HistoryEventSubType.RECEIVE
            event.counterparty = CPT_ZAPPER
            event.notes = f'Receive {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} as the result of a swap in Zapper'  # noqa: E501

        maybe_reshuffle_events(
            ordered_events=out_events + in_events,
            events_list=decoded_events,
        )
        return decoded_events

    # -- DecoderInterface methods

    def addresses_to_counterparties(self) -> dict[ChecksumEvmAddress, str]:
        return {ZAPPER_SWAP_CONTRACT: CPT_ZAPPER}

    def post_decoding_rules(self) -> dict[str, list[tuple[int, Callable]]]:
        return {CPT_ZAPPER: [(0, self._process_swap)]}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (ZAPPER_CPT_DETAILS,)
