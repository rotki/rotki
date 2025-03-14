from typing import TYPE_CHECKING

from rotkehlchen.chain.ethereum.modules.monerium.constants import ETHEREUM_MONERIUM_ADDRESSES
from rotkehlchen.chain.evm.decoding.monerium.decoder import MoneriumCommonDecoder

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


class MoneriumDecoder(MoneriumCommonDecoder):

    def __init__(
            self,
            ethereum_inquirer: 'EthereumInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=ethereum_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            monerium_token_addresses=ETHEREUM_MONERIUM_ADDRESSES,
        )
