from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.summer_fi.decoder import SummerFiCommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class SummerFiDecoder(SummerFiCommonDecoder):

    def __init__(
            self,
            optimism_inquirer: 'OptimismInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=optimism_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            account_factory=string_to_evm_address('0xaaf64927BaFe68E389DE3627AA6b52D81bdA2323'),
        )
