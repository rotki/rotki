import logging
from typing import TYPE_CHECKING

from rotkehlchen.chain.ethereum.modules.curve.constants import (
    AAVE_POOLS,
    CURVE_DEPOSIT_CONTRACTS,
    CURVE_SWAP_ROUTER,
    GAUGE_CONTROLLER,
)
from rotkehlchen.chain.evm.decoding.curve.decoder import CurveCommonDecoder
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class CurveDecoder(CurveCommonDecoder):

    def __init__(
            self,
            evm_inquirer: 'EthereumInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            native_currency=A_ETH,
            aave_pools=AAVE_POOLS,
            curve_deposit_contracts=CURVE_DEPOSIT_CONTRACTS,
            curve_swap_router=CURVE_SWAP_ROUTER,
            gauge_controller=GAUGE_CONTROLLER,
        )
