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
                string_to_evm_address('0x8de918F0163b2021839A8D84954dD7E8e151326D'),
            ],
            payout_strategy_addresses=[  # they match to the above round_impl addresses. Can be found by roundimpl.payoutStrategy()  # noqa: E501
                string_to_evm_address('0xEb33BB3705135e99F7975cDC931648942cB2A96f'),
            ],
            voting_impl_addresses=[
                string_to_evm_address('0x99906Ea77C139000681254966b397a98E4bFdE21'),
                string_to_evm_address('0x6526B0942E171A933Fd9aF90C993d9c547251042'),
                string_to_evm_address('0x8dE199ec70057A324053E454741997F2A99FE771'),
                string_to_evm_address('0x201bF28933bdbe7c7ddde85D26646b524D4830DD'),
                string_to_evm_address('0xFc78164b7Ae88ae0F1394A94868E6172E84928D1'),
                string_to_evm_address('0xeE14BFf31165D23422a989201Db4cF70a420B5F0'),
                string_to_evm_address('0x390664d7951AD78B1dE1E733016B9A9b2F0007e9'),
                string_to_evm_address('0xCf065AA4a2870f9D762FaF2f9d760fbB174C6449'),
                string_to_evm_address('0x1444D2837BDFfc409B66bD6BEeb38784e82F57ff'),
            ],
        )
