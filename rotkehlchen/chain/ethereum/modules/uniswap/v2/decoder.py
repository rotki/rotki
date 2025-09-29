from typing import TYPE_CHECKING, Final

from rotkehlchen.chain.evm.decoding.uniswap.v2.decoder import Uniswapv2CommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator

UNISWAP_V2_ROUTER: Final = string_to_evm_address('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D')


class Uniswapv2Decoder(Uniswapv2CommonDecoder):

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
            router_address=UNISWAP_V2_ROUTER,
            factory_address=string_to_evm_address('0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f'),
        )
