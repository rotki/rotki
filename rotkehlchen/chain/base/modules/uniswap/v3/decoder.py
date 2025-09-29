from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.uniswap.v3.decoder import Uniswapv3CommonDecoder

if TYPE_CHECKING:
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator

from .constants import UNISWAP_ROUTER_ADDRESSES, UNISWAP_V3_NFT_MANAGER


class Uniswapv3Decoder(Uniswapv3CommonDecoder):

    def __init__(
            self,
            base_inquirer: 'BaseInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=base_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            routers_addresses=UNISWAP_ROUTER_ADDRESSES,
            nft_manager=UNISWAP_V3_NFT_MANAGER,
        )
