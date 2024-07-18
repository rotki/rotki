from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.odos.v2.decoder import Odosv2DecoderBase

from .constants import ODOS_V2_ROUTER

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.scroll.node_inquirer import ScrollInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class Odosv2Decoder(Odosv2DecoderBase):
    def __init__(
            self,
            evm_inquirer: 'ScrollInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            router_address=ODOS_V2_ROUTER,
        )
