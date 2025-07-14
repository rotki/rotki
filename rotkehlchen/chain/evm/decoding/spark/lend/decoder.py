from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.aave.v3.decoder import Aavev3LikeCommonDecoder
from rotkehlchen.chain.evm.decoding.spark.constants import (
    CPT_SPARK,
    SPARK_COUNTERPARTY_DETAILS,
)
from rotkehlchen.chain.evm.decoding.spark.decoder import SparkCommonDecoder
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.types import ChecksumEvmAddress
    from rotkehlchen.user_messages import MessagesAggregator


class SparklendCommonDecoder(Aavev3LikeCommonDecoder, SparkCommonDecoder):
    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            pool_addresses: Sequence['ChecksumEvmAddress'],
            native_gateways: 'tuple[ChecksumEvmAddress, ...]',
            treasury: 'ChecksumEvmAddress',
            incentives: 'ChecksumEvmAddress',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            pool_addresses=pool_addresses,
            native_gateways=native_gateways,
            treasury=treasury,
            incentives=incentives,
            counterparty=CPT_SPARK,
            label=SPARK_COUNTERPARTY_DETAILS.label,  # type: ignore  # this is "Spark"
        )

    def post_decoding_rules(self) -> dict[str, list[tuple[int, Callable]]]:
        return {CPT_SPARK: [(0, self._decode_interest)]}

    @staticmethod
    def counterparties() -> tuple['CounterpartyDetails', ...]:
        return (SPARK_COUNTERPARTY_DETAILS,)
