from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.stakedao.v2.decoder import Stakedaov2CommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


class Stakedaov2Decoder(Stakedaov2CommonDecoder):
    def __init__(
            self,
            arbitrum_one_inquirer: 'ArbitrumOneInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ):
        super().__init__(
            evm_inquirer=arbitrum_one_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            accountant_address=string_to_evm_address('0x93b4B9bd266fFA8AF68e39EDFa8cFe2A62011Ce0'),
            reward_token_address=string_to_evm_address('0x11cDb42B0EB46D95f990BeDD4695A6e3fA034978'),
        )
