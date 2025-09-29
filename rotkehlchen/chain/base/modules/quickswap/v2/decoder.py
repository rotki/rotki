from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.quickswap.v2.decoder import Quickswapv2CommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.polygon_pos.node_inquirer import PolygonPOSInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class Quickswapv2Decoder(Quickswapv2CommonDecoder):

    def __init__(
            self,
            polygon_pos_inquirer: 'PolygonPOSInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=polygon_pos_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            router_address=string_to_evm_address('0x4a012af2b05616Fb390ED32452641C3F04633bb5'),
            factory_address=string_to_evm_address('0xEC6540261aaaE13F236A032d454dc9287E52e56A'),
        )
