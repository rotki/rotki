from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.gitcoin.decoder import GitcoinV2CommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class Gitcoinv2Decoder(GitcoinV2CommonDecoder):
    """This is the gitcoin v2 (allo protocol) decoder for Ethereum

    No gitcoin v1 in optimism since v1 was only on mainnet and zksync lite (maybe polygon too?)
    """

    def __init__(  # pylint: disable=super-init-not-called
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            project_registry=string_to_evm_address('0x03506eD3f57892C85DB20C36846e9c808aFe9ef4'),
            round_impl_addresses=[
                string_to_evm_address('0xe575282b376E3c9886779A841A2510F1Dd8C2CE4'),
            ],
            voting_impl_addresses=[
                string_to_evm_address('0xDA2F26B30e8f5aa9cbE9c5B7Ed58E1cA81D0EbF2'),
            ],
        )
