from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.quickswap.v2.decoder import Quickswapv2CommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.polygon_pos.node_inquirer import PolygonPOSInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class Quickswapv2Decoder(Quickswapv2CommonDecoder):

    def __init__(
            self,
            polygon_pos_inquirer: 'PolygonPOSInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=polygon_pos_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            router_address=string_to_evm_address('0xa5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff'),
            factory_address=string_to_evm_address('0x5757371414417b8C6CAad45bAeF941aBc7d3Ab32'),
        )
