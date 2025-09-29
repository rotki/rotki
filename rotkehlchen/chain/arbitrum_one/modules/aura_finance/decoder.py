from typing import TYPE_CHECKING

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.decoding.aura_finance.decoder import AuraFinanceCommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


class AuraFinanceDecoder(AuraFinanceCommonDecoder):

    def __init__(
            self,
            evm_inquirer: 'ArbitrumOneInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            claim_zap_address=string_to_evm_address('0x617963D46B882ecE880Ab18Bc232f513E91FDd47'),
            base_reward_tokens=(
                Asset('eip155:42161/erc20:0x1509706a6c66CA549ff0cB464de88231DDBe213B'),  # Aura
                Asset('eip155:42161/erc20:0x040d1EdC9569d4Bab2D15287Dc5A4F10F56a56B8'),  # BAL
            ),
        )
