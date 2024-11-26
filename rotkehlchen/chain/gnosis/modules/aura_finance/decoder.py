from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.aura_finance.decoder import AuraFinanceCommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.gnosis.node_inquirer import GnosisInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class AuraFinanceDecoder(AuraFinanceCommonDecoder):

    def __init__(
            self,
            evm_inquirer: 'GnosisInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            claim_zap_address=string_to_evm_address('0x4EA38a5739D467F7f84c06155ee2Ad745E5328E8'),
        )
