from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.magpie.decoder import MagpieCommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.polygon_pos.node_inquirer import PolygonPOSInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class MagpieDecoder(MagpieCommonDecoder):
    def __init__(
            self,
            evm_inquirer: 'PolygonPOSInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            router_addresses=[
                string_to_evm_address('0xA6E941eaB67569ca4522f70d343714fF51d571c4'),  # v3.1
            ],
        )
