import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Optional

from rotkehlchen.assets.asset import CryptoAsset
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    FAILED_ENRICHMENT_OUTPUT,
    EnricherContext,
    TransferEnrichmentOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction
from rotkehlchen.utils.misc import bytes_to_address, from_wei

from .constants import CPT_RAINBOW_SWAPS

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
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

    def _create_and_append_fee_event(
            self,
            transaction: EvmTransaction,
            fee_amount: FVal,
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
            amount=fee_amount,
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

    def _process_swap(
            self,
            transaction: 'EvmTransaction',
            decoded_events: list['EvmEvent'],
            all_logs: list['EvmTxReceiptLog'],
    ) -> list['EvmEvent']:
        """
        Process a swap transaction by decoding the relevant events and logs.

        The function handles different types of swaps:
        - Native token to EVM token swap, when the output asset is
        eth and input asset is token
        - EVM token to native token swap, when the output asset is
        token and input asset is eth
        - EVM token to EVM token swap, when both the input and output assets are tokens
        """
        out_event = in_event = None
        for event in decoded_events:
            if event.address != self.router_address:
                continue

            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE
            ):
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.RECEIVE
                event.counterparty = CPT_RAINBOW_SWAPS
                in_event = event
            elif (
                (event.event_type == HistoryEventType.SPEND and event.event_subtype == HistoryEventSubType.NONE) or  # noqa: E501
                # case for when other post decoding logic triggers before this one
                (event.event_type == HistoryEventType.TRADE and event.event_subtype == HistoryEventSubType.SPEND)  # noqa: E501
            ):
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.SPEND
                event.counterparty = CPT_RAINBOW_SWAPS
                event.address = self.router_address
                out_event = event

        if out_event is None or in_event is None:
            log.error(f'Failed to find swap events in rainbow swap at {transaction}')
            return decoded_events

        self._find_fees(
            out_event=out_event,
            in_event=in_event,
            transaction=transaction,
            decoded_events=decoded_events,
            all_logs=all_logs,
        )

        # update the note with the actual value. This is the amount used by the rainbow
        # router to swap. The final amount could actually be lower since solvers
        # may also charge a fee.
        out_event.notes = f'Swap {out_event.amount} {out_event.asset.resolve_to_asset_with_symbol().symbol} in Rainbow'  # noqa: E501
        in_event.notes = f'Receive {in_event.amount} {in_event.asset.resolve_to_asset_with_symbol().symbol} as the result of a swap in Rainbow'  # noqa: E501
        return decoded_events

    def _find_fees(
            self,
            out_event: 'EvmEvent',
            in_event: 'EvmEvent',
            transaction: 'EvmTransaction',
            decoded_events: list['EvmEvent'],
            all_logs: list['EvmTxReceiptLog'],
    ) -> None:
        """Check transfers to find the fee taken from rainbow. They can be ETH fees in which
        case we check the internal transactions or token fees which we check in the log events
        """
        swapped_amount = out_event.amount
        # if we are dealing with eth swaps check the internal transfers of eth from/to
        # the rainbow router
        if self.evm_inquirer.native_token in {out_event.asset, in_event.asset}:
            for internal_tx in DBEvmTx(self.evm_inquirer.database).get_evm_internal_transactions(
                parent_tx_hash=transaction.tx_hash,
                blockchain=self.evm_inquirer.blockchain,
            ):
                if ((
                    internal_tx.from_address == self.router_address and
                    internal_tx.to_address != out_event.location_label
                ) or (
                    internal_tx.from_address != out_event.location_label and
                    internal_tx.to_address == self.router_address
                )):
                    swapped_amount = from_wei(internal_tx.value)
                    break

        # When eth is swapped the fee is taken from the sent ETH. When ETH is received the
        # fee is taken from the received amount. The fee is the amount diff with the amount
        # that the proxy sends to the swap solver
        fee_asset = fee_amount = None
        if (
            out_event.asset == self.evm_inquirer.native_token and
            (possible_fee_amount := out_event.amount - swapped_amount) > 0
        ):
            fee_amount = possible_fee_amount
            out_event.amount -= fee_amount
            fee_asset = self.evm_inquirer.native_token
        elif (
            in_event.asset == self.evm_inquirer.native_token and
            (possible_fee_amount := swapped_amount - in_event.amount) > 0
        ):
            fee_amount = possible_fee_amount
            fee_asset = self.evm_inquirer.native_token
        else:  # token transfer
            # check the event logs for the transfers made by the router to find if the fee was
            # taken from the asset sent or the asset received
            for log_event in all_logs:
                if len(log_event.topics) != 3 or log_event.topics[0] == ERC20_OR_ERC721_TRANSFER:
                    continue  # we only look for transfers

                if (
                    bytes_to_address(log_event.topics[1]) == self.router_address and
                    bytes_to_address(log_event.topics[2]) != in_event.location_label and
                    (possible_fee_amount := (out_event.amount - asset_normalized_value(
                        amount=int.from_bytes(log_event.data),
                        asset=(out_asset := out_event.asset.resolve_to_crypto_asset()),
                    ))) > 0
                ):  # this is the router sending the token to the solver and charging a fee
                    fee_amount = possible_fee_amount
                    out_event.amount -= fee_amount
                    fee_asset = out_asset
                    break
                elif (
                    bytes_to_address(log_event.topics[1]) != in_event.location_label and  # from
                    bytes_to_address(log_event.topics[2]) == self.router_address and  # to
                    (possible_fee_amount := asset_normalized_value(
                        amount=int.from_bytes(log_event.data),
                        asset=(in_asset := in_event.asset.resolve_to_crypto_asset()),
                    ) - in_event.amount) > 0
                ):
                    fee_amount = possible_fee_amount
                    fee_asset = in_asset
                    break

        if fee_asset is None or fee_amount is None:
            log.debug(f'Failed to get fee amount in rainbow transaction {transaction}')
            return

        self._create_and_append_fee_event(
            transaction=transaction,
            fee_amount=fee_amount,
            fee_asset=fee_asset,
            sender=out_event.location_label,  # type: ignore
            decoded_events=decoded_events,
            in_event=in_event,
            out_event=out_event,
        )

    def _maybe_enrich_rainbow_transfer(
            self,
            context: EnricherContext,
    ) -> TransferEnrichmentOutput:
        """
        Enricher transfer events to rainbow router. The contract doesn't emit events for swaps.
        """
        if context.event.address == self.router_address:
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
