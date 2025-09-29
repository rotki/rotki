from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.aave.v3.constants import EVM_POOLS
from rotkehlchen.chain.evm.decoding.aave.v3.decoder import Aavev3LikeCommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class Aavev3Decoder(Aavev3LikeCommonDecoder):

    def __init__(
            self,
            evm_inquirer: 'OptimismInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            pool_addresses=EVM_POOLS,
            native_gateways=(
                string_to_evm_address('0x60eE8b61a13c67d0191c851BEC8F0bc850160710'),
                string_to_evm_address('0xe9E52021f4e11DEAD8661812A0A6c8627abA2a54'),
            ),
            treasury=string_to_evm_address('0xB2289E329D2F85F1eD31Adbb30eA345278F21bcf'),
            incentives=string_to_evm_address('0x929EC64c34a17401F460460D4B9390518E5B473e'),
            collateral_swap_address=string_to_evm_address('0x830C5A67a0C95D69dA5fb7801Ac1773c6fB53857'),
        )
