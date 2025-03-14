import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Optional

from rotkehlchen.assets.asset import CryptoAsset
from rotkehlchen.chain.ethereum.utils import asset_normalized_value, asset_raw_value
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    FAILED_ENRICHMENT_OUTPUT,
    ActionItem,
    EnricherContext,
    TransferEnrichmentOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.weth.decoder import WETH_DEPOSIT_TOPIC, WETH_WITHDRAW_TOPIC
from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
from rotkehlchen.errors.asset import UnsupportedAsset
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction, EVMTxHash, Timestamp
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

    def _enricher_event(
            self,
            event: 'EvmEvent',
            sender: ChecksumEvmAddress,
    ) -> None:
        """Enricher the event to rainbow event
        """
        if (event.event_type == HistoryEventType.RECEIVE and event.event_subtype == HistoryEventSubType.NONE and event.location_label == sender):  # noqa: E501
            # Find the receive event
            event.event_type = HistoryEventType.TRADE
            event.event_subtype = HistoryEventSubType.RECEIVE
            event.counterparty = CPT_RAINBOW_SWAPS
            event.notes = f'Receive {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} as the result of a Rainbow Swap'  # noqa: E501
        elif (event.event_type == HistoryEventType.SPEND and event.event_subtype == HistoryEventSubType.NONE and event.location_label == sender):  # noqa: E501
            # Find the spend event
            event.event_type = HistoryEventType.TRADE
            event.event_subtype = HistoryEventSubType.SPEND
            event.notes = f'Swap {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} in Rainbow Swap'  # noqa: E501
            event.counterparty = CPT_RAINBOW_SWAPS
            event.address = self.router_address

    def _get_in_out_events(
            self,
            events: list['EvmEvent'],
            sender: ChecksumEvmAddress,
    ) -> tuple[Optional['EvmEvent'], Optional['EvmEvent']]:
        in_event = out_event = None
        for event in events:
            self._enricher_event(event, sender)
            if (
                event.event_type == HistoryEventType.TRADE and
                event.event_subtype == HistoryEventSubType.RECEIVE
            ):
                in_event = event
            elif (
                event.event_type == HistoryEventType.TRADE and
                event.event_subtype == HistoryEventSubType.SPEND
            ):
                out_event = event

        return in_event, out_event

    def _create_fee_event(
            self,
            tx_hash: EVMTxHash,
            sequence_index: int,
            timestamp: Timestamp,
            fee_raw: int,
            fee_asset: CryptoAsset,
            sender: ChecksumEvmAddress,
    ) -> 'EvmEvent':
        """Create a new fee event for rainbow swap

        Args:
            tx_hash (EVMTxHash): transaction hash
            sequence_index (int): event sequence index
            timestamp (int): transaction timestamp
            fee_raw (int): amount of fee charged in wei
            fee_asset (Asset): fee asset
            sender (ChecksumEvmAddress): sender address
        """
        return self.base.make_event(
            tx_hash=tx_hash,
            sequence_index=sequence_index,
            timestamp=timestamp,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=fee_asset,
            amount=(fee_amount := asset_normalized_value(amount=fee_raw, asset=fee_asset)),
            location_label=sender,
            notes=f'Spend {fee_amount} {fee_asset.resolve_to_asset_with_symbol().symbol} as Rainbow Swap fees',  # noqa: E501
            counterparty=CPT_RAINBOW_SWAPS,
            address=self.router_address,
        )

    def _maybe_decode_swap_native_to_token(
            self,
            transaction: EvmTransaction,
            event: 'EvmEvent',
            decoded_events: list['EvmEvent'],
            action_items: list[ActionItem],
            sender: ChecksumEvmAddress,
            wrap_log: EvmTxReceiptLog,
            transfer_log: EvmTxReceiptLog,
    ) -> bool:
        """
        Decodes a swap transaction from native token to another token.
        Check if the first log is deposit and the last is transfer log
        """
        # The fee amount is the difference of msg.value and the wrapped token amount
        fee_raw = transaction.value - int.from_bytes(wrap_log.data)
        # The Buy asset and amount is stored in the last transfer log
        buy_asset = self.base.get_or_create_evm_token(transfer_log.address)

        # Remove the transfer event
        # of the purchased token to the user's wallet
        # to create a new event with the right sequence index
        remove_action = ActionItem(
            action='skip',
            from_event_type=HistoryEventType.RECEIVE,
            from_event_subtype=HistoryEventSubType.NONE,
            asset=buy_asset,
        )

        # Create fee event as the last event
        fee_event = self._create_fee_event(
            tx_hash=transaction.tx_hash,
            sequence_index=event.sequence_index + 1,
            timestamp=transaction.timestamp,
            fee_raw=fee_raw,
            fee_asset=self.evm_inquirer.native_token,
            sender=sender,
        )

        # Create event to fee
        decoded_events.append(fee_event)

        # Add the action to remove the receive
        action_items.extend([remove_action])

        return True

    def _maybe_decode_swap_token_to_native(
            self,
            transaction: EvmTransaction,
            decoded_events: list['EvmEvent'],
            in_event: Optional['EvmEvent'],
            out_event: Optional['EvmEvent'],
            sender: ChecksumEvmAddress,
            unwrap_log: EvmTxReceiptLog,
    ) -> bool:
        """
        Decodes a swap transaction from token to native token.
        Check if the first log is transfer and the last log is withdrawn
        """
        native_token = self.evm_inquirer.native_token
        tx_hash = transaction.tx_hash

        if not (in_event and out_event):
            log.error(
                f'Failed to decode swap from token to native token'
                f' for tranction {tx_hash.hex()}.',
            )
            return False

        try:
            in_amount = asset_raw_value(in_event.amount, native_token)
        except UnsupportedAsset:
            in_amount = 0
        # The fee will be the withdraw data subtract the in_amount
        fee_raw = int.from_bytes(unwrap_log.data) - in_amount

        # Need to change the index of receive to respect the events order
        in_event.sequence_index = out_event.sequence_index + 1

        # Create the event for the fee
        fee_event = self._create_fee_event(
            tx_hash=tx_hash,
            sequence_index=out_event.sequence_index + 2,
            timestamp=transaction.timestamp,
            fee_raw=fee_raw,
            fee_asset=native_token,
            sender=sender,
        )
        decoded_events.append(fee_event)

        return True

    def _maybe_decode_swap_token_to_token(
            self,
            transaction: EvmTransaction,
            decoded_events: list['EvmEvent'],
            all_logs: list[EvmTxReceiptLog],
            action_items: list[ActionItem],
            sender: ChecksumEvmAddress,
            out_event: Optional['EvmEvent'],
    ) -> bool:
        """Decodes a swap transaction from token to native token.
        Check if the first and last logs is transfer
        """
        tx_hash = transaction.tx_hash

        if out_event is None:
            log.error(
                f'Failed to decode swap from token to native token'
                f' for tranction {tx_hash.hex()} due the out_event is null.',
            )
            return False

        sell_amount = swap_amount = None
        for tx_log in all_logs:
            if (
                tx_log.address == out_event.asset.resolve_to_evm_token().evm_address and
                tx_log.topics[0] == ERC20_OR_ERC721_TRANSFER
            ):
                # Find the transfer log from the user wallet to router
                if bytes_to_address(tx_log.topics[2]) == self.router_address:
                    sell_amount = int.from_bytes(tx_log.data)

                # Find the transfer log from the router to the swap
                if bytes_to_address(tx_log.topics[1]) == self.router_address:
                    swap_amount = int.from_bytes(tx_log.data)

                if swap_amount and sell_amount:
                    break

        if not (sell_amount and swap_amount):
            log.error(
                f'Failed to decode swap from token to token'
                f' for tranction {tx_hash.hex()} due the sell_amount or swap_amount being null.',
            )
            return False

        # Remove the transfer event
        # of the purchased token to the user's wallet
        # to create a new event with the right sequence index
        transfer_log = all_logs[-1]
        buy_asset = self.base.get_or_create_evm_token(transfer_log.address)
        buy_amount = int.from_bytes(transfer_log.data)
        remove_action = ActionItem(
            action='skip',
            from_event_type=HistoryEventType.RECEIVE,
            from_event_subtype=HistoryEventSubType.NONE,
            asset=buy_asset,
        )

        # Create a new event for receive with right index
        amount = asset_normalized_value(buy_amount, buy_asset)
        in_event = self.base.make_event_next_index(
            tx_hash=tx_hash,
            timestamp=transaction.timestamp,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=buy_asset,
            amount=amount,
            location_label=sender,
            notes=f'Receive {amount} {buy_asset.resolve_to_asset_with_symbol().symbol} as the result of a Rainbow Swap',  # noqa: E501
            counterparty=CPT_RAINBOW_SWAPS,
            address=self.router_address,
        )
        decoded_events.append(in_event)

        fee_event = self._create_fee_event(
            tx_hash=transaction.tx_hash,
            sequence_index=in_event.sequence_index + 1,
            timestamp=transaction.timestamp,
            fee_raw=sell_amount - swap_amount,
            fee_asset=out_event.asset.resolve_to_evm_token(),
            sender=sender,
        )
        decoded_events.append(fee_event)
        action_items.append(remove_action)

        return True

    def _maybe_enricher_rainbow_transfer(
            self,
            context: EnricherContext,
    ) -> TransferEnrichmentOutput:
        sender = context.transaction.from_address
        tx_log = context.tx_log
        events = [context.event]
        events.extend(context.decoded_events)

        # Add the event to a local list to enrich it without
        # modifying the global decoded_events list
        in_event, out_event = self._get_in_out_events(events, sender)

        if out_event is None:
            log.error(
                f'Failed to enrich rainbow transfer for transaction {context.transaction.tx_hash.hex()}'  # noqa: E501
                f' due to missing out_event.',
            )
            return FAILED_ENRICHMENT_OUTPUT

        # Check if the log is transfer the token to user wallet
        if bytes_to_address(tx_log.topics[2]) == sender:
            # Try to find if have wrap eth into weth log
            # and the log index is before the token transfer
            for tx_lg in context.all_logs:
                if tx_lg.topics[0] == WETH_DEPOSIT_TOPIC and tx_lg.log_index < tx_log.log_index:
                    success_decoded = self._maybe_decode_swap_native_to_token(
                        transaction=context.transaction,
                        event=context.event,  # in this case the event is the in_event
                        decoded_events=context.decoded_events,
                        action_items=context.action_items,
                        sender=sender,
                        wrap_log=tx_lg,
                        transfer_log=tx_log,
                    )

                    if success_decoded:
                        break

        # Check if the first log is token transfer and
        # the last transfer is token withdraw
        if bytes_to_address(tx_log.topics[1]) == sender:
            for tx_lg in context.all_logs:
                # Try to find if have unwrap weth into eth log
                # and the log index is after the token transfer
                if tx_lg.topics[0] == WETH_WITHDRAW_TOPIC and tx_lg.log_index > tx_log.log_index:
                    if in_event is None:
                        log.error(
                            f'Failed to enrich rainbow transfer for transaction {context.transaction.tx_hash.hex()}'  # noqa: E501
                            f' due to missing int_event.',
                        )
                        return FAILED_ENRICHMENT_OUTPUT

                    success_decoded = self._maybe_decode_swap_token_to_native(
                        transaction=context.transaction,
                        decoded_events=context.decoded_events,
                        in_event=in_event,
                        out_event=out_event,
                        sender=sender,
                        unwrap_log=tx_lg,
                    )

                    if success_decoded:
                        break

        # Check if is the transfer is from the user to the router
        # and the last log is transfer to user
        last_log = context.all_logs[-1]
        if (
            (bytes_to_address(tx_log.topics[1]) == sender and bytes_to_address(tx_log.topics[2]) == self.router_address) and  # noqa: E501
            last_log.topics[0] == ERC20_OR_ERC721_TRANSFER and bytes_to_address(last_log.topics[2]) == sender  # noqa: E501
        ):
            self._maybe_decode_swap_token_to_token(
                transaction=context.transaction,
                decoded_events=context.decoded_events,
                all_logs=context.all_logs,
                action_items=context.action_items,
                sender=sender,
                out_event=context.event,
            )

        return FAILED_ENRICHMENT_OUTPUT

    def enricher_rules(self) -> list[Callable]:
        return [self._maybe_enricher_rainbow_transfer]

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_RAINBOW_SWAPS,
            label='rainbow swaps',
            image='rainbow.svg',
        ),)
