from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.airdrops import AIRDROP_IDENTIFIER_KEY
from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER, OPTIMISM_CPT_DETAILS
from rotkehlchen.chain.evm.decoding.interfaces import MerkleClaimDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.optimism.constants import CPT_OPTIMISM
from rotkehlchen.constants.assets import A_OP
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
    from rotkehlchen.user_messages import MessagesAggregator

PEEL_4BYTE: Final = b'C\x914\x91'
OPTIMISM_AIRDROP_1: Final = string_to_evm_address('0xFeDFAF1A10335448b7FA0268F56D2B44DBD357de')
OPTIMISM_AIRDROP_4: Final = string_to_evm_address('0xFb4D5A94b516DF77Fbdbcf3CfeB262baAF7D4dB7')
OPTIMISM_AIRDROP_5: Final = string_to_evm_address('0x9a69d97a451643a0Bb4462476942D2bC844431cE')
OPTIMISM_FOUNDATION_ADDRESS: Final = string_to_evm_address('0x2501c477D0A35545a387Aa4A3EEe4292A9a8B3F0')  # noqa: E501


class AirdropsDecoder(MerkleClaimDecoderInterface):

    def __init__(
            self,
            optimism_inquirer: 'OptimismInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=optimism_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.op_token = A_OP.resolve_to_evm_token()

    def _decode_distributed_airdrop(self, context: DecoderContext) -> DecodingOutput:
        """This decodes airdrops sent directly to users by the OP Foundation:
        - Airdrop 1: For users who did not claim their allocation.
        - Airdrop 2 & 3: Automatically distributed, no claim required.
        """
        if (
            bytes_to_address(context.tx_log.topics[1]) != OPTIMISM_FOUNDATION_ADDRESS and
            not self.base.is_tracked(bytes_to_address(context.tx_log.topics[2]))
        ):
            return DEFAULT_DECODING_OUTPUT

        if context.transaction.to_address == string_to_evm_address('0xbE9a9B1B07f027130e56d8569d1aeA5dd5a86013'):  # noqa: E501
            airdrop_identifier, note_suffix = 'optimism_2', '2'
        elif context.transaction.to_address == string_to_evm_address('0x53466D3cabb3B59aa6065fd732672d68f191EfC0'):  # noqa: E501
            airdrop_identifier, note_suffix = 'optimism_1', '1'
        elif context.transaction.to_address == string_to_evm_address('0x4bd927E14f828e5862F166919Fd5091dA6ae44c0'):  # noqa: E501
            airdrop_identifier, note_suffix = 'optimism_3', '3'
        else:
            return DEFAULT_DECODING_OUTPUT

        context.action_items.append(ActionItem(
            action='transform',
            from_event_type=HistoryEventType.RECEIVE,
            from_event_subtype=HistoryEventSubType.NONE,
            asset=self.op_token,
            amount=(amount := token_normalized_value_decimals(
                token_amount=int.from_bytes(context.tx_log.data),
                token_decimals=self.op_token.decimals,
            )),
            to_counterparty=CPT_OPTIMISM,
            to_event_type=HistoryEventType.RECEIVE,
            to_event_subtype=HistoryEventSubType.AIRDROP,
            to_notes=f'Receive {amount} OP from the optimism airdrop {note_suffix}',
            extra_data={AIRDROP_IDENTIFIER_KEY: airdrop_identifier},
        ))
        return DEFAULT_DECODING_OUTPUT

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            distributor_address: (
                self._decode_merkle_claim,
                CPT_OPTIMISM,  # counterparty
                self.op_token.identifier,  # token id
                18,  # token decimals
                f'OP from the optimism airdrop {note_suffix}',  # notes suffix
                airdrop_identifier,
            )
            for airdrop_identifier, distributor_address, note_suffix in (
                ('optimism_1', OPTIMISM_AIRDROP_1, '1'),
                ('optimism_4', OPTIMISM_AIRDROP_4, '4'),
                ('optimism_5', OPTIMISM_AIRDROP_5, '5'),
            )
        }

    def decoding_by_input_data(self) -> dict[bytes, dict[bytes, Callable]]:
        return {PEEL_4BYTE: {ERC20_OR_ERC721_TRANSFER: self._decode_distributed_airdrop}}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (OPTIMISM_CPT_DETAILS,)
