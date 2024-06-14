from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.curve.constants import (
    CURVE_SWAP_ROUTER_NG,
    DEPOSIT_AND_STAKE_ZAP,
)
from rotkehlchen.chain.evm.decoding.curve.decoder import CurveCommonDecoder
from rotkehlchen.constants.assets import A_XDAI

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.gnosis.node_inquirer import GnosisInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class CurveDecoder(CurveCommonDecoder):

    def __init__(
            self,
            evm_inquirer: 'GnosisInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            native_currency=A_XDAI,
            aave_pools=set(),
            curve_deposit_contracts={DEPOSIT_AND_STAKE_ZAP},
            curve_swap_routers={CURVE_SWAP_ROUTER_NG},
        )
