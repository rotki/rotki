import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Any

from construct import Bytes, Int64ul, Struct
from construct.core import ConstructError

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.utils import get_or_create_solana_token
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.utils import token_normalized_value
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.solana.decoding.interfaces import SolanaDecoderInterface
from rotkehlchen.chain.solana.decoding.structures import (
    DEFAULT_SOLANA_DECODING_OUTPUT,
    SolanaDecoderContext,
    SolanaDecodingOutput,
)
from rotkehlchen.constants.assets import A_SOL
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import SolanaAddress
from rotkehlchen.utils.misc import bytes_to_solana_address

from .constants import (
    CPT_JUPITER,
    FILL_DISCRIMINATOR,
    JUPITER_AGGREGATOR_PROGRAM_V6,
    JUPITER_RFQ_ORDER_ENGINE_PROGRAM,
    ROUTE_DISCRIMINATOR,
    ROUTE_V2_DISCRIMINATOR,
    SWAP_EVENT_DISCRIMINATOR,
    SWAP_EVENT_DISCRIMINATOR_LEN,
)

if TYPE_CHECKING:
    from rotkehlchen.fval import FVal

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# Solana binary layout for Jupiter swap event data
SWAP_EVENT_LAYOUT = Struct(
    'amm' / Bytes(32),          # AMM program that executed the swap
    'inputMint' / Bytes(32),    # Token mint being swapped from
    'inputAmount' / Int64ul,    # Amount of input tokens (raw units)
    'outputMint' / Bytes(32),   # Token mint being swapped to
    'outputAmount' / Int64ul,   # Amount of output tokens (raw units)
)
A_WSOL = Asset('solana/token:So11111111111111111111111111111111111111112')


