from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.aave.v3.constants import POOL_ADDRESS
from rotkehlchen.chain.evm.decoding.aave.v3.decoder import Aavev3CommonDecoder

from .constants import AAVE_TREASURY, ETH_GATEWAYS

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class Aavev3Decoder(Aavev3CommonDecoder):

    def __init__(
            self,
            evm_inquirer: 'OptimismInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            pool_address=POOL_ADDRESS,
            eth_gateways=ETH_GATEWAYS,
            treasury=AAVE_TREASURY,
        )
