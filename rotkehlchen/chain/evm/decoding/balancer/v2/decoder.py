import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.utils import asset_normalized_value
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.balancer.balancer_cache import (
    read_balancer_pools_and_gauges_from_cache,
)
from rotkehlchen.chain.evm.decoding.balancer.constants import (
    BALANCER_CACHE_TYPE_MAPPING,
    BALANCER_LABEL,
    BALANCER_VERSION_MAPPING,
    CPT_BALANCER_V2,
        BalancerCounterparty,
)
from rotkehlchen.chain.evm.decoding.balancer.decoder import BalancerCommonDecoder
from rotkehlchen.chain.evm.decoding.balancer.v2.constants import V2_SWAP, VAULT_ADDRESS
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from collections.abc import Callable

    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction
    from rotkehlchen.user_messages import MessagesAggregator


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

POOL_BALANCE_CHANGED_TOPIC = b'\xe5\xce$\x90\x87\xce\x04\xf0Z\x95q\x92CT\x00\xfd\x97\x86\x8d\xba\x0ejKL\x04\x9a\xbf\x8a\xf8\r\xaex'  # noqa: E501


class Balancerv2CommonDecoder(BalancerCommonDecoder):

    def __init__(
            self,
            evm_inquirer: EvmNodeInquirer,
            base_tools: BaseEvmDecoderTools,
            msg_aggregator: MessagesAggregator,
            counterparty: BalancerCounterparty = CPT_BALANCER_V2,
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            counterparty=counterparty,
            read_fn=lambda chain_id: read_balancer_pools_and_gauges_from_cache(
                version=BALANCER_VERSION_MAPPING[counterparty],
                chain_id=chain_id,
                cache_type=BALANCER_CACHE_TYPE_MAPPING[counterparty],
            ),
        )

    def decode_vault_events(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] == V2_SWAP:
            return EvmDecodingOutput(matched_counterparty=self.counterparty)
        if context.tx_log.topics[0] == POOL_BALANCE_CHANGED_TOPIC:
            return self._decode_join_or_exit(context)

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_join_or_exit(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decodes and processes Balancer v2 pool join/exit events"""
        send_events, receive_events = [], []
        pool_label = self.protocol_label
        for event in context.decoded_events:
            token = event.asset.resolve_to_asset_with_symbol()
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.address == ZERO_ADDRESS
            ):  # exit pool: return wrapped token
                event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                event.notes = f'Return {event.amount} {token.symbol} to a {pool_label} pool'
                event.counterparty = self.counterparty
                send_events.append(event)

            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.address == context.tx_log.address
            ):  # exit pool: withdraw token
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REDEEM_WRAPPED
                event.counterparty = self.counterparty
                event.notes = f'Receive {event.amount} {token.symbol} after removing liquidity from a {pool_label} pool'  # noqa: E501
                receive_events.append(event)

            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.address == ZERO_ADDRESS
            ):  # join pool: receive wrapped token
                event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                event.counterparty = self.counterparty
                event.notes = f'Receive {event.amount} {token.symbol} from a {pool_label} pool'
                receive_events.append(event)

            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.address == VAULT_ADDRESS
            ):  # join pool: deposit token
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
                event.counterparty = self.counterparty
                event.notes = f'Deposit {event.amount} {token.symbol} to a {pool_label} pool'
                send_events.append(event)

        # Keep receive last before grouping in _check_deposits_withdrawals.
        maybe_reshuffle_events(
            ordered_events=send_events + receive_events,
            events_list=context.decoded_events,
        )
        self._check_deposits_withdrawals(
            all_logs=context.all_logs,
            transaction=context.transaction,
            decoded_events=context.decoded_events,
        )
        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_pool_events(self, context: DecoderContext) -> EvmDecodingOutput:
        return DEFAULT_EVM_DECODING_OUTPUT  # no-op

    def _handle_post_decoding(
            self,
            transaction: EvmTransaction,
            decoded_events: list[EvmEvent],
            all_logs: list[EvmTxReceiptLog],
    ) -> list[EvmEvent]:
        """Decode Balancer v2 swaps by matching swap logs against transfer events."""
        token_amounts_spent, token_amounts_received = set(), set()
        total_token_amounts_spent: defaultdict[Any, Any] = defaultdict(lambda: ZERO)
        total_token_amounts_received: defaultdict[Any, Any] = defaultdict(lambda: ZERO)
        for tx_log in all_logs:
            if tx_log.topics[0] == V2_SWAP:
                token_amounts_spent.add(((from_token := self.base.get_or_create_evm_token(bytes_to_address(tx_log.topics[2]))), (from_amount := asset_normalized_value(amount=int.from_bytes(tx_log.data[0:32]), asset=from_token))))  # noqa: E501
                token_amounts_received.add(((to_token := self.base.get_or_create_evm_token(bytes_to_address(tx_log.topics[3]))), (to_amount := asset_normalized_value(amount=int.from_bytes(tx_log.data[32:64]), asset=to_token))))  # noqa: E501
                total_token_amounts_spent[from_token] += from_amount
                total_token_amounts_received[to_token] += to_amount

        spend_event, receive_event = None, None
        for event in decoded_events:
            if (
                event.event_subtype != HistoryEventSubType.NONE or
                event.address != VAULT_ADDRESS
            ):
                continue  # This event isn't associated with a balancer swap
            event_token = self.node_inquirer.wrapped_native_token if event.asset == self.node_inquirer.native_token else event.asset  # noqa: E501
            event_token_amount = (event_token, event.amount)

            if (
                event_token_amount in token_amounts_spent and
                event.event_type == HistoryEventType.SPEND
            ):
                spend_event = event
            elif (
                event_token_amount in token_amounts_received and
                event.event_type == HistoryEventType.RECEIVE
            ):
                receive_event = event
            elif (
                event.event_type == HistoryEventType.SPEND and
                total_token_amounts_spent.get(event_token, ZERO) == event.amount
            ):
                # Some batch swaps emit multiple V2_SWAP logs for the same token pair,
                # but transfer events are netted into a single spend/receive transfer.
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.SPEND
                event.notes = f'Swap {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} via {self.protocol_label}'  # noqa: E501
                event.counterparty = self.counterparty
                spend_event = event
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                total_token_amounts_received.get(event_token, ZERO) == event.amount
            ):
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.RECEIVE
                event.notes = f'Receive {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} as the result of a swap via {self.protocol_label}'  # noqa: E501
                event.counterparty = self.counterparty
                receive_event = event

        if spend_event is None or receive_event is None:
            log.error(f'Failed to find both in and out events for a Balancer v2 swap in {transaction}')  # noqa: E501
        else:
            self._finalize_swap_events(
                decoded_events=decoded_events,
                spend_event=spend_event,
                receive_event=receive_event,
            )

        return decoded_events

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return super().addresses_to_decoders() | {
            VAULT_ADDRESS: (self.decode_vault_events,),
        }

    def post_decoding_rules(self) -> dict[str, list[tuple[int, Callable]]]:
        return {self.counterparty: [(0, self._handle_post_decoding)]}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_BALANCER_V2,
            label=BALANCER_LABEL,
            image='balancer.svg',
        ),)
