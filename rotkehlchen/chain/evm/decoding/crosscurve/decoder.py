import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.crosscurve.constants import (
    CPT_CROSSCURVE,
    CROSSCHAIN_SWAP_COMPLETED,
    CROSSCHAIN_SWAP_INITIATED,
    CROSSCURVE_CPT_DETAILS,
    CROSSCURVE_RELAYER,
)
from rotkehlchen.chain.evm.decoding.curve.constants import CPT_CURVE
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from collections.abc import Callable

    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.types import EvmTransaction
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class CrossCurveCommonDecoder(EvmDecoderInterface):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            router_addresses: tuple[ChecksumEvmAddress, ...],
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.router_addresses = router_addresses

    def _post_decode_send(
            self,
            transaction: 'EvmTransaction',
            decoded_events: list['EvmEvent'],
            all_logs: list['EvmTxReceiptLog'],
    ) -> list['EvmEvent']:
        """Run after all events are decoded to label CrossCurve bridge send events.

        Scans all_logs for CROSSCHAIN_SWAP_INITIATED events on our router addresses.
        At this point all decoded_events are available, including the bridged token transfer.
        """
        for tx_log in all_logs:
            if (
                tx_log.address not in self.router_addresses or
                len(tx_log.topics) < 2 or
                tx_log.topics[0] != CROSSCHAIN_SWAP_INITIATED
            ):
                continue

            sender = bytes_to_address(tx_log.topics[1])
            if not self.base.is_tracked(sender):
                continue

            router_address = tx_log.address
            bridge_found = False
            for event in decoded_events:
                if (
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.location_label == sender
                ):
                    if event.address == router_address:
                        # Native token sent to the router as cross-chain messaging fee
                        event.event_subtype = HistoryEventSubType.FEE
                        event.counterparty = CPT_CROSSCURVE
                        event.notes = f'Pay {event.amount} {event.asset.symbol_or_name()} as CrossCurve bridge fee'  # noqa: E501
                    else:
                        event.event_type = HistoryEventType.DEPOSIT
                        event.event_subtype = HistoryEventSubType.BRIDGE
                        event.counterparty = CPT_CROSSCURVE
                        event.notes = f'Bridge {event.amount} {event.asset.symbol_or_name()} via CrossCurve'  # noqa: E501
                        bridge_found = True

            if not bridge_found:
                log.error(
                    f'Could not find token transfer event for CrossCurve bridge send in '
                    f'{transaction.tx_hash!s}',
                )

        return decoded_events

    def _decode_receive(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] != CROSSCHAIN_SWAP_COMPLETED:
            return DEFAULT_EVM_DECODING_OUTPUT

        found = False
        for event in context.decoded_events:
            if not self.base.is_tracked(event.location_label):  # type: ignore[arg-type]
                continue
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE
            ) or (
                # CrossCurve uses Curve pool liquidity to complete bridges, so the
                # receive event may already be decoded as a Curve withdrawal.
                event.event_type == HistoryEventType.WITHDRAWAL and
                event.event_subtype == HistoryEventSubType.REDEEM_WRAPPED and
                event.counterparty == CPT_CURVE
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.BRIDGE
                event.counterparty = CPT_CROSSCURVE
                event.notes = f'Bridge {event.amount} {event.asset.symbol_or_name()} via CrossCurve'  # noqa: E501
                found = True

        if not found:
            log.error(
                f'Could not find token transfer event for CrossCurve bridge receive in '
                f'{context.transaction.tx_hash!s}',
            )

        return DEFAULT_EVM_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {CROSSCURVE_RELAYER: (self._decode_receive,)}

    def addresses_to_counterparties(self) -> dict[ChecksumEvmAddress, str]:
        return dict.fromkeys(self.router_addresses, CPT_CROSSCURVE)

    def post_decoding_rules(self) -> dict[str, list[tuple[int, 'Callable']]]:
        return {CPT_CROSSCURVE: [(0, self._post_decode_send)]}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CROSSCURVE_CPT_DETAILS,)
