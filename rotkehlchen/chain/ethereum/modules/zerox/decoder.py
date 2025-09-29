from typing import TYPE_CHECKING

from rotkehlchen.chain.ethereum.modules.zerox.constants import (
    SETTLER_ROUTERS,
    ZEROX_FLASH_WALLET,
    ZEROX_ROUTER,
)
from rotkehlchen.chain.evm.decoding.zerox.decoder import ZeroxCommonDecoder

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


class ZeroxDecoder(ZeroxCommonDecoder):

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
            router_address=ZEROX_ROUTER,
            flash_wallet_address=ZEROX_FLASH_WALLET,
            settler_routers_addresses=SETTLER_ROUTERS,
        )
