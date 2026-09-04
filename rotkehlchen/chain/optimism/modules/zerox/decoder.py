from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.zerox.decoder import ZeroxCommonDecoder
from rotkehlchen.chain.optimism.modules.zerox.constants import (
    ZEROX_FLASH_WALLET,
    ZEROX_ROUTER,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class ZeroxDecoder(ZeroxCommonDecoder):

    def __init__(
            self,
            optimism_inquirer: OptimismInquirer,
            base_tools: BaseEvmDecoderTools,
            msg_aggregator: MessagesAggregator,
    ) -> None:
        super().__init__(
            evm_inquirer=optimism_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            router_address=ZEROX_ROUTER,
            flash_wallet_address=ZEROX_FLASH_WALLET,
        )
