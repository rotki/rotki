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
from rotkehlchen.errors.misc import NotSPLConformant
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
    from rotkehlchen.assets.asset import Asset, SolanaToken
    from rotkehlchen.chain.solana.rpc import Signature
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
        tx_signature: Signature,
) -> list[tuple[SolanaAddress, int]]:
    """Extract non-zero (fee_mint, raw_fee_amount) pairs from fee-bearing OKX CPI events."""
    fees: list[tuple[SolanaAddress, int]] = []
    if event_discriminator in (
        SWAP_WITH_FEES_CPI_EVENT2_DISCRIMINATOR,
        SWAP_WITH_FEES_CPI_EVENT_DISCRIMINATOR,
        SWAP_WITH_FEES_CPI_EVENT_ENHANCED2_DISCRIMINATOR,
    ):
        if len(payload) < 288:
            log.warning(
                'OKX fee CPI event payload too short (%s bytes, expected >= 288) in transaction %s',  # noqa: E501
                len(payload),
                tx_signature,
            )
            return fees

        fee_mint = source_mint if payload[160] != 0 else destination_mint
        for raw_amount, mint in (
            (int.from_bytes(payload[165:173], byteorder='little'), fee_mint),
            (int.from_bytes(payload[207:215], byteorder='little'), fee_mint),
            (int.from_bytes(payload[248:256], byteorder='little'), destination_mint),
        ):
            if raw_amount > 0:
                fees.append((mint, raw_amount))

        if event_discriminator == SWAP_WITH_FEES_CPI_EVENT_ENHANCED2_DISCRIMINATOR:
            if len(payload) < 330:
                log.warning(
                    'OKX enhanced fee CPI event payload too short (%s bytes, expected >= 330) in transaction %s',  # noqa: E501
                    len(payload),
                    tx_signature,
                )
            elif (charge_amount := int.from_bytes(payload[290:298], byteorder='little')) > 0:
                fees.append((fee_mint, charge_amount))
    elif event_discriminator in (
        SWAP_TOB_V2_CPI_EVENT2_DISCRIMINATOR,
        SWAP_TOC_V2_CPI_EVENT2_DISCRIMINATOR,
    ):
        if len(payload) < 295:
            log.warning(
                'OKX ToB/ToC fee CPI event payload too short (%s bytes, expected >= 295) in transaction %s',  # noqa: E501
                len(payload),
                tx_signature,
            )
            return fees

        fee_mint = source_mint if payload[160] != 0 else destination_mint
        for raw_amount, mint in (
            (int.from_bytes(payload[169:177], byteorder='little'), fee_mint),
            (int.from_bytes(payload[213:221], byteorder='little'), fee_mint),
            (int.from_bytes(payload[255:263], byteorder='little'), fee_mint),
        ):
            if raw_amount > 0:
                fees.append((mint, raw_amount))

        if event_discriminator == SWAP_TOB_V2_CPI_EVENT2_DISCRIMINATOR:
            if len(payload) < 336:
                log.warning(
                    'OKX ToB v2 CPI event payload too short (%s bytes, expected >= 336) in transaction %s',  # noqa: E501
                    len(payload),
                    tx_signature,
                )
            elif (trim_amount := int.from_bytes(payload[296:304], byteorder='little')) > 0:
                fees.append((destination_mint, trim_amount))

    return fees


def _matches_mint(asset: Asset, mint: SolanaAddress, has_native_wsol: bool) -> bool:
    return mint in asset.identifier or (
        has_native_wsol and asset == A_SOL and mint in A_WSOL.identifier
    )


def _apply_native_wsol_asset(event: SolanaEvent, effective_asset: Asset) -> None:
    if event.asset == effective_asset:
        return

    event.asset = effective_asset
    if event.notes is not None:
        event.notes = event.notes.replace(' WSOL', ' SOL')


