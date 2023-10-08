from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.oneinch.constants import CPT_ONEINCH
from rotkehlchen.chain.evm.decoding.oneinch.decoder import OneinchCommonDecoder
from rotkehlchen.chain.evm.decoding.structures import DecoderContext, DecodingOutput
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

from .constants import ONEINCH_POLYGON_POS_ROUTER


class OneinchDecoder(OneinchCommonDecoder):

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
            router_address=ONEINCH_POLYGON_POS_ROUTER,
            swapped_signatures=[b'\xd6\xd4\xf5h\x1c$l\x9fB\xc2\x03\xe2\x87\x97Z\xf1`\x1f\x8d\xf8\x03Z\x92Q\xf7\x9a\xab\\\x8f\t\xe2\xf8'],
            counterparty=CPT_ONEINCH,
        )

    def _decode_swapped(self, context: DecoderContext) -> DecodingOutput:
        return self._create_swapped_events(
            context=context,
            sender=hex_or_bytes_to_address(context.tx_log.data[:32]),
            receiver=hex_or_bytes_to_address(context.tx_log.data[96:128]),
            source_token_address=hex_or_bytes_to_address(context.tx_log.data[32:64]),
            destination_token_address=hex_or_bytes_to_address(context.tx_log.data[64:96]),
            spent_amount_raw=hex_or_bytes_to_int(context.tx_log.data[128:160]),
            return_amount_raw=hex_or_bytes_to_int(context.tx_log.data[160:]),
        )
