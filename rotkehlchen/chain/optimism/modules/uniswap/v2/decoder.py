from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.uniswap.v2.decoder import Uniswapv2CommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class Uniswapv2Decoder(Uniswapv2CommonDecoder):

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
            router_address=string_to_evm_address('0x4A7b5Da61326A6379179b40d00F57E5bbDC962c2'),
            factory_address=string_to_evm_address('0x0c3c1c532F1e39EdF36BE9Fe0bE1410313E074Bf'),
        )
