import logging
from collections import defaultdict
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from eth_abi import decode as decode_abi

from rotkehlchen.assets.utils import CHAIN_TO_WRAPPED_TOKEN, asset_normalized_value
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.balancer.balancer_cache import (
    read_balancer_pools_and_gauges_from_cache,
)
from rotkehlchen.chain.evm.decoding.balancer.constants import BALANCER_LABEL, CPT_BALANCER_V3
from rotkehlchen.chain.evm.decoding.balancer.decoder import BalancerCommonDecoder
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import CacheType, ChecksumEvmAddress, EvmTransaction
from rotkehlchen.utils.misc import bytes_to_address

from .constants import (
    BALANCER_V3_POOL_ABI,
    CPT_BALANCER_SWAP_V3,
    LIQUIDITY_ADDED_TOPIC,
    LIQUIDITY_REMOVED_TOPIC,
    SWAP_TOPIC,
    VAULT_ADDRESS,
)

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.fval import FVal
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Balancerv3CommonDecoder(BalancerCommonDecoder):

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
            counterparty=CPT_BALANCER_V3,
            read_fn=lambda chain_id: read_balancer_pools_and_gauges_from_cache(
                version=3,
                chain_id=chain_id,
                cache_type=CacheType.BALANCER_V3_POOLS,
            ),
        )
        self.wrapped_native_token = CHAIN_TO_WRAPPED_TOKEN[evm_inquirer.blockchain]

    def _decode_pool_events(self, context: DecoderContext) -> EvmDecodingOutput:
        # no-op implementation of abstract method from ReloadablePoolsAndGaugesDecoderMixin.
        # balancer v3 pool deposits and withdrawals are handled by _decode_liquidity_event.
        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_liquidity_event(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode liquidity events (inflow & outflow) for Balancer V3 pools."""
        if context.tx_log.topics[0] not in (LIQUIDITY_ADDED_TOPIC, LIQUIDITY_REMOVED_TOPIC):
            return DEFAULT_EVM_DECODING_OUTPUT

        if context.tx_log.topics[0] == LIQUIDITY_ADDED_TOPIC:
            pool_token_event_type = HistoryEventType.RECEIVE
            pool_token_event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
            pool_token_notes_template = 'Receive {amount} {symbol} from a Balancer v3 pool'
            from_event_type = HistoryEventType.SPEND
            to_event_type = HistoryEventType.DEPOSIT
            to_event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
            to_notes_template = 'Deposit {amount} {symbol} to a Balancer v3 pool'
        else:  # LIQUIDITY_REMOVED_TOPIC
            pool_token_event_type = HistoryEventType.SPEND
            pool_token_event_subtype = HistoryEventSubType.RETURN_WRAPPED
            pool_token_notes_template = 'Return {amount} {symbol} to a Balancer v3 pool'
            from_event_type = HistoryEventType.RECEIVE
            to_event_type = HistoryEventType.WITHDRAWAL
            to_event_subtype = HistoryEventSubType.REDEEM_WRAPPED
            to_notes_template = 'Withdraw {amount} {symbol} from a Balancer v3 pool'

        pool_tokens = self.node_inquirer.call_contract(
            contract_address=(lp_token_address := bytes_to_address(context.tx_log.topics[1])),
            method_name='getTokens',
            abi=BALANCER_V3_POOL_ABI,
        )
        lp_token_identifier = evm_address_to_identifier(
            address=lp_token_address,
            chain_id=self.node_inquirer.chain_id,
        )
        pool_token_event = None
        for event in context.decoded_events:
            if (
                    event.event_type == pool_token_event_type and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.address == ZERO_ADDRESS and
                    event.asset == lp_token_identifier
            ):
                event.event_subtype = pool_token_event_subtype
                event.counterparty = CPT_BALANCER_V3
                event.notes = pool_token_notes_template.format(
                    amount=event.amount,
                    symbol=event.asset.resolve_to_asset_with_symbol().symbol,
                )
                pool_token_event = event

        if pool_token_event is None:
            log.error(f'Failed to find balancer v3 pool token event in transaction {context.transaction}')  # noqa: E501
            return DEFAULT_EVM_DECODING_OUTPUT

        action_items = []
        amounts = decode_abi(  # totalSupply, amounts, swapFeeAmountsRaw
            types=['uint256', 'uint256[]', 'uint256[]'],
            data=context.tx_log.data,
        )[1]
        for token_address, amount_raw in zip(pool_tokens, amounts, strict=False):
            if amount_raw == 0:
                continue

            # Match both wrapped and native tokens since
            # pools may unwrap WETH to ETH and vice-versa
            amount = asset_normalized_value(
                amount=amount_raw,
                asset=(token := self.base.get_or_create_evm_asset(deserialize_evm_address(token_address))),  # noqa: E501
            )
            if token == self.wrapped_native_token:
                for event in context.decoded_events:
                    if (
                            event.event_type == from_event_type and
                            event.event_subtype == HistoryEventSubType.NONE and
                            event.asset == self.node_inquirer.native_token and
                            event.amount == amount
                    ):
                        event.event_type = to_event_type
                        event.counterparty = CPT_BALANCER_V3
                        event.event_subtype = to_event_subtype
                        event.notes = to_notes_template.format(
                            amount=event.amount,
                            symbol=self.node_inquirer.native_token.symbol,
                        )
                        break

            action_items.append(ActionItem(
                action='transform',
                from_event_type=from_event_type,
                from_event_subtype=HistoryEventSubType.NONE,
                amount=amount,
                asset=token,
                to_event_type=to_event_type,
                to_event_subtype=to_event_subtype,
                to_notes=to_notes_template.format(amount=amount, symbol=token.symbol),
                to_counterparty=CPT_BALANCER_V3,
            ))

        return EvmDecodingOutput(action_items=action_items, matched_counterparty=CPT_BALANCER_V3)

    @staticmethod
    def _decode_swap_event(context: DecoderContext) -> EvmDecodingOutput:
        """Identifies swap events and marks them for later processing."""
        return EvmDecodingOutput(matched_counterparty=CPT_BALANCER_SWAP_V3)

    @staticmethod
    def _order_lp_events(
            transaction: 'EvmTransaction',
            decoded_events: list['EvmEvent'],
            all_logs: list['EvmTxReceiptLog'],
    ) -> list['EvmEvent']:
        """Order liquidity provision events for proper display."""
        deposit_events, receive_events, return_events, withdrawal_events = [], [], [], []
        for event in decoded_events:
            if event.counterparty != CPT_BALANCER_V3:
                continue

            if event.event_subtype == HistoryEventSubType.DEPOSIT_FOR_WRAPPED:
                deposit_events.append(event)
            elif event.event_subtype == HistoryEventSubType.RECEIVE_WRAPPED:
                receive_events.append(event)
            elif event.event_subtype == HistoryEventSubType.RETURN_WRAPPED:
                return_events.append(event)
            elif event.event_subtype == HistoryEventSubType.REDEEM_WRAPPED:
                withdrawal_events.append(event)

        # For LP addition: deposit events first, then receive wrapped
        # For LP removal: return wrapped first, then withdrawal events
        maybe_reshuffle_events(
            ordered_events=deposit_events + receive_events + return_events + withdrawal_events,
            events_list=decoded_events,
        )
        return decoded_events

    def _process_swap_events(
            self,
            transaction: 'EvmTransaction',
            decoded_events: list['EvmEvent'],
            all_logs: list['EvmTxReceiptLog'],
    ) -> list['EvmEvent']:
        """Process Balancer v3 swap events by consolidating transfers into proper trade events.

        Reads swap logs to identify which tokens are involved in swaps, then transforms
        corresponding transfer events into trade events. Removes duplicate events for the same token.
        """  # noqa: E501
        in_assets, out_assets = set(), set()
        for tx_log in all_logs:
            if tx_log.topics[0] != SWAP_TOPIC:
                continue

            # track involved assets only, not amounts. When multiple swaps occur in a transaction,
            # wrapping/unwrapping operations can happen before swaps, so using individual
            # swap log amounts would miss wrapped token portions and only capture direct
            # swap amounts, leading to incomplete event matching across the full transaction flow
            if (token_out := self.base.get_or_create_evm_asset(bytes_to_address(tx_log.topics[2]))) == self.wrapped_native_token:  # noqa: E501
                out_assets.add(self.node_inquirer.native_token)
            if (token_in := self.base.get_or_create_evm_asset(bytes_to_address(tx_log.topics[3]))) == self.wrapped_native_token:  # noqa: E501
                in_assets.add(self.node_inquirer.native_token)

            in_assets.add(token_in)
            out_assets.add(token_out)

        # collect amounts, find events to transform, and identify duplicates
        out_amounts: defaultdict[Asset, FVal] = defaultdict(lambda: ZERO)
        in_amounts: defaultdict[Asset, FVal] = defaultdict(lambda: ZERO)
        processed_tokens, in_event, out_event, events_to_remove = set(), None, None, []
        for event in decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset in out_assets
            ):  # accumulate amounts and keep one event to transform
                out_amounts[event.asset] += event.amount
                if event.asset in processed_tokens:
                    events_to_remove.append(event)
                else:
                    out_event = event
                    processed_tokens.add(event.asset)

            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset in in_assets
            ):  # accumulate amounts and keep one event to transform
                in_amounts[event.asset] += event.amount
                if event.asset in processed_tokens:
                    events_to_remove.append(event)
                else:
                    in_event = event
                    processed_tokens.add(event.asset)

        if not (in_event and out_event):
            log.error(f'Failed to find in/out event for balancer v3 swap in transaction {transaction}')  # noqa: E501
            return decoded_events

        # transform the found events
        out_event.event_type = HistoryEventType.TRADE
        out_event.event_subtype = HistoryEventSubType.SPEND
        out_event.counterparty = CPT_BALANCER_V3
        out_event.amount = out_amounts[out_event.asset]
        out_event.notes = f'Swap {out_event.amount} {out_event.asset.resolve_to_asset_with_symbol().symbol} in Balancer v3'  # noqa: E501

        in_event.event_type = HistoryEventType.TRADE
        in_event.event_subtype = HistoryEventSubType.RECEIVE
        in_event.counterparty = CPT_BALANCER_V3
        in_event.amount = in_amounts[in_event.asset]
        in_event.notes = f'Receive {in_event.amount} {in_event.asset.resolve_to_asset_with_symbol().symbol} as the result of a swap in Balancer v3'  # noqa: E501
        for event in events_to_remove:
            decoded_events.remove(event)

        maybe_reshuffle_events(
            ordered_events=[out_event, in_event],
            events_list=decoded_events,
        )
        return decoded_events

    def _decode_vault_events(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] in (LIQUIDITY_ADDED_TOPIC, LIQUIDITY_REMOVED_TOPIC):
            return self._decode_liquidity_event(context)
        elif context.tx_log.topics[0] == SWAP_TOPIC:
            return self._decode_swap_event(context)

        return DEFAULT_EVM_DECODING_OUTPUT

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return super().addresses_to_decoders() | {
            VAULT_ADDRESS: (self._decode_vault_events,),
        }

    def post_decoding_rules(self) -> dict[str, list[tuple[int, Callable]]]:
        return {
            CPT_BALANCER_V3: [(0, self._order_lp_events)],
            CPT_BALANCER_SWAP_V3: [(0, self._process_swap_events)],
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_BALANCER_V3,
            label=BALANCER_LABEL,
            image='balancer.svg',
        ),)
