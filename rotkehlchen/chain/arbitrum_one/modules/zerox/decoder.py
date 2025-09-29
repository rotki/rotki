from typing import TYPE_CHECKING

from rotkehlchen.chain.arbitrum_one.modules.zerox.constants import SETTLER_ROUTERS
from rotkehlchen.chain.ethereum.modules.zerox.constants import ZEROX_ROUTER
from rotkehlchen.chain.evm.decoding.zerox.decoder import ZeroxCommonDecoder
from rotkehlchen.chain.polygon_pos.modules.zerox.constants import ZEROX_FLASH_WALLET

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


class ZeroxDecoder(ZeroxCommonDecoder):

    def __init__(
            self,
            arbitrum_one_inquirer: 'ArbitrumOneInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=arbitrum_one_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            router_address=ZEROX_ROUTER,
            flash_wallet_address=ZEROX_FLASH_WALLET,
            settler_routers_addresses=SETTLER_ROUTERS,
        )
