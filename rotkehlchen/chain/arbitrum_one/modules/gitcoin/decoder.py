import logging
from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.chain.evm.decoding.constants import CPT_GITCOIN
from rotkehlchen.chain.evm.decoding.gitcoinv2.decoder import GitcoinV2CommonDecoder
from rotkehlchen.chain.evm.decoding.structures import DEFAULT_DECODING_OUTPUT, DecodingOutput
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address, from_wei

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.decoding.structures import DecoderContext
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

ON_ATTESTED: Final = b';\xdb\xa5P\x8aX\xb2%\x9e\xce\x9bEU\x84;\x90W\xcb+\xfa\xb8\xf3\x84\x0bm\xf3P\xda`k(q'  # noqa: E501


class GitcoinDecoder(GitcoinV2CommonDecoder):
    """This is the gitcoin v2 (allo protocol) decoder for Arbitrum"""

    def __init__(  # pylint: disable=super-init-not-called
            self,
            optimism_inquirer: 'ArbitrumOneInquirer',
            base_tools: 'BaseEvmDecoderTools',
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
            direct_allocation_strategy_addresses=[string_to_evm_address('0x91AD709FE04E214eF53218572D8d8690a8b4FdD0')],
        )

    def _decode_donation_impact_minting(self, context: 'DecoderContext') -> DecodingOutput:
        if context.tx_log.topics[0] != ON_ATTESTED:
            return DEFAULT_DECODING_OUTPUT

        if not self.base.is_tracked(recipient := bytes_to_address(context.tx_log.topics[2])):
            return DEFAULT_DECODING_OUTPUT

        amount = from_wei(int.from_bytes(context.tx_log.data[:32]))
        for event in context.decoded_events:
            if event.event_type == HistoryEventType.SPEND and event.event_subtype == HistoryEventSubType.NONE and event.asset == A_ETH and event.location_label == recipient and event.amount == amount:  # noqa: E501
                event.counterparty = CPT_GITCOIN
                event.event_type = HistoryEventType.MINT
                event.event_subtype = HistoryEventSubType.FEE
                event.notes = f'Mint donation impact attestation 0x{context.tx_log.topics[1].hex()} for a fee of {amount} ETH'  # noqa: E501
                break

        else:
            log.error(f'In minting donation impact could not find the ETH fee transfer in {context.transaction}')  # noqa: E501

        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return super().addresses_to_decoders() | {
            string_to_evm_address('0x2ce7E4cB5Edb140A9327e67De85463186E757C8f'): (self._decode_donation_impact_minting,),  # noqa: E501
        }
