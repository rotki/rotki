from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.sushiswap.decoder import SushiswapCommonDecoder

if TYPE_CHECKING:
    from rotkehlchen.chain.binance_sc.node_inquirer import BinanceSCInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


class SushiswapDecoder(SushiswapCommonDecoder):

    def __init__(
            self,
            evm_inquirer: 'BinanceSCInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
