from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.spark.savings.decoder import SparksavingsCommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class SparksavingsDecoder(SparksavingsCommonDecoder):
    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            psm_address=string_to_evm_address('0x1601843c5E9bC251A3272907010AFa41Fa18347E'),
            spark_savings_tokens=(
                string_to_evm_address('0x3128a0F7f0ea68E7B7c9B00AFa7E41045828e858'),  # sUSDC
                string_to_evm_address('0x5875eEE11Cf8398102FdAd704C9E96607675467a'),  # sUSDS
            ),
        )
