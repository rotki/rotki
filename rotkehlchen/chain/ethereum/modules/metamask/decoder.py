from typing import TYPE_CHECKING

from rotkehlchen.chain.ethereum.modules.metamask.constants import (
    METAMASK_FEE_RECEIVER_ADDRESS,
    METAMASK_ROUTER,
)
from rotkehlchen.chain.evm.decoding.metamask.decoder import MetamaskCommonDecoder

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class MetamaskDecoder(MetamaskCommonDecoder):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            router_address=METAMASK_ROUTER,
            fee_receiver_address=METAMASK_FEE_RECEIVER_ADDRESS,
        )
