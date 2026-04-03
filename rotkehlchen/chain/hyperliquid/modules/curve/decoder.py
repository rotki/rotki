from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.curve.decoder import CurveCommonDecoder
from rotkehlchen.constants.assets import A_HYPE

from .constants import CHILD_GAUGE_FACTORY, CURVE_SWAP_ROUTER, DEPOSIT_AND_STAKE_ZAP

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.hyperliquid.node_inquirer import HyperliquidInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class CurveDecoder(CurveCommonDecoder):

    def __init__(
            self,
            evm_inquirer: 'HyperliquidInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            native_currency=A_HYPE,
            aave_pools=set(),
            curve_deposit_contracts={DEPOSIT_AND_STAKE_ZAP},
            curve_swap_routers={CURVE_SWAP_ROUTER},
            crv_minter_addresses={CHILD_GAUGE_FACTORY},
        )
