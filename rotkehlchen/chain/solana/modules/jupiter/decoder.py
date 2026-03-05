import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.utils import token_normalized_value
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.solana.decoding.constants import (
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
from rotkehlchen.chain.solana.decoding.utils import get_data_for_discriminator, match_discriminator
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_SOL, A_WSOL
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import SolanaAddress

from .constants import (
    CPT_JUPITER,
    FILL_DISCRIMINATOR,
    JUPITER_AGGREGATOR_PROGRAM_V6,
    JUPITER_LEND_BORROW_PROGRAM,
    JUPITER_LEND_EARN_PROGRAM,
    JUPITER_LEND_LIQUIDITY_PROGRAM,
    JUPITER_RFQ_ORDER_ENGINE_PROGRAM,
    LEND_DEPOSIT_DISCRIMINATOR,
    LEND_INIT_POSITION_DISCRIMINATOR,
    LEND_OPERATE_DISCRIMINATOR,
    LEND_WITHDRAW_DISCRIMINATOR,
    ROUTE_DISCRIMINATORS_TO_MINT_IDX,
    SWAP_EVENT_DISCRIMINATOR,
    SWAPS_EVENT_DISCRIMINATOR,
)

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset, AssetWithSymbol, SolanaToken
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
            token=(input_token := self.base.get_or_create_solana_token(
                address=context.instruction.accounts[6],
            )),
            token_amount=int.from_bytes(context.instruction.data[8:16], byteorder='little'),
        )
        output_amount = token_normalized_value(
            token=(output_token := self.base.get_or_create_solana_token(
                address=context.instruction.accounts[8],
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

    def decode_earn_deposit_withdraw(
            self,
            context: SolanaDecoderContext,
            is_deposit: bool,
    ) -> SolanaDecodingOutput:
        if len(context.instruction.accounts) < 12:
            log.error(
                'Encountered Jupiter earn deposit instruction with insufficient number of '
                f'accounts. Expected at least 12, only got: {len(context.instruction.accounts)}',
            )
            return DEFAULT_SOLANA_DECODING_OUTPUT

        if is_deposit:
            mint_address = context.instruction.accounts[3]
            liquidity_address = context.instruction.accounts[11]
            expected_underlying_event_type = HistoryEventType.SPEND
            new_underlying_event_type = HistoryEventType.DEPOSIT
            new_underlying_event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
            expected_vault_event_type = HistoryEventType.RECEIVE
            new_vault_event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
            underlying_notes = 'Deposit {amount} {asset} to Jupiter vault'
            vault_notes = 'Receive {amount} {asset} after a deposit in Jupiter'
        else:
            mint_address = context.instruction.accounts[5]
            liquidity_address = context.instruction.accounts[12]
            expected_underlying_event_type = HistoryEventType.RECEIVE
            new_underlying_event_type = HistoryEventType.WITHDRAWAL
            new_underlying_event_subtype = HistoryEventSubType.REDEEM_WRAPPED
            expected_vault_event_type = HistoryEventType.SPEND
            new_vault_event_subtype = HistoryEventSubType.RETURN_WRAPPED
            underlying_notes = 'Withdraw {amount} {asset} from Jupiter vault'
            vault_notes = 'Return {amount} {asset} to Jupiter'

        underlying_token = self.base.get_or_create_solana_token(address=mint_address)
        vault_token = self.base.get_or_create_solana_token(
            address=context.instruction.accounts[6],
        )
        for event in context.decoded_events:
            if (
                event.event_type == expected_underlying_event_type and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == underlying_token and
                event.address == liquidity_address
            ):
                event.event_type = new_underlying_event_type
                event.event_subtype = new_underlying_event_subtype
                event.counterparty = CPT_JUPITER
                event.notes = underlying_notes.format(
                    amount=event.amount,
                    asset=event.asset.resolve_to_asset_with_symbol().symbol,
                )
            elif (
                event.event_type == expected_vault_event_type and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == vault_token and
                event.address is None
            ):
                event.event_subtype = new_vault_event_subtype
                event.counterparty = CPT_JUPITER
                event.notes = vault_notes.format(
                    amount=event.amount,
                    asset=event.asset.resolve_to_asset_with_symbol().symbol,
                )

        return DEFAULT_SOLANA_DECODING_OUTPUT

    def decode_lend_earn_events(self, context: SolanaDecoderContext) -> SolanaDecodingOutput:
        if match_discriminator(context.instruction.data, LEND_DEPOSIT_DISCRIMINATOR):
            return self.decode_earn_deposit_withdraw(context, is_deposit=True)
        if match_discriminator(context.instruction.data, LEND_WITHDRAW_DISCRIMINATOR):
            return self.decode_earn_deposit_withdraw(context, is_deposit=False)

        return DEFAULT_SOLANA_DECODING_OUTPUT

    def decode_lend_init_position(self, context: SolanaDecoderContext) -> SolanaDecodingOutput:
        """Decode a Jupiter lend init position instruction."""
        if (
            not match_discriminator(context.instruction.data, LEND_INIT_POSITION_DISCRIMINATOR) or
            len(context.instruction.accounts) < 7  # there are more, but we don't use them here.
        ):
            return DEFAULT_SOLANA_DECODING_OUTPUT

        metadata_address = context.instruction.accounts[6]
        vault_id = int.from_bytes(context.instruction.data[8:10], byteorder='little')
        vault_symbol = f'jv{vault_id}'
        mint_event = fee_event = None
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.address is None and
                event.amount == ONE and
                'solana/nft:' in event.asset.identifier and
                event.asset.resolve_to_asset_with_symbol().symbol == vault_symbol
            ):
                event.event_type = HistoryEventType.MINT
                event.event_subtype = HistoryEventSubType.NFT
                event.counterparty = CPT_JUPITER
                event.notes = f'Create Jupiter position with vault id {vault_id}'
                mint_event = event
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.address == metadata_address and
                event.asset == A_SOL
            ):  # When initializing a position, some SOL is sent when creating the metadata account
                # so decoding this as a fee, since it is never returned to the user.
                event.event_subtype = HistoryEventSubType.FEE
                event.counterparty = CPT_JUPITER
                event.notes = f'Spend {event.amount} SOL as Jupiter position initialization fee'
                fee_event = event

        if mint_event is None or fee_event is None:
            log.error(
                f'Failed to find both mint and fee events for '
                f'Jupiter lend init position transaction {context.transaction.signature}',
            )
            return DEFAULT_SOLANA_DECODING_OUTPUT

        maybe_reshuffle_events(
            ordered_events=[mint_event, fee_event],
            events_list=context.decoded_events,
        )
        return DEFAULT_SOLANA_DECODING_OUTPUT

    def _maybe_get_wsol_ata(
            self,
            operation_token: 'SolanaToken',
            context: SolanaDecoderContext,
            is_out_operation: bool,
    ) -> SolanaAddress | None:
        """Find the WSOL ata from the SPL_TOKEN_PROGRAM SyncNative or CloseAccount instructions
        if the current operation token is WSOL. Used to detect wrap/unwrap of SOL.
        """
        if operation_token != A_WSOL:
            return None

        for instruction in context.transaction.instructions:
            if instruction.program_id != SPL_TOKEN_PROGRAM:
                continue

            if (
                instruction.data == SPL_TOKEN_SYNC_NATIVE_DISCRIMINATOR and
                len(instruction.accounts) == 1 and
                (ata_data := context.ata_data.get(wsol_ata_address := instruction.accounts[0])) is not None and  # noqa: E501
                self.base.is_tracked(ata_data[0]) and
                ata_data[1] in A_WSOL.identifier and
                is_out_operation
            ):  # This is an OUT of SOL that gets wrapped into WSOL.
                return wsol_ata_address
            elif (
                instruction.data == SPL_TOKEN_CLOSE_ACCOUNT_DISCRIMINATOR and
                len(instruction.accounts) == 3 and
                (ata_data := context.ata_data.get(wsol_ata_address := instruction.accounts[0])) is not None and  # noqa: E501
                self.base.is_tracked(ata_data[0]) and
                ata_data[1] in A_WSOL.identifier and
                not is_out_operation
            ):  # This is an IN of SOL from unwrapping WSOL
                return wsol_ata_address

        return None

    def decode_lend_collateral_deposit_withdraw(
            self,
            context: SolanaDecoderContext,
            collateral_token: 'SolanaToken',
            raw_collateral_amount: int,
            liquidity_address: SolanaAddress,
    ) -> None:
        """Decode a Jupiter lend collateral deposit/withdraw event.

        Handles native/wrapped native tokens as follows:
        - Deposits: we get a spend of both SOL and WSOL, so remove the WSOL event.
        - Withdrawals: we only get a receive of WSOL, so change its asset to SOL.
        """
        new_collateral = token_normalized_value(
            token=collateral_token,
            token_amount=abs(raw_collateral_amount),
        )
        wsol_ata_address = self._maybe_get_wsol_ata(
            operation_token=collateral_token,
            context=context,
            is_out_operation=(is_deposit := raw_collateral_amount > 0),
        )
        expected_token: AssetWithSymbol = collateral_token
        new_token: AssetWithSymbol = collateral_token
        expected_address = liquidity_address
        if is_deposit:
            expected_collateral_event_type = HistoryEventType.SPEND
            new_collateral_event_type = HistoryEventType.DEPOSIT
            new_collateral_event_subtype = HistoryEventSubType.DEPOSIT_ASSET
            new_collateral_notes = f'Deposit {new_collateral} {{asset}} as collateral to Jupiter'
            if wsol_ata_address is not None:
                expected_token = new_token = A_SOL.resolve_to_asset_with_symbol()
                expected_address = wsol_ata_address
        else:
            expected_collateral_event_type = HistoryEventType.RECEIVE
            new_collateral_event_type = HistoryEventType.WITHDRAWAL
            new_collateral_event_subtype = HistoryEventSubType.REMOVE_ASSET
            new_collateral_notes = f'Withdraw {new_collateral} {{asset}} as collateral from Jupiter'  # noqa: E501
            if wsol_ata_address is not None:
                expected_token = collateral_token
                new_token = A_SOL.resolve_to_asset_with_symbol()
                expected_address = liquidity_address

        event_to_remove = None
        for event in context.decoded_events:
            if (
                event.event_type == expected_collateral_event_type and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == expected_token and
                event.amount == new_collateral and
                event.address == expected_address
            ):
                event.event_type = new_collateral_event_type
                event.event_subtype = new_collateral_event_subtype
                event.counterparty = CPT_JUPITER
                event.address = liquidity_address
                event.asset = new_token
                event.notes = new_collateral_notes.format(asset=new_token.symbol)
            elif (
                wsol_ata_address is not None and
                expected_collateral_event_type == HistoryEventType.SPEND and
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == A_WSOL and
                event.amount == new_collateral and
                event.address == liquidity_address
            ):  # Remove the extra WSOL event in deposits
                event_to_remove = event

        if event_to_remove is not None:
            context.decoded_events.remove(event_to_remove)

    def decode_lend_borrow_repay(
            self,
            context: SolanaDecoderContext,
            debt_token: 'SolanaToken',
            raw_debt_amount: int,
    ) -> None:
        """Decode a Jupiter lend borrow/repay event."""
        new_debt = token_normalized_value(
            token=debt_token,
            token_amount=abs(raw_debt_amount),
        )
        wsol_ata_address = self._maybe_get_wsol_ata(
            operation_token=debt_token,
            context=context,
            is_out_operation=(is_repay := raw_debt_amount < 0),
        )
        expected_token: AssetWithSymbol = debt_token
        new_token: AssetWithSymbol = debt_token
        if is_repay:
            expected_debt_event_type = HistoryEventType.SPEND
            new_debt_event_subtype = HistoryEventSubType.PAYBACK_DEBT
            new_debt_notes = f'Repay {new_debt} {{asset}} to Jupiter'
            if wsol_ata_address is not None:
                expected_token = new_token = A_SOL.resolve_to_asset_with_symbol()
        else:
            expected_debt_event_type = HistoryEventType.RECEIVE
            new_debt_event_subtype = HistoryEventSubType.GENERATE_DEBT
            new_debt_notes = f'Borrow {new_debt} {{asset}} from Jupiter'
            if wsol_ata_address is not None:
                expected_token = debt_token
                new_token = A_SOL.resolve_to_asset_with_symbol()

        event_to_remove = None
        for event in context.decoded_events:
            if (
                event.event_type == expected_debt_event_type and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == expected_token and
                event.amount == new_debt
            ):
                event.event_subtype = new_debt_event_subtype
                event.counterparty = CPT_JUPITER
                event.asset = new_token
                event.notes = new_debt_notes.format(asset=new_token.symbol)
            elif (
                wsol_ata_address is not None and
                expected_debt_event_type == HistoryEventType.SPEND and
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == A_WSOL and
                event.amount == new_debt
            ):  # Remove the extra WSOL event in deposits
                event_to_remove = event

        if event_to_remove is not None:
            context.decoded_events.remove(event_to_remove)

    def decode_lend_operate(self, context: SolanaDecoderContext) -> SolanaDecodingOutput:
        """Decode a Jupiter lend operate instruction. Will be either a collateral deposit/withdraw
        or a debt borrow/repay."""
        if (
            not match_discriminator(context.instruction.data, LEND_OPERATE_DISCRIMINATOR) or
            len(context.instruction.accounts) < 4  # there are more, but we don't use them here.
        ):
            return DEFAULT_SOLANA_DECODING_OUTPUT

        liquidity_address = context.instruction.accounts[1]
        operation_token = self.base.get_or_create_solana_token(
            address=context.instruction.accounts[3],
        )
        if (raw_collateral_amount := int.from_bytes(context.instruction.data[8:24], byteorder='little', signed=True)) != 0:  # noqa: E501
            self.decode_lend_collateral_deposit_withdraw(
                context=context,
                collateral_token=operation_token,
                raw_collateral_amount=raw_collateral_amount,
                liquidity_address=liquidity_address,
            )
        if (raw_debt_amount := int.from_bytes(context.instruction.data[24:40], byteorder='little', signed=True)) != 0:  # noqa: E501
            self.decode_lend_borrow_repay(
                context=context,
                debt_token=operation_token,
                raw_debt_amount=raw_debt_amount,
            )

        return DEFAULT_SOLANA_DECODING_OUTPUT

    def addresses_to_decoders(self) -> dict[SolanaAddress, tuple[Any, ...]]:
        return {
            JUPITER_AGGREGATOR_PROGRAM_V6: (self.decode_v6_swap,),
            JUPITER_RFQ_ORDER_ENGINE_PROGRAM: (self.decode_rfq_swap,),
            JUPITER_LEND_EARN_PROGRAM: (self.decode_lend_earn_events,),
            JUPITER_LEND_BORROW_PROGRAM: (self.decode_lend_init_position,),
            JUPITER_LEND_LIQUIDITY_PROGRAM: (self.decode_lend_operate,),
        }

    @staticmethod
    def counterparties() -> tuple['CounterpartyDetails', ...]:
        return (CounterpartyDetails(
            identifier=CPT_JUPITER,
            label='Jupiter',
            image='jupiter.svg',
        ),)
