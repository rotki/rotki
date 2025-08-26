from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.uniswap.v2.decoder import Uniswapv2CommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.polygon_pos.node_inquirer import PolygonPOSInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class Uniswapv2Decoder(Uniswapv2CommonDecoder):

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
            router_address=string_to_evm_address('0xedf6066a2b290C185783862C7F4776A2C8077AD1'),
            factory_address=string_to_evm_address('0x9e5A52f57b3038F1B8EeE45F28b3C1967e22799C'),
        )
