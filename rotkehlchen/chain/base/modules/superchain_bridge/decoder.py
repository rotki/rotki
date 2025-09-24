import logging
from typing import TYPE_CHECKING

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.constants import BASE_CPT_DETAILS
from rotkehlchen.chain.evm.decoding.superchain_bridge.l2.decoder import (
    SuperchainL2SideBridgeCommonDecoder,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class SuperchainBridgeDecoder(SuperchainL2SideBridgeCommonDecoder):
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
            native_assets=(A_ETH,),
            bridge_addresses=(
                # Normal Bridge
                string_to_evm_address('0x4200000000000000000000000000000000000010'),
            ),
            counterparty=BASE_CPT_DETAILS,
        )

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (BASE_CPT_DETAILS,)
