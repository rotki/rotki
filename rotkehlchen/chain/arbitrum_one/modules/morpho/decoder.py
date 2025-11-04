from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.morpho.decoder import MorphoCommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


class MorphoDecoder(MorphoCommonDecoder):

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
            bundlers={string_to_evm_address('0x1FA4431bC113D308beE1d46B0e98Cb805FB48C13')},  # Bundler3  # noqa: E501
            adapters={
                string_to_evm_address('0x9954aFB60BB5A222714c478ac86990F221788B88'),  # GeneralAdapter1  # noqa: E501
                string_to_evm_address('0xAA5c30C1482c189cA0d56057D3ac4dD7Af1e4726'),  # ParaswapAdapter  # noqa: E501
                string_to_evm_address('0x1923670d4F4eB7435d865E7477d28FEAFfA40C93'),  # AaveV3MigrationAdapter  # noqa: E501
                string_to_evm_address('0x86Ca77a4a37A9CDBe9bBf4975F6d69531B96444b'),  # CompoundV3MigrationAdapter  # noqa: E501
            },
        )
