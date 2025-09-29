from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.curve.constants import (
    CHILD_LIQUIDITY_GAUGE_FACTORY,
    CURVE_SWAP_ROUTERS_NG,
    DEPOSIT_AND_STAKE_ZAP,
)
from rotkehlchen.chain.evm.decoding.curve.decoder import CurveCommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_XDAI

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.gnosis.node_inquirer import GnosisInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class CurveDecoder(CurveCommonDecoder):

    def __init__(
            self,
            evm_inquirer: 'GnosisInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            native_currency=A_XDAI,
            aave_pools=set(),
            curve_deposit_contracts={
                DEPOSIT_AND_STAKE_ZAP,
                string_to_evm_address('0xE3FFF29d4DC930EBb787FeCd49Ee5963DADf60b6'),  # EURe/3CRV metapool zap contract  # noqa: E501
                string_to_evm_address('0x87C067fAc25f123554a0E76596BF28cFa37fD5E9'),  # MetaUSD Zap
            },
            curve_swap_routers=CURVE_SWAP_ROUTERS_NG,
            crv_minter_addresses={CHILD_LIQUIDITY_GAUGE_FACTORY},
        )
