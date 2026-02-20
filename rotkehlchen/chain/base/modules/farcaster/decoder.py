from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.base.modules.farcaster.constants import (
    CPT_FARCASTER,
    FARCASTER_CPT_DETAILS,
    FARCASTER_PRO,
    PURCHASED_TIER_TOPIC,
)
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.decoding.types import CounterpartyDetails
    from rotkehlchen.types import ChecksumEvmAddress


class FarcasterDecoder(EvmDecoderInterface):

    def _decode_purchase_log(self, context: DecoderContext) -> EvmDecodingOutput:
        if (
            context.tx_log.topics[0] != PURCHASED_TIER_TOPIC or
            not self.base.is_tracked(payer := bytes_to_address(context.tx_log.topics[3]))
        ):
            return DEFAULT_EVM_DECODING_OUTPUT

        tier = int.from_bytes(context.tx_log.topics[2])
        duration_days = int.from_bytes(context.tx_log.data[:32])
        action_item = ActionItem(
            action='transform',
            from_event_type=HistoryEventType.SPEND,
            from_event_subtype=HistoryEventSubType.NONE,
            location_label=payer,
            to_notes=f'Pay {{amount}} USDC for Farcaster Pro tier {tier} for {duration_days} days',
            to_counterparty=CPT_FARCASTER,
            to_event_subtype=HistoryEventSubType.PAYMENT,
        )

        context.action_items.append(action_item)
        return DEFAULT_EVM_DECODING_OUTPUT

    def addresses_to_decoders(self) -> dict['ChecksumEvmAddress', tuple[Any, ...]]:
        return {FARCASTER_PRO: (self._decode_purchase_log,)}

    @staticmethod
    def counterparties() -> tuple['CounterpartyDetails', ...]:
        return (FARCASTER_CPT_DETAILS,)
