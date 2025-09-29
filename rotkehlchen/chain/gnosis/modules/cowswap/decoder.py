import logging
from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.cowswap.decoder import CowswapCommonDecoderWithVCOW
from rotkehlchen.constants.assets import A_GNOSIS_COW, A_GNOSIS_VCOW, A_WXDAI, A_XDAI, Asset
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
            native_asset=A_XDAI,
            wrapped_native_asset=A_WXDAI,
            vcow_token=A_GNOSIS_VCOW,
            cow_token=A_GNOSIS_COW,
            gno_token=Asset('eip155:100/erc20:0x9C58BAcC331c9aa871AFD802DB6379a98e80CEdb'),
        )
