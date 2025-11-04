import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.utils import get_or_create_solana_token
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.utils import token_normalized_value
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.solana.decoding.constants import ANCHOR_EVENT_DISCRIMINATOR
from rotkehlchen.chain.solana.decoding.interfaces import SolanaDecoderInterface
from rotkehlchen.chain.solana.decoding.structures import (
    DEFAULT_SOLANA_DECODING_OUTPUT,
    SolanaDecoderContext,
    SolanaDecodingOutput,
)
from rotkehlchen.chain.solana.decoding.utils import get_data_for_discriminator, match_discriminator
from rotkehlchen.constants.assets import A_SOL, A_WSOL
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import SolanaAddress

from .constants import (
    CPT_JUPITER,
    FILL_DISCRIMINATOR,
    JUPITER_AGGREGATOR_PROGRAM_V6,
    JUPITER_RFQ_ORDER_ENGINE_PROGRAM,
    ROUTE_DISCRIMINATORS_TO_MINT_IDX,
    SWAP_EVENT_DISCRIMINATOR,
    SWAPS_EVENT_DISCRIMINATOR,
)

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.history.events.structures.solana_event import SolanaEvent

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class JupiterDecoder(SolanaDecoderInterface):

    def decode_v6_swap(self, context: SolanaDecoderContext) -> SolanaDecodingOutput:
        """Decode swaps via the Jupiter aggregator v6 program.

        Matches the swap event instruction and the corresponding route instruction and combines
        all swaps in the route into a single swap event group.

        IDL reference:
        https://github.com/jup-ag/instruction-parser/blob/e6f77951377847c579112e6a16d8c17c5c092485/src/idl/jupiter.ts
        """
        if not (
            (event_data := get_data_for_discriminator(context.instruction.data, ANCHOR_EVENT_DISCRIMINATOR)) is not None and (  # noqa: E501
                match_discriminator(event_data, SWAP_EVENT_DISCRIMINATOR) or
                match_discriminator(event_data, SWAPS_EVENT_DISCRIMINATOR)
            )
        ):
            return DEFAULT_SOLANA_DECODING_OUTPUT

        # Find the route instruction corresponding to this swap event instruction
        for instruction in context.transaction.instructions:
            if (
                instruction.execution_index != context.instruction.parent_execution_index or
                (mint_idx := ROUTE_DISCRIMINATORS_TO_MINT_IDX.get(instruction.data[:8])) is None or
                len(instruction.accounts) < mint_idx + 1
            ):
                continue

            destination_mint = instruction.accounts[mint_idx]
            route_instruction = instruction
            break
        else:
            log.error(f'Failed to find Jupiter route instruction in transaction {context.transaction!s}')  # noqa: E501
            return DEFAULT_SOLANA_DECODING_OUTPUT

        unrelated_events, other_events, platform_fee_event = [], [], None
        out_events_by_asset: dict[Asset, SolanaEvent] = {}
        in_events_by_asset: dict[Asset, SolanaEvent] = {}
        for event in context.decoded_events:
            if (
                (event_instruction := self.base.event_instructions.get(event)) is None or
                event_instruction.parent_execution_index != route_instruction.execution_index
            ):
                unrelated_events.append(event)
                continue

            if (  # platform fee comes immediately after the swap events instruction
                event_instruction.execution_index == context.instruction.execution_index + 1 and
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE
            ):
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.FEE
                event.counterparty = CPT_JUPITER
                event.notes = f'Spend {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} as Jupiter platform fee'  # noqa: E501
                platform_fee_event = event
            elif (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE
            ):
                if (existing_event := out_events_by_asset.get(event.asset)) is not None:
                    existing_event.amount += event.amount
                else:
                    out_events_by_asset[event.asset] = event
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE
            ):
                if (existing_event := in_events_by_asset.get(event.asset)) is not None:
                    existing_event.amount += event.amount
                else:
                    in_events_by_asset[event.asset] = event
            else:
                other_events.append(event)

        # Combine any opposite side events that have the same asset
        events_to_skip = set()
        for in_event in in_events_by_asset.values():
            if (out_event := out_events_by_asset.get(in_event.asset)) is None:
                continue

            if in_event.amount == out_event.amount:
                events_to_skip.add(in_event)
                events_to_skip.add(out_event)
            elif out_event.amount > in_event.amount:
                out_event.amount -= in_event.amount
                events_to_skip.add(in_event)
            else:  # out_event.amount < in_event.amount
                in_event.amount -= out_event.amount
                events_to_skip.add(out_event)

        # Update the amount in the event notes and skip unneeded events
        out_events: list[SolanaEvent] = []
        in_events: list[SolanaEvent] = []
        slippage_events: list[SolanaEvent] = []
        for events_by_asset, final_list, sub_type, notes_template in (
            (out_events_by_asset, out_events, HistoryEventSubType.SPEND, 'Swap {amount} {asset} in Jupiter'),  # noqa: E501
            (in_events_by_asset, in_events, HistoryEventSubType.RECEIVE, 'Receive {amount} {asset} as the result of a swap in Jupiter'),  # noqa: E501
        ):
            for trade_event in events_by_asset.values():
                if trade_event in events_to_skip:
                    continue

                trade_event.counterparty = CPT_JUPITER
                if (
                    sub_type == HistoryEventSubType.RECEIVE and
                    destination_mint not in trade_event.asset.identifier
                ):
                    trade_event.event_type = HistoryEventType.RECEIVE
                    trade_event.event_subtype = HistoryEventSubType.NONE
                    trade_event.notes = f'Receive {trade_event.amount} {trade_event.asset.resolve_to_asset_with_symbol().symbol} due to positive slippage in a Jupiter swap'  # noqa: E501
                    slippage_events.append(trade_event)
                    continue

                trade_event.event_type = HistoryEventType.TRADE
                trade_event.event_subtype = sub_type
                trade_event.notes = notes_template.format(
                    amount=trade_event.amount,
                    asset=trade_event.asset.resolve_to_asset_with_symbol().symbol,
                )
                final_list.append(trade_event)

        if len(out_events) == 0 or len(in_events) == 0:
            log.error(
                f'Failed to find both out and in events for '
                f'Jupiter swap transaction {context.transaction.signature}',
            )
            return DEFAULT_SOLANA_DECODING_OUTPUT

        # replace decoded events with only the filtered events
        filtered_events = (
            out_events + in_events +
            ([platform_fee_event] if platform_fee_event is not None else []) +
            slippage_events + other_events
        )
        context.decoded_events[:] = unrelated_events + filtered_events

        maybe_reshuffle_events(ordered_events=filtered_events, events_list=context.decoded_events)
        return SolanaDecodingOutput(process_swaps=True)

    def decode_rfq_swap(self, context: SolanaDecoderContext) -> SolanaDecodingOutput:
        """Decode Jupiter RFQ (request for quote) fill order swaps.
        Docs: https://dev.jup.ag/docs/routing/rfq-integration#order-engine
        """
        if context.instruction.data[:8] != FILL_DISCRIMINATOR:
            return DEFAULT_SOLANA_DECODING_OUTPUT

        if (accounts_len := len(context.instruction.accounts)) < 11:  # IDL specifies 11, but some txs have extra ones  # noqa: E501
            log.error(
                f'Encountered Jupiter RFQ Fill instruction with insufficient number of accounts. '
                f'Expected at least 11, got: {accounts_len}',
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
            JUPITER_AGGREGATOR_PROGRAM_V6: (self.decode_v6_swap,),
            JUPITER_RFQ_ORDER_ENGINE_PROGRAM: (self.decode_rfq_swap,),
        }

    @staticmethod
    def counterparties() -> tuple['CounterpartyDetails', ...]:
        return (CounterpartyDetails(
            identifier=CPT_JUPITER,
            label='Jupiter',
            image='jupiter.svg',
        ),)
