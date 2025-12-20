import logging
from typing import Any

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

from .constants import (
    CPT_MINTCLUB,
    MINTCLUB_CLAIMED_TOPIC,
    MINTCLUB_CPT_DETAILS,
    MINTCLUB_DISTRIBUTOR_ADDRESS,
)

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class MintclubDecoder(EvmDecoderInterface):
    def _decode_claim_event(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] != MINTCLUB_CLAIMED_TOPIC:
            return DEFAULT_EVM_DECODING_OUTPUT

        claimer = bytes_to_address(context.tx_log.data[:32])
        if self.base.is_tracked(claimer) is False:
            return DEFAULT_EVM_DECODING_OUTPUT

        distribution_id = int.from_bytes(context.tx_log.topics[1], 'big')
        for event in context.decoded_events:
            if (
                    event.event_type != HistoryEventType.RECEIVE or
                    event.location_label != claimer or
                    event.counterparty is not None
            ):
                continue

            token_symbol = event.asset.resolve_to_asset_with_symbol().symbol
            event.counterparty = CPT_MINTCLUB
            event.event_subtype = HistoryEventSubType.REWARD
            event.notes = f'Claim {event.amount} {token_symbol} from MintClub distribution #{distribution_id}'  # noqa: E501
            break

        else:
            log.error(
                f'Failed to match MintClub transfer after claim for {context.transaction}',
            )

        return DEFAULT_EVM_DECODING_OUTPUT

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {MINTCLUB_DISTRIBUTOR_ADDRESS: (self._decode_claim_event,)}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (MINTCLUB_CPT_DETAILS,)
