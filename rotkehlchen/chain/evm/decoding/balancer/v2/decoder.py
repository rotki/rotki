import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.utils import CHAIN_TO_WRAPPED_TOKEN
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.ethereum.utils import (
    asset_normalized_value,
)
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.balancer.balancer_cache import (
    read_balancer_pools_and_gauges_from_cache,
)
from rotkehlchen.chain.evm.decoding.balancer.constants import CPT_BALANCER_V2
from rotkehlchen.chain.evm.decoding.balancer.decoder import BalancerCommonDecoder
from rotkehlchen.chain.evm.decoding.balancer.v2.constants import V2_SWAP, VAULT_ADDRESS
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import CacheType, ChecksumEvmAddress, EvmTransaction
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.user_messages import MessagesAggregator


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

POOL_BALANCE_CHANGED_TOPIC = b'\xe5\xce$\x90\x87\xce\x04\xf0Z\x95q\x92CT\x00\xfd\x97\x86\x8d\xba\x0ejKL\x04\x9a\xbf\x8a\xf8\r\xaex'  # noqa: E501


class Balancerv2CommonDecoder(BalancerCommonDecoder):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            counterparty=CPT_BALANCER_V2,
            read_fn=lambda chain_id: read_balancer_pools_and_gauges_from_cache(
                version=2,
                chain_id=chain_id,
                cache_type=CacheType.BALANCER_V2_POOLS,
            ),
        )
        self.wrapped_native_token = CHAIN_TO_WRAPPED_TOKEN[self.node_inquirer.blockchain].resolve_to_evm_token()  # noqa: E501

    def decode_vault_events(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] == V2_SWAP:
            return EvmDecodingOutput(matched_counterparty=CPT_BALANCER_V2)
        if context.tx_log.topics[0] == POOL_BALANCE_CHANGED_TOPIC:
            return self._decode_join_or_exit(context)

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_join_or_exit(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decodes and processes Balancer v2 pool join/exit events"""
        send_events, receive_events = [], []
        for event in context.decoded_events:
            token = event.asset.resolve_to_asset_with_symbol()
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.address == ZERO_ADDRESS
            ):  # exit pool: return wrapped token
                event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                event.notes = f'Return {event.amount} {token.symbol} to a Balancer v2 pool'
                event.counterparty = CPT_BALANCER_V2
                send_events.append(event)

            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.address == context.tx_log.address
            ):  # exit pool: withdraw token
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REDEEM_WRAPPED
                event.counterparty = CPT_BALANCER_V2
                event.notes = f'Receive {event.amount} {token.symbol} after removing liquidity from a Balancer v2 pool'  # noqa: E501
                receive_events.append(event)

            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.address == ZERO_ADDRESS
            ):  # join pool: receive wrapped token
                event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                event.counterparty = CPT_BALANCER_V2
                event.notes = f'Receive {event.amount} {token.symbol} from a Balancer v2 pool'
                receive_events.append(event)

            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.address == VAULT_ADDRESS
            ):  # join pool: deposit token
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
                event.counterparty = CPT_BALANCER_V2
                event.notes = f'Deposit {event.amount} {token.symbol} to a Balancer v2 pool'
                send_events.append(event)

        # in _check_deposits_withdrawals we expect the receive to be the last event.
        # This happens almost always but there are some cases like rETH on arb where it doesn't.
        # This reshuffle ensures that the receive event is always the last one before grouping
        # them in _check_deposits_withdrawals.
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
            transaction: 'EvmTransaction',
            decoded_events: list['EvmEvent'],
            all_logs: list['EvmTxReceiptLog'],
    ) -> list['EvmEvent']:
        """Decode swaps in Balancer v2. SWAP tx_log events are created at the tx start containing
        token and amount information, followed by transfer executions. Since tokens may be swapped
        multiple times before reaching the desired token, the tokens and amounts from all present
        swap logs must be matched against the events.

        Native assets are wrapped/unwrapped before/after the swap, so the token shows as a
        wrapped native asset, but we have a native asset transfer from the user.
        """
        token_amounts_spent, token_amounts_received = set(), set()
        for tx_log in all_logs:
            if tx_log.topics[0] == V2_SWAP:
                token_amounts_spent.add((
                    (from_token := self.base.get_or_create_evm_token(bytes_to_address(tx_log.topics[2]))),  # noqa: E501
                    asset_normalized_value(amount=int.from_bytes(tx_log.data[0:32]), asset=from_token),  # noqa: E501
                ))
                token_amounts_received.add((
                    (to_token := self.base.get_or_create_evm_token(bytes_to_address(tx_log.topics[3]))),  # noqa: E501
                    asset_normalized_value(amount=int.from_bytes(tx_log.data[32:64]), asset=to_token),  # noqa: E501
                ))

        spend_event, receive_event = None, None
        for event in decoded_events:
            if (
                event.event_subtype != HistoryEventSubType.NONE or
                event.address != VAULT_ADDRESS
            ):
                continue  # This event isn't associated with a balancer swap

            if (
                (event_token_amount := (
                    self.wrapped_native_token if event.asset == self.node_inquirer.native_token else event.asset,  # noqa: E501
                    event.amount,
                )) in token_amounts_spent and
                event.event_type == HistoryEventType.SPEND
            ):
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.SPEND
                event.notes = f'Swap {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} via Balancer v2'  # noqa: E501
                event.counterparty = CPT_BALANCER_V2
                spend_event = event
            elif (
                event_token_amount in token_amounts_received and
                event.event_type == HistoryEventType.RECEIVE
            ):
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.RECEIVE
                event.notes = f'Receive {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} as the result of a swap via Balancer v2'  # noqa: E501
                event.counterparty = CPT_BALANCER_V2
                receive_event = event

        if spend_event is None or receive_event is None:
            log.error(f'Failed to find both in and out events for a Balancer v2 swap in {transaction}')  # noqa: E501
        else:
            maybe_reshuffle_events(
                ordered_events=[spend_event, receive_event],
                events_list=decoded_events,
            )

        return decoded_events

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return super().addresses_to_decoders() | {
            VAULT_ADDRESS: (self.decode_vault_events,),
        }

    def post_decoding_rules(self) -> dict[str, list[tuple[int, Callable]]]:
        return {CPT_BALANCER_V2: [(0, self._handle_post_decoding)]}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_BALANCER_V2,
            label=CPT_BALANCER_V2.capitalize().replace('-v', ' V'),
            image='balancer.svg',
        ),)
