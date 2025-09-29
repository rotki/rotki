from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.curve.constants import CHILD_LIQUIDITY_GAUGE_FACTORY
from rotkehlchen.chain.evm.decoding.curve.decoder import CurveCommonDecoder
from rotkehlchen.constants.assets import A_ETH

from .constants import CURVE_SWAP_ROUTERS_NG, DEPOSIT_AND_STAKE_ZAP

if TYPE_CHECKING:
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


class CurveDecoder(CurveCommonDecoder):

    def __init__(
            self,
            evm_inquirer: 'BaseInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            native_currency=A_ETH,
            aave_pools=set(),
            curve_deposit_contracts={DEPOSIT_AND_STAKE_ZAP},
            curve_swap_routers=CURVE_SWAP_ROUTERS_NG,
            crv_minter_addresses={CHILD_LIQUIDITY_GAUGE_FACTORY},
        )
