from typing import TYPE_CHECKING

from rotkehlchen.chain.ethereum.modules.paraswap.constants import (
    PARASWAP_AUGUSTUS_ROUTER,
    PARASWAP_FEE_CLAIMER,
)
from rotkehlchen.chain.evm.decoding.paraswap.decoder import ParaswapCommonDecoder

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class ParaswapDecoder(ParaswapCommonDecoder):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            router_address=PARASWAP_AUGUSTUS_ROUTER,
            fee_receiver_address=PARASWAP_FEE_CLAIMER,
        )
