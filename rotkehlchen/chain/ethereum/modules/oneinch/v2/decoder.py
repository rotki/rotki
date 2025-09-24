from typing import TYPE_CHECKING

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.oneinch.decoder import OneinchCommonDecoder
from rotkehlchen.chain.evm.decoding.structures import DecoderContext, DecodingOutput
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

from ..constants import CPT_ONEINCH_V2
from .constants import ONEINCH_V2_MAINNET_ROUTER


class Oneinchv2Decoder(OneinchCommonDecoder):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            router_address=ONEINCH_V2_MAINNET_ROUTER,
            swapped_signatures=[b'v\xaf"J\x148e\xa5\x0bAIn\x1asb&\x98i,V\\\x12\x14\xbc\x86/\x18\xe2-\x82\x9c^'],
            counterparty=CPT_ONEINCH_V2,
        )

    def _decode_swapped(self, context: DecoderContext) -> DecodingOutput:
        return self._create_swapped_events(
            context=context,
            sender=bytes_to_address(context.tx_log.topics[1]),
            receiver=bytes_to_address(context.tx_log.data[0:32]),
            source_token_address=bytes_to_address(context.tx_log.topics[2]),
            destination_token_address=bytes_to_address(context.tx_log.topics[3]),
            spent_amount_raw=int.from_bytes(context.tx_log.data[64:96]),
            return_amount_raw=int.from_bytes(context.tx_log.data[96:128]),
        )

    # -- DecoderInterface methods

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return OneinchCommonDecoder.generate_counterparty_details(CPT_ONEINCH_V2)
