import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.solana.decoding.constants import ANCHOR_EVENT_DISCRIMINATOR
from rotkehlchen.chain.solana.decoding.interfaces import SolanaDecoderInterface
from rotkehlchen.chain.solana.decoding.structures import DEFAULT_SOLANA_DECODING_OUTPUT
from rotkehlchen.chain.solana.decoding.utils import get_data_for_discriminator, match_discriminator
from rotkehlchen.chain.solana.modules.jupiter.decoder import A_WSOL
from rotkehlchen.chain.solana.modules.pump_fun.constants import (
    BUY_EVENT_DISCRIMINATOR,
    CPT_PUMP_FUN,
    GET_FEES_DISCRIMINATOR,
    PUMP_FEES_PROGRAM,
    PUMP_FUN_AMM,
)
from rotkehlchen.chain.solana.utils import lamports_to_sol
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import SolanaAddress
from rotkehlchen.utils.misc import bytes_to_solana_address

if TYPE_CHECKING:
    from rotkehlchen.chain.solana.decoding.structures import (
        SolanaDecoderContext,
        SolanaDecodingOutput,
    )

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class PumpFunDecoder(SolanaDecoderInterface):
    """Pump.fun Decoder. Currently only decodes swap fees because if they are left undecoded
    in a Jupiter swap (routing through Pump.fun) then the swap decodes incorrectly.
    TODO: Add decoding for the full Pump.fun protocol.
    """

    def decode_swap_fees(self, context: 'SolanaDecoderContext') -> 'SolanaDecodingOutput':
        """Decode Pump.fun swap fees."""
        if not match_discriminator(context.instruction.data, GET_FEES_DISCRIMINATOR):
            return DEFAULT_SOLANA_DECODING_OUTPUT

        for instruction in context.transaction.instructions:
            if (
                instruction.parent_execution_index == context.instruction.parent_execution_index and  # noqa: E501
                instruction.program_id == PUMP_FUN_AMM and
                (events_data := get_data_for_discriminator(instruction.data, ANCHOR_EVENT_DISCRIMINATOR)) is not None and  # noqa: E501
                (buy_event_data := get_data_for_discriminator(events_data, BUY_EVENT_DISCRIMINATOR)) is not None  # noqa: E501
            ):
                buy_event_instruction = instruction
                break
        else:
            log.error(f'Failed to find Pump.fun buy event instruction in transaction {context.transaction!s}')  # noqa: E501
            return DEFAULT_SOLANA_DECODING_OUTPUT

        protocol_fee = int.from_bytes(buy_event_data[88:96], byteorder='little')
        protocol_fee_recipient = bytes_to_solana_address(buy_event_data[240:272])
        coin_creator_fee = int.from_bytes(buy_event_data[344:352], byteorder='little')
        for event in context.decoded_events:
            if not (
                (event_instruction := self.base.event_instructions.get(event)) is not None and
                event_instruction.parent_execution_index == context.instruction.parent_execution_index and  # noqa: E501
                context.instruction.execution_index < event_instruction.execution_index < buy_event_instruction.execution_index and  # noqa: E501
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == A_WSOL
            ):  # skip if not a WSOL Spend originating between the get_fees and buy_event instructions  # noqa: E501
                continue

            if (
                event.address == protocol_fee_recipient and
                event.amount == lamports_to_sol(protocol_fee)
            ):
                event.notes = f'Spend {event.amount} WSOL as Pump.fun protocol fee'
            elif event.amount == lamports_to_sol(coin_creator_fee):
                event.notes = f'Spend {event.amount} WSOL as Pump.fun coin creator fee'
            else:
                continue

            event.event_subtype = HistoryEventSubType.FEE
            event.counterparty = CPT_PUMP_FUN

        return DEFAULT_SOLANA_DECODING_OUTPUT

    def addresses_to_decoders(self) -> dict[SolanaAddress, tuple[Any, ...]]:
        return {PUMP_FEES_PROGRAM: (self.decode_swap_fees,)}

    @staticmethod
    def counterparties() -> tuple['CounterpartyDetails', ...]:
        return (CounterpartyDetails(
            identifier=CPT_PUMP_FUN,
            label='Pump.fun',
            image='pump-fun.png',
        ),)
