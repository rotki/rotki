from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.morpho.decoder import MorphoCommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class MorphoDecoder(MorphoCommonDecoder):

    def __init__(
            self,
            optimism_inquirer: 'OptimismInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=optimism_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            bundlers={string_to_evm_address('0xFBCd3C258feB131D8E038F2A3a670A7bE0507C05')},  # Bundler3  # noqa: E501
            adapters={
                string_to_evm_address('0x79481C87f24A3C4332442A2E9faaf675e5F141f0'),  # GeneralAdapter1  # noqa: E501
                string_to_evm_address('0x31F539f4Ed14fA1fd18781e93f6739249692aDC5'),  # ParaswapAdapter  # noqa: E501
            },
        )
