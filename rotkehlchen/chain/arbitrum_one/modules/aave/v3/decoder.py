from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.aave.v3.constants import EVM_POOLS
from rotkehlchen.chain.evm.decoding.aave.v3.decoder import Aavev3CommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


class Aavev3Decoder(Aavev3CommonDecoder):

    def __init__(
            self,
            evm_inquirer: 'ArbitrumOneInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            pool_addresses=EVM_POOLS,
            native_gateways=(string_to_evm_address('0xecD4bd3121F9FD604ffaC631bF6d41ec12f1fafb'),),
            treasury=string_to_evm_address('0x053D55f9B5AF8694c503EB288a1B7E552f590710'),
            incentives=string_to_evm_address('0x929EC64c34a17401F460460D4B9390518E5B473e'),
        )
