from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.aura_finance.decoder import AuraFinanceCommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


class AuraFinanceDecoder(AuraFinanceCommonDecoder):

    def __init__(
            self,
            evm_inquirer: 'BaseInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            claim_zap_address=string_to_evm_address('0x5a5094e2a2a4c1B48a6630138a3b1076eC00B10d'),
        )
