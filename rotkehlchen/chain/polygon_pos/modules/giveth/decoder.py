import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.utils import asset_normalized_value
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.giveth.constants import CPT_DETAILS_GIVETH, CPT_GIVETH
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.decoding.utils import get_donation_event_params
from rotkehlchen.history.events.structures.types import HistoryEventSubType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.misc import bytes_to_address

from .constants import DONATION_MADE_TOPIC, GIVETH_DONATION_CONTRACT_ADDRESS

if TYPE_CHECKING:
    from rotkehlchen.types import ChecksumEvmAddress

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class GivethDecoder(EvmDecoderInterface):

    def _decode_donation_events(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] != DONATION_MADE_TOPIC:
            return DEFAULT_EVM_DECODING_OUTPUT

        sender_tracked = self.base.is_tracked(sender_address := context.transaction.from_address)
        recipient_tracked = self.base.is_tracked(recipient_address := bytes_to_address(context.tx_log.topics[1]))  # noqa: E501
        if not sender_tracked and not recipient_tracked:
            return DEFAULT_EVM_DECODING_OUTPUT

        amount_received = asset_normalized_value(
            amount=int.from_bytes(context.tx_log.data[:32]),
            asset=(token_received := self.base.get_token_or_native(bytes_to_address(context.tx_log.topics[2]))),  # noqa: E501
        )
        new_type, expected_type, _, _, notes = get_donation_event_params(
            context=context,
            sender_address=sender_address,
            recipient_address=recipient_address,
            sender_tracked=sender_tracked,
            recipient_tracked=recipient_tracked,
            asset=token_received,
            amount=amount_received,
            payer_address=sender_address,
            counterparty=CPT_GIVETH,
        )
        for event in context.decoded_events:
            if (
                    event.event_type == expected_type and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset == token_received and
                    event.amount == amount_received
            ):
                event.event_type = new_type
                event.counterparty = CPT_GIVETH
                event.event_subtype = HistoryEventSubType.DONATE
                event.notes = notes
                break
        else:
            log.error(f'Failed to find giveth donation event in {context.transaction}')

        return DEFAULT_EVM_DECODING_OUTPUT

    def addresses_to_decoders(self) -> dict['ChecksumEvmAddress', tuple[Any, ...]]:
        return {GIVETH_DONATION_CONTRACT_ADDRESS: (self._decode_donation_events,)}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CPT_DETAILS_GIVETH,)
