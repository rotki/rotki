from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.quickswap.v3.decoder import Quickswapv3CommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.polygon_pos.node_inquirer import PolygonPOSInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class Quickswapv3Decoder(Quickswapv3CommonDecoder):

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
            router_address=string_to_evm_address('0xf5b509bB0909a69B1c207E495f687a596C168E12'),
        )
