from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.curve.constants import (
    CHILD_LIQUIDITY_GAUGE_FACTORY,
    CURVE_SWAP_ROUTER_NG,
    DEPOSIT_AND_STAKE_ZAP,
)
from rotkehlchen.chain.evm.decoding.curve.decoder import CurveCommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_POLYGON_POS_MATIC

from .constants import AAVE_POOLS

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.polygon_pos.node_inquirer import PolygonPOSInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class CurveDecoder(CurveCommonDecoder):

    def __init__(
            self,
            evm_inquirer: 'PolygonPOSInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            native_currency=A_POLYGON_POS_MATIC,
            aave_pools=AAVE_POOLS,
            curve_deposit_contracts={
                DEPOSIT_AND_STAKE_ZAP,
                string_to_evm_address('0x3FCD5De6A9fC8A99995c406c77DDa3eD7E406f81'),  # ATriCrypto Zap  # noqa: E501
                string_to_evm_address('0x1d8b86e3D88cDb2d34688e87E72F388Cb541B7C8'),  # ATriCrypto3 Zap  # noqa: E501
                string_to_evm_address('0x225FB4176f0E20CDb66b4a3DF70CA3063281E855'),  # EURTUSD Zap
                string_to_evm_address('0x4DF7eF55E99a56851187822d96B4E17D98A47DeD'),  # EURs Zap
                string_to_evm_address('0x5ab5C56B9db92Ba45a0B46a207286cD83C15C939'),  # MetaUSD Zap
                string_to_evm_address('0xE2e6DC1708337A6e59f227921db08F21e3394723'),  # MetaBTC Zap
            },
            curve_swap_routers={CURVE_SWAP_ROUTER_NG},
            crv_minter_addresses={CHILD_LIQUIDITY_GAUGE_FACTORY},
        )
