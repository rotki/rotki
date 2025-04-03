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
            claim_bounty_addresses={string_to_evm_address('0xAbf4368d120190B4F111C30C92cc9f8f6a6BE233')},
        )
