from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.extrafi.decoder import ExtrafiCommonDecoder

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class ExtrafiDecoder(ExtrafiCommonDecoder):

    def __init__(
            self,
            optimism_inquirer: 'OptimismInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=optimism_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            extra_token_identifier='eip155:10/erc20:0x2dAD3a13ef0C6366220f989157009e501e7938F8',
        )
