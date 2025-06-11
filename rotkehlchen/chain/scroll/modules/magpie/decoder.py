from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.magpie.decoder import MagpieCommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.scroll.node_inquirer import ScrollInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class MagpieDecoder(MagpieCommonDecoder):
    def __init__(
            self,
            evm_inquirer: 'ScrollInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            router_addresses=[
                string_to_evm_address('0x9eE06954418687C6fb3a9966F7c46E0A245F0183'),  # v3.1
            ],
        )
