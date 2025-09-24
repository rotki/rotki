import abc
import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.llamazip.constants import CPT_LLAMAZIP, LLAMAZIP_CPT_DETAILS
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class LlamazipCommonDecoder(DecoderInterface, abc.ABC):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            router_addresses: tuple['ChecksumEvmAddress', ...],
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.router_addresses = router_addresses

    def _decode_swap(
            self,
            transaction: EvmTransaction,
            decoded_events: list['EvmEvent'],
            all_logs: list['EvmTxReceiptLog'],  # pylint: disable=unused-argument
    ) -> list['EvmEvent']:
        spend_event = receive_event = None
        for event in decoded_events:
            if (
                (event.event_type == HistoryEventType.TRADE and event.event_subtype == HistoryEventSubType.SPEND) or  # noqa: E501
                (event.event_type == HistoryEventType.SPEND and event.event_subtype == HistoryEventSubType.NONE)  # noqa: E501
            ):
                spend_event = event
                spend_event.counterparty = CPT_LLAMAZIP
                spend_event.event_type = HistoryEventType.TRADE
                spend_event.event_subtype = HistoryEventSubType.SPEND
                spend_event.notes = f'Swap {event.amount} {event.asset.symbol_or_name()} in LlamaZip'  # noqa: E501
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.address in self.router_addresses
            ):
                receive_event = event
                receive_event.event_type = HistoryEventType.TRADE
                receive_event.event_subtype = HistoryEventSubType.RECEIVE
                receive_event.notes = f'Receive {event.amount} {event.asset.symbol_or_name()} as the result of a swap in LlamaZip'  # noqa: E501

        if None not in (spend_event, receive_event):
            maybe_reshuffle_events(
                ordered_events=[spend_event, receive_event],
                events_list=decoded_events,
            )
        else:
            log.error(f'Failed to find LlamaZip swap events for {transaction}')

        return decoded_events

    # -- DecoderInterface methods

    def addresses_to_counterparties(self) -> dict[ChecksumEvmAddress, str]:
        return dict.fromkeys(self.router_addresses, CPT_LLAMAZIP)

    def post_decoding_rules(self) -> dict[str, list[tuple[int, Callable]]]:
        return {CPT_LLAMAZIP: [(0, self._decode_swap)]}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (LLAMAZIP_CPT_DETAILS,)
