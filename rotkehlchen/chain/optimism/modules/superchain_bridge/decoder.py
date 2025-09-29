import logging
from typing import TYPE_CHECKING

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.constants import OPTIMISM_CPT_DETAILS
from rotkehlchen.chain.evm.decoding.superchain_bridge.l2.decoder import (
    SuperchainL2SideBridgeCommonDecoder,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH, A_OPTIMISM_ETH
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
    from rotkehlchen.user_messages import MessagesAggregator


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class SuperchainBridgeDecoder(SuperchainL2SideBridgeCommonDecoder):
    def __init__(
            self,
            evm_inquirer: 'OptimismInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            native_assets=(A_OPTIMISM_ETH, A_ETH),
            bridge_addresses=(
                # Normal Bridge
                string_to_evm_address('0x4200000000000000000000000000000000000010'),
                # L2DAITokenBridge
                string_to_evm_address('0x467194771dAe2967Aef3ECbEDD3Bf9a310C76C65'),
            ),
            counterparty=OPTIMISM_CPT_DETAILS,
        )

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (OPTIMISM_CPT_DETAILS,)
