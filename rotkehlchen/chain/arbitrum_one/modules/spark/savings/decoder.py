from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.spark.savings.decoder import SparksavingsCommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class SparksavingsDecoder(SparksavingsCommonDecoder):
    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            psm_address=string_to_evm_address('0x2B05F8e1cACC6974fD79A673a341Fe1f58d27266'),
            spark_savings_tokens=(
                string_to_evm_address('0x940098b108fB7D0a7E374f6eDED7760787464609'),  # sUSDC
                string_to_evm_address('0xdDb46999F8891663a8F2828d25298f70416d7610'),  # sUSDS
            ),
        )
