from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.gitcoinv2.decoder import GitcoinV2CommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class Gitcoinv2Decoder(GitcoinV2CommonDecoder):
    """This is the gitcoin v2 (allo protocol) decoder for Polygon"""

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
            project_registry=None,  # can't find it
            round_impl_addresses=[
                string_to_evm_address('0xa1D52F9b5339792651861329A046dD912761E9A9'),
            ],
            payout_strategy_addresses=[  # they match to the above round_impl addresses. Can be found by roundimpl.payoutStrategy()  # noqa: E501
                string_to_evm_address('0x89d97d76a1f6853202aC2870F5bafc09d0162D75'),
            ],
            voting_impl_addresses=[
                string_to_evm_address('0x03e50B688beB7c0E5e90F51188D0fa38c9152f9d'),
            ],
        )
