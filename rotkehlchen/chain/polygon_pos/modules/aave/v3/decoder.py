from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.aave.v3.constants import EVM_POOLS
from rotkehlchen.chain.evm.decoding.aave.v3.decoder import Aavev3LikeCommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.polygon_pos.node_inquirer import PolygonPOSInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class Aavev3Decoder(Aavev3LikeCommonDecoder):

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
            pool_addresses=EVM_POOLS,
            native_gateways=(
                string_to_evm_address('0xF5f61a1ab3488fCB6d86451846bcFa9cdc108eB0'),
                string_to_evm_address('0xC1E320966c485ebF2A0A2A6d3c0Dc860A156eB1B'),
            ),
            treasury=string_to_evm_address('0xe8599F3cc5D38a9aD6F3684cd5CEa72f10Dbc383'),
            incentives=string_to_evm_address('0x929EC64c34a17401F460460D4B9390518E5B473e'),
            collateral_swap_address=string_to_evm_address('0xC4aff49fCeD8ac1D818a6DCAB063f9f97E66ec5E'),
        )
