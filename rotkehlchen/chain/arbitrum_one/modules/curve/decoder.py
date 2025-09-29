from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.curve.constants import (
    CHILD_LIQUIDITY_GAUGE_FACTORY,
    CURVE_SWAP_ROUTER_V1,
    DEPOSIT_AND_STAKE_ZAP,
)
from rotkehlchen.chain.evm.decoding.curve.decoder import CurveCommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


class CurveDecoder(CurveCommonDecoder):

    def __init__(
            self,
            evm_inquirer: 'ArbitrumOneInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            native_currency=A_ETH,
            aave_pools=set(),
            curve_deposit_contracts={
                DEPOSIT_AND_STAKE_ZAP,
                string_to_evm_address('0xF97c707024ef0DD3E77a0824555a46B622bfB500'),  # Tricrypto Zap  # noqa: E501
                string_to_evm_address('0x25e2e8d104BC1A70492e2BE32dA7c1f8367F9d2c'),  # EURs Zap
                string_to_evm_address('0x7544Fe3d184b6B55D6B36c3FCA1157eE0Ba30287'),  # MetaUSD Zap
                string_to_evm_address('0x803A2B40c5a9BB2B86DD630B274Fa2A9202874C2'),  # MetaBTC Zap
            },
            curve_swap_routers={
                CURVE_SWAP_ROUTER_V1,
                string_to_evm_address('0x2191718CD32d02B8E60BAdFFeA33E4B5DD9A0A0D'),  # CurveRouterSidechain v1.1  # noqa: E501
            },
            crv_minter_addresses={CHILD_LIQUIDITY_GAUGE_FACTORY},
        )
