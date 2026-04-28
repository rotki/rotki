import logging
from typing import Any

from rotkehlchen.assets.utils import token_normalized_value
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address, bytes_to_hexstr

from .constants import (
    CPT_MORPHO_BLUE,
    MORPHO_BLUE,
    MORPHO_BLUE_BORROW,
    MORPHO_BLUE_CPT_DETAILS,
    MORPHO_BLUE_REPAY,
    MORPHO_BLUE_SUPPLY,
    MORPHO_BLUE_SUPPLY_COLLATERAL,
    MORPHO_BLUE_WITHDRAW,
    MORPHO_BLUE_WITHDRAW_COLLATERAL,
)

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class MorphoBlueDecoder(EvmDecoderInterface):

    def _decode_morpho_blue_event(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] not in (
                MORPHO_BLUE_BORROW,
                MORPHO_BLUE_REPAY,
                MORPHO_BLUE_SUPPLY,
                MORPHO_BLUE_SUPPLY_COLLATERAL,
                MORPHO_BLUE_WITHDRAW,
                MORPHO_BLUE_WITHDRAW_COLLATERAL,
        ):
            return DEFAULT_EVM_DECODING_OUTPUT

        if context.tx_log.topics[0] == MORPHO_BLUE_BORROW:
            # Borrow logs are emitted before the ERC20 transfer, so the matching receive event
            # is not decoded yet. Register an action item to transform it once it is created.
            return EvmDecodingOutput(action_items=[ActionItem(
                action='transform',
                from_event_type=HistoryEventType.RECEIVE,
                from_event_subtype=HistoryEventSubType.NONE,
                location_label=bytes_to_address(context.tx_log.topics[3]),
                to_event_type=HistoryEventType.RECEIVE,
                to_event_subtype=HistoryEventSubType.GENERATE_DEBT,
                to_notes='Borrow {amount} {symbol} from Morpho Blue',
                to_counterparty=CPT_MORPHO_BLUE,
                to_address=MORPHO_BLUE,
                extra_data={'market_id': bytes_to_hexstr(context.tx_log.topics[1])},
            )])

        if context.tx_log.topics[0] == MORPHO_BLUE_WITHDRAW:
            # Withdraw logs are emitted before the ERC20 transfer, so the matching receive event
            # is not decoded yet. Register an action item to transform it once it is created.
            return EvmDecodingOutput(action_items=[ActionItem(
                action='transform',
                from_event_type=HistoryEventType.RECEIVE,
                from_event_subtype=HistoryEventSubType.NONE,
                location_label=bytes_to_address(context.tx_log.data[:32]),
                to_event_type=HistoryEventType.WITHDRAWAL,
                to_event_subtype=HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
                to_notes='Withdraw {amount} {symbol} from Morpho Blue',
                to_counterparty=CPT_MORPHO_BLUE,
                to_address=MORPHO_BLUE,
                extra_data={'market_id': bytes_to_hexstr(context.tx_log.topics[1])},
            )])

        if context.tx_log.topics[0] == MORPHO_BLUE_WITHDRAW_COLLATERAL:
            # WithdrawCollateral logs are emitted before the ERC20 transfer, so the matching
            # receive event is not decoded yet. Register an action item to transform it.
            return EvmDecodingOutput(action_items=[ActionItem(
                action='transform',
                from_event_type=HistoryEventType.RECEIVE,
                from_event_subtype=HistoryEventSubType.NONE,
                location_label=bytes_to_address(context.tx_log.topics[3]),
                to_event_type=HistoryEventType.WITHDRAWAL,
                to_event_subtype=HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
                to_notes='Withdraw {amount} {symbol} collateral from Morpho Blue',
                to_counterparty=CPT_MORPHO_BLUE,
                to_address=MORPHO_BLUE,
                extra_data={'market_id': bytes_to_hexstr(context.tx_log.topics[1])},
            )])

        if context.tx_log.topics[0] == MORPHO_BLUE_REPAY:
            # Repay logs are emitted before the ERC20 transfer, so the matching spend event
            # is not decoded yet. Register an action item to transform it once it is created.
            return EvmDecodingOutput(action_items=[ActionItem(
                action='transform',
                from_event_type=HistoryEventType.SPEND,
                from_event_subtype=HistoryEventSubType.NONE,
                location_label=bytes_to_address(context.tx_log.topics[2]),
                to_event_type=HistoryEventType.SPEND,
                to_event_subtype=HistoryEventSubType.PAYBACK_DEBT,
                to_notes='Repay {amount} {symbol} to Morpho Blue',
                to_counterparty=CPT_MORPHO_BLUE,
                to_address=MORPHO_BLUE,
                extra_data={'market_id': bytes_to_hexstr(context.tx_log.topics[1])},
            )])

        if context.tx_log.topics[0] == MORPHO_BLUE_SUPPLY_COLLATERAL:
            # SupplyCollateral logs are emitted before the ERC20 transfer, so the matching
            # spend event is not decoded yet. Use _process_spend_event to find and transform
            # it, but skip the bundler check because when using a bundler (caller != onBehalf)
            # the user's spend goes to the bundler first, and the bundler->Morpho transfer is
            # not tracked so it never triggers an action item.
            return self._process_spend_event(
                context=context,
                to_event_type=HistoryEventType.DEPOSIT,
                to_event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
                notes_template='Deposit {amount} {symbol} as collateral into Morpho Blue',
                action_name='supply_collateral',
                skip_bundler_check=True,
                fallback_location_label=bytes_to_address(context.tx_log.topics[3]),
                to_address=MORPHO_BLUE,
            )

        return self._process_spend_event(
            context=context,
            to_event_type=HistoryEventType.DEPOSIT,
            to_event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
            notes_template='Deposit {amount} {symbol} into Morpho Blue',
            action_name='supply',
            skip_bundler_check=True,
            fallback_location_label=bytes_to_address(context.tx_log.topics[3]),
            to_address=MORPHO_BLUE,
        )

    def _process_spend_event(
            self,
            context: DecoderContext,
            to_event_type: HistoryEventType,
            to_event_subtype: HistoryEventSubType,
            notes_template: str,
            action_name: str,
            skip_bundler_check: bool = False,
            fallback_location_label: ChecksumEvmAddress | None = None,
            to_address: ChecksumEvmAddress | None = None,
    ) -> EvmDecodingOutput:
        assets_amount_raw = int.from_bytes(context.tx_log.data[:32])
        later_transfer_sender = self._maybe_get_later_morpho_transfer_sender(
            context=context,
            amount_raw=assets_amount_raw,
        )

        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset.is_evm_token() and
                    token_normalized_value(
                        token_amount=assets_amount_raw,
                        token=event.asset.resolve_to_evm_token(),
                    ) == event.amount
            ):
                # Avoid transforming third-party vault deposits (for example Beefy -> Morpho).
                # In these transactions the user first sends funds to the tx target vault, and
                # then that vault supplies into Morpho with caller == onBehalf == vault address.
                # Matching by amount alone would incorrectly rewrite the user's vault deposit as a
                # Morpho deposit, so skip this candidate and let the upstream protocol decoder
                # claim it.
                if (
                        context.transaction.to_address is not None and
                        event.address == context.transaction.to_address and
                        (supply_caller := bytes_to_address(context.tx_log.topics[2])) ==
                        (supply_on_behalf := bytes_to_address(context.tx_log.topics[3])) and
                        supply_caller != context.transaction.to_address and
                        event.location_label != supply_on_behalf
                ):
                    continue

                if (
                        not skip_bundler_check and
                        later_transfer_sender is not None and
                        context.transaction.to_address is not None and
                        context.transaction.to_address != MORPHO_BLUE and
                        event.address == context.transaction.to_address
                ):
                    return DEFAULT_EVM_DECODING_OUTPUT

                event.event_type = to_event_type
                event.event_subtype = to_event_subtype
                event.counterparty = CPT_MORPHO_BLUE
                if to_address is not None:
                    event.address = to_address
                symbol = event.asset.resolve_to_asset_with_symbol().symbol
                event.notes = notes_template.format(amount=event.amount, symbol=symbol)
                event.extra_data = {'market_id': bytes_to_hexstr(context.tx_log.topics[1])}
                break
        else:
            if later_transfer_sender is not None:
                return EvmDecodingOutput(action_items=[ActionItem(
                    action='transform',
                    from_event_type=HistoryEventType.SPEND,
                    from_event_subtype=HistoryEventSubType.NONE,
                    location_label=fallback_location_label or later_transfer_sender,
                    to_event_type=to_event_type,
                    to_event_subtype=to_event_subtype,
                    to_notes=notes_template,
                    to_counterparty=CPT_MORPHO_BLUE,
                    to_address=to_address or MORPHO_BLUE,
                    extra_data={'market_id': bytes_to_hexstr(context.tx_log.topics[1])},
                )])

            log.debug(f'Expected Morpho Blue {action_name} in {context.transaction} not found.')

        return DEFAULT_EVM_DECODING_OUTPUT

    @staticmethod
    def _maybe_get_later_morpho_transfer_sender(
            context: DecoderContext,
            amount_raw: int,
    ) -> ChecksumEvmAddress | None:
        """Return sender of a later ERC20 transfer to Morpho for the same amount if present.

        Morpho Blue can emit Supply before the actual token transfer. In that case the spend
        event is not decoded yet and transforming an earlier equal-amount spend is too broad.
        """
        for tx_log in context.all_logs:
            if tx_log.log_index <= context.tx_log.log_index:
                continue

            if (
                    len(tx_log.topics) == 3 and
                    tx_log.topics[0] == ERC20_OR_ERC721_TRANSFER and
                    bytes_to_address(tx_log.topics[2]) == MORPHO_BLUE and
                    int.from_bytes(tx_log.data[:32]) == amount_raw
            ):
                return bytes_to_address(tx_log.topics[1])

        return None

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {MORPHO_BLUE: (self._decode_morpho_blue_event,)}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (MORPHO_BLUE_CPT_DETAILS,)

    def addresses_to_counterparties(self) -> dict[ChecksumEvmAddress, str]:
        return {MORPHO_BLUE: CPT_MORPHO_BLUE}
