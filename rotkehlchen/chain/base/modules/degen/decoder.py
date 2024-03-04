from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.base.modules.degen.constants import CLAIM_AIRDROP_2_CONTRACT, CPT_DEGEN
from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.constants import DEFAULT_TOKEN_DECIMALS, MERKLE_CLAIM
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

if TYPE_CHECKING:
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.types import ChecksumEvmAddress
    from rotkehlchen.user_messages import MessagesAggregator


class DegenDecoder(DecoderInterface):

    def __init__(
            self,
            evm_inquirer: 'BaseInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(evm_inquirer, base_tools, msg_aggregator)
        self.degen = Asset('eip155:8453/erc20:0x4ed4E862860beD51a9570b96d89aF5E1B0Efefed')

    def _decode_claim(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] != MERKLE_CLAIM:
            return DEFAULT_DECODING_OUTPUT

        user_address = hex_or_bytes_to_address(context.tx_log.topics[2])
        raw_amount = hex_or_bytes_to_int(context.tx_log.topics[3])
        amount = token_normalized_value_decimals(
            token_amount=raw_amount,
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )

        for event in context.decoded_events:
            if event.event_type == HistoryEventType.RECEIVE and event.location_label == user_address and amount == event.balance.amount and self.degen == event.asset:  # noqa: E501
                event.event_type = HistoryEventType.RECEIVE
                event.event_subtype = HistoryEventSubType.AIRDROP
                event.counterparty = CPT_DEGEN
                event.notes = f'Claimed {amount} DEGEN from Degen airdrop 2'
                break

        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict['ChecksumEvmAddress', tuple[Any, ...]]:
        return {CLAIM_AIRDROP_2_CONTRACT: (self._decode_claim,)}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_DEGEN,
            label='Degen',
            image='degen.svg',
        ),)
