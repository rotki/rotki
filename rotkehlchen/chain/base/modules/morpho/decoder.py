from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.morpho.decoder import MorphoCommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_WETH_BASE

if TYPE_CHECKING:
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


class MorphoDecoder(MorphoCommonDecoder):

    def __init__(
            self,
            base_inquirer: 'BaseInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=base_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            bundlers={
                string_to_evm_address('0x6BFd8137e702540E7A42B74178A4a49Ba43920C4'),  # ChainAgnosticBundlerV3  # noqa: E501
                string_to_evm_address('0x23055618898e202386e6c13955a58D3C68200BFB'),  # ChainAgnosticBundlerV2  # noqa: E501
                string_to_evm_address('0x123f3167a416cA19365dE03a65e0AF3532af7223'),  # CompoundV2MigrationBundlerV2  # noqa: E501
                string_to_evm_address('0x1f8076e2EB6f10b12e6886f30D4909A91969F7dA'),  # CompoundV3MigrationBundlerV2  # noqa: E501
                string_to_evm_address('0xcAe2929baBc60Be34818EaA5F40bF69265677108'),  # AaveV3MigrationBundlerV2  # noqa: E501
            },
            weth=A_WETH_BASE,
        )
