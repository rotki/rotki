from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.hop.decoder import HopCommonDecoder

from .constants import BRIDGES, REWARD_CONTRACTS

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.gnosis.node_inquirer import GnosisInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class HopDecoder(HopCommonDecoder):
    def __init__(
            self,
            gnosis_inquirer: 'GnosisInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=gnosis_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            bridges=BRIDGES,
            reward_contracts=REWARD_CONTRACTS,
        )
