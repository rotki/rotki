import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.assets.utils import CHAIN_TO_WRAPPED_TOKEN
from rotkehlchen.chain.ethereum.utils import (
    asset_normalized_value,
    token_normalized_value_decimals,
)
from rotkehlchen.chain.evm.constants import DEFAULT_TOKEN_DECIMALS, ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.balancer.balancer_cache import (
    read_balancer_pools_and_gauges_from_cache,
)
from rotkehlchen.chain.evm.decoding.balancer.constants import CPT_BALANCER_V2
from rotkehlchen.chain.evm.decoding.balancer.decoder import BalancerCommonDecoder
from rotkehlchen.chain.evm.decoding.balancer.v2.constants import V2_SWAP, VAULT_ADDRESS
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    FAILED_ENRICHMENT_OUTPUT,
    ActionItem,
    DecoderContext,
    DecodingOutput,
    EnricherContext,
    TransferEnrichmentOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import CacheType, ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

POOL_BALANCE_CHANGED_TOPIC = b'\xe5\xce$\x90\x87\xce\x04\xf0Z\x95q\x92CT\x00\xfd\x97\x86\x8d\xba\x0ejKL\x04\x9a\xbf\x8a\xf8\r\xaex'  # noqa: E501


class Balancerv2CommonDecoder(BalancerCommonDecoder):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            counterparty=CPT_BALANCER_V2,
            pool_cache_type=CacheType.BALANCER_V2_POOLS,
            read_fn=lambda chain_id: read_balancer_pools_and_gauges_from_cache(
                version='2',
                chain_id=chain_id,
                cache_type=CacheType.BALANCER_V2_POOLS,
            ),
        )

    def decode_vault_events(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] == V2_SWAP:
            return self._decode_swap_creation(context)

        if context.tx_log.topics[0] == POOL_BALANCE_CHANGED_TOPIC:
            return self._decode_join_or_exit(context)

        return DEFAULT_DECODING_OUTPUT

    def _decode_join_or_exit(self, context: DecoderContext) -> DecodingOutput:
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
        return DEFAULT_DECODING_OUTPUT

    def _decode_pool_events(self, context: DecoderContext) -> DecodingOutput:
        return DEFAULT_DECODING_OUTPUT  # no-op

    def _decode_swap_creation(self, context: DecoderContext) -> DecodingOutput:
        """Decode swaps in Balancer v2. A SWAP event is created at transaction start containing
        token and amount information, followed by transfer executions.

        The swap event must be detected and transfer amounts matched against it. Special handling
        is needed when native asset is swapped - it's wrapped before sending, so the token shows
        as wrapped native asset, but we have a native asset transfer from user.
        """
        # The transfer event appears after the swap event, so we need to propagate information
        from_token_address = bytes_to_address(context.tx_log.topics[2])
        to_token_address = bytes_to_address(context.tx_log.topics[3])
        amount_in = int.from_bytes(context.tx_log.data[0:32])
        amount_out = int.from_bytes(context.tx_log.data[32:64])

        # Create action item to propagate the information about the swap to the transfer enrichers
        to_token = self.base.get_or_create_evm_token(to_token_address)
        to_amount = asset_normalized_value(
            amount=amount_out,
            asset=to_token,
        )
        action_item = ActionItem(
            action='skip & keep',
            from_event_type=HistoryEventType.RECEIVE,
            from_event_subtype=HistoryEventSubType.NONE,
            asset=to_token,
            amount=to_amount,
            to_event_type=None,
            to_event_subtype=None,
            to_counterparty=CPT_BALANCER_V2,
            to_notes=None,
            extra_data={
                'from_token': from_token_address,
                'amount_in': amount_in,
            },
        )

        # For native asset swaps, it's wrapped and the native transfer happens before SWAP.
        # Detect such event if not already found.
        if (
            len(context.action_items) == 0 and
            CHAIN_TO_WRAPPED_TOKEN[self.evm_inquirer.chain_id.to_blockchain()].resolve_to_evm_token().evm_address == from_token_address  # noqa: E501
        ):
            # When swapping native asset, transfer precedes V2_SWAP.
            # Check if native asset was swapped
            amount_of_eth = token_normalized_value_decimals(
                token_amount=amount_in,
                token_decimals=DEFAULT_TOKEN_DECIMALS,
            )
            for event in context.decoded_events:
                if (
                    event.asset == self.evm_inquirer.native_token and event.amount == amount_of_eth and  # noqa: E501
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE
                ):
                    event.event_type = HistoryEventType.TRADE
                    event.event_subtype = HistoryEventSubType.SPEND
                    event.notes = f'Swap {event.amount} {self.evm_inquirer.native_token.symbol} in Balancer v2'  # noqa: E501
                    event.counterparty = CPT_BALANCER_V2

        return DecodingOutput(action_items=[action_item], process_swaps=True)

    def _maybe_enrich_balancer_v2_transfers(
            self,
            context: EnricherContext,
    ) -> TransferEnrichmentOutput:
        """
        Enrich transfer transactions to account for swaps in balancer v2 protocol.
        May raise:
        - UnknownAsset
        - WrongAssetType
        """
        if context.action_items is None or len(context.action_items) == 0 or context.transaction.to_address != VAULT_ADDRESS:  # noqa: E501
            return FAILED_ENRICHMENT_OUTPUT

        if context.action_items[-1].extra_data is None:
            return FAILED_ENRICHMENT_OUTPUT

        asset = context.event.asset.resolve_to_evm_token()
        if (
            context.action_items[-1].asset and isinstance(context.action_items[-1].asset, EvmToken) is False and  # noqa: E501
            not ((
                context.action_items[-1].asset.evm_address != context.tx_log.address and  # type: ignore[attr-defined]  # mypy fails to understand that due the previous statement in the or this check won't be evaluated if the asset isn't a token
                context.action_items[-1].amount != context.event.amount
            ) or (
                context.action_items[-1].extra_data['from_token'] != context.tx_log.address and
                context.action_items[-1].extra_data['amount_in'] != context.event.amount
            ))
        ):
            return FAILED_ENRICHMENT_OUTPUT

        context.event.counterparty = CPT_BALANCER_V2
        if context.event.event_type == HistoryEventType.RECEIVE:
            context.event.event_subtype = HistoryEventSubType.RECEIVE
            context.event.notes = f'Receive {context.event.amount} {asset.symbol} as the result of a swap via Balancer v2'  # noqa: E501
        else:
            context.event.event_subtype = HistoryEventSubType.SPEND
            context.event.notes = f'Swap {context.event.amount} {asset.symbol} via Balancer v2'

        context.event.event_type = HistoryEventType.TRADE

        return TransferEnrichmentOutput(matched_counterparty=CPT_BALANCER_V2, process_swaps=True)

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return super().addresses_to_decoders() | {
            VAULT_ADDRESS: (self.decode_vault_events,),
        }

    def enricher_rules(self) -> list[Callable]:
        return [
            self._maybe_enrich_balancer_v2_transfers,
        ]

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_BALANCER_V2,
            label=CPT_BALANCER_V2.capitalize().replace('-v', ' V'),
            image='balancer.svg',
        ),)
