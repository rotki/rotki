from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.gitcoinv2.decoder import GitcoinV2CommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class Gitcoinv2Decoder(GitcoinV2CommonDecoder):
    """This is the gitcoin v2 (allo protocol) decoder for Ethereum"""

    def __init__(  # pylint: disable=super-init-not-called
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            project_registry=string_to_evm_address('0x03506eD3f57892C85DB20C36846e9c808aFe9ef4'),
            round_impl_addresses=[
                string_to_evm_address('0xe575282b376E3c9886779A841A2510F1Dd8C2CE4'),
                string_to_evm_address('0xdf22a2C8F6BA9376fF17EE13E6154B784ee92094'),
                string_to_evm_address('0x64E5b2228eF31437909900B38fC42Dd5E4B83147'),
            ],
            payout_strategy_addresses=[  # they match to the above round_impl addresses. Can be found by roundimpl.payoutStrategy()  # noqa: E501
                string_to_evm_address('0xc41bBa19D78242C141D229e5Fe9078def93f304f'),
                string_to_evm_address('0xebaF311F318b5426815727101fB82f0Af3525d7b'),
                string_to_evm_address('0xD32c97242c30AcFFbd30808A31a785772640C6Db'),
            ],
            voting_impl_addresses=[
                string_to_evm_address('0xDA2F26B30e8f5aa9cbE9c5B7Ed58E1cA81D0EbF2'),
                string_to_evm_address('0x8fBEa07446DdF4518b1a7BA2B4f11Bd140a8DF41'),
                string_to_evm_address('0xA09a77809785452c7a5E3d087aFa4B6Bc66Ec881'),
            ],
        )
