from typing import TYPE_CHECKING

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
                string_to_evm_address('0xDA3B55A9bCf58Bb2d9F673836Beab3aE47cA9184'),
                string_to_evm_address('0xE03a19f4921D69cddD37f54dFe814DC66AA92100'),
                string_to_evm_address('0xeDb366e318fc2C94c16852ff2fb99a3F59Db8CBb'),
                string_to_evm_address('0x1B48bB09930676d99dDA36C1aD27ff0a5A5f3911'),
                string_to_evm_address('0x1b0Caf40F491dCE9c51E7e33d6E86112Bb0BB91B'),
                string_to_evm_address('0xC1cffd1845dEeE83aB44cae123738a854593BCd2'),
                string_to_evm_address('0x0C0412DDB846096Ea1e37de717921EBF4fEF9A39'),
                string_to_evm_address('0x0023055B2F86EAE827C2bee06BBF483738fb600c'),
                string_to_evm_address('0x347Ff9951D24E29b559E3323b5370Aa29993e613'),
                string_to_evm_address('0xe5B88c67fCd25f0a7BAD6cF7c5A5197e61BFd143'),
                string_to_evm_address('0x145052E87140b7309F6EE18Ba12fC187560d5D89'),
                string_to_evm_address('0x3E93205B786796Cf7Ea70404E89c7dda3b84D07a'),
            ],
            retro_funding_strategy_addresses=[string_to_evm_address('0x2Caa214E2de4b05A9E0E1a1cCfDb3c673a28acCf')],
        )
