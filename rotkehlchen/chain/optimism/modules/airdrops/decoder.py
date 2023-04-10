from typing import TYPE_CHECKING, Any

from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.decoding.constants import OPTIMISM_CPT_DETAILS
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails, EventCategory
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.optimism.constants import CPT_OPTIMISM
from rotkehlchen.constants.assets import A_OP
from rotkehlchen.types import ChecksumEvmAddress, DecoderEventMappingType
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
    from rotkehlchen.user_messages import MessagesAggregator


OPTIMISM_AIRDROP = string_to_evm_address('0xFeDFAF1A10335448b7FA0268F56D2B44DBD357de')
OP_CLAIMED = b'N\xc9\x0e\x96U\x19\xd9&\x81&tg\xf7u\xad\xa5\xbd!J\xa9,\r\xc9=\x90\xa5\xe8\x80\xce\x9e\xd0&'  # noqa: E501


class AirdropsDecoder(DecoderInterface):

    def __init__(
            self,
            optimism_inquirer: 'OptimismInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=optimism_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.op_token = A_OP.resolve_to_evm_token()

    def _decode_optimism_airdrop_claim(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] != OP_CLAIMED:
            return DEFAULT_DECODING_OUTPUT

        user_address = hex_or_bytes_to_address(context.tx_log.data[32:64])
        raw_amount = hex_or_bytes_to_int(context.tx_log.data[64:96])
        amount = asset_normalized_value(amount=raw_amount, asset=self.op_token)

        for event in context.decoded_events:
            if event.event_type == HistoryEventType.RECEIVE and event.location_label == user_address and amount == event.balance.amount and self.op_token == event.asset:  # noqa: E501
                event.event_type = HistoryEventType.RECEIVE
                event.event_subtype = HistoryEventSubType.AIRDROP
                event.counterparty = CPT_OPTIMISM
                event.notes = f'Claimed {amount} OP from optimism airdrop'
                break

        return DEFAULT_DECODING_OUTPUT

    def possible_events(self) -> DecoderEventMappingType:
        return {CPT_OPTIMISM: {
            HistoryEventType.RECEIVE: {
                HistoryEventSubType.AIRDROP: EventCategory.AIRDROP,
            },
        }}

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            OPTIMISM_AIRDROP: (self._decode_optimism_airdrop_claim,),
        }

    def counterparties(self) -> list[CounterpartyDetails]:
        return [OPTIMISM_CPT_DETAILS]
