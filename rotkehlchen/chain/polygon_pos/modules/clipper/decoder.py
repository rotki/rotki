from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.clipper.decoder import ClipperCommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.polygon_pos.node_inquirer import PolygonPOSInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class ClipperDecoder(ClipperCommonDecoder):

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
            pool_addresses={
                string_to_evm_address('0x6Bfce69d1Df30FD2B2C8e478EDEC9dAa643Ae3B8'),
            },
        )
