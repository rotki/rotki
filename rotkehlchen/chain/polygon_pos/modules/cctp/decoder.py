from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.cctp.decoder import CctpCommonDecoder

from .constants import MESSAGE_TRANSMITTER, TOKEN_MESSENGER, USDC_IDENTIFIER_POLYGON

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.polygon_pos.node_inquirer import PolygonPOSInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class CctpDecoder(CctpCommonDecoder):
    def __init__(
            self,
            evm_inquirer: 'PolygonPOSInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            token_messenger=TOKEN_MESSENGER,
            message_transmitter=MESSAGE_TRANSMITTER,
            asset_identifier=USDC_IDENTIFIER_POLYGON,
        )
