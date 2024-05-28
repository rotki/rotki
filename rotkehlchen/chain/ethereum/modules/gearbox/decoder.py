from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.gearbox.decoder import GearboxCommonDecoder
from rotkehlchen.chain.evm.decoding.gearbox.gearbox_cache import read_gearbox_data_from_cache
from rotkehlchen.types import ChainID

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


class GearboxDecoder(GearboxCommonDecoder):
    def __init__(
            self,
            ethereum_inquirer: 'EthereumInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=ethereum_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            read_fn=read_gearbox_data_from_cache,
            chain_id=ChainID.ETHEREUM,
        )
