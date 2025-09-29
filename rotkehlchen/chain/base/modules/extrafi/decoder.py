from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.extrafi.decoder import ExtrafiCommonDecoder

if TYPE_CHECKING:
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


class ExtrafiDecoder(ExtrafiCommonDecoder):

    def __init__(
            self,
            optimism_inquirer: 'BaseInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=optimism_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            extra_token_identifier='eip155:8453/erc20:0x2dad3a13ef0c6366220f989157009e501e7938f8',
        )
