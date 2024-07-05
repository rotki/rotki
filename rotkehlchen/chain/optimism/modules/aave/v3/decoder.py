from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.aave.v3.constants import POOL_ADDRESS
from rotkehlchen.chain.evm.decoding.aave.v3.decoder import Aavev3CommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class Aavev3Decoder(Aavev3CommonDecoder):

    def __init__(
            self,
            evm_inquirer: 'OptimismInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            pool_address=POOL_ADDRESS,
            native_gateways=(string_to_evm_address('0xe9E52021f4e11DEAD8661812A0A6c8627abA2a54'),),
            treasury=string_to_evm_address('0xB2289E329D2F85F1eD31Adbb30eA345278F21bcf'),
            incentives=string_to_evm_address('0x929EC64c34a17401F460460D4B9390518E5B473e'),
        )
