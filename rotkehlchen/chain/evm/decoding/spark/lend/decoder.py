from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.aave.v3.decoder import Aavev3LikeCommonDecoder
from rotkehlchen.chain.evm.decoding.spark.constants import (
    CPT_SPARK,
    SPARK_COUNTERPARTY_LABEL,
)
from rotkehlchen.chain.evm.decoding.spark.decoder import SparkCommonDecoder

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.types import ChecksumEvmAddress
    from rotkehlchen.user_messages import MessagesAggregator


class SparklendCommonDecoder(Aavev3LikeCommonDecoder, SparkCommonDecoder):
    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            pool_addresses: Sequence['ChecksumEvmAddress'],
            native_gateways: 'tuple[ChecksumEvmAddress, ...]',
            treasury: 'ChecksumEvmAddress',
            incentives: 'ChecksumEvmAddress',
    ) -> None:
        Aavev3LikeCommonDecoder.__init__(
            self=self,
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            pool_addresses=pool_addresses,
            native_gateways=native_gateways,
            treasury=treasury,
            incentives=incentives,
            counterparty=CPT_SPARK,
            label=SPARK_COUNTERPARTY_LABEL,
        )
        SparkCommonDecoder.__init__(
            self=self,
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )

    def post_decoding_rules(self) -> dict[str, list[tuple[int, Callable]]]:
        return {CPT_SPARK: [(0, self._decode_interest)]}
