from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.uniswap.v4.decoder import Uniswapv4CommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.binance_sc.node_inquirer import BinanceSCInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


class Uniswapv4Decoder(Uniswapv4CommonDecoder):

    def __init__(
            self,
            binance_sc_inquirer: 'BinanceSCInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=binance_sc_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            pool_manager=string_to_evm_address('0x28e2Ea090877bF75740558f6BFB36A5ffeE9e9dF'),
            universal_router=string_to_evm_address('0x1906c1d672b88cD1B9aC7593301cA990F94Eae07'),
        )
