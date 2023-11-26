import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from rotkehlchen.accounting.structures.base import HistoryEventSubType, HistoryEventType
from rotkehlchen.accounting.structures.evm_event import EvmProduct
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.modules.convex.constants import (
    BOOSTER,
    CONVEX_ABRAS_HEX,
    CONVEX_CPT_DETAILS,
    CONVEX_VIRTUAL_REWARDS,
    CPT_CONVEX,
    CVX_LOCKER,
    CVX_LOCKER_V2,
    CVX_REWARDS,
    CVXCRV_REWARDS,
    REWARD_TOPICS,
    WITHDRAWAL_TOPICS,
)
from rotkehlchen.chain.ethereum.modules.convex.convex_cache import (
    query_convex_data,
    read_convex_data_from_cache,
    save_convex_data_to_cache,
)
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface, ReloadableCacheDecoderMixin
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    FAILED_ENRICHMENT_OUTPUT,
    DecoderContext,
    DecodingOutput,
    EnricherContext,
    TransferEnrichmentOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.constants.assets import A_CRV, A_CVX
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import CURVE_POOL_PROTOCOL, CacheType, ChecksumEvmAddress
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

DEPOSIT_EVENT = b'\x9eq\xbc\x8e\xea\x02\xa69i\xf5\t\x81\x8f-\xaf\xb9%E2\x90C\x19\xf9\xdb\xday\xb6{\xd3J_='  # noqa: E501
REWARD_ADDED = b'\xde\x88\xa9"\xe0\xd3\xb8\x8b$\xe9b>\xfe\xb4d\x91\x9ck\xf9\xf6hW\xa6^+\xfc\xf2\xce\x87\xa9C='  # noqa: E501


