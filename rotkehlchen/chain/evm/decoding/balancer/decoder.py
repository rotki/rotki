from abc import ABC
from collections.abc import Callable
from typing import TYPE_CHECKING, Literal

from rotkehlchen.assets.utils import asset_normalized_value
from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.constants import DEPOSIT_TOPIC_V2, WITHDRAW_TOPIC_V2
from rotkehlchen.chain.evm.decoding.balancer.balancer_cache import query_balancer_data
from rotkehlchen.chain.evm.decoding.balancer.constants import (
    BALANCER_CACHE_TYPE_MAPPING,
    BALANCER_VERSION_MAPPING,
    CPT_BALANCER_V1,
    CPT_BALANCER_V2,
)
from rotkehlchen.chain.evm.decoding.interfaces import (
    EvmDecoderInterface,
    ReloadablePoolsAndGaugesDecoderMixin,
)
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import ChainID, ChecksumEvmAddress, EvmTransaction

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.user_messages import MessagesAggregator


class BalancerCommonDecoder(EvmDecoderInterface, ReloadablePoolsAndGaugesDecoderMixin, ABC):
    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            counterparty: Literal['balancer-v1', 'balancer-v2', 'balancer-v3'],
            read_fn: Callable[[ChainID], tuple[set[ChecksumEvmAddress], set[ChecksumEvmAddress]]],
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        ReloadablePoolsAndGaugesDecoderMixin.__init__(
            self,
            evm_inquirer=evm_inquirer,
            cache_type_to_check_for_freshness=BALANCER_CACHE_TYPE_MAPPING[counterparty],
            query_data_method=lambda inquirer, cache_type, msg_aggregator, reload_all: query_balancer_data(  # noqa: E501
                inquirer=inquirer,
                cache_type=cache_type,
                protocol=counterparty,
                msg_aggregator=msg_aggregator,
                version=BALANCER_VERSION_MAPPING[counterparty],
                reload_all=reload_all,
            ),
            read_data_from_cache_method=read_fn,
            chain_id=evm_inquirer.chain_id,
        )
        self.counterparty: Literal['balancer-v1', 'balancer-v2', 'balancer-v3'] = counterparty

    @property
    def pools(self) -> set[ChecksumEvmAddress]:
        assert isinstance(self.cache_data[0], set), f'{self.counterparty} Decoder cache_data[0] is not a set'  # noqa: E501
        return self.cache_data[0]

    def _decode_gauge_events(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] not in (DEPOSIT_TOPIC_V2, WITHDRAW_TOPIC_V2):
            return DEFAULT_EVM_DECODING_OUTPUT

        gauge_asset = self.base.get_or_create_evm_token(context.tx_log.address)
        amount = asset_normalized_value(
            amount=int.from_bytes(context.tx_log.data[:32]),
            asset=gauge_asset,
        )
        paired_events_data, from_event_type, from_event_subtype, to_event_type, to_event_subtype, to_notes = None, None, None, None, None, ''  # noqa: E501
        for event in context.decoded_events:
            if (
                 event.amount != amount or
                 event.event_subtype != HistoryEventSubType.NONE or
                 (evm_asset := event.asset.resolve_to_evm_token()).evm_address not in self.pools
            ):
                continue

            if event.event_type == HistoryEventType.SPEND:
                paired_events_data = ([event], True)
                from_event_type = HistoryEventType.RECEIVE
                from_event_subtype = HistoryEventSubType.NONE
                to_event_type = HistoryEventType.RECEIVE
                to_event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                to_notes = f'Receive {amount} {gauge_asset.symbol} after depositing in {self.counterparty} gauge'  # noqa: E501

                event.counterparty = self.counterparty
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
                event.notes = f'Deposit {amount} {evm_asset.symbol} into {self.counterparty} gauge'
            elif event.event_type == HistoryEventType.RECEIVE:
                paired_events_data = ([event], False)
                from_event_type = HistoryEventType.SPEND
                from_event_subtype = HistoryEventSubType.NONE
                to_event_type = HistoryEventType.SPEND
                to_event_subtype = HistoryEventSubType.RETURN_WRAPPED
                to_notes = f'Return {amount} {gauge_asset.symbol} after withdrawing from {self.counterparty} gauge'  # noqa: E501

                event.counterparty = self.counterparty
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REDEEM_WRAPPED
                event.notes = f'Withdraw {amount} {evm_asset.symbol} from {self.counterparty} gauge'  # noqa: E501

        return EvmDecodingOutput(action_items=[] if paired_events_data is None else [
            ActionItem(
                action='transform',
                from_event_type=from_event_type,  # type: ignore[arg-type]  # it cannot be none if paired_events_data is present
                from_event_subtype=from_event_subtype,  # type: ignore[arg-type] # it cannot be none if paired_events_data is present
                asset=gauge_asset,
                amount=amount,
                to_counterparty=self.counterparty,
                to_notes=to_notes,
                paired_events_data=paired_events_data,
                to_event_type=to_event_type,
                to_event_subtype=to_event_subtype,
            ),
        ])

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
                event.event_subtype == HistoryEventSubType.DEPOSIT_FOR_WRAPPED
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
                event.event_subtype == HistoryEventSubType.REDEEM_WRAPPED
            ):
                related_events.append(event)

        # Handle any remaining return BPT token operations
        if last_event is not None and last_event.event_type == HistoryEventType.SPEND:
            related_events_map[last_event] = related_events

        if len(related_events_map) == 0:
            return decoded_events  # Not a balancer related transaction

        for pool_token_event, token_related_events in related_events_map.items():
            if pool_token_event.event_type == HistoryEventType.RECEIVE:
                ordered_events = token_related_events + [pool_token_event]
            else:
                ordered_events = [pool_token_event] + token_related_events

            # Sort events: wrapped token first, then related events
            maybe_reshuffle_events(
                ordered_events=ordered_events,
                events_list=decoded_events,
            )

        return decoded_events
