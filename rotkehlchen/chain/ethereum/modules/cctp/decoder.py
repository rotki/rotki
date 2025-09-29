from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.cctp.decoder import CctpCommonDecoder
from rotkehlchen.constants.assets import A_USDC

from .constants import MESSAGE_TRANSMITTER, TOKEN_MESSENGER

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


class CctpDecoder(CctpCommonDecoder):
    def __init__(
            self,
            ethereum_inquirer: 'EthereumInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=ethereum_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            token_messenger=TOKEN_MESSENGER,
            asset_identifier=A_USDC.identifier,
            message_transmitter=MESSAGE_TRANSMITTER,
        )
