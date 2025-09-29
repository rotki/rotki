from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.monerium.decoder import MoneriumCommonDecoder

from .constants import SCROLL_MONERIUM_ADDRESSES

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.scroll.node_inquirer import ScrollInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class MoneriumDecoder(MoneriumCommonDecoder):

    def __init__(
            self,
            scroll_inquirer: 'ScrollInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=scroll_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            monerium_token_addresses=SCROLL_MONERIUM_ADDRESSES,
        )
