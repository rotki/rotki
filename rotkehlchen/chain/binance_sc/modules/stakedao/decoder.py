from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.stakedao.decoder import StakedaoCommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class StakedaoDecoder(StakedaoCommonDecoder):
    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ):
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            claim_bribe_addresses=[],
            claim_bounty_addresses=[string_to_evm_address('0x62c5D779f5e56F6BC7578066546527fEE590032c')],
        )
