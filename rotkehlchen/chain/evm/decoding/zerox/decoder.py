import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.modules.uniswap.constants import UNISWAP_SIGNATURES
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.transactions import EvmTransactions
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction
from rotkehlchen.utils.misc import hex_or_bytes_to_address

from .constants import CPT_ZEROX

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class ZeroxCommonDecoder(DecoderInterface):
    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            router_address: ChecksumEvmAddress,
            flash_wallet_address: ChecksumEvmAddress,
            native_currency: Asset,
    ) -> None:
        """router_address is the main point of contact with the 0x protocol.
        flash_wallet_address is a contract that can execute arbitrary calls from 0x router_address.
        Docs: https://0x.org/docs/introduction/0x-cheat-sheet#exchange-proxy-addresses"""
        super().__init__(evm_inquirer, base_tools, msg_aggregator)
        self.evm_txns = EvmTransactions(self.evm_inquirer, self.base.database)
        self.router_address = router_address
        self.flash_wallet_address = flash_wallet_address
        self.native_currency = native_currency

    def _update_send_and_receive_events(
            self,
            send_event: 'EvmEvent | None' = None,
            receive_event: 'EvmEvent | None' = None,
    ) -> None:
        """An auxiliary function to update the send and/or receive events with the 0x values"""
        if send_event is not None:
            send_event.counterparty = CPT_ZEROX
            send_event.address = self.router_address
            send_event.event_type = HistoryEventType.TRADE
            send_event.event_subtype = HistoryEventSubType.SPEND
            send_event.notes = f'Swap {send_event.balance.amount} {send_event.asset.symbol_or_name()} via the 0x protocol'  # noqa: E501
        if receive_event is not None:
            receive_event.counterparty = CPT_ZEROX
            receive_event.address = self.router_address
            receive_event.event_type = HistoryEventType.TRADE
            receive_event.event_subtype = HistoryEventSubType.RECEIVE
            receive_event.notes = f'Receive {receive_event.balance.amount} {receive_event.asset.symbol_or_name()} as the result of a swap via the 0x protocol'  # noqa: E501

    def _decode_swap(
            self,
            transaction: 'EvmTransaction',
            decoded_events: 'list[EvmEvent]',
            all_logs: 'list[EvmTxReceiptLog]',
    ) -> 'list[EvmEvent]':
        """This function is used to decode the swaps done via 0x. It checks if already decoded
        events interacted with the 0x router, and overwrites them if they did."""
        send_address_to_events: dict[ChecksumEvmAddress, 'EvmEvent'] = {}
        receive_address_to_events: dict[ChecksumEvmAddress, 'EvmEvent'] = {}
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
                received_asset = event.asset
                receive_address_to_events[event.address] = event

        if sent_asset is None or received_asset is None:
            return decoded_events  # not a 0x related transaction

        for zero_x_address in (self.router_address, self.flash_wallet_address):
            if (
                not sent_asset.is_evm_token() and  # sent_asset is native currency
                zero_x_address in send_address_to_events and  # is sent to 0x
                send_address_to_events[zero_x_address].event_type == HistoryEventType.SPEND and
                send_address_to_events[zero_x_address].event_subtype == HistoryEventSubType.NONE
            ):
                self._update_send_and_receive_events(
                    send_event=send_address_to_events[zero_x_address],
                )

            if (
                not received_asset.is_evm_token() and  # received_asset is native_currency
                zero_x_address in receive_address_to_events and  # is received from 0x
                receive_address_to_events[zero_x_address].event_type == HistoryEventType.RECEIVE and  # noqa: E501
                receive_address_to_events[zero_x_address].event_subtype == HistoryEventSubType.NONE
            ):
                self._update_send_and_receive_events(
                    receive_event=receive_address_to_events[zero_x_address],
                )

        for _log in all_logs:
            send_event = send_address_to_events.get(_log.address)
            receive_event = receive_address_to_events.get(_log.address)

            if _log.topics[0] in UNISWAP_SIGNATURES and self.router_address in {
                hex_or_bytes_to_address(_log.topics[1]),  # 0x is sender
                hex_or_bytes_to_address(_log.topics[2]),  # 0x is receiver
            }:
                self._update_send_and_receive_events(send_event=send_event, receive_event=receive_event)  # noqa: E501

            if (  # sent_token is transfered from tracked sender to 0x
                send_event is not None and
                send_event.asset.is_evm_token() and
                _log.address == send_event.asset.evm_address and  # type: ignore[attr-defined]  # is EVM token
                _log.topics[0] == ERC20_OR_ERC721_TRANSFER and
                hex_or_bytes_to_address(_log.topics[1]) == send_event.location_label and
                hex_or_bytes_to_address(_log.topics[2]) == self.flash_wallet_address
            ):
                self._update_send_and_receive_events(send_event=send_event)

        summed_send_event, summed_receive_event = (
            self.base.make_event_next_index(
                tx_hash=transaction.tx_hash,
                timestamp=transaction.timestamp,
                asset=asset,
                balance=Balance(),  # Empty init. Populated below
                event_type=HistoryEventType.TRADE,
                event_subtype=subtype,
                location_label=transaction.from_address,
            ) for asset, subtype in (
                (sent_asset, HistoryEventSubType.SPEND),
                (received_asset, HistoryEventSubType.RECEIVE),
            )
        )

        for send_event in send_address_to_events.values():
            summed_send_event.balance += send_event.balance  # add sent balances
            decoded_events.remove(send_event)
        for receive_event in receive_address_to_events.values():
            summed_receive_event.balance += receive_event.balance  # add received balances
            decoded_events.remove(receive_event)

        self._update_send_and_receive_events(
            send_event=summed_send_event,
            receive_event=summed_receive_event,
        )

        decoded_events.append(summed_send_event)
        decoded_events.append(summed_receive_event)
        maybe_reshuffle_events(
            ordered_events=[summed_send_event, summed_receive_event],
            events_list=decoded_events,
        )

        return decoded_events

    # -- DecoderInterface methods

    # 0x router contract doesn't log most of the events, so we post decode the swap events
    def post_decoding_rules(self) -> dict[str, list[tuple[int, Callable]]]:
        return {CPT_ZEROX: [(-1, self._decode_swap)]}

    def addresses_to_counterparties(self) -> dict[ChecksumEvmAddress, str]:
        return {self.router_address: CPT_ZEROX}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_ZEROX,
            label='0x',
            image='0x.svg',
        ),)
