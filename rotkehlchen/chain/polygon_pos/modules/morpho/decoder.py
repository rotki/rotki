from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.morpho.decoder import MorphoCommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.polygon_pos.node_inquirer import PolygonPOSInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class MorphoDecoder(MorphoCommonDecoder):

    def __init__(
            self,
            polygon_pos_inquirer: 'PolygonPOSInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=polygon_pos_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            bundlers={string_to_evm_address('0x2d9C3A9E67c966C711208cc78b34fB9E9f8db589')},  # Bundler3  # noqa: E501
            adapters={
                string_to_evm_address('0xB261B51938A9767406ef83bbFbaAFE16691b7047'),  # GeneralAdapter1  # noqa: E501
                string_to_evm_address('0x5F2617F12D1fDd1e43e72Cb80C92dFcE8124Db8d'),  # ParaswapAdapter  # noqa: E501
            },
        )
