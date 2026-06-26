from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.across.decoder import AcrossCommonDecoder

from .constants import HUB_POOL, LP_STAKING, SPOKE_POOL

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


class AcrossDecoder(AcrossCommonDecoder):

    def __init__(
            self,
            evm_inquirer: 'EthereumInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            spoke_pool=SPOKE_POOL,
            hub_pools=(HUB_POOL,),
            staking_contracts=(LP_STAKING,),
        )
