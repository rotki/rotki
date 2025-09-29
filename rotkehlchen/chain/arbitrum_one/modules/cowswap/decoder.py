from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.cowswap.decoder import CowswapCommonDecoder
from rotkehlchen.constants.assets import A_ETH, A_WETH

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


class CowswapDecoder(CowswapCommonDecoder):

    def __init__(
            self,
            arbitrum_one_inquirer: 'ArbitrumOneInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=arbitrum_one_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            native_asset=A_ETH,
            wrapped_native_asset=A_WETH,
        )
