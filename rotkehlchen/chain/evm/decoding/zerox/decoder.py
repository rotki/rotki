import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.decoding.uniswap.constants import UNISWAP_SIGNATURES
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.transactions import EvmTransactions
from rotkehlchen.constants import ZERO
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction
from rotkehlchen.utils.misc import bytes_to_address

from .constants import CPT_ZEROX, METATX_ZEROX

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.fval import FVal
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class ZeroxCommonDecoder(EvmDecoderInterface):
    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            router_address: ChecksumEvmAddress,
            flash_wallet_address: ChecksumEvmAddress,
            settler_routers_addresses: set[ChecksumEvmAddress] | None = None,
    ) -> None:
        """router_address is the main point of contact with the 0x protocol.
        flash_wallet_address is a contract that can execute arbitrary calls from 0x router_address.
        Docs: https://0x.org/docs/introduction/0x-cheat-sheet#exchange-proxy-addresses"""
        super().__init__(evm_inquirer, base_tools, msg_aggregator)
        self.evm_txns = EvmTransactions(self.node_inquirer, self.base.database)
        self.router_address = router_address
        self.settler_routers_addresses = settler_routers_addresses
        self.flash_wallet_address = flash_wallet_address
        self.router_addresses_set = {self.router_address}
        if self.settler_routers_addresses:
            self.router_addresses_set |= self.settler_routers_addresses

    def _update_send_receive_fee_events(
            self,
            send_event: 'EvmEvent | None' = None,
            receive_event: 'EvmEvent | None' = None,
            fee_event: 'EvmEvent | None' = None,
            used_router_address: 'ChecksumEvmAddress | None' = None,
    ) -> None:
        """An auxiliary function to update the send, receive and/or fee events with the 0x values"""  # noqa: E501
        # This is a case for swaps made via the settler
        # The send event contains the settler address, so need to
        # update the others events with the settler address
        router_address = self.router_address
        if (
            send_event is not None and
            self.settler_routers_addresses is not None and
            send_event.address in self.settler_routers_addresses
        ):
            router_address = send_event.address
        elif used_router_address is not None:
            router_address = used_router_address

        if send_event is not None:
            send_event.counterparty = CPT_ZEROX
            send_event.address = router_address
            send_event.event_type = HistoryEventType.TRADE
            send_event.event_subtype = HistoryEventSubType.SPEND
            send_event.notes = f'Swap {send_event.amount} {send_event.asset.symbol_or_name()} via the 0x protocol'  # noqa: E501
        if receive_event is not None:
            receive_event.event_type = HistoryEventType.TRADE
            receive_event.event_subtype = HistoryEventSubType.RECEIVE
            receive_event.notes = f'Receive {receive_event.amount} {receive_event.asset.symbol_or_name()} as the result of a swap via the 0x protocol'  # noqa: E501
        if fee_event is not None:
            fee_event.event_type = HistoryEventType.TRADE
            fee_event.event_subtype = HistoryEventSubType.FEE
            fee_event.notes = f'Spend {fee_event.amount} {fee_event.asset.symbol_or_name()} as a 0x protocol fee'  # noqa: E501

    def _merge_split_swap_events(
            self,
            decoded_events: list['EvmEvent'],
            send_events: list['EvmEvent'],
            receive_events: list['EvmEvent'],
            fee_event: 'EvmEvent | None' = None,
            return_amount: 'FVal' = ZERO,
    ) -> None:
        """Sum the balances of the events, update them with the 0x values, replace them with the
        Merged Events in decoded_events list, and maybe shuffle them with proper order. This is
        helpful in multiplex swaps, where a swap is done via multiple routes."""
        summed_send_event = send_events[0] if len(send_events) > 0 else None
        summed_receive_event = receive_events[0] if len(receive_events) > 0 else None
        events_to_remove = set()

        if summed_send_event is not None:
            for event in send_events[1:]:
                summed_send_event.amount += event.amount
                events_to_remove.add(event)
            summed_send_event.amount -= return_amount
        if summed_receive_event is not None:
            for event in receive_events[1:]:
                summed_receive_event.amount += event.amount
                events_to_remove.add(event)

        self._update_send_receive_fee_events(
            send_event=summed_send_event,
            receive_event=summed_receive_event,
            fee_event=fee_event,
        )
        # in-place edit the decoded_events reference and filter out events_to_remove
        decoded_events[:] = [event for event in decoded_events if event not in events_to_remove]
        maybe_reshuffle_events(
            ordered_events=[summed_send_event, summed_receive_event, fee_event],
            events_list=decoded_events,
        )

    def _decode_swap(
            self,
            transaction: 'EvmTransaction',
            decoded_events: list['EvmEvent'],
            all_logs: list['EvmTxReceiptLog'],
    ) -> list['EvmEvent']:
        """This function is used to decode the swaps done via 0x. It checks if already decoded
        events interacted with the 0x router, and overwrites them if they did."""
        send_address_to_events: dict[ChecksumEvmAddress, EvmEvent] = {}
        receive_address_to_events: dict[ChecksumEvmAddress, EvmEvent] = {}
        receive_events: list[EvmEvent] = []
        sent_asset = received_asset = None
        for event in decoded_events:
            if (
                event.location_label is None or event.location_label != transaction.from_address or
                not self.base.is_tracked(event.location_label)  # type: ignore  # it's a checksum address here
            ):
                continue

            if ((
                event.event_type == HistoryEventType.TRADE and  # for token to token
                event.event_subtype == HistoryEventSubType.SPEND
            ) or (
                event.event_type == HistoryEventType.SPEND and  # for eth to token
                event.event_subtype == HistoryEventSubType.NONE
            )) and event.address is not None:
                sent_asset = event.asset
                send_address_to_events[event.address] = event

            if ((
                event.event_type == HistoryEventType.TRADE and  # for token to token
                event.event_subtype == HistoryEventSubType.RECEIVE
            ) or (
                event.event_type == HistoryEventType.RECEIVE and  # for token to eth
                event.event_subtype == HistoryEventSubType.NONE
            )) and event.address is not None:
                receive_events.append(event)

        return_amount = ZERO
        for event in receive_events:
            if event.asset == sent_asset:
                return_amount = event.amount
                decoded_events.remove(event)
            else:
                received_asset = event.asset
                receive_address_to_events[event.address] = event  # type: ignore[index]  # address will not be None, checked when appending to receive_events

        if sent_asset is None or received_asset is None:
            return decoded_events  # not a 0x related transaction

        for zero_x_address in (self.router_address, self.flash_wallet_address):
            if (
                not sent_asset.is_evm_token() and  # sent_asset is native currency
                zero_x_address in send_address_to_events and  # is sent to 0x
                send_address_to_events[zero_x_address].event_type == HistoryEventType.SPEND and
                send_address_to_events[zero_x_address].event_subtype == HistoryEventSubType.NONE
            ):
                self._update_send_receive_fee_events(
                    send_event=send_address_to_events[zero_x_address],
                )

            if (
                not received_asset.is_evm_token() and  # received_asset is native_currency
                zero_x_address in receive_address_to_events and  # is received from 0x
                receive_address_to_events[zero_x_address].event_type == HistoryEventType.RECEIVE and  # noqa: E501
                receive_address_to_events[zero_x_address].event_subtype == HistoryEventSubType.NONE
            ):
                self._update_send_receive_fee_events(
                    receive_event=receive_address_to_events[zero_x_address],
                )

        for _log in all_logs:
            send_event = send_address_to_events.get(_log.address)
            receive_event = receive_address_to_events.get(_log.address)
            if (
                _log.topics[0] in UNISWAP_SIGNATURES and
                len(used_router_address := self.router_addresses_set & {
                    bytes_to_address(_log.topics[1]),  # 0x is sender
                    bytes_to_address(_log.topics[2]),  # 0x is receiver
                }) > 0
            ):
                # Some events are already being decoded as a swap through uniswap,
                # and do not have the 0x router address. Therefore, it is necessary
                # to update the events with the values from the 0x protocol. To do this,
                # we need to pass the used router address (ZeroEx or Settler) to update
                # the event with the correct router address.
                self._update_send_receive_fee_events(
                    send_event=send_event,
                    receive_event=receive_event,
                    used_router_address=used_router_address.pop(),
                )

            if (  # sent_token is transferred from tracked sender to 0x
                send_event is not None and
                send_event.asset.is_evm_token() and
                _log.address == send_event.asset.evm_address and  # type: ignore[attr-defined]  # is EVM token
                _log.topics[0] == ERC20_OR_ERC721_TRANSFER and
                bytes_to_address(_log.topics[1]) == send_event.location_label and
                bytes_to_address(_log.topics[2]) == self.flash_wallet_address
            ):
                self._update_send_receive_fee_events(send_event=send_event)

        self._merge_split_swap_events(
            decoded_events=decoded_events,
            send_events=list(send_address_to_events.values()),
            receive_events=list(receive_address_to_events.values()),
            return_amount=return_amount,
        )

        return decoded_events

    def _decode_meta_tx_swap(self, context: 'DecoderContext') -> EvmDecodingOutput:
        """Decodes the swap event from the 0x router contract via executeMetaTransactionV2."""
        if context.tx_log.topics[0] != METATX_ZEROX or context.tx_log.address != self.router_address:  # noqa: E501
            return DEFAULT_EVM_DECODING_OUTPUT

        # using [] for cases with multiple dexes, where multiple send/receive events exist
        send_events, receive_events, fee_event = [], [], None
        for event in context.decoded_events:
            if event.location_label is None or not self.base.is_tracked(event.location_label):  # type: ignore  # it's a checksum address here
                continue

            if (
                event.event_type == HistoryEventType.TRADE and
                event.event_subtype == HistoryEventSubType.SPEND
            ):
                send_events.append(event)

            elif ((
                event.event_type == HistoryEventType.TRADE and
                event.event_subtype == HistoryEventSubType.RECEIVE
            ) or (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.address == self.flash_wallet_address
            )):
                receive_events.append(event)

            elif (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE
            ):
                if event.address == self.flash_wallet_address:
                    send_events.append(event)
                else:
                    fee_event = event

        self._merge_split_swap_events(
            decoded_events=context.decoded_events,
            send_events=send_events,
            receive_events=receive_events,
            fee_event=fee_event,
        )

        return EvmDecodingOutput(process_swaps=True)

    # -- DecoderInterface methods

    # 0x router contract doesn't log most of the events, so we post decode the swap events
    def post_decoding_rules(self) -> dict[str, list[tuple[int, Callable]]]:
        return {CPT_ZEROX: [(-1, self._decode_swap)]}

    def addresses_to_counterparties(self) -> dict[ChecksumEvmAddress, str]:
        return dict.fromkeys(self.router_addresses_set, CPT_ZEROX)

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {self.router_address: (self._decode_meta_tx_swap,)}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_ZEROX,
            label='0x',
            image='0x.svg',
        ),)