class ConvexDecoder(DecoderInterface, ReloadableCacheDecoderMixin):
    def __init__(
            self,
            ethereum_inquirer: 'EthereumInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=ethereum_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        ReloadableCacheDecoderMixin.__init__(
            self,
            evm_inquirer=ethereum_inquirer,
            cache_type_to_check_for_freshness=CacheType.CONVEX_POOL_ADDRESS,
            query_data_method=query_convex_data,
            save_data_to_cache_method=save_convex_data_to_cache,
            read_data_from_cache_method=read_convex_data_from_cache,
        )

    @property
    def pools(self) -> dict[ChecksumEvmAddress, str]:
        assert isinstance(self.cache_data[0], dict), 'ConvexDecoder cache_data[0] is not a dict'
        return self.cache_data[0]

    def _cache_mapping_methods(self) -> tuple[Callable[[DecoderContext], DecodingOutput]]:
        return (self._decode_pool_events,)

    def _decode_pool_events(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] == REWARD_ADDED:
            return self._decode_compound_crv(context=context)

        return self._decode_gauge_events(context=context)

    def _decode_compound_crv(self, context: DecoderContext) -> DecodingOutput:
        """Decode compounding of CRV in convex pools"""
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == A_CRV
            ):
                event.event_subtype = HistoryEventSubType.REWARD
                event.counterparty = CPT_CONVEX
                event.notes = f'Claim {event.balance.amount} {event.asset.resolve_to_crypto_asset().symbol} after compounding Convex pool'  # noqa: E501

        return DEFAULT_DECODING_OUTPUT

    def _decode_gauge_events(self, context: DecoderContext) -> DecodingOutput:
        """
        Decode events in convex gauges:
        - deposits/withdrawals
        - claim rewards
        """
        amount_raw = hex_or_bytes_to_int(context.tx_log.data[0:32])
        interacted_address = hex_or_bytes_to_address(context.tx_log.topics[1])
        found_event_modifying_balances = False

        for event in context.decoded_events:
            try:
                crypto_asset = event.asset.resolve_to_crypto_asset()
            except (UnknownAsset, WrongAssetType):
                self.notify_user(event=event, counterparty=CPT_CONVEX)
                continue

            amount = asset_normalized_value(amount_raw, crypto_asset)
            if (
                event.location_label == context.transaction.from_address == interacted_address is False or  # noqa: E501
                (event.address != ZERO_ADDRESS and event.balance.amount != amount)
            ):
                continue
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE
            ):
                found_event_modifying_balances = True
                if event.address == ZERO_ADDRESS:
                    event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                    event.counterparty = CPT_CONVEX
                    if context.tx_log.address in self.pools:
                        event.notes = f'Return {event.balance.amount} {crypto_asset.symbol} to convex {self.pools[context.tx_log.address]} pool'  # noqa: E501
                    else:
                        event.notes = f'Return {event.balance.amount} {crypto_asset.symbol} to convex'  # noqa: E501
                else:
                    event.event_type = HistoryEventType.DEPOSIT
                    event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                    event.counterparty = CPT_CONVEX
                    if context.tx_log.address in self.pools:
                        event.notes = f'Deposit {event.balance.amount} {crypto_asset.symbol} into convex {self.pools[context.tx_log.address]} pool'  # noqa: E501
                        event.product = EvmProduct.GAUGE
                    else:
                        event.notes = f'Deposit {event.balance.amount} {crypto_asset.symbol} into convex'  # noqa: E501
                        if (
                            isinstance(crypto_asset, EvmToken) and
                            crypto_asset.protocol == CURVE_POOL_PROTOCOL
                        ):
                            event.product = EvmProduct.GAUGE
                        elif crypto_asset == A_CVX:
                            event.product = EvmProduct.STAKING

                    # in this case store information about the gauge in the extra details to use
                    # it during balances queries
                    for log_event in context.all_logs:
                        if log_event.topics[0] == DEPOSIT_EVENT:
                            deposit_amount_raw = hex_or_bytes_to_int(context.tx_log.data[0:32])
                            staking_address = hex_or_bytes_to_address(log_event.topics[1])
                            if deposit_amount_raw == amount_raw and staking_address == event.location_label:  # noqa: E501
                                event.extra_data = {'gauge_address': log_event.address}
                                break

            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE
            ):
                if context.tx_log.topics[0] in WITHDRAWAL_TOPICS:
                    event.event_type = HistoryEventType.WITHDRAWAL
                    event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                    event.counterparty = CPT_CONVEX
                    found_event_modifying_balances = True
                    if context.tx_log.address in self.pools:
                        event.notes = f'Withdraw {event.balance.amount} {crypto_asset.symbol} from convex {self.pools[context.tx_log.address]} pool'  # noqa: E501
                        event.product = EvmProduct.GAUGE
                    else:
                        event.notes = f'Withdraw {event.balance.amount} {crypto_asset.symbol} from convex'  # noqa: E501
                        if (
                            isinstance(crypto_asset, EvmToken) and
                            crypto_asset.protocol == CURVE_POOL_PROTOCOL
                        ):
                            event.product = EvmProduct.GAUGE
                elif context.tx_log.topics[0] in REWARD_TOPICS:
                    event.event_subtype = HistoryEventSubType.REWARD
                    event.counterparty = CPT_CONVEX
                    found_event_modifying_balances = True
                    if context.tx_log.address in self.pools:
                        event.notes = f'Claim {event.balance.amount} {crypto_asset.symbol} reward from convex {self.pools[context.tx_log.address]} pool'  # noqa: E501
                    else:
                        event.notes = f'Claim {event.balance.amount} {crypto_asset.symbol} reward from convex'  # noqa: E501
        return DecodingOutput(refresh_balances=found_event_modifying_balances)

    def _maybe_enrich_convex_transfers(self, context: EnricherContext) -> TransferEnrichmentOutput:
        """
        Used for rewards paid with abracadabras. Problem is that the transfer event in this
        case happens at the end of the transaction and there is no reward event after it to
        emit event processing.

        May raise:
        - UnknownAsset
        - WrongAssetType
        """
        if (
            context.tx_log.topics[0] == ERC20_OR_ERC721_TRANSFER and
            context.tx_log.topics[1] in CONVEX_ABRAS_HEX and
            context.event.location_label == context.transaction.from_address and
            context.event.event_type == HistoryEventType.RECEIVE and
            context.event.event_subtype == HistoryEventSubType.NONE
        ):
            crypto_asset = context.event.asset.resolve_to_crypto_asset()
            context.event.event_subtype = HistoryEventSubType.REWARD
            if context.tx_log.address in self.pools:
                context.event.notes = f'Claim {context.event.balance.amount} {crypto_asset.symbol} reward from convex {self.pools[context.tx_log.address]} pool'  # noqa: E501
            else:
                context.event.notes = f'Claim {context.event.balance.amount} {crypto_asset.symbol} reward from convex'  # noqa: E501
            context.event.counterparty = CPT_CONVEX
            return TransferEnrichmentOutput(matched_counterparty=CPT_CONVEX)
        return FAILED_ENRICHMENT_OUTPUT

    @staticmethod
    def possible_products() -> dict[str, list[EvmProduct]]:
        return {
            CPT_CONVEX: [EvmProduct.GAUGE, EvmProduct.STAKING],
        }

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        decoder_mappings: dict[ChecksumEvmAddress, tuple[Callable, ...]] = {
            BOOSTER: (self._decode_pool_events,),
            CVX_LOCKER: (self._decode_pool_events,),
            CVX_LOCKER_V2: (self._decode_pool_events,),
            CVX_REWARDS: (self._decode_pool_events,),
            CVXCRV_REWARDS: (self._decode_pool_events,),
        }
        pools = {pool: (self._decode_pool_events,) for pool in self.pools}
        virtual_rewards = {addr: (self._decode_pool_events,) for addr in CONVEX_VIRTUAL_REWARDS}
        decoder_mappings.update(pools)
        decoder_mappings.update(virtual_rewards)
        return decoder_mappings

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CONVEX_CPT_DETAILS,)

    def enricher_rules(self) -> list[Callable]:
        return [self._maybe_enrich_convex_transfers]
