import logging
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Optional

from rotkehlchen.accounting.structures.evm_event import EvmEvent, EvmProduct
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.utils import set_token_protocol_if_missing
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface, ReloadableDecoderMixin
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails, EventCategory
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.optimism.modules.velodrome.constants import CPT_VELODROME
from rotkehlchen.chain.optimism.modules.velodrome.velodrome_cache import (
    query_velodrome_data,
    read_velodrome_pools_and_gauges_from_cache,
    save_velodrome_data_to_cache,
)
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import (
    VELODROME_POOL_PROTOCOL,
    CacheType,
    ChecksumEvmAddress,
    DecoderEventMappingType,
)
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.chain.optimism.manager import OptimismInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


ROUTER_V2 = string_to_evm_address('0xa062aE8A9c5e11aaA026fc2670B0D65cCc8B2858')
ROUTER_V1 = string_to_evm_address('0x9c12939390052919aF3155f41Bf4160Fd3666A6f')
ADD_LIQUIDITY_EVENT = b'L \x9b_\xc8\xadPu\x8f\x13\xe2\xe1\x08\x8b\xa5jV\r\xffi\n\x1co\xef&9OL\x03\x82\x1cO'  # Mint event (mints LP tokens) same for v1 and v2  # noqa: E501
REMOVE_LIQUIDITY_EVENT_V2 = b']bJ\xa9\xc1H\x15:\xb3Dl\x1b\x15Of\x0e\xe7p\x1eT\x9f\xe9\xb6-\xabqq\xb1\xc8\x0eo\xa2'  # Burn event (burns LP tokens)  # noqa: E501
REMOVE_LIQUIDITY_EVENT_V1 = b'\xdc\xcdA/\x0b\x12R\x81\x9c\xb1\xfd3\x0b\x93"L\xa4&\x12\x89+\xb3\xf4\xf7\x89\x97nm\x81\x93d\x96'  # noqa: E501
SWAP_V2 = b'\xb3\xe2w6\x06\xab\xfd6\xb5\xbd\x919K:T\xd19\x836\xc6P\x05\xba\xf7\xbfz\x05\xef\xef\xfa\xf7['  # noqa: E501
SWAP_V1 = b'\xd7\x8a\xd9_\xa4l\x99KeQ\xd0\xda\x85\xfc\'_\xe6\x13\xce7e\x7f\xb8\xd5\xe3\xd10\x84\x01Y\xd8"'  # noqa: E501
GAUGE_DEPOSIT_V2 = b'UH\xc87\xab\x06\x8c\xf5j,$y\xdf\x08\x82\xa4\x92/\xd2\x03\xed\xb7Qs!\x83\x1d\x95\x07\x8c_b'  # noqa: E501
GAUGE_WITHDRAW_V2 = b'\x88N\xda\xd9\xceo\xa2D\r\x8aT\xcc\x124\x90\xeb\x96\xd2v\x84y\xd4\x9f\xf9\xc76a%\xa9BCd'  # noqa: E501
CLAIM_REWARDS_V2 = b"\x1f\x89\xf9c3\xd3\x130\x00\xeeDts\x15\x1f\xa9`eC6\x8f\x02'\x1c\x9d\x95\xae\x14\xf1;\xccg"  # noqa: E501


