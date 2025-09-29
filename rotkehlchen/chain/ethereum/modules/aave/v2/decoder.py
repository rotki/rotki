from typing import TYPE_CHECKING

from rotkehlchen.chain.ethereum.modules.aave.constants import V3_MIGRATION_HELPER
from rotkehlchen.chain.evm.decoding.aave.v2.decoder import Aavev2CommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

from .constants import ETH_GATEWAYS, POOL_ADDRESS

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


class Aavev2Decoder(Aavev2CommonDecoder):

    def __init__(
            self,
            evm_inquirer: 'EthereumInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            pool_addresses=(POOL_ADDRESS,),
            native_gateways=ETH_GATEWAYS,
            incentives=string_to_evm_address('0xd784927Ff2f95ba542BfC824c8a8a98F3495f6b5'),
            incentives_reward_token=string_to_evm_address('0x4da27a545c0c5B758a6BA100e3a049001de870f5'),  # stkAAVE  # noqa: E501
            v3_migration_helper=V3_MIGRATION_HELPER,
        )
