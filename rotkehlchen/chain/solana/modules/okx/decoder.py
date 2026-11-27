import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.utils import token_normalized_value
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.solana.decoding.constants import (
    ANCHOR_DISCRIMINATOR_LEN,
    ANCHOR_EVENT_DISCRIMINATOR,
    SPL_TOKEN_CLOSE_ACCOUNT_DISCRIMINATOR,
    SPL_TOKEN_PROGRAM,
    SPL_TOKEN_SYNC_NATIVE_DISCRIMINATOR,
)
from rotkehlchen.chain.solana.decoding.interfaces import SolanaDecoderInterface
from rotkehlchen.chain.solana.decoding.structures import (
    DEFAULT_SOLANA_DECODING_OUTPUT,
    SolanaDecoderContext,
    SolanaDecodingOutput,
)
from rotkehlchen.chain.solana.decoding.utils import get_data_for_discriminator
from rotkehlchen.constants.assets import A_SOL, A_WSOL
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.misc import bytes_to_solana_address

from .constants import (
    COMMON_SWAP_CPI_EVENT_HEADER_LEN,
    CPT_OKX,
    OKX_DEX_ROUTER_V1_PROGRAM,
    OKX_DEX_ROUTER_V2_PROGRAM,
    SUMMARY_SWAP_CPI_EVENT_DISCRIMINATORS,
    SWAP_TOB_V2_CPI_EVENT2_DISCRIMINATOR,
    SWAP_TOC_V2_CPI_EVENT2_DISCRIMINATOR,
    SWAP_WITH_FEES_CPI_EVENT2_DISCRIMINATOR,
    SWAP_WITH_FEES_CPI_EVENT_DISCRIMINATOR,
    SWAP_WITH_FEES_CPI_EVENT_ENHANCED2_DISCRIMINATOR,
)

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.chain.solana.types import SolanaInstruction
    from rotkehlchen.fval import FVal
    from rotkehlchen.history.events.structures.solana_event import SolanaEvent
    from rotkehlchen.types import SolanaAddress

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _parse_cpi_event_fees(
        event_discriminator: bytes,
        payload: bytes,
        source_mint: SolanaAddress,
        destination_mint: SolanaAddress,
) -> list[tuple[SolanaAddress, int]]:
    """Extract non-zero (fee_mint, raw_fee_amount) pairs from fee-bearing OKX CPI events."""
    fees: list[tuple[SolanaAddress, int]] = []
    if event_discriminator in (
        SWAP_WITH_FEES_CPI_EVENT2_DISCRIMINATOR,
        SWAP_WITH_FEES_CPI_EVENT_DISCRIMINATOR,
        SWAP_WITH_FEES_CPI_EVENT_ENHANCED2_DISCRIMINATOR,
    ):
        if len(payload) < 288:
            return fees

        fee_mint = source_mint if payload[160] != 0 else destination_mint
        for raw_amount, mint in (
            (int.from_bytes(payload[165:173], byteorder='little'), fee_mint),
            (int.from_bytes(payload[207:215], byteorder='little'), fee_mint),
            (int.from_bytes(payload[248:256], byteorder='little'), destination_mint),
        ):
            if raw_amount > 0:
                fees.append((mint, raw_amount))

        if (
            event_discriminator == SWAP_WITH_FEES_CPI_EVENT_ENHANCED2_DISCRIMINATOR and
            len(payload) >= 330 and
            (charge_amount := int.from_bytes(payload[290:298], byteorder='little')) > 0
        ):
            fees.append((fee_mint, charge_amount))
    elif event_discriminator in (
        SWAP_TOB_V2_CPI_EVENT2_DISCRIMINATOR,
        SWAP_TOC_V2_CPI_EVENT2_DISCRIMINATOR,
    ):
        if len(payload) < 295:
            return fees

        fee_mint = source_mint if payload[160] != 0 else destination_mint
        for raw_amount, mint in (
            (int.from_bytes(payload[169:177], byteorder='little'), fee_mint),
            (int.from_bytes(payload[213:221], byteorder='little'), fee_mint),
            (int.from_bytes(payload[255:263], byteorder='little'), fee_mint),
        ):
            if raw_amount > 0:
                fees.append((mint, raw_amount))

        if (
            event_discriminator == SWAP_TOB_V2_CPI_EVENT2_DISCRIMINATOR and
            len(payload) >= 336 and
            (trim_amount := int.from_bytes(payload[296:304], byteorder='little')) > 0
        ):
            fees.append((destination_mint, trim_amount))

    return fees


