from typing import TYPE_CHECKING, Final

from rotkehlchen.chain.evm.decoding.omnibridge.decoder import OmnibridgeCommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.types import ChainID

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator

BRIDGE_ADDRESS: Final = string_to_evm_address('0xf6A78083ca3e2a662D6dd1703c939c8aCE2e268d')


class OmnibridgeDecoder(OmnibridgeCommonDecoder):

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
            bridge_address=BRIDGE_ADDRESS,
            source_chain=ChainID.GNOSIS,
            target_chain=ChainID.ETHEREUM,
        )
