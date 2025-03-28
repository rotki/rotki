from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.compound.v3.decoder import Compoundv3CommonDecoder

from .constants import COMPOUND_BULKER_ADDRESS, COMPOUND_REWARDS_ADDRESS

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.scroll.node_inquirer import ScrollInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class Compoundv3Decoder(Compoundv3CommonDecoder):

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
            rewards_address=COMPOUND_REWARDS_ADDRESS,
            bulker_address=COMPOUND_BULKER_ADDRESS,
        )
