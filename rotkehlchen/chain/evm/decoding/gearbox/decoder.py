import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.chain.ethereum.utils import (
    token_normalized_value,
    token_normalized_value_decimals,
)
from rotkehlchen.chain.evm.constants import DEFAULT_TOKEN_DECIMALS
from rotkehlchen.chain.evm.decoding.gearbox.gearbox_cache import (
    GearboxPoolData,
    query_gearbox_data,
    read_gearbox_data_from_cache,
)
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface, ReloadableCacheDecoderMixin
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.constants.assets import A_WETH, A_WETH_ARB, A_WETH_OPT
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmProduct
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import CacheType, ChecksumEvmAddress
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

from .constants import (
    CLAIM_GEAR_WITHDRAWAL,
    CPT_GEARBOX,
    DEPOSIT,
    DEPOSIT_GEAR,
    GEARBOX_CPT_DETAILS,
    WITHDRAW,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class GearboxCommonDecoder(DecoderInterface, ReloadableCacheDecoderMixin):
    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            staking_contract: ChecksumEvmAddress,
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        ReloadableCacheDecoderMixin.__init__(
            self,
            evm_inquirer=evm_inquirer,
            cache_type_to_check_for_freshness=CacheType.GEARBOX_POOL_ADDRESS,
            query_data_method=query_gearbox_data,
            read_data_from_cache_method=read_gearbox_data_from_cache,
            chain_id=self.evm_inquirer.chain_id,
        )
        self.staking_contract = staking_contract

    @property
    def pools(self) -> dict[ChecksumEvmAddress, GearboxPoolData]:
        assert isinstance(self.cache_data[0], dict), 'GearboxCommonDecoder cache_data[0] is not a dict'  # noqa: E501
        return self.cache_data[0]

    def _cache_mapping_methods(self) -> tuple[Callable[[DecoderContext], DecodingOutput]]:
        return (self._decode_pool_events,)

    def _is_weth_pool(self, token: EvmToken) -> bool:
        """Check if one side of the pool includes WETH by verifying if the underlying token of the
        farming token is WETH.

        May raise:
            IndexError: if there is no underlying token detected for the farming token
        """
        return token.underlying_tokens[0].get_identifier(self.evm_inquirer.chain_id) in {
            A_WETH,
            A_WETH_ARB,
            A_WETH_OPT,
        }

    def _decode_common(self, context: DecoderContext, address_offset: int | None = None) -> tuple[ChecksumEvmAddress, GearboxPoolData, FVal, FVal] | None:  # noqa: E501
        """
        This function decodes the common data for the deposit and withdraw events.
        The 'address_offset' is an optional index indicating where the user's EVM address
        starts within the transaction's input data. If not provided, the offset is automatically
        determined based on the associated token type (0 for WETH and 32 for others).
        """
        try:
            pool_info = self.pools[context.tx_log.address]
        except KeyError:
            log.error(f'Could not find {self.evm_inquirer.chain_name} Gearbox pool info for {context.tx_log.address}')  # noqa: E501
            return None

        token = EvmToken(pool_info.farming_pool_token)
        if address_offset is None:
            try:
                address_offset = 0 if self._is_weth_pool(token) is True else 32
            except IndexError:
                return None

        if not self.base.is_tracked(user_address := hex_or_bytes_to_address(context.transaction.input_data[4 + address_offset: 36 + address_offset])):  # noqa: E501
            return None

        amount = token_normalized_value(
            token_amount=hex_or_bytes_to_int(context.tx_log.data[:32]),
            token=token,
        )
        shares = token_normalized_value(
            token_amount=hex_or_bytes_to_int(context.tx_log.data[32:64]),
            token=token,
        )
        return user_address, pool_info, amount, shares

    @staticmethod
    def _get_note_by_pool(pool_info: GearboxPoolData, asset: Asset, amount: FVal) -> str:
        """Determines if the user is providing liquidity or staking and returns
        the appropriate note."""
        action = 'providing liquidity' if asset.identifier in pool_info.lp_tokens else 'depositing'
        return f'Receive {amount} {asset.symbol_or_name()} after {action} in Gearbox'

    def _decode_deposit(self, context: DecoderContext) -> DecodingOutput:
        """
        Decode the deposit event done via Gearbox protocol. The ActionItem handles both the
        lp tokens (providing liqudity) and the farming pool (staking) token/event. The note for the
        event is different depending on the asset being deposited. Gearbox pools can have
        multiple lp tokens, they include their old lp tokens with the newer ones.
        """
        if (lp_data := self._decode_common(context)) is None:
            return DEFAULT_DECODING_OUTPUT

        user_address, pool_info, amount, shares = lp_data
        found_receive_event = False
        action_items = []
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.balance.amount == amount and
                event.location_label == user_address
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.counterparty = CPT_GEARBOX
                event.notes = f'Deposit {event.balance.amount} {event.asset.symbol_or_name()} to Gearbox'  # noqa: E501
            elif (
                # in case of just providing lp, this event is already decoded here and doesnt need an ActionItem  # noqa: E501
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == user_address and
                event.balance.amount == shares
            ):
                event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                event.counterparty = CPT_GEARBOX
                event.notes = self._get_note_by_pool(pool_info, event.asset, shares)
                found_receive_event = True

        if not found_receive_event:
            action_items = [
                ActionItem(
                    action='transform',
                    from_event_type=HistoryEventType.RECEIVE,
                    from_event_subtype=HistoryEventSubType.NONE,
                    asset=(asset := Asset(asset_id)),
                    amount=shares,
                    location_label=user_address,
                    to_event_type=HistoryEventType.RECEIVE,
                    to_event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
                    to_notes=self._get_note_by_pool(pool_info, asset, shares),
                    to_counterparty=CPT_GEARBOX,
                ) for asset_id in pool_info.lp_tokens.union({pool_info.farming_pool_token})
            ]

        return DecodingOutput(action_items=action_items)

    def _decode_withdraw(self, context: DecoderContext) -> DecodingOutput:
        if (lp_data := self._decode_common(context=context, address_offset=32)) is None:
            return DEFAULT_DECODING_OUTPUT

        user_address, _, amount, shares = lp_data
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == user_address and
                event.balance.amount == amount
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                event.counterparty = CPT_GEARBOX
                event.notes = f'Withdraw {event.balance.amount} {event.asset.symbol_or_name()} from Gearbox'  # noqa: E501
            elif (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.balance.amount == shares and
                event.location_label == user_address
            ):
                event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                event.counterparty = CPT_GEARBOX
                event.notes = f'Return {event.balance.amount} {event.asset.symbol_or_name()}'

        return DEFAULT_DECODING_OUTPUT

    def _decode_pool_events(self, context: DecoderContext) -> DecodingOutput:
        """Decode the deposit and withdrawal events done via Gearbox protocol."""
        if context.tx_log.topics[0] == DEPOSIT:
            return self._decode_deposit(context=context)

        if context.tx_log.topics[0] == WITHDRAW:
            return self._decode_withdraw(context=context)

        return DEFAULT_DECODING_OUTPUT

    def _decode_stake(self, context: DecoderContext) -> DecodingOutput:
        user_address = hex_or_bytes_to_address(context.tx_log.topics[1])
        amount = token_normalized_value_decimals(
            token_amount=hex_or_bytes_to_int(context.tx_log.data[:32]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )

        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.balance.amount == amount and
                event.location_label == user_address
            ):
                event.event_type = HistoryEventType.STAKING
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.counterparty = CPT_GEARBOX
                event.product = EvmProduct.STAKING
                event.notes = f'Stake {amount} GEAR'
                break
        else:
            log.error(f'Could not find matching spend event for {self.evm_inquirer.chain_name} gearbox staking deposit {context.transaction.tx_hash.hex()}')  # noqa: E501

        return DEFAULT_DECODING_OUTPUT

    def _decode_unstake(self, context: DecoderContext) -> DecodingOutput:
        user_address = hex_or_bytes_to_address(context.tx_log.data[:32])
        amount = token_normalized_value_decimals(
            token_amount=hex_or_bytes_to_int(context.tx_log.data[32:64]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.balance.amount == amount and
                event.location_label == user_address
            ):
                event.event_type = HistoryEventType.STAKING
                event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                event.counterparty = CPT_GEARBOX
                event.product = EvmProduct.STAKING
                event.notes = f'Unstake {amount} GEAR'
                break
        else:
            log.error(f'Could not find matching receive event for {self.evm_inquirer.chain_name} gearbox unstaking withdrawal {context.transaction.tx_hash.hex()}')  # noqa: E501

        return DEFAULT_DECODING_OUTPUT

    def _decode_staking_events(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] == DEPOSIT_GEAR:
            return self._decode_stake(context=context)

        if context.tx_log.topics[0] == CLAIM_GEAR_WITHDRAWAL:
            return self._decode_unstake(context=context)

        return DEFAULT_DECODING_OUTPUT

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {self.staking_contract: (self._decode_staking_events,)}

    @staticmethod
    def possible_products() -> dict[str, list[EvmProduct]]:
        return {
            CPT_GEARBOX: [EvmProduct.STAKING],
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (GEARBOX_CPT_DETAILS,)
