from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.sushiswap.decoder import SushiswapCommonDecoder

from .constants import SUSHI_ROUTE_PROCESSORS

if TYPE_CHECKING:
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


class SushiswapDecoder(SushiswapCommonDecoder):

    def __init__(
            self,
            base_inquirer: 'BaseInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=base_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            extra_route_processors=SUSHI_ROUTE_PROCESSORS,
        )
