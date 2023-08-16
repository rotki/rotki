from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.gitcoin.decoder import GitcoinV2CommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class GitcoinDecoder(GitcoinV2CommonDecoder):
    """This is the gitcoin v2 (allo protocol) decoder for Optimism

    No gitcoin v1 in optimism since v1 was only on mainnet and zksync lite (maybe polygon too?)
    """

    def __init__(  # pylint: disable=super-init-not-called
            self,
            optimism_inquirer: 'OptimismInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=optimism_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            project_registry=string_to_evm_address('0x8e1bD5Da87C14dd8e08F7ecc2aBf9D1d558ea174'),
            round_impl_addresses=[
                string_to_evm_address('0x99906Ea77C139000681254966b397a98E4bFdE21'),
            ],
        )
