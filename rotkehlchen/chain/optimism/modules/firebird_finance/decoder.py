from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.firebird_finance.decoder import FirebirdFinanceCommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class FirebirdFinanceDecoder(FirebirdFinanceCommonDecoder):

    def __init__(
            self,
            evm_inquirer: 'OptimismInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            router_address=string_to_evm_address('0x0c6134Abc08A1EafC3E2Dc9A5AD023Bb08Da86C3'),
        )
