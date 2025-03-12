import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Optional

from rotkehlchen.assets.asset import CryptoAsset
from rotkehlchen.chain.ethereum.utils import asset_normalized_value, asset_raw_value
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    FAILED_ENRICHMENT_OUTPUT,
    EnricherContext,
    TransferEnrichmentOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.decoding.weth.decoder import WETH_DEPOSIT_TOPIC, WETH_WITHDRAW_TOPIC
from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
from rotkehlchen.errors.asset import UnsupportedAsset, WrongAssetType
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction
from rotkehlchen.utils.misc import bytes_to_address

from .constants import CPT_RAINBOW_SWAPS

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class RainbowCommonDecoder(DecoderInterface):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            router_address: ChecksumEvmAddress,
    ) -> None:
        super().__init__(evm_inquirer, base_tools, msg_aggregator)
        self.router_address = router_address

    def _maybe_set_event_properties(
            self,
            event: 'EvmEvent',
            sender: ChecksumEvmAddress,
    ) -> None:
        """Set properties of the event to a rainbow swap considering the event direction"""
        if (
            event.location_label != sender or
            event.address != self.router_address or
            event.counterparty is not None
        ):
            return
        if event.event_type == HistoryEventType.RECEIVE and event.event_subtype == HistoryEventSubType.NONE:  # noqa: E501
            # Find the receive event
            event.event_type = HistoryEventType.TRADE
            event.event_subtype = HistoryEventSubType.RECEIVE
            event.counterparty = CPT_RAINBOW_SWAPS
            event.notes = f'Receive {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} as the result of a swap in Rainbow'  # noqa: E501
        elif event.event_type == HistoryEventType.SPEND and event.event_subtype == HistoryEventSubType.NONE:  # noqa: E501
            # Find the spend event
            event.event_type = HistoryEventType.TRADE
            event.event_subtype = HistoryEventSubType.SPEND
            event.notes = f'Swap {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} in Rainbow'  # noqa: E501
            event.counterparty = CPT_RAINBOW_SWAPS
            event.address = self.router_address

    def _find_event_by_log(
            self,
            logs: list['EvmTxReceiptLog'],
            event_signature: bytes,
    ) -> EvmTxReceiptLog | None:
        """
        Find the log that matches  the provided event signature.

        Returns the log event if found or None otherwise.
        """
        for tx_log in logs:
            if tx_log.topics[0] == event_signature:
                return tx_log

        return None

    def _get_in_out_events(
            self,
            events: list['EvmEvent'],
            sender: ChecksumEvmAddress,
    ) -> tuple[Optional['EvmEvent'], Optional['EvmEvent']]:
        """
        Extracts 'in' and 'out' events for a sender from a list of events.

        Args:
            events: List of EVM events.
            sender: Sender address to filter events by.

        Returns:
            Tuple of (in_event, out_event), representing token receive and spend
            events respectively.
        """
        in_event = out_event = None
        for event in events:
            if (
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == self.evm_inquirer.native_token
            ):
                # The "send eth" event is not enriched by enricher_rules,
                # so it needs to be enriched here
                self._maybe_set_event_properties(event, sender)

            if (
                event.event_type == HistoryEventType.TRADE and
                event.event_subtype == HistoryEventSubType.RECEIVE and
                event.counterparty == CPT_RAINBOW_SWAPS
            ):
                in_event = event
            elif (
                event.event_type == HistoryEventType.TRADE and
                event.event_subtype == HistoryEventSubType.SPEND and
                event.counterparty == CPT_RAINBOW_SWAPS
            ):
                out_event = event

        return in_event, out_event

    def _create_and_append_fee_event(
            self,
            transaction: EvmTransaction,
            fee_raw: int,
            fee_asset: CryptoAsset,
            sender: ChecksumEvmAddress,
            decoded_events: list['EvmEvent'],
            in_event: Optional['EvmEvent'],
            out_event: Optional['EvmEvent'],
    ) -> None:
        """Create and append a fee event to the decoded events list."""
        fee_event = self.base.make_event(
            tx_hash=transaction.tx_hash,
            sequence_index=self.base.get_next_sequence_index(),
            timestamp=transaction.timestamp,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=fee_asset,
            amount=(fee_amount := asset_normalized_value(amount=fee_raw, asset=fee_asset)),
            location_label=sender,
            notes=f'Spend {fee_amount} {fee_asset.resolve_to_asset_with_symbol().symbol} a Rainbow fee',  # noqa: E501
            counterparty=CPT_RAINBOW_SWAPS,
            address=self.router_address,
        )
        decoded_events.append(fee_event)
        maybe_reshuffle_events(
            ordered_events=[out_event, in_event, fee_event],
            events_list=decoded_events,
        )

    def _maybe_decode_fee_from_swap_native_to_token(
            self,
            transaction: EvmTransaction,
            out_event: 'EvmEvent',
            in_event: 'EvmEvent',
            decoded_events: list['EvmEvent'],
            sender: ChecksumEvmAddress,
            wrap_event: EvmTxReceiptLog,
    ) -> None:
        """
        Decodes the fee from a swap transaction involving native token to another token.

        The fee is calculated as the difference between the amount of native token sent
        and the amount of native token wrapped into the token.
        """
        try:
            swap_amount = asset_raw_value(out_event.amount, self.evm_inquirer.native_token)
        except UnsupportedAsset:
            log.error(
                f'Failed to decode rainbow swap from {self.evm_inquirer.native_token} to token'
                f' for transaction {transaction} '
                f'due to unsupported asset {out_event.asset.identifier}.',
            )
            return

        self._create_and_append_fee_event(
            transaction=transaction,
            fee_raw=swap_amount - int.from_bytes(wrap_event.data),
            fee_asset=self.evm_inquirer.native_token,
            sender=sender,
            decoded_events=decoded_events,
            in_event=in_event,
            out_event=out_event,
        )

    def _maybe_decode_fee_from_swap_token_to_native(
            self,
            transaction: EvmTransaction,
            decoded_events: list['EvmEvent'],
            in_event: Optional['EvmEvent'],
            out_event: Optional['EvmEvent'],
            sender: ChecksumEvmAddress,
            unwrap_event: EvmTxReceiptLog,
    ) -> None:
        """
        Decodes the fee from a swap transaction involving token to native token.

        The fee is calculated as the difference between the amount unwrapped to native token
        and the amount of native token received by the user.
        """
        if in_event is None or out_event is None:
            log.error(
                f'Failed to decode fee from rainbow swap token to '
                f'{self.evm_inquirer.native_token} for transaction {transaction}.',
            )
            return

        try:
            in_amount = asset_raw_value(in_event.amount, self.evm_inquirer.native_token)
        except UnsupportedAsset:
            log.error(
                f'Failed to decode fee from rainbow swap token to '
                f'{self.evm_inquirer.native_token} for transaction {transaction} '
                f'due to unsupported asset {in_event.asset.identifier}.',
            )
            in_amount = 0

        self._create_and_append_fee_event(
            transaction=transaction,
            fee_raw=int.from_bytes(unwrap_event.data) - in_amount,
            fee_asset=self.evm_inquirer.native_token,
            sender=sender,
            decoded_events=decoded_events,
            in_event=in_event,
            out_event=out_event,
        )

    def _maybe_decode_fee_from_swap_token_to_token(
            self,
            transaction: EvmTransaction,
            decoded_events: list['EvmEvent'],
            all_logs: list[EvmTxReceiptLog],
            sender: ChecksumEvmAddress,
            out_event: 'EvmEvent',
            in_event: 'EvmEvent',
    ) -> None:
        """
        Decodes the fee from a swap transaction involving token to token.

        The function identifies the fee by analyzing the transfer logs:
        - It looks for the transfer log from the user's wallet to the router
        to determine the sell amount.
        - It looks for the transfer log from the router to the swap provider
        to determine the swap amount.
        - The fee is calculated as the difference between the sell amount and the swap amount.
        """
        try:
            token_address = out_event.asset.resolve_to_evm_token().evm_address
        except WrongAssetType:
            log.error(
                f'Failed to decode fee from rainbow swap token to token '
                f'for transaction {transaction} due to token_address being null.',
            )
            return

        sell_amount = swap_amount = None
        for tx_log in all_logs:
            if (
                tx_log.topics[0] == ERC20_OR_ERC721_TRANSFER and
                tx_log.address == token_address
            ):
                if bytes_to_address(tx_log.topics[2]) == self.router_address:
                    sell_amount = int.from_bytes(tx_log.data)
                elif bytes_to_address(tx_log.topics[1]) == self.router_address:
                    swap_amount = int.from_bytes(tx_log.data)

                if swap_amount and sell_amount:
                    break
        else:
            log.error(
                f'Failed to decode fee from rainbow swap token to token '
                f'for transaction {transaction} due to sell_amount '
                'or swap_amount being null.',
            )
            return

        self._create_and_append_fee_event(
            transaction=transaction,
            fee_raw=sell_amount - swap_amount,
            fee_asset=out_event.asset.resolve_to_evm_token(),
            sender=sender,
            decoded_events=decoded_events,
            in_event=in_event,
            out_event=out_event,
        )

    def _process_swap(self,
            transaction: 'EvmTransaction',
            decoded_events: list['EvmEvent'],
            all_logs: list['EvmTxReceiptLog'],
    ) -> list['EvmEvent']:
        """
        Process a swap transaction by decoding the relevant events and logs.

        The function handles different types of swaps:
        - Native token to EVM token swap, looking for the output asset is
        eth and input asset is token
        - EVM token to native token swap, looking for the output asset is
        token and input asset is eth
        - EVM token to EVM token swap, looking for input and output assets are tokens

        It attempts to find the necessary logs for wrapping and unwrapping tokens
        and decodes the swap accordingly.
        If the required logs are missing, it logs an error and returns
        the original decoded events.
        """
        in_event, out_event = self._get_in_out_events(
            events=decoded_events,
            sender=(sender := transaction.from_address),
        )
        if in_event is None or out_event is None:
            log.error(
                f'Failed to post decode rainbow {transaction} '
                f'due to missing in_event or out_event.',
            )
            return decoded_events

        out_asset_is_evm_token = out_event.asset.is_evm_token()
        in_asset_is_evm_token = in_event.asset.is_evm_token()

        if out_event.asset == self.evm_inquirer.native_token and in_asset_is_evm_token:
            # See if we have a eth into weth log event
            # TODO: Change this logic to get the amount of eth wrapped
            if (wrap_event := self._find_event_by_log(all_logs, WETH_DEPOSIT_TOPIC)) is None:
                log.error(
                    f'Failed to decode fee from rainbow swap involving '
                    f'{self.evm_inquirer.native_token} to token for transaction '
                    f'{transaction} due to missing wrap log.',
                )
                return decoded_events

            self._maybe_decode_fee_from_swap_native_to_token(
                transaction=transaction,
                out_event=out_event,
                in_event=in_event,
                decoded_events=decoded_events,
                sender=sender,
                wrap_event=wrap_event,
            )
        elif out_asset_is_evm_token and in_event.asset == self.evm_inquirer.native_token:
            # TODO: Change this logic to get the amount of eth unwrapped
            if (unwrap_event := self._find_event_by_log(all_logs, WETH_WITHDRAW_TOPIC)) is None:
                log.error(
                    f'Failed to decode fee from rainbow swap involving'
                    f'token to {self.evm_inquirer.native_token} for transaction '
                    f'{transaction} due to missing unwrap log.',
                )
                return decoded_events

            self._maybe_decode_fee_from_swap_token_to_native(
                transaction=transaction,
                decoded_events=decoded_events,
                in_event=in_event,
                out_event=out_event,
                sender=sender,
                unwrap_event=unwrap_event,
            )
        elif out_asset_is_evm_token and in_asset_is_evm_token:
            self._maybe_decode_fee_from_swap_token_to_token(
                transaction=transaction,
                decoded_events=decoded_events,
                all_logs=all_logs,
                sender=sender,
                out_event=out_event,
                in_event=in_event,
            )

        return decoded_events

    def _maybe_enrich_rainbow_transfer(
            self,
            context: EnricherContext,
    ) -> TransferEnrichmentOutput:
        """
        Enricher transfer events to rainbow router. The contract doesn't emit events for swaps.
        """
        if context.event.address != self.router_address:
            return FAILED_ENRICHMENT_OUTPUT

        self._maybe_set_event_properties(context.event, context.transaction.from_address)
        if context.event.counterparty == CPT_RAINBOW_SWAPS:
            return TransferEnrichmentOutput(matched_counterparty=CPT_RAINBOW_SWAPS)

        return FAILED_ENRICHMENT_OUTPUT

    def enricher_rules(self) -> list[Callable]:
        return [self._maybe_enrich_rainbow_transfer]

    def post_decoding_rules(self) -> dict[str, list[tuple[int, Callable]]]:
        return {CPT_RAINBOW_SWAPS: [(0, self._process_swap)]}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_RAINBOW_SWAPS,
            label='rainbow swaps',
            image='rainbow.svg',
        ),)
