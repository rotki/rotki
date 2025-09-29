from typing import TYPE_CHECKING, Final

from rotkehlchen.chain.evm.decoding.llamazip.decoder import LlamazipCommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
    from rotkehlchen.user_messages import MessagesAggregator

ROUTER_ADDRESSES: Final = (
    string_to_evm_address('0x6f9d14Cf4A06Dd9C70766Bd161cf8d4387683E1b'),
)


class LlamazipDecoder(LlamazipCommonDecoder):

    def __init__(
            self,
            optimism_inquirer: 'OptimismInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=optimism_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            router_addresses=ROUTER_ADDRESSES,
        )