class JupiterDecoder(SolanaDecoderInterface):

    def _decode_swap(self, context: SolanaDecoderContext) -> SolanaDecodingOutput:
        """Decode swaps via the Jupiter aggregator program.

        Parses the inner instructions of a route instruction to extract swap event data for all
        the swaps in the route. Then updates and reshuffles the decoded transfers, removing any
        events relating to intermediate swaps so the full route is decoded as one swap.

        IDL reference:
        https://github.com/jup-ag/instruction-parser/blob/e6f77951377847c579112e6a16d8c17c5c092485/src/idl/jupiter.ts
        """
        if context.instruction.data[:8] not in (ROUTE_DISCRIMINATOR, ROUTE_V2_DISCRIMINATOR):
            return DEFAULT_SOLANA_DECODING_OUTPUT

        # Parse inner instructions to extract swap events data
        in_token_amounts: defaultdict[Asset, set[FVal]] = defaultdict(set)
        out_token_amounts: defaultdict[Asset, set[FVal]] = defaultdict(set)
        for instruction in context.transaction.instructions:
            if (
                    instruction.parent_execution_index != context.instruction.execution_index or
                    instruction.data[:SWAP_EVENT_DISCRIMINATOR_LEN] != SWAP_EVENT_DISCRIMINATOR
            ):
                continue

            try:
                decoded_event = SWAP_EVENT_LAYOUT.parse(instruction.data[SWAP_EVENT_DISCRIMINATOR_LEN:])  # skip 16-byte discriminator  # noqa: E501
            except ConstructError as e:
                log.error(
                    f'Failed to parse Jupiter swap event data in transaction '
                    f'{context.transaction.signature} at execution_index {instruction.execution_index} '  # noqa: E501
                    f'(parent: {instruction.parent_execution_index}): {e}',
                )
                continue

            for token_amounts, mint_address_bytes, raw_amount in [
                (out_token_amounts, decoded_event.inputMint, decoded_event.inputAmount),
                (in_token_amounts, decoded_event.outputMint, decoded_event.outputAmount),
            ]:
                token_amounts[token := get_or_create_solana_token(
                    userdb=self.node_inquirer.database,
                    address=bytes_to_solana_address(mint_address_bytes),
                    solana_inquirer=self.node_inquirer,
                )].add(token_normalized_value(token=token, token_amount=raw_amount))

        out_event, in_event, filtered_events = None, None, []
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.amount in out_token_amounts[event.asset]
            ):
                if event.amount in in_token_amounts[event.asset]:
                    continue  # don't add these to filtered_events

                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.SPEND
                event.counterparty = CPT_JUPITER
                event.notes = f'Swap {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} in Jupiter'  # noqa: E501
                out_event = event

            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.amount in in_token_amounts[event.asset]
            ):
                if event.amount in out_token_amounts[event.asset]:
                    continue  # don't add these to filtered_events

                event.counterparty = CPT_JUPITER
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.RECEIVE
                event.notes = f'Receive {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} as the result of a swap in Jupiter'  # noqa: E501
                in_event = event

            filtered_events.append(event)

        # replace decoded events with only the filtered events, removing any intermediate swaps
        # so there is only a single swap for the full route.
        context.decoded_events[:] = filtered_events

        if out_event is None or in_event is None:
            log.error(
                f'Failed to find both out and in events for '
                f'Jupiter swap transaction {context.transaction.signature}',
            )
            return DEFAULT_SOLANA_DECODING_OUTPUT

        maybe_reshuffle_events(
            ordered_events=[out_event, in_event],
            events_list=context.decoded_events,
        )
        return SolanaDecodingOutput(process_swaps=True)

    def decode_rfq_swap(self, context: SolanaDecoderContext) -> SolanaDecodingOutput:
        """Decode Jupiter RFQ (request for quote) fill order swaps.
        Docs: https://dev.jup.ag/docs/routing/rfq-integration#order-engine
        """
        if context.instruction.data[:8] != FILL_DISCRIMINATOR:
            return DEFAULT_SOLANA_DECODING_OUTPUT

        if (accounts_len := len(context.instruction.accounts)) < 12:
            log.error(
                f'Encountered Jupiter RFQ Fill instruction with insufficient number of accounts. '
                f'Expected 12, got: {accounts_len}',
            )
            return DEFAULT_SOLANA_DECODING_OUTPUT

        input_amount = token_normalized_value(
            token=(input_token := get_or_create_solana_token(
                userdb=self.node_inquirer.database,
                address=context.instruction.accounts[6],
                solana_inquirer=self.node_inquirer,
            )),
            token_amount=int.from_bytes(context.instruction.data[8:16], byteorder='little'),
        )
        output_amount = token_normalized_value(
            token=(output_token := get_or_create_solana_token(
                userdb=self.node_inquirer.database,
                address=context.instruction.accounts[8],
                solana_inquirer=self.node_inquirer,
            )),
            token_amount=int.from_bytes(context.instruction.data[16:24], byteorder='little'),
        )
        spend_event, receive_event = None, None
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.amount == input_amount and
                (event.asset == input_token or (input_token == A_WSOL and event.asset == A_SOL))
            ):
                event.counterparty = CPT_JUPITER
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.SPEND
                event.notes = f'Swap {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} in Jupiter'  # noqa: E501
                spend_event = event
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.amount == output_amount and
                (event.asset == output_token or (output_token == A_WSOL and event.asset == A_SOL))
            ):
                event.counterparty = CPT_JUPITER
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.RECEIVE
                event.notes = f'Receive {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} as the result of a swap in Jupiter'  # noqa: E501
                receive_event = event

        if spend_event is None or receive_event is None:
            log.error(
                f'Failed to find both spend and receive events for '
                f'Jupiter RFQ swap transaction {context.transaction.signature}',
            )
            return DEFAULT_SOLANA_DECODING_OUTPUT

        maybe_reshuffle_events(
            ordered_events=[spend_event, receive_event],
            events_list=context.decoded_events,
        )
        return SolanaDecodingOutput(process_swaps=True)

    def addresses_to_decoders(self) -> dict[SolanaAddress, tuple[Any, ...]]:
        return {
            JUPITER_AGGREGATOR_PROGRAM_V6: (self._decode_swap,),
            JUPITER_RFQ_ORDER_ENGINE_PROGRAM: (self.decode_rfq_swap,),
        }

    @staticmethod
    def counterparties() -> tuple['CounterpartyDetails', ...]:
        return (CounterpartyDetails(
            identifier=CPT_JUPITER,
            label='Jupiter',
            image='jupiter.svg',
        ),)
