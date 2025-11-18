from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.stakedao.v2.decoder import Stakedaov2CommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


class Stakedaov2Decoder(Stakedaov2CommonDecoder):

    def __init__(
            self,
            base_inquirer: 'BaseInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ):
        super().__init__(
            evm_inquirer=base_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            accountant_address=string_to_evm_address('0x8f872cE018898ae7f218E5a3cE6Fe267206697F8'),
            reward_token_address=string_to_evm_address('0x8Ee73c484A26e0A5df2Ee2a4960B789967dd0415'),
        )
