from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.stakedao.v2.decoder import Stakedaov2CommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class Stakedaov2Decoder(Stakedaov2CommonDecoder):

    def __init__(
            self,
            optimism_inquirer: 'OptimismInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ):
        super().__init__(
            evm_inquirer=optimism_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            accountant_address=string_to_evm_address('0x8f872cE018898ae7f218E5a3cE6Fe267206697F8'),
            reward_token_address=string_to_evm_address('0x0994206dfE8De6Ec6920FF4D779B0d950605Fb53'),
        )
