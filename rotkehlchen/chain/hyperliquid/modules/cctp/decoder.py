from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.cctp.v2_decoder import CctpV2CommonDecoder

from .constants import MESSAGE_TRANSMITTER_V2, TOKEN_MESSENGER_V2, USDC_IDENTIFIER_HYPERLIQUID

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.hyperliquid.node_inquirer import HyperliquidInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class CctpDecoder(CctpV2CommonDecoder):
    def __init__(
            self,
            evm_inquirer: 'HyperliquidInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            token_messenger=TOKEN_MESSENGER_V2,
            message_transmitter=MESSAGE_TRANSMITTER_V2,
            asset_identifier=USDC_IDENTIFIER_HYPERLIQUID,
        )
