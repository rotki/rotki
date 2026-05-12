from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.clipper.decoder import ClipperCommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


class ClipperDecoder(ClipperCommonDecoder):

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
            pool_addresses={
                string_to_evm_address('0x655eDCE464CC797526600a462A8154650EEe4B77'),
                string_to_evm_address('0xE7b0CE0526fbE3969035a145C9e9691d4d9D216c'),
            },
        )
