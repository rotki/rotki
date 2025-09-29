import logging
from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.cowswap.decoder import CowswapCommonDecoderWithVCOW
from rotkehlchen.constants.assets import A_COW, A_ETH, A_GNO, A_VCOW, A_WETH
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class CowswapDecoder(CowswapCommonDecoderWithVCOW):

    def __init__(
            self,
            ethereum_inquirer: 'EthereumInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=ethereum_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            native_asset=A_ETH,
            wrapped_native_asset=A_WETH,
            vcow_token=A_VCOW,
            cow_token=A_COW,
            gno_token=A_GNO,
        )
