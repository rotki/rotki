import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from eth_abi import decode as decode_abi

from rotkehlchen.assets.utils import CHAIN_TO_WRAPPED_TOKEN
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.balancer.constants import BALANCER_LABEL, CPT_BALANCER_V3
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction
from rotkehlchen.utils.misc import bytes_to_address

from .constants import (
    BALANCER_V3_POOL_ABI,
    LIQUIDITY_ADDED_TOPIC,
    LIQUIDITY_REMOVED_TOPIC,
    VAULT_ADDRESS,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.history.events.structures.evm_event import EvmEvent

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Balancerv3CommonDecoder(DecoderInterface):

    def _decode_liquidity_event(self, context: DecoderContext) -> DecodingOutput:
        """Decode liquidity events (inflow & outflow) for Balancer V3 pools."""
        if context.tx_log.topics[0] not in (LIQUIDITY_ADDED_TOPIC, LIQUIDITY_REMOVED_TOPIC):
            return DEFAULT_DECODING_OUTPUT

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

        pool_tokens = self.evm_inquirer.call_contract(
            contract_address=(lp_token_address := bytes_to_address(context.tx_log.topics[1])),
            method_name='getTokens',
            abi=BALANCER_V3_POOL_ABI,
        )
        lp_token_identifier = evm_address_to_identifier(
            address=lp_token_address,
            chain_id=self.evm_inquirer.chain_id,
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
            return DEFAULT_DECODING_OUTPUT

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
            if token == CHAIN_TO_WRAPPED_TOKEN[self.evm_inquirer.blockchain]:
                for event in context.decoded_events:
                    if (
                            event.event_type == from_event_type and
                            event.event_subtype == HistoryEventSubType.NONE and
                            event.asset == self.evm_inquirer.native_token and
                            event.amount == amount
                    ):
                        event.event_type = to_event_type
                        event.counterparty = CPT_BALANCER_V3
                        event.event_subtype = to_event_subtype
                        event.notes = to_notes_template.format(
                            amount=event.amount,
                            symbol=self.evm_inquirer.native_token.symbol,
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

        return DecodingOutput(action_items=action_items, matched_counterparty=CPT_BALANCER_V3)

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

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {VAULT_ADDRESS: (self._decode_liquidity_event,)}

    def post_decoding_rules(self) -> dict[str, list[tuple[int, Callable]]]:
        return {CPT_BALANCER_V3: [(0, self._order_lp_events)]}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_BALANCER_V3,
            label=BALANCER_LABEL,
            image='balancer.svg',
        ),)
