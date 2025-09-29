from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.summer_fi.decoder import SummerFiCommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


class SummerFiDecoder(SummerFiCommonDecoder):

    def __init__(
            self,
            arbitrum_one_inquirer: 'ArbitrumOneInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=arbitrum_one_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            account_factory=string_to_evm_address('0xCcB155E5B2A3201d5e10EdAa6e9F908871d1722B'),
        )
