from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.uniswap.v2.decoder import Uniswapv2CommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.binance_sc.node_inquirer import BinanceSCInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


class Uniswapv2Decoder(Uniswapv2CommonDecoder):

    def __init__(
            self,
            binance_sc_inquirer: 'BinanceSCInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=binance_sc_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            router_address=string_to_evm_address('0x4752ba5DBc23f44D87826276BF6Fd6b1C372aD24'),
            factory_address=string_to_evm_address('0x8909Dc15e40173Ff4699343b6eB8132c65e18eC6'),
        )
