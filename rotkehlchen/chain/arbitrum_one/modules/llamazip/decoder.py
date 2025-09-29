from typing import TYPE_CHECKING, Final

from rotkehlchen.chain.evm.decoding.llamazip.decoder import LlamazipCommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator

ROUTER_ADDRESSES: Final = (
    string_to_evm_address('0x5279EBC4e5BA9eA09F19ADE49F2Bc98339aeA4d7'),
    string_to_evm_address('0x973bf562407766e77f885c1cd1a8060e5303C745'),
)


class LlamazipDecoder(LlamazipCommonDecoder):

    def __init__(
            self,
            arbitrum_inquirer: 'ArbitrumOneInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=arbitrum_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            router_addresses=ROUTER_ADDRESSES,
        )
