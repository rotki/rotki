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
            psm_address=string_to_evm_address('0xe0F9978b907853F354d79188A3dEfbD41978af62'),
            spark_savings_tokens=(
                string_to_evm_address('0xCF9326e24EBfFBEF22ce1050007A43A3c0B6DB55'),  # sUSDC
                string_to_evm_address('0xb5B2dc7fd34C249F4be7fB1fCea07950784229e0'),  # sUSDS
            ),
        )
