from typing import TYPE_CHECKING

from rotkehlchen.chain.arbitrum_one.modules.gearbox.constants import (
    GEAR_STAKING_CONTRACT,
    GEAR_TOKEN_ARB,
)
from rotkehlchen.chain.evm.decoding.gearbox.decoder import GearboxCommonDecoder

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


class GearboxDecoder(GearboxCommonDecoder):
    def __init__(
            self,
            ethereum_inquirer: 'ArbitrumOneInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=ethereum_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            staking_contract=GEAR_STAKING_CONTRACT,
            gear_token_identifier=GEAR_TOKEN_ARB.identifier,
        )
