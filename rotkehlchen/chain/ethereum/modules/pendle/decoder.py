from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.pendle.decoder import PendleCommonDecoder

from .constants import PENDLE_TOKEN, VE_PENDLE_CONTRACT_ADDRESS

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class PendleDecoder(PendleCommonDecoder):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            ve_pendle_contract=VE_PENDLE_CONTRACT_ADDRESS,
            pendle_token=PENDLE_TOKEN,
        )