class OkxDecoder(SolanaDecoderInterface):

    @staticmethod
    def _find_route_instruction(context: SolanaDecoderContext) -> SolanaInstruction | None:
        for instruction in context.transaction.instructions:
            if (
                instruction.parent_execution_index is None and
                instruction.execution_index == context.instruction.parent_execution_index and
                instruction.program_id == context.instruction.program_id
            ):
                return instruction

        return None

    def _get_native_wsol_atas(
            self,
            context: SolanaDecoderContext,
            route_instruction: SolanaInstruction,
    ) -> tuple[set[SolanaAddress], set[SolanaAddress]]:
        """Find tracked WSOL ATAs involved in this swap that are wrapped/unwrapped from/to SOL.

        Returns `(native_wsol_atas, router_closed_wsol_atas)`, where `router_closed_wsol_atas`
        holds ATAs closed by the router to an intermediary (e.g. `acc_close_flag=true`).
        """
        if len(route_instruction.accounts) < 3:
            return set(), set()

        swap_token_accounts = set(route_instruction.accounts[1:3])
        native_wsol_atas: set[SolanaAddress] = set()
        router_closed_wsol_atas: set[SolanaAddress] = set()
        for instruction in context.transaction.instructions:
            if instruction.program_id != SPL_TOKEN_PROGRAM:
                continue

            is_sync_native = (
                instruction.data == SPL_TOKEN_SYNC_NATIVE_DISCRIMINATOR and
                len(instruction.accounts) == 1
            )
            is_close_account = (
                instruction.data == SPL_TOKEN_CLOSE_ACCOUNT_DISCRIMINATOR and
                len(instruction.accounts) == 3
            )
            if not (is_sync_native or is_close_account):
                continue

            wsol_ata = instruction.accounts[0]
            if (
                wsol_ata not in swap_token_accounts or
                (ata_data := context.ata_data.get(wsol_ata)) is None or
                not self.base.is_tracked(ata_data[0]) or
                ata_data[1] not in A_WSOL.identifier
            ):
                continue

            native_wsol_atas.add(wsol_ata)
            if (
                is_close_account and
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
            tx_signature: Signature,
    ) -> list[tuple[set[Asset], FVal]]:
        """Normalize raw CPI event fees into `(accepted_assets, amount)` pairs."""
        remaining_fees: list[tuple[set[Asset], FVal]] = []
        resolved_tokens: dict[SolanaAddress, SolanaToken] = {}
        failed_mints: set[SolanaAddress] = set()
        for fee_mint, raw_fee_amount in _parse_cpi_event_fees(
            event_discriminator=event_discriminator,
            payload=payload,
            source_mint=source_mint,
            destination_mint=destination_mint,
            tx_signature=tx_signature,
        ):
            if fee_mint in A_WSOL.identifier:
                fee_token = A_WSOL.resolve_to_solana_token()
                fee_assets: set[Asset] = {A_WSOL, A_SOL}
            elif fee_mint in failed_mints:
                continue
            else:
                if (cached_token := resolved_tokens.get(fee_mint)) is None:
                    try:
                        cached_token = self.base.get_or_create_solana_token(address=fee_mint)
                    except NotSPLConformant as e:
                        log.error(
                            'Failed to load OKX swap fee SPL token %s in transaction %s due to %s',
                            fee_mint,
                            tx_signature,
                            e,
                        )
                        failed_mints.add(fee_mint)
                        continue
                    resolved_tokens[fee_mint] = cached_token
                fee_token = cached_token
                fee_assets = {fee_token}

            fee_amount = token_normalized_value(token=fee_token, token_amount=raw_fee_amount)
            remaining_fees.append((fee_assets, fee_amount))

        return remaining_fees

    def _partition_events(
            self,
            context: SolanaDecoderContext,
            route_instruction: SolanaInstruction,
            native_wsol_atas: set[SolanaAddress],
            router_closed_wsol_atas: set[SolanaAddress],
    ) -> tuple[
        list[SolanaEvent],
        list[tuple[SolanaEvent, SolanaInstruction]],
        set[SolanaEvent],
        FVal,
    ]:
        """Partition decoded events into unrelated and route-scoped events.

        Native SOL transfers funding a wrapped WSOL ATA before the route instruction are
        dropped immediately when user-closed, or tracked in `router_closed_rent_events` so
        they are only dropped if the unwrapped SOL receive reflects the refunded rent.
        """
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

        router_closed_rent_events: set[SolanaEvent] = set()
        dropped_router_closed_rent = ZERO
        if len(native_wsol_atas) != 0:
            filtered_unrelated: list[SolanaEvent] = []
            for event in unrelated_events:
                if (
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset == A_SOL and
                    event.address in native_wsol_atas and
                    (event_instruction := self.base.event_instructions.get(event)) is not None and
                    event_instruction.execution_index < route_instruction.execution_index
                ):
                    if event.address in router_closed_wsol_atas:
                        router_closed_rent_events.add(event)
                        dropped_router_closed_rent += event.amount
                        filtered_unrelated.append(event)
                    continue

                filtered_unrelated.append(event)
            unrelated_events = filtered_unrelated

        return (
            unrelated_events,
            route_events,
            router_closed_rent_events,
            dropped_router_closed_rent,
        )

    @staticmethod
    def _classify_route_events(
            route_events: list[tuple[SolanaEvent, SolanaInstruction]],
            remaining_fees: list[tuple[set[Asset], FVal]],
            native_wsol_atas: set[SolanaAddress],
            router_closed_wsol_atas: set[SolanaAddress],
            source_mint: SolanaAddress,
            destination_mint: SolanaAddress,
            expected_destination_sol: FVal,
            dropped_router_closed_rent: FVal,
    ) -> tuple[
        dict[Asset, tuple[SolanaEvent, FVal]],
        dict[Asset, tuple[SolanaEvent, FVal]],
        list[tuple[SolanaEvent, Asset]],
        list[tuple[SolanaEvent, Asset]],
        bool,
    ]:
        has_native_wsol = len(native_wsol_atas) > 0
        has_route_native_sol_receive = any(
            e.asset == A_SOL and
            e.event_type == HistoryEventType.RECEIVE and
            e.event_subtype == HistoryEventSubType.NONE
            for e, _ in route_events
        )
        other_items: list[tuple[SolanaEvent, Asset]] = []
        fee_items: list[tuple[SolanaEvent, Asset]] = []
        out_by_asset: dict[Asset, tuple[SolanaEvent, FVal]] = {}
        in_by_asset: dict[Asset, tuple[SolanaEvent, FVal]] = {}
        rent_adjusted = False
        for event, event_instruction in route_events:
            if (
                has_route_native_sol_receive and
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
                    _matches_mint(effective_asset, destination_mint, has_native_wsol) and
                    not _matches_mint(effective_asset, source_mint, has_native_wsol)
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
                if (
                    not rent_adjusted and
                    len(router_closed_wsol_atas) > 0 and
                    effective_asset == A_SOL and
                    dropped_router_closed_rent > ZERO and
                    event.amount == expected_destination_sol + dropped_router_closed_rent
                ):
                    effective_amount = expected_destination_sol
                    rent_adjusted = True
                else:
                    effective_amount = event.amount

                if (existing := in_by_asset.get(effective_asset)) is not None:
                    in_by_asset[effective_asset] = (existing[0], existing[1] + effective_amount)
                else:
                    in_by_asset[effective_asset] = (event, effective_amount)
            else:
                other_items.append((event, effective_asset))

        return out_by_asset, in_by_asset, fee_items, other_items, rent_adjusted

    @staticmethod
    def _net_same_asset_events(
            in_by_asset: dict[Asset, tuple[SolanaEvent, FVal]],
            out_by_asset: dict[Asset, tuple[SolanaEvent, FVal]],
    ) -> None:
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

    @staticmethod
    def _finalize_swap_events(
            out_items: list[tuple[Asset, tuple[SolanaEvent, FVal]]],
            in_items: list[tuple[Asset, tuple[SolanaEvent, FVal]]],
            fee_items: list[tuple[SolanaEvent, Asset]],
            slippage_items: list[tuple[Asset, tuple[SolanaEvent, FVal]]],
            other_items: list[tuple[SolanaEvent, Asset]],
    ) -> list[SolanaEvent]:
        out_events: list[SolanaEvent] = []
        in_events: list[SolanaEvent] = []
        for items, final_list, sub_type, notes_template in (
            (out_items, out_events, HistoryEventSubType.SPEND, 'Swap {amount} {asset} in OKX'),
            (in_items, in_events, HistoryEventSubType.RECEIVE, 'Receive {amount} {asset} as the result of a swap in OKX'),  # noqa: E501
        ):
            for asset, (trade_event, amount) in items:
                trade_event.asset = asset
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
            slippage_event.asset = asset
            slippage_event.amount = amount
            slippage_event.counterparty = CPT_OKX
            slippage_event.event_type = HistoryEventType.RECEIVE
            slippage_event.event_subtype = HistoryEventSubType.NONE
            slippage_event.notes = f'Receive {amount} {asset.resolve_to_asset_with_symbol().symbol} due to positive slippage in an OKX swap'  # noqa: E501
            slippage_events.append(slippage_event)

        fee_events: list[SolanaEvent] = []
        for fee_event, asset in fee_items:
            fee_event.asset = asset
            fee_event.event_type = HistoryEventType.TRADE
            fee_event.event_subtype = HistoryEventSubType.FEE
            fee_event.counterparty = CPT_OKX
            fee_event.notes = f'Spend {fee_event.amount} {asset.resolve_to_asset_with_symbol().symbol} as OKX swap fee'  # noqa: E501
            fee_events.append(fee_event)

        other_events: list[SolanaEvent] = []
        for other_event, asset in other_items:
            _apply_native_wsol_asset(other_event, asset)
            other_events.append(other_event)

        return out_events + in_events + fee_events + slippage_events + other_events

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

        if (route_instruction := self._find_route_instruction(context)) is None:
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
            tx_signature=context.transaction.signature,
        )
        native_wsol_atas, router_closed_wsol_atas = self._get_native_wsol_atas(
            context=context,
            route_instruction=route_instruction,
        )
        unrelated_events, route_events, router_closed_rent_events, dropped_router_closed_rent = (
            self._partition_events(
                context=context,
                route_instruction=route_instruction,
                native_wsol_atas=native_wsol_atas,
                router_closed_wsol_atas=router_closed_wsol_atas,
            )
        )

        expected_destination_sol = ZERO
        if len(router_closed_wsol_atas) > 0 and destination_mint in A_WSOL.identifier:
            expected_destination_sol = token_normalized_value(
                token=A_WSOL.resolve_to_solana_token(),
                token_amount=raw_destination_change,
            )

        out_by_asset, in_by_asset, fee_items, other_items, rent_adjusted = (
            self._classify_route_events(
                route_events=route_events,
                remaining_fees=remaining_fees,
                native_wsol_atas=native_wsol_atas,
                router_closed_wsol_atas=router_closed_wsol_atas,
                source_mint=source_mint,
                destination_mint=destination_mint,
                expected_destination_sol=expected_destination_sol,
                dropped_router_closed_rent=dropped_router_closed_rent,
            )
        )
        self._net_same_asset_events(in_by_asset=in_by_asset, out_by_asset=out_by_asset)

        out_items = list(out_by_asset.items())
        in_items: list[tuple[Asset, tuple[SolanaEvent, FVal]]] = []
        slippage_items: list[tuple[Asset, tuple[SolanaEvent, FVal]]] = []
        has_native_wsol = len(native_wsol_atas) > 0
        for asset, entry in in_by_asset.items():
            if _matches_mint(asset, destination_mint, has_native_wsol):
                in_items.append((asset, entry))
            else:
                slippage_items.append((asset, entry))

        if len(out_items) == 0 or len(in_items) == 0:
            log.error(
                'Failed to find both out and in events for OKX swap transaction %s',
                context.transaction.signature,
            )
            return DEFAULT_SOLANA_DECODING_OUTPUT

        if rent_adjusted and len(router_closed_rent_events) > 0:
            unrelated_events = [e for e in unrelated_events if e not in router_closed_rent_events]

        filtered_events = self._finalize_swap_events(
            out_items=out_items,
            in_items=in_items,
            fee_items=fee_items,
            slippage_items=slippage_items,
            other_items=other_items,
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