class VelodromeDecoder(DecoderInterface, ReloadableDecoderMixin):
    """A decoder class for velodrome related events."""

    def __init__(
            self,
            optimism_inquirer: 'OptimismInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=optimism_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.pools, self.gauges = read_velodrome_pools_and_gauges_from_cache()
        self.protocol_addresses = {ROUTER_V2, ROUTER_V1}.union(self.pools)  # velodrome addresses that appear on decoded events  # noqa: E501

    def _decode_add_liquidity_events(
            self,
            tx_log: 'EvmTxReceiptLog',
            decoded_events: list['EvmEvent'],
    ) -> DecodingOutput:
        """
        Decodes events that add liquidity to a velodrome v1 or v2 pool.

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
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.counterparty = CPT_VELODROME
                event.notes = f'Deposit {event.balance.amount} {crypto_asset.symbol} in velodrome pool {event.address}'  # noqa: E501
                event.product = EvmProduct.POOL
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.address == ZERO_ADDRESS
            ):
                event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                event.counterparty = CPT_VELODROME
                event.notes = f'Receive {event.balance.amount} {crypto_asset.symbol} after depositing in velodrome pool {tx_log.address}'  # noqa: E501
                event.product = EvmProduct.POOL
                set_token_protocol_if_missing(
                    evm_token=event.asset.resolve_to_evm_token(),
                    protocol=VELODROME_POOL_PROTOCOL,
                )

        return DEFAULT_DECODING_OUTPUT

    def _decode_remove_liquidity_events(
            self,
            tx_log: 'EvmTxReceiptLog',
            decoded_events: list['EvmEvent'],
    ) -> DecodingOutput:
        """Decodes events that remove liquidity from a velodrome v1 or v2 pool"""
        for event in decoded_events:
            crypto_asset = event.asset.resolve_to_crypto_asset()
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.address in self.pools
            ):
                event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                event.counterparty = CPT_VELODROME
                event.notes = f'Return {event.balance.amount} {crypto_asset.symbol}'
                event.product = EvmProduct.POOL
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.address in self.pools
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                event.counterparty = CPT_VELODROME
                event.notes = f'Remove {event.balance.amount} {crypto_asset.symbol} from velodrome pool {tx_log.address}'  # noqa: E501
                event.product = EvmProduct.POOL

        return DEFAULT_DECODING_OUTPUT

    def _decode_swap(self, context: DecoderContext) -> DecodingOutput:
        """Decodes events that swap eth or tokens in a velodrome v1 or v2 pool"""
        spend_event, receive_event = None, None
        for event in context.decoded_events:
            crypto_asset = event.asset.resolve_to_crypto_asset()
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.address in self.protocol_addresses
            ):
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.SPEND
                event.counterparty = CPT_VELODROME
                event.notes = f'Swap {event.balance.amount} {crypto_asset.symbol} in {CPT_VELODROME}'  # noqa: E501
                spend_event = event
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.address in self.protocol_addresses
            ):
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.RECEIVE
                event.counterparty = CPT_VELODROME
                event.notes = f'Receive {event.balance.amount} {crypto_asset.symbol} as the result of a swap in {CPT_VELODROME}'  # noqa: E501
                receive_event = event

        if spend_event is None or receive_event is None:
            log.error(
                'A swap in velodrome pool must have both a spend and a receive event but one or '
                'both of them are missing for transaction hash: '
                f'{context.transaction.tx_hash.hex()}. '
                f'Spend event: {spend_event}, receive event: {receive_event}.',
            )
            return DEFAULT_DECODING_OUTPUT

        maybe_reshuffle_events(
            ordered_events=[spend_event, receive_event],
            events_list=context.decoded_events,
        )
        return DEFAULT_DECODING_OUTPUT

    def _decode_velodrome_pool_events(self, context: DecoderContext) -> DecodingOutput:
        """Decodes transactions that interact with a velodrome v1 or v2 pool"""
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

    def _decode_velodrome_gauge_events(self, context: DecoderContext) -> DecodingOutput:
        """
        Decodes transactions that interact with a velodrome v2 gauge. Velodrome v1 had no gauges
        """
        if context.tx_log.topics[0] not in (GAUGE_DEPOSIT_V2, GAUGE_WITHDRAW_V2, CLAIM_REWARDS_V2):
            return DEFAULT_DECODING_OUTPUT

        user_or_contract_address = hex_or_bytes_to_address(context.tx_log.topics[1])
        gauge_address = context.tx_log.address
        raw_amount = hex_or_bytes_to_int(context.tx_log.data)
        found_event_modifying_balances = False
        for event in context.decoded_events:
            crypto_asset = event.asset.resolve_to_crypto_asset()
            if (
                event.location_label == user_or_contract_address and
                event.address == gauge_address and
                event.balance.amount == asset_normalized_value(amount=raw_amount, asset=crypto_asset)  # noqa: E501
            ):
                event.counterparty = CPT_VELODROME
                event.product = EvmProduct.GAUGE
                found_event_modifying_balances = True
                if context.tx_log.topics[0] == GAUGE_DEPOSIT_V2:
                    event.event_type = HistoryEventType.DEPOSIT
                    event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                    event.notes = f'Deposit {event.balance.amount} {crypto_asset.symbol} into {gauge_address} velodrome gauge'  # noqa: E501
                    set_token_protocol_if_missing(event.asset.resolve_to_evm_token(), VELODROME_POOL_PROTOCOL)  # noqa: E501
                elif context.tx_log.topics[0] == GAUGE_WITHDRAW_V2:
                    event.event_type = HistoryEventType.WITHDRAWAL
                    event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                    event.notes = f'Withdraw {event.balance.amount} {crypto_asset.symbol} from {gauge_address} velodrome gauge'  # noqa: E501
                else:  # CLAIM_REWARDS
                    event.event_type = HistoryEventType.WITHDRAWAL
                    event.event_subtype = HistoryEventSubType.REWARD
                    event.notes = f'Receive {event.balance.amount} {crypto_asset.symbol} rewards from {gauge_address} velodrome gauge'  # noqa: E501

        return DecodingOutput(refresh_balances=found_event_modifying_balances)

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        mapping: dict[ChecksumEvmAddress, tuple[Any, ...]] = {
            address: (self._decode_velodrome_pool_events,)
            for address in self.pools
        }
        mapping.update({  # addresses of pools and gauges don't intersect, so combining like this is fine  # noqa: E501
            gauge_address: (self._decode_velodrome_gauge_events,)
            for gauge_address in self.gauges
        })
        return mapping

    def possible_events(self) -> DecoderEventMappingType:
        return {
            CPT_VELODROME: {
                HistoryEventType.TRADE: {
                    HistoryEventSubType.SPEND: EventCategory.SWAP_OUT,
                    HistoryEventSubType.RECEIVE: EventCategory.SWAP_IN,
                },
                HistoryEventType.WITHDRAWAL: {
                    HistoryEventSubType.REMOVE_ASSET: EventCategory.WITHDRAW,
                },
                HistoryEventType.RECEIVE: {
                    HistoryEventSubType.RECEIVE_WRAPPED: EventCategory.RECEIVE,
                    HistoryEventSubType.REWARD: EventCategory.CLAIM_REWARD,
                },
                HistoryEventType.SPEND: {
                    HistoryEventSubType.RETURN_WRAPPED: EventCategory.SEND,
                },
                HistoryEventType.DEPOSIT: {
                    HistoryEventSubType.DEPOSIT_ASSET: EventCategory.DEPOSIT,
                },
            },
        }

    @staticmethod
    def possible_products() -> dict[str, list[EvmProduct]]:
        return {
            CPT_VELODROME: [EvmProduct.POOL, EvmProduct.GAUGE],
        }

    def counterparties(self) -> list['CounterpartyDetails']:
        return [CounterpartyDetails(identifier=CPT_VELODROME, label='velodrome_finance', image='velodrome.svg')]  # noqa: E501

    def reload_data(self) -> Optional[Mapping[ChecksumEvmAddress, tuple[Any, ...]]]:
        """Make sure velodrome pools are recently queried from the chain, saved in the DB
        and loaded to the decoder's memory.

        If a query happens and any new mappings are generated they are returned,
        otherwise `None` is returned.
        TODO: consider abstracting this method (it is similar to curve's one)
        """
        self.evm_inquirer.ensure_cache_data_is_updated(  # type: ignore  # mypy doesn't understand that the optimism inquirer is a DSProxyInquirerWithCacheData with an ensure_cache_data_is_updated method  # noqa: E501
            cache_type=CacheType.VELODROME_POOL_ADDRESS,
            query_method=query_velodrome_data,
            save_method=save_velodrome_data_to_cache,
        )
        new_pools, new_gauges = read_velodrome_pools_and_gauges_from_cache()
        pools_diff = new_pools - self.pools
        gauges_diff = new_gauges - self.gauges
        if len(pools_diff) == 0 and len(gauges_diff) == 0:
            return None

        self.pools = new_pools
        self.gauges = new_gauges
        new_mapping: dict[ChecksumEvmAddress, tuple[Any, ...]] = {
            pool_address: (self._decode_velodrome_pool_events,)
            for pool_address in pools_diff
        }
        new_mapping.update({
            # addresses of pools and gauges don't intersect, so combining like this is fine
            gauge_address: (self._decode_velodrome_gauge_events,)
            for gauge_address in gauges_diff
        })
        return new_mapping
