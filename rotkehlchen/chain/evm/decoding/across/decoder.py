import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.across.constants import (
    ACROSS_CHAIN_MAPPING,
    ACROSS_CPT_DETAILS,
    CPT_ACROSS,
    DEPOSIT_TOPICS,
    FILL_TOPICS,
    LIQUIDITY_ADDED,
    LIQUIDITY_REMOVED,
    LP_TOKEN_STAKED,
    LP_TOKEN_UNSTAKED,
)
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class AcrossCommonDecoder(EvmDecoderInterface):
    """Decoder for Across protocol bridge transactions on SpokePool contracts.

    Across uses a SpokePool contract on each supported chain. Users deposit
    tokens into the source SpokePool (FundsDeposited event) and relayers fill
    the deposits on the destination SpokePool (FilledRelay event), sending
    tokens to the recipient.
    """

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            spoke_pool: ChecksumEvmAddress,
            hub_pools: tuple[ChecksumEvmAddress, ...] = (),
            staking_contracts: tuple[ChecksumEvmAddress, ...] = (),
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.spoke_pool = spoke_pool
        self.hub_pools = hub_pools
        self.staking_contracts = staking_contracts

    def _decode_deposit(self, context: DecoderContext) -> EvmDecodingOutput:
        """Handle FundsDeposited — user sends tokens to SpokePool on the source chain."""
        if not self.base.is_tracked(depositor := bytes_to_address(context.tx_log.topics[3])):
            return DEFAULT_EVM_DECODING_OUTPUT

        destination_chain_id = int.from_bytes(context.tx_log.topics[1])
        if (to_chain := ACROSS_CHAIN_MAPPING.get(destination_chain_id)) is not None:
            chain_info = f' from {self.node_inquirer.chain_id.label()} to {to_chain.label()}'
        else:
            chain_info = ''

        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == depositor and
                event.counterparty is None
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.BRIDGE
                event.counterparty = CPT_ACROSS
                event.notes = (
                    f'Bridge {event.amount} {event.asset.symbol_or_name()}'
                    f'{chain_info} via Across'
                )
                break
        else:
            log.error(
                'Could not find matching spend event for %s Across bridge deposit %s',
                self.node_inquirer.chain_name,
                context.transaction.tx_hash,
            )

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_fill(self, context: DecoderContext) -> EvmDecodingOutput:
        """Handle FilledRelay — user receives tokens from SpokePool on the destination chain.

        The recipient address is at word 9 (bytes 288:320) of the non-indexed
        event data across all versions of the FilledRelay event.
        """
        if not self.base.is_tracked(recipient := bytes_to_address(context.tx_log.data[288:320])):
            return DEFAULT_EVM_DECODING_OUTPUT

        origin_chain_id = int.from_bytes(context.tx_log.topics[1])
        if (from_chain := ACROSS_CHAIN_MAPPING.get(origin_chain_id)) is not None:
            chain_info = f' from {from_chain.label()} to {self.node_inquirer.chain_id.label()}'
        else:
            chain_info = ''

        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == recipient and
                event.counterparty is None
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.BRIDGE
                event.counterparty = CPT_ACROSS
                event.notes = (
                    f'Bridge {event.amount} {event.asset.symbol_or_name()}'
                    f'{chain_info} via Across'
                )
                break
        else:
            return EvmDecodingOutput(action_items=[ActionItem(
                action='transform',
                from_event_type=HistoryEventType.RECEIVE,
                from_event_subtype=HistoryEventSubType.NONE,
                location_label=recipient,
                to_event_type=HistoryEventType.WITHDRAWAL,
                to_event_subtype=HistoryEventSubType.BRIDGE,
                to_counterparty=CPT_ACROSS,
                to_notes=(
                    f'Bridge {{amount}} {{symbol}}'
                    f'{chain_info} via Across'
                ),
            )])

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_add_liquidity(self, context: DecoderContext) -> EvmDecodingOutput:
        """Handle liquidity additions to Across pools."""
        if (
            context.tx_log.topics[0] != LIQUIDITY_ADDED or
            not self.base.is_tracked(user_address := bytes_to_address(context.tx_log.topics[2]))
        ):
            return DEFAULT_EVM_DECODING_OUTPUT

        deposit_event, receive_event = None, None
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == user_address and
                event.address == context.tx_log.address and
                event.counterparty is None
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
                event.counterparty = CPT_ACROSS
                event.notes = f'Deposit {event.amount} {event.asset.symbol_or_name()} to Across'
                deposit_event = event
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == user_address and
                event.address == ZERO_ADDRESS and
                event.counterparty is None
            ):
                event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                event.counterparty = CPT_ACROSS
                event.notes = f'Receive {event.amount} {event.asset.symbol_or_name()} from Across'
                receive_event = event

        if deposit_event is not None and receive_event is not None:
            maybe_reshuffle_events(
                ordered_events=[deposit_event, receive_event],
                events_list=context.decoded_events,
            )

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_remove_liquidity(self, context: DecoderContext) -> EvmDecodingOutput:
        """Handle liquidity removals from Across pools."""
        if (
            context.tx_log.topics[0] != LIQUIDITY_REMOVED or
            not self.base.is_tracked(user_address := bytes_to_address(context.tx_log.topics[2]))
        ):
            return DEFAULT_EVM_DECODING_OUTPUT

        return_event, receive_event = None, None
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == user_address and
                event.address == ZERO_ADDRESS and
                event.counterparty is None
            ):
                event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                event.counterparty = CPT_ACROSS
                event.notes = f'Return {event.amount} {event.asset.symbol_or_name()} to Across'
                return_event = event
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == user_address and
                event.address == context.tx_log.address and
                event.counterparty is None
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REDEEM_WRAPPED
                event.counterparty = CPT_ACROSS
                event.notes = f'Receive {event.amount} {event.asset.symbol_or_name()} after removing liquidity from Across'  # noqa: E501
                receive_event = event

        if return_event is not None and receive_event is not None:
            maybe_reshuffle_events(
                ordered_events=[return_event, receive_event],
                events_list=context.decoded_events,
            )

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_lp_staking(self, context: DecoderContext) -> EvmDecodingOutput:
        if (
            context.tx_log.topics[0] not in (LP_TOKEN_STAKED, LP_TOKEN_UNSTAKED) or
            not self.base.is_tracked(user_address := bytes_to_address(context.tx_log.topics[2]))
        ):
            return DEFAULT_EVM_DECODING_OUTPUT

        for event in context.decoded_events:
            if (
                context.tx_log.topics[0] == LP_TOKEN_STAKED and
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == user_address and
                event.address == context.tx_log.address and
                event.counterparty is None
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_TO_PROTOCOL
                event.counterparty = CPT_ACROSS
                event.notes = f'Deposit {event.amount} {event.asset.symbol_or_name()} into Across'
                break

            if (
                context.tx_log.topics[0] == LP_TOKEN_UNSTAKED and
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == user_address and
                event.address == context.tx_log.address and
                event.counterparty is None
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.WITHDRAW_FROM_PROTOCOL
                event.counterparty = CPT_ACROSS
                event.notes = f'Withdraw {event.amount} {event.asset.symbol_or_name()} from Across'
                break

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_hub_pool(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] == LIQUIDITY_ADDED:
            return self._decode_add_liquidity(context)

        if context.tx_log.topics[0] == LIQUIDITY_REMOVED:
            return self._decode_remove_liquidity(context)

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_bridge(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] in DEPOSIT_TOPICS:
            return self._decode_deposit(context)

        if context.tx_log.topics[0] in FILL_TOPICS:
            return self._decode_fill(context)

        return DEFAULT_EVM_DECODING_OUTPUT

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (ACROSS_CPT_DETAILS,)

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            self.spoke_pool: (self._decode_bridge,),
            **dict.fromkeys(self.hub_pools, (self._decode_hub_pool,)),
            **dict.fromkeys(self.staking_contracts, (self._decode_lp_staking,)),
        }
