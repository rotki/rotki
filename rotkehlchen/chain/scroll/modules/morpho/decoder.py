from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.morpho.decoder import MorphoCommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.scroll.node_inquirer import ScrollInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class MorphoDecoder(MorphoCommonDecoder):

    def __init__(
            self,
            scroll_inquirer: 'ScrollInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=scroll_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            bundlers={string_to_evm_address('0x60F9159d4dCd724e743212416FD57d8aC0B60768')},  # Bundler3  # noqa: E501
            adapters={string_to_evm_address('0xD2780fae0869cDc06EE202152304A39653361525')},  # GeneralAdapter1  # noqa: E501
        )
