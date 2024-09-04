from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.monerium.decoder import MoneriumCommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


class MoneriumDecoder(MoneriumCommonDecoder):

    def __init__(
            self,
            ethereum_inquirer: 'EthereumInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=ethereum_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            monerium_token_addresses={
                string_to_evm_address('0x3231Cb76718CDeF2155FC47b5286d82e6eDA273f'),  # EURe
                string_to_evm_address('0x7ba92741bf2a568abc6f1d3413c58c6e0244f8fd'),  # GBPe
                string_to_evm_address('0xbc5142e0cc5eb16b47c63b0f033d4c2480853a52'),  # USDe
                string_to_evm_address('0xc642549743a93674cf38d6431f75d6443f88e3e2'),  # ISKe
            },
        )
