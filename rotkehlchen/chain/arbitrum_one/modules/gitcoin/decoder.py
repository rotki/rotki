from typing import TYPE_CHECKING

from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
from rotkehlchen.chain.evm.decoding.gitcoinv2.decoder import GitcoinV2CommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


class GitcoinDecoder(GitcoinV2CommonDecoder):
    """This is the gitcoin v2 (allo protocol) decoder for Arbitrum"""

    def __init__(  # pylint: disable=super-init-not-called
            self,
            optimism_inquirer: 'ArbitrumOneInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=optimism_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            project_registry=None,
            round_impl_addresses=[],
            payout_strategy_addresses=[],
            voting_impl_addresses=[],
            voting_merkle_distributor_addresses=[
                string_to_evm_address('0x9c239f3317C6DF0b4b381B965617162312dc8CAA'),
                string_to_evm_address('0xB91B59c91B09D127D269e53019F2420E8c2C7cE7'),
                string_to_evm_address('0x2D4d59757d5A7C3c376fC47b9F4501C347B9654d'),
            ],
        )
