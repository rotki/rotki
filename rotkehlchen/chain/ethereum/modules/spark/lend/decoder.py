from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.spark.lend.decoder import SparklendCommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


class SparklendDecoder(SparklendCommonDecoder):
    def __init__(
            self,
            evm_inquirer: 'EthereumInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            pool_addresses=(string_to_evm_address('0xC13e21B648A5Ee794902342038FF3aDAB66BE987'),),
            native_gateways=(string_to_evm_address('0xBD7D6a9ad7865463DE44B05F04559f65e3B11704'),),
            treasury=string_to_evm_address('0xb137E7d16564c81ae2b0C8ee6B55De81dd46ECe5'),
            incentives=string_to_evm_address('0x4370D3b6C9588E02ce9D22e684387859c7Ff5b34'),
        )
