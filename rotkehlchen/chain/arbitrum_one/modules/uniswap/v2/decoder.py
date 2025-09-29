from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.uniswap.v2.decoder import Uniswapv2CommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


class Uniswapv2Decoder(Uniswapv2CommonDecoder):

    def __init__(
            self,
            arbitrum_one_inquirer: 'ArbitrumOneInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=arbitrum_one_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            router_address=string_to_evm_address('0x4752ba5DBc23f44D87826276BF6Fd6b1C372aD24'),
            factory_address=string_to_evm_address('0xf1D7CC64Fb4452F05c498126312eBE29f30Fbcf9'),
        )
