from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.uniswap.v4.decoder import Uniswapv4CommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


class Uniswapv4Decoder(Uniswapv4CommonDecoder):

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
            pool_manager=string_to_evm_address('0x360E68faCcca8cA495c1B759Fd9EEe466db9FB32'),
            position_manager=string_to_evm_address('0xd88F38F930b7952f2DB2432Cb002E7abbF3dD869'),
            universal_router=string_to_evm_address('0xA51afAFe0263b40EdaEf0Df8781eA9aa03E381a3'),
        )
