from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.uniswap.v4.decoder import Uniswapv4CommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


class Uniswapv4Decoder(Uniswapv4CommonDecoder):

    def __init__(
            self,
            base_inquirer: 'BaseInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=base_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            pool_manager=string_to_evm_address('0x498581fF718922c3f8e6A244956aF099B2652b2b'),
            universal_router=string_to_evm_address('0x6fF5693b99212Da76ad316178A184AB56D299b43'),
        )
