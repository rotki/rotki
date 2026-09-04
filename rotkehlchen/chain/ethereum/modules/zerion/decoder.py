import logging
from typing import TYPE_CHECKING

from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter

from .constants import (
    CPT_ZERION,
    EXECUTED_ACTION,
    ZERION_CORE,
    ZERION_CPT_DETAILS,
    ZERION_ROUTER,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from rotkehlchen.chain.decoding.types import CounterpartyDetails
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class ZerionDecoder(EvmDecoderInterface):
    """Decoder for the Zerion DeFi SDK router (https://github.com/zeriontech/defi-sdk).

    The router chains protocol adapters (Uniswap, Curve, yearn, Balancer, ...) in a single
    transaction: it pulls the input assets from the user into the Core contract, runs the
    adapters there and sends whatever comes out back to the user. Since the intermediate steps
    never touch the user's address, the whole execution is treated as a swap of the assets the
    user sent for the assets the user got back, mentioning the adapters that were used.
    """

    @staticmethod
    def _get_used_protocols(all_logs: list[EvmTxReceiptLog]) -> list[str]:
        """Return the names of the protocol adapters executed by the Core, in execution order"""
        protocols: list[str] = []
        for tx_log in all_logs:
            if tx_log.address != ZERION_CORE or tx_log.topics[0] != EXECUTED_ACTION:
                continue

            # The log data is an abi encoded Action struct. Its first dynamic field is the
            # bytes32 adapter name, which uses the last byte as an adapter version number.
            name = tx_log.data[32:63].rstrip(b'\x00').decode('ascii', errors='ignore')
            if name != '' and name not in protocols:
                protocols.append(name)

        return protocols

    def _process_execution(
            self,
            transaction: EvmTransaction,
            decoded_events: list[EvmEvent],
            all_logs: list[EvmTxReceiptLog],
    ) -> list[EvmEvent]:
        out_events, in_events = [], []
        for event in decoded_events:
            if event.address not in (ZERION_ROUTER, ZERION_CORE):
                continue

            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE
            ):
                out_events.append(event)
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE
            ):
                in_events.append(event)

        if len(out_events) == 0 or len(in_events) == 0:
            log.debug(
                'Could not find both sides of the zerion execution',
                tx_hash=transaction.tx_hash.hex(),
            )
            return decoded_events

        used_protocols = self._get_used_protocols(all_logs)
        protocols_suffix = f' using {", ".join(used_protocols)}' if len(used_protocols) != 0 else ''  # noqa: E501
        for event in out_events:
            event.event_type = HistoryEventType.TRADE
            event.event_subtype = HistoryEventSubType.SPEND
            event.counterparty = CPT_ZERION
            event.address = ZERION_ROUTER
            event.notes = f'Swap {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} in Zerion{protocols_suffix}'  # noqa: E501

        for event in in_events:
            event.event_type = HistoryEventType.TRADE
            event.event_subtype = HistoryEventSubType.RECEIVE
            event.counterparty = CPT_ZERION
            event.address = ZERION_ROUTER
            event.notes = f'Receive {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} as the result of a swap in Zerion'  # noqa: E501

        maybe_reshuffle_events(
            ordered_events=out_events + in_events,
            events_list=decoded_events,
        )
        return decoded_events

    # -- DecoderInterface methods

    def addresses_to_counterparties(self) -> dict[ChecksumEvmAddress, str]:
        return {ZERION_ROUTER: CPT_ZERION, ZERION_CORE: CPT_ZERION}

    def post_decoding_rules(self) -> dict[str, list[tuple[int, Callable]]]:
        return {CPT_ZERION: [(0, self._process_execution)]}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (ZERION_CPT_DETAILS,)
