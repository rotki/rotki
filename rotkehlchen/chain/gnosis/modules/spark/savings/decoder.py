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
            spark_savings_tokens=(string_to_evm_address('0xaf204776c7245bF4147c2612BF6e5972Ee483701'),),  # sxDAI  # noqa: E501
        )
