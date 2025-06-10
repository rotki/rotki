from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.magpie.decoder import MagpieDecoder as MagpieCommonDecoder

if TYPE_CHECKING:
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


class MagpieDecoder(MagpieCommonDecoder):
    """Magpie decoder for Base chain"""

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
        )
