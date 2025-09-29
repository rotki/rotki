from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.arbitrum_one.constants import ARBITRUM_ONE_CPT_DETAILS, CPT_ARBITRUM_ONE
from rotkehlchen.chain.arbitrum_one.decoding.interfaces import ArbitrumDecoderInterface
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ARB
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


ARBITRUM_ONE_AIRDROP = string_to_evm_address('0x67a24CE4321aB3aF51c2D0a4801c3E111D88C9d9')
ARB_CLAIMED = b'\x86)\xb2\x00\xeb\xe4=\xb5\x8a\xd6\x88\xb8Q1\xd52Q\xf3\xf3\xbeL\x14\x93;FA\xae\xeb\xac\xf1\xc0\x8c'  # noqa: E501


class AirdropsDecoder(ArbitrumDecoderInterface):

    def __init__(
            self,
            arbitrum_one_inquirer: 'ArbitrumOneInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=arbitrum_one_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.arb_token = A_ARB.resolve_to_evm_token()

    def _decode_arbitrum_airdrop_claim(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] != ARB_CLAIMED:
            return DEFAULT_DECODING_OUTPUT

        user_address = bytes_to_address(context.tx_log.topics[1])
        raw_amount = int.from_bytes(context.tx_log.data[0:32])
        amount = asset_normalized_value(amount=raw_amount, asset=self.arb_token)

        for event in context.decoded_events:
            if event.event_type == HistoryEventType.RECEIVE and event.location_label == user_address and amount == event.amount and self.arb_token == event.asset:  # noqa: E501
                event.event_type = HistoryEventType.RECEIVE
                event.event_subtype = HistoryEventSubType.AIRDROP
                event.counterparty = CPT_ARBITRUM_ONE
                event.notes = f'Claimed {amount} ARB from arbitrum airdrop'
                break

        return DEFAULT_DECODING_OUTPUT

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            ARBITRUM_ONE_AIRDROP: (self._decode_arbitrum_airdrop_claim,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (ARBITRUM_ONE_CPT_DETAILS,)
