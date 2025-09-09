from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.quickswap.v4.decoder import Quickswapv4CommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

from .constants import QUICKSWAP_V4_NFT_MANAGER

if TYPE_CHECKING:
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


class Quickswapv4Decoder(Quickswapv4CommonDecoder):

    def __init__(
            self,
            base_inquirer: 'BaseInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=base_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            swap_router=string_to_evm_address('0xe6c9bb24ddB4aE5c6632dbE0DE14e3E474c6Cb04'),
            nft_manager=QUICKSWAP_V4_NFT_MANAGER,
        )
