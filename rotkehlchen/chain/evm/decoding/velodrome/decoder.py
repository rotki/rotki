import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Literal

from rotkehlchen.chain.ethereum.modules.uniswap.v2.constants import SWAP_SIGNATURE as SWAP_V1
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.interfaces import (
    DecoderInterface,
    ReloadablePoolsAndGaugesDecoderMixin,
)
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.decoding.velodrome.constants import (
    ADD_LIQUIDITY_EVENT,
    CLAIM_REWARDS_V2,
    GAUGE_DEPOSIT_V2,
    GAUGE_WITHDRAW_V2,
    REMOVE_LIQUIDITY_EVENT_V1,
    REMOVE_LIQUIDITY_EVENT_V2,
    SWAP_V2,
)
from rotkehlchen.chain.evm.decoding.velodrome.velodrome_cache import (
    query_velodrome_like_data,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.evm_event import EvmProduct
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import CacheType, ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.chain.optimism.manager import OptimismInquirer
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class VelodromeLikeDecoder(DecoderInterface, ReloadablePoolsAndGaugesDecoderMixin):
    """A decoder class for velodrome-like related events."""

    def __init__(
            self,
            evm_inquirer: 'OptimismInquirer | BaseInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            counterparty: Literal['velodrome', 'aerodrome'],
            routers: set[ChecksumEvmAddress],
            pool_cache_type: CacheType,
            read_fn: Callable[[], tuple[set[ChecksumEvmAddress], set[ChecksumEvmAddress]]],
            pool_token_protocol: str,
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        ReloadablePoolsAndGaugesDecoderMixin.__init__(
            self,
            evm_inquirer=evm_inquirer,
            cache_type_to_check_for_freshness=pool_cache_type,
            query_data_method=query_velodrome_like_data,
            read_data_from_cache_method=read_fn,
        )
        self.counterparty = counterparty
        self.pool_token_protocol = pool_token_protocol
        self.protocol_addresses = routers  # protocol_addresses are updated with pools in post_cache_update_callback  # noqa: E501

    @property
    def pools(self) -> set[ChecksumEvmAddress]:
        assert isinstance(self.cache_data[0], set), f'{self.counterparty} Decoder cache_data[0] is not a set'  # noqa: E501
        return self.cache_data[0]

    def post_cache_update_callback(self) -> None:
        self.protocol_addresses.update(self.pools)

    def _decode_add_liquidity_events(
            self,
            tx_log: 'EvmTxReceiptLog',
            decoded_events: list['EvmEvent'],
    ) -> DecodingOutput:
        """
        Decodes events that add liquidity to a (velo/aero)drome v1 or v2 pool.

        It can raise
        - UnknownAsset if the asset identifier is not known
        - WrongAssetType if the asset is not of the correct type
        """
        for event in decoded_events:
            crypto_asset = event.asset.resolve_to_crypto_asset()
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.address in self.pools
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
                event.counterparty = self.counterparty
                event.notes = f'Deposit {event.amount} {crypto_asset.symbol} in {self.counterparty} pool {event.address}'  # noqa: E501
                event.product = EvmProduct.POOL
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.address == ZERO_ADDRESS
            ):
                event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                event.counterparty = self.counterparty
                event.notes = f'Receive {event.amount} {crypto_asset.symbol} after depositing in {self.counterparty} pool {tx_log.address}'  # noqa: E501
                event.product = EvmProduct.POOL
                GlobalDBHandler.set_token_protocol_if_missing(
                    token=event.asset.resolve_to_evm_token(),
                    new_protocol=self.pool_token_protocol,
                )

        return DEFAULT_DECODING_OUTPUT

    def _decode_remove_liquidity_events(
            self,
            tx_log: 'EvmTxReceiptLog',
            decoded_events: list['EvmEvent'],
    ) -> DecodingOutput:
        """Decodes events that remove liquidity from a (velo/aero)drome v1 or v2 pool"""
        for event in decoded_events:
            crypto_asset = event.asset.resolve_to_crypto_asset()
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.address in self.pools
            ):
                event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                event.counterparty = self.counterparty
                event.notes = f'Return {event.amount} {crypto_asset.symbol}'
                event.product = EvmProduct.POOL
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.address in self.pools
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REDEEM_WRAPPED
                event.counterparty = self.counterparty
                event.notes = f'Remove {event.amount} {crypto_asset.symbol} from {self.counterparty} pool {tx_log.address}'  # noqa: E501
                event.product = EvmProduct.POOL

        return DEFAULT_DECODING_OUTPUT

    def _decode_swap(self, context: DecoderContext) -> DecodingOutput:
        """Decodes events that swap eth or tokens in a (velo/aero)drome v1 or v2 pool"""
        spend_event, receive_event = None, None
        for event in context.decoded_events:
            crypto_asset = event.asset.resolve_to_crypto_asset()
            if ((
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE
            ) or ((
                event.event_type == HistoryEventType.TRADE and
                event.event_subtype == HistoryEventSubType.SPEND
            ) and event.address in self.protocol_addresses)):
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.SPEND
                event.counterparty = self.counterparty
                event.notes = f'Swap {event.amount} {crypto_asset.symbol} in {self.counterparty}'
                spend_event = event
            elif ((
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE
            ) or ((
                event.event_type == HistoryEventType.TRADE and
                event.event_subtype == HistoryEventSubType.RECEIVE
            ) and event.address in self.protocol_addresses)):
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.RECEIVE
                event.counterparty = self.counterparty
                event.notes = f'Receive {event.amount} {crypto_asset.symbol} as the result of a swap in {self.counterparty}'  # noqa: E501
                receive_event = event

        if spend_event is None or receive_event is None:
            log.error(
                f'A swap in {self.counterparty} pool must have both a spend and a receive event '
                'but one or both of them are missing for transaction hash: '
                f'{context.transaction.tx_hash.hex()}. '
                f'Spend event: {spend_event}, receive event: {receive_event}.',
            )
            return DEFAULT_DECODING_OUTPUT

        maybe_reshuffle_events(
            ordered_events=[spend_event, receive_event],
            events_list=context.decoded_events,
        )
        return DEFAULT_DECODING_OUTPUT

    def _decode_pool_events(self, context: DecoderContext) -> DecodingOutput:
        """Decodes transactions that interact with a (velo/aero)drome v1 or v2 pool"""
        if context.tx_log.topics[0] in (REMOVE_LIQUIDITY_EVENT_V2, REMOVE_LIQUIDITY_EVENT_V1):
            return self._decode_remove_liquidity_events(
                tx_log=context.tx_log,
                decoded_events=context.decoded_events,
            )
        if context.tx_log.topics[0] == ADD_LIQUIDITY_EVENT:
            return self._decode_add_liquidity_events(
                tx_log=context.tx_log,
                decoded_events=context.decoded_events,
            )
        if context.tx_log.topics[0] in (SWAP_V2, SWAP_V1):
            return self._decode_swap(context=context)

        return DEFAULT_DECODING_OUTPUT

    def _decode_gauge_events(self, context: DecoderContext) -> DecodingOutput:
        """
        Decodes transactions that interact with a (velo/aero)drome v2 gauge.
        Velodrome v1 had no gauges.
        """
        if context.tx_log.topics[0] not in (GAUGE_DEPOSIT_V2, GAUGE_WITHDRAW_V2, CLAIM_REWARDS_V2):
            return DEFAULT_DECODING_OUTPUT

        user_or_contract_address = bytes_to_address(context.tx_log.topics[1])
        gauge_address = context.tx_log.address
        raw_amount = int.from_bytes(context.tx_log.data)
        found_event_modifying_balances = False
        for event in context.decoded_events:
            crypto_asset = event.asset.resolve_to_crypto_asset()
            if (
                event.location_label == user_or_contract_address and
                event.address == gauge_address and
                event.amount == asset_normalized_value(amount=raw_amount, asset=crypto_asset)
            ):
                event.counterparty = self.counterparty
                event.product = EvmProduct.GAUGE
                found_event_modifying_balances = True
                if context.tx_log.topics[0] == GAUGE_DEPOSIT_V2:
                    event.event_type = HistoryEventType.DEPOSIT
                    event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                    event.notes = f'Deposit {event.amount} {crypto_asset.symbol} into {gauge_address} {self.counterparty} gauge'  # noqa: E501
                    GlobalDBHandler.set_token_protocol_if_missing(
                        token=event.asset.resolve_to_evm_token(),
                        new_protocol=self.pool_token_protocol,
                    )
                elif context.tx_log.topics[0] == GAUGE_WITHDRAW_V2:
                    event.event_type = HistoryEventType.WITHDRAWAL
                    event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                    event.notes = f'Withdraw {event.amount} {crypto_asset.symbol} from {gauge_address} {self.counterparty} gauge'  # noqa: E501
                else:  # CLAIM_REWARDS
                    event.event_type = HistoryEventType.RECEIVE
                    event.event_subtype = HistoryEventSubType.REWARD
                    event.notes = f'Receive {event.amount} {crypto_asset.symbol} rewards from {gauge_address} {self.counterparty} gauge'  # noqa: E501

        return DecodingOutput(refresh_balances=found_event_modifying_balances)
