from typing import TYPE_CHECKING

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.decoding.aura_finance.decoder import AuraFinanceCommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


class AuraFinanceDecoder(AuraFinanceCommonDecoder):

    def __init__(
            self,
            evm_inquirer: 'BaseInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            claim_zap_address=string_to_evm_address('0x5a5094e2a2a4c1B48a6630138a3b1076eC00B10d'),
            base_reward_tokens=(
                Asset('eip155:8453/erc20:0x1509706a6c66CA549ff0cB464de88231DDBe213B'),  # Aura
                Asset('eip155:8453/erc20:0x4158734D47Fc9692176B5085E0F52ee0Da5d47F1'),  # BAL
            ),
        )
