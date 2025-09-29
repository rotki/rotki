from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.uniswap.v4.decoder import Uniswapv4CommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


class Uniswapv4Decoder(Uniswapv4CommonDecoder):

    def __init__(
            self,
            ethereum_inquirer: 'EthereumInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=ethereum_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            pool_manager=string_to_evm_address('0x000000000004444c5dc75cB358380D2e3dE08A90'),
            position_manager=string_to_evm_address('0xbD216513d74C8cf14cf4747E6AaA6420FF64ee9e'),
            universal_router=string_to_evm_address('0x66a9893cC07D91D95644AEDD05D03f95e1dBA8Af'),
        )
