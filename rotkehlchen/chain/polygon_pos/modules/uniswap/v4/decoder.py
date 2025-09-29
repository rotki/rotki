from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.uniswap.v4.decoder import Uniswapv4CommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.polygon_pos.node_inquirer import PolygonPOSInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class Uniswapv4Decoder(Uniswapv4CommonDecoder):

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
            pool_manager=string_to_evm_address('0x67366782805870060151383F4BbFF9daB53e5cD6'),
            position_manager=string_to_evm_address('0x1Ec2eBf4F37E7363FDfe3551602425af0B3ceef9'),
            universal_router=string_to_evm_address('0x1095692A6237d83C6a72F3F5eFEdb9A670C49223'),
        )
