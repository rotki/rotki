from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType

from .constants import CPT_FLYING_TULIP, FLYING_TULIP_CPT_DETAILS

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.decoding.types import CounterpartyDetails
    from rotkehlchen.fval import FVal
    from rotkehlchen.types import ChecksumEvmAddress


class FlyingTulipCommonDecoder(EvmDecoderInterface):
    """Shared base for the Flying Tulip product decoders.

    Each product (ftUSD, lending, puts) has its own decoder inheriting from
    this class so they all expose the same counterparty metadata.
    """

    def _transform_or_defer(
            self,
            context: DecoderContext,
            from_event_type: HistoryEventType,
            token: 'EvmToken',
            amount: 'FVal',
            location_label: 'ChecksumEvmAddress | None',
            to_event_type: HistoryEventType,
            to_event_subtype: HistoryEventSubType,
            notes: str,
    ) -> EvmDecodingOutput:
        """Match the wallet transfer belonging to a protocol event.

        The transfer may appear before the protocol's own log (deposits,
        repayments) or after it (withdrawals, borrows), so already-decoded
        events are searched first and an action item covers transfers decoded
        later. Nothing is created when no transfer exists, since such events
        move funds inside the protocol without touching the wallet.
        """
        for event in context.decoded_events:
            if (
                    event.event_type == from_event_type and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset == token and
                    event.amount == amount and
                    (location_label is None or event.location_label == location_label)
            ):
                event.event_type = to_event_type
                event.event_subtype = to_event_subtype
                event.notes = notes
                event.counterparty = CPT_FLYING_TULIP
                event.address = context.tx_log.address
                return DEFAULT_EVM_DECODING_OUTPUT

        return EvmDecodingOutput(action_items=[ActionItem(
            action='transform',
            from_event_type=from_event_type,
            from_event_subtype=HistoryEventSubType.NONE,
            asset=token,
            amount=amount,
            location_label=location_label,
            to_event_type=to_event_type,
            to_event_subtype=to_event_subtype,
            to_notes=notes,
            to_counterparty=CPT_FLYING_TULIP,
            to_address=context.tx_log.address,
        )])

    @staticmethod
    def counterparties() -> tuple['CounterpartyDetails', ...]:
        return (FLYING_TULIP_CPT_DETAILS,)
