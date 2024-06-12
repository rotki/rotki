from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.gearbox.decoder import GearboxCommonDecoder
from rotkehlchen.chain.optimism.modules.gearbox.constants import GEAR_STAKING_CONTRACT

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class GearboxDecoder(GearboxCommonDecoder):
    def __init__(
            self,
            ethereum_inquirer: 'OptimismInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=ethereum_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            staking_contract=GEAR_STAKING_CONTRACT,
        )
