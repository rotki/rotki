from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.monerium.decoder import MoneriumCommonDecoder

from .constants import ARBITRUM_MONERIUM_ADDRESSES

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


class MoneriumDecoder(MoneriumCommonDecoder):

    def __init__(
            self,
            arbitrum_one_inquirer: 'ArbitrumOneInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=arbitrum_one_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            monerium_token_addresses=ARBITRUM_MONERIUM_ADDRESSES,
        )
