from typing import TYPE_CHECKING, Literal

from rotkehlchen.chain.evm.decoding.balancer.constants import CPT_BALANCER_V1, CPT_BALANCER_V2
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import EvmTransaction

if TYPE_CHECKING:
    from rotkehlchen.history.events.structures.evm_event import EvmEvent


class BalancerCommonAccountingMixin:
    def __init__(self, counterparty: Literal['balancer-v1', 'balancer-v2']) -> None:
        self.counterparty = counterparty

    def _check_deposits_withdrawals(
            self,
            transaction: EvmTransaction,  # pylint: disable=unused-argument
            decoded_events: list['EvmEvent'],
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
    ) -> list['EvmEvent']:
        """Order Balancer pool events for accurate accounting.

        OUT events precede IN events:
        - Deposits: asset(s) deposit -> LP token receipt
        - Withdrawals: LP token return -> asset(s) receipt
        """
        related_events: list[EvmEvent] = []
        related_events_map: dict[EvmEvent, list[EvmEvent]] = {}
        # last event is only tracked in the case of exiting a pool
        # and contains the event sending the BPT token
        last_event = None
        for event in decoded_events:
            if event.counterparty != self.counterparty:
                continue

            # When joining a pool:
            # - V1: first we spend the assets, then we receive the BPT token
            # - V2: first we receive the BPT token, then we spend the assets
            # When exiting a pool:
            # First we return the BPT token, then we receive the assets (both V1 and V2)
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.RECEIVE_WRAPPED
            ):  # For V1, we map the deposit events to the pool token event
                if len(related_events) != 0 and self.counterparty == CPT_BALANCER_V1:
                    related_events_map[event] = related_events
                    related_events = []
                    last_event = None
                # For V2, we start tracking events after receiving the pool token
                elif self.counterparty == CPT_BALANCER_V2:
                    related_events = []
                    last_event = event

            elif (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.RETURN_WRAPPED
            ):
                related_events = []
                last_event = event

            elif ((
                event.event_type == HistoryEventType.DEPOSIT and
                event.event_subtype == HistoryEventSubType.DEPOSIT_ASSET
            ) or (
                event.event_type == HistoryEventType.WITHDRAWAL and
                event.event_subtype == HistoryEventSubType.REFUND
            )):  # Handle direction change from spending to receiving assets
                if last_event is not None and last_event.event_type == HistoryEventType.SPEND:
                    # save the exit event and reset the related events
                    related_events_map[last_event] = related_events
                    last_event = None
                    related_events = []

                related_events.append(event)

                if (  # For V2 joins, map deposit events to the preceding pool token event
                    self.counterparty == CPT_BALANCER_V2 and
                    last_event is not None and
                    last_event.event_type == HistoryEventType.RECEIVE
                ):
                    related_events_map[last_event] = related_events

            elif (
                event.event_type == HistoryEventType.WITHDRAWAL and
                event.event_subtype == HistoryEventSubType.REMOVE_ASSET
            ):
                related_events.append(event)

        # Handle any remaining return BPT token operations
        if last_event is not None and last_event.event_type == HistoryEventType.SPEND:
            related_events_map[last_event] = related_events

        if len(related_events_map) == 0:
            # Not a balancer related transaction
            return decoded_events

        for pool_token_event, token_related_events in related_events_map.items():
            if pool_token_event.event_type == HistoryEventType.RECEIVE:
                ordered_events = token_related_events + [pool_token_event]
                pool_token_event.extra_data = {'deposit_events_num': len(token_related_events)}
            else:
                ordered_events = [pool_token_event] + token_related_events
                pool_token_event.extra_data = {'withdrawal_events_num': len(token_related_events)}

            # Sort events: wrapped token first, then related events
            maybe_reshuffle_events(
                ordered_events=ordered_events,
                events_list=decoded_events,
            )

        return decoded_events