def _apply_native_wsol_asset(event: SolanaEvent, effective_asset: Asset) -> None:
    if event.asset == effective_asset:
        return

    event.asset = effective_asset
    if event.notes is not None:
        event.notes = event.notes.replace(' WSOL', ' SOL')


class OkxDecoder(SolanaDecoderInterface):

    def _get_native_wsol_atas(
            self,
            context: SolanaDecoderContext,
            route_instruction: SolanaInstruction,
    ) -> tuple[set[SolanaAddress], set[SolanaAddress]]:
        """Find tracked WSOL ATAs involved in this swap that are wrapped/unwrapped from/to SOL.

        Returns `(native_wsol_atas, router_closed_wsol_atas)`, where `router_closed_wsol_atas`
        holds ATAs closed by the router to an intermediary (e.g. `acc_close_flag=true`).
        """
        swap_token_accounts = (
            set(route_instruction.accounts[1:3])
            if len(route_instruction.accounts) >= 3 else set()
        )
        native_wsol_atas: set[SolanaAddress] = set()
        router_closed_wsol_atas: set[SolanaAddress] = set()
        for instruction in context.transaction.instructions:
            if instruction.program_id != SPL_TOKEN_PROGRAM:
                continue

            if (
                instruction.data == SPL_TOKEN_SYNC_NATIVE_DISCRIMINATOR and
                len(instruction.accounts) == 1
            ):
                wsol_ata = instruction.accounts[0]
                if (
                    wsol_ata in swap_token_accounts and
                    (ata_data := context.ata_data.get(wsol_ata)) is not None and
                    self.base.is_tracked(ata_data[0]) and
                    ata_data[1] in A_WSOL.identifier
                ):
                    native_wsol_atas.add(wsol_ata)
            elif (
                instruction.data == SPL_TOKEN_CLOSE_ACCOUNT_DISCRIMINATOR and
                len(instruction.accounts) == 3
            ):
                wsol_ata = instruction.accounts[0]
                if (
                    wsol_ata in swap_token_accounts and
                    (ata_data := context.ata_data.get(wsol_ata)) is not None and
                    self.base.is_tracked(ata_data[0]) and
                    ata_data[1] in A_WSOL.identifier
                ):
                    native_wsol_atas.add(wsol_ata)
                    if (
                        instruction.parent_execution_index == route_instruction.execution_index and
                        instruction.accounts[1] != ata_data[0]
                    ):
                        router_closed_wsol_atas.add(wsol_ata)

        return native_wsol_atas, router_closed_wsol_atas

    def _build_remaining_fees(
            self,
            event_discriminator: bytes,
            payload: bytes,
            source_mint: SolanaAddress,
            destination_mint: SolanaAddress,
    ) -> list[tuple[set[Asset], FVal]]:
        """Normalize raw CPI event fees into `(accepted_assets, amount)` pairs."""
        remaining_fees: list[tuple[set[Asset], FVal]] = []
        for fee_mint, raw_fee_amount in _parse_cpi_event_fees(
            event_discriminator=event_discriminator,
            payload=payload,
            source_mint=source_mint,
            destination_mint=destination_mint,
        ):
            fee_token = self.base.get_or_create_solana_token(address=fee_mint)
            fee_amount = token_normalized_value(token=fee_token, token_amount=raw_fee_amount)
            fee_assets: set[Asset] = (
                {A_WSOL, A_SOL} if fee_mint in A_WSOL.identifier else {fee_token}
            )
            remaining_fees.append((fee_assets, fee_amount))

        return remaining_fees

    def _is_destination_asset(
            self,
            asset: Asset,
            destination_mint: SolanaAddress,
            has_native_wsol: bool,
    ) -> bool:
        if destination_mint in asset.identifier:
            return True
        return has_native_wsol and asset == A_SOL and destination_mint in A_WSOL.identifier

    def decode_swap(self, context: SolanaDecoderContext) -> SolanaDecodingOutput:
        """Decode swaps routed through the OKX DEX Router (v1 and v2 programs)."""
        if (
            (event_data := get_data_for_discriminator(context.instruction.data, ANCHOR_EVENT_DISCRIMINATOR)) is None or  # noqa: E501
            (event_discriminator := event_data[:ANCHOR_DISCRIMINATOR_LEN]) not in SUMMARY_SWAP_CPI_EVENT_DISCRIMINATORS  # noqa: E501
        ):
            return DEFAULT_SOLANA_DECODING_OUTPUT

        payload = event_data[ANCHOR_DISCRIMINATOR_LEN:]
        if len(payload) < COMMON_SWAP_CPI_EVENT_HEADER_LEN:
            log.error(
                'OKX swap CPI event payload too short (%s bytes) in transaction %s',
                len(payload),
                context.transaction,
            )
            return DEFAULT_SOLANA_DECODING_OUTPUT

        for instruction in context.transaction.instructions:
            if (
                instruction.parent_execution_index is None and
                instruction.execution_index == context.instruction.parent_execution_index and
                instruction.program_id == context.instruction.program_id
            ):
                route_instruction = instruction
                break
        else:
            log.error('Failed to find OKX route instruction in transaction %s', context.transaction)  # noqa: E501
            return DEFAULT_SOLANA_DECODING_OUTPUT

        source_mint = bytes_to_solana_address(payload[8:40])
        destination_mint = bytes_to_solana_address(payload[40:72])
        raw_destination_change = int.from_bytes(payload[152:160], byteorder='little')

        remaining_fees = self._build_remaining_fees(
            event_discriminator=event_discriminator,
            payload=payload,
            source_mint=source_mint,
            destination_mint=destination_mint,
        )
        native_wsol_atas, router_closed_wsol_atas = self._get_native_wsol_atas(
            context=context,
            route_instruction=route_instruction,
        )

        unrelated_events: list[SolanaEvent] = []
        route_events: list[tuple[SolanaEvent, SolanaInstruction]] = []
        for event in context.decoded_events:
            if (
                (event_instruction := self.base.event_instructions.get(event)) is None or
                event_instruction.parent_execution_index != route_instruction.execution_index
            ):
                unrelated_events.append(event)
            else:
                route_events.append((event, event_instruction))

        dropped_router_closed_rent = ZERO
        if len(native_wsol_atas) != 0:
            filtered_unrelated: list[SolanaEvent] = []
            for event in unrelated_events:
                if (
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset == A_SOL and
                    event.address in native_wsol_atas
                ):
                    if event.address in router_closed_wsol_atas:
                        dropped_router_closed_rent += event.amount
                    continue

                filtered_unrelated.append(event)
            unrelated_events = filtered_unrelated

        expected_destination_sol = ZERO
        if len(router_closed_wsol_atas) > 0 and destination_mint in A_WSOL.identifier:
            expected_destination_sol = token_normalized_value(
                token=A_WSOL.resolve_to_solana_token(),
                token_amount=raw_destination_change,
            )

        other_items: list[tuple[SolanaEvent, Asset]] = []
        fee_items: list[tuple[SolanaEvent, Asset]] = []
        out_by_asset: dict[Asset, tuple[SolanaEvent, FVal]] = {}
        in_by_asset: dict[Asset, tuple[SolanaEvent, FVal]] = {}
        for event, event_instruction in route_events:
            if (
                event.asset == A_WSOL and
                event.event_type == HistoryEventType.RECEIVE and
                any(ata in event_instruction.accounts for ata in router_closed_wsol_atas)
            ):
                continue

            effective_asset: Asset = (
                A_SOL if (
                    event.asset == A_WSOL and
                    any(ata in event_instruction.accounts for ata in native_wsol_atas)
                ) else event.asset
            )

            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE
            ):
                matched_fee_idx = next(
                    (
                        idx for idx, (fee_assets, fee_amount) in enumerate(remaining_fees)
                        if effective_asset in fee_assets and event.amount == fee_amount
                    ),
                    None,
                )
                if matched_fee_idx is not None:
                    remaining_fees.pop(matched_fee_idx)
                    fee_items.append((event, effective_asset))
                    continue

                if (
                    self._is_destination_asset(
                        asset=effective_asset,
                        destination_mint=destination_mint,
                        has_native_wsol=len(native_wsol_atas) > 0,
                    ) and
                    source_mint not in effective_asset.identifier and
                    not (effective_asset == A_SOL and source_mint in A_WSOL.identifier)
                ):
                    other_items.append((event, effective_asset))
                    continue

                if (existing := out_by_asset.get(effective_asset)) is not None:
                    out_by_asset[effective_asset] = (existing[0], existing[1] + event.amount)
                else:
                    out_by_asset[effective_asset] = (event, event.amount)
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE
            ):
                effective_amount = (
                    expected_destination_sol if (
                        len(router_closed_wsol_atas) > 0 and
                        effective_asset == A_SOL and
                        dropped_router_closed_rent > ZERO and
                        event.amount == expected_destination_sol + dropped_router_closed_rent
                    ) else event.amount
                )
                if (existing := in_by_asset.get(effective_asset)) is not None:
                    in_by_asset[effective_asset] = (existing[0], existing[1] + effective_amount)
                else:
                    in_by_asset[effective_asset] = (event, effective_amount)
            else:
                other_items.append((event, effective_asset))

        for asset in list(in_by_asset.keys()):
            if (out_entry := out_by_asset.get(asset)) is None:
                continue

            in_event, in_amount = in_by_asset[asset]
            out_event, out_amount = out_entry
            if in_amount == out_amount:
                del in_by_asset[asset]
                del out_by_asset[asset]
            elif out_amount > in_amount:
                out_by_asset[asset] = (out_event, out_amount - in_amount)
                del in_by_asset[asset]
            else:
                in_by_asset[asset] = (in_event, in_amount - out_amount)
                del out_by_asset[asset]

        out_items = list(out_by_asset.items())
        in_items: list[tuple[Asset, tuple[SolanaEvent, FVal]]] = []
        slippage_items: list[tuple[Asset, tuple[SolanaEvent, FVal]]] = []
        has_native_wsol = len(native_wsol_atas) > 0
        for asset, entry in in_by_asset.items():
            if self._is_destination_asset(
                asset=asset,
                destination_mint=destination_mint,
                has_native_wsol=has_native_wsol,
            ):
                in_items.append((asset, entry))
            else:
                slippage_items.append((asset, entry))

        if len(out_items) == 0 or len(in_items) == 0:
            log.error(
                'Failed to find both out and in events for OKX swap transaction %s',
                context.transaction.signature,
            )
            return DEFAULT_SOLANA_DECODING_OUTPUT

        out_events: list[SolanaEvent] = []
        in_events: list[SolanaEvent] = []
        for items, final_list, sub_type, notes_template in (
            (out_items, out_events, HistoryEventSubType.SPEND, 'Swap {amount} {asset} in OKX'),
            (in_items, in_events, HistoryEventSubType.RECEIVE, 'Receive {amount} {asset} as the result of a swap in OKX'),  # noqa: E501
        ):
            for asset, (trade_event, amount) in items:
                _apply_native_wsol_asset(trade_event, asset)
                trade_event.amount = amount
                trade_event.counterparty = CPT_OKX
                trade_event.event_type = HistoryEventType.TRADE
                trade_event.event_subtype = sub_type
                trade_event.notes = notes_template.format(
                    amount=amount,
                    asset=asset.resolve_to_asset_with_symbol().symbol,
                )
                final_list.append(trade_event)

        slippage_events: list[SolanaEvent] = []
        for asset, (slippage_event, amount) in slippage_items:
            _apply_native_wsol_asset(slippage_event, asset)
            slippage_event.amount = amount
            slippage_event.counterparty = CPT_OKX
            slippage_event.event_type = HistoryEventType.RECEIVE
            slippage_event.event_subtype = HistoryEventSubType.NONE
            slippage_event.notes = f'Receive {amount} {asset.resolve_to_asset_with_symbol().symbol} due to positive slippage in an OKX swap'  # noqa: E501
            slippage_events.append(slippage_event)

        fee_events: list[SolanaEvent] = []
        for fee_event, asset in fee_items:
            _apply_native_wsol_asset(fee_event, asset)
            fee_event.event_type = HistoryEventType.TRADE
            fee_event.event_subtype = HistoryEventSubType.FEE
            fee_event.counterparty = CPT_OKX
            fee_event.notes = f'Spend {fee_event.amount} {asset.resolve_to_asset_with_symbol().symbol} as OKX swap fee'  # noqa: E501
            fee_events.append(fee_event)

        other_events: list[SolanaEvent] = []
        for other_event, asset in other_items:
            _apply_native_wsol_asset(other_event, asset)
            other_events.append(other_event)

        filtered_events = (
            out_events + in_events + fee_events + slippage_events + other_events
        )
        context.decoded_events[:] = unrelated_events + filtered_events
        maybe_reshuffle_events(ordered_events=filtered_events, events_list=context.decoded_events)
        return SolanaDecodingOutput(process_swaps=True)

    def addresses_to_decoders(self) -> dict[SolanaAddress, tuple[Any, ...]]:
        return {
            OKX_DEX_ROUTER_V2_PROGRAM: (self.decode_swap,),
            OKX_DEX_ROUTER_V1_PROGRAM: (self.decode_swap,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_OKX,
            label='OKX',
            image='okx.svg',
        ),)
