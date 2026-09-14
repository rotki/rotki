from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.cctp.v2_decoder import CctpV2CommonDecoder
from rotkehlchen.constants.assets import A_USDC

from .constants import MESSAGE_TRANSMITTER_V2, TOKEN_MESSENGER_V2

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


class CctpV2Decoder(CctpV2CommonDecoder):
    def __init__(
            self,
            ethereum_inquirer: EthereumInquirer,
            base_tools: BaseEvmDecoderTools,
            msg_aggregator: MessagesAggregator,
    ) -> None:
        super().__init__(
            evm_inquirer=ethereum_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            token_messenger=TOKEN_MESSENGER_V2,
            message_transmitter=MESSAGE_TRANSMITTER_V2,
            asset_identifier=A_USDC.identifier,
        )
