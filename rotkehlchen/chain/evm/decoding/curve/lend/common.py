import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Literal

from eth_typing import ABI

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.modules.curve.crvusd.constants import CURVE_CRVUSD_CONTROLLER_ABI
from rotkehlchen.chain.ethereum.utils import token_normalized_value
from rotkehlchen.chain.evm.decoding.curve.constants import (
    CPT_CURVE,
    CURVE_COUNTERPARTY_DETAILS,
)
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.errors.misc import NotERC20Conformant, NotERC721Conformant, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.globaldb.cache import (
    globaldb_get_unique_cache_value,
    globaldb_set_unique_cache_value,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import CacheType, ChecksumEvmAddress

from .constants import BORROW_TOPIC, CURVE_VAULT_ABI, REMOVE_COLLATERAL_TOPIC, REPAY_TOPIC

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.fval import FVal
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class CurveBorrowRepayCommonDecoder(EvmDecoderInterface, ABC):
    """Common borrow/repay event decoder for both crvUSD markets and llamalend vaults."""

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',  # pylint: disable=unused-argument
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            leverage_zap: 'ChecksumEvmAddress | None' = None,
    ) -> None:
        """Decoder for Curve borrow/repay events.
        `evm_product` is used by the balances logic to differentiate between events for
        lending vault controllers and crvUSD minting market controllers.
        """
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.controllers: set[ChecksumEvmAddress] = set()  # populated via reload_data in subclasses  # noqa: E501
        self.leverage_zap = leverage_zap

    def _maybe_get_cached_address_from_contract(
            self,
            cache_type: Literal[
                CacheType.CURVE_LENDING_VAULT_CONTROLLER,
                CacheType.CURVE_LENDING_VAULT_BORROWED_TOKEN,
                CacheType.CURVE_CRVUSD_COLLATERAL_TOKEN,
                CacheType.CURVE_CRVUSD_AMM,
            ],
            contract_address: 'ChecksumEvmAddress',
            contract_abi: ABI,
            contract_method: Literal['amm', 'controller', 'collateral_token', 'borrowed_token'],
    ) -> ChecksumEvmAddress | None:
        """Get address from the cache or the specified vault contract method.
        Returns the address or None on error."""
        with GlobalDBHandler().conn.read_ctx() as cursor:
            if (value := globaldb_get_unique_cache_value(
                cursor=cursor,
                key_parts=(cache_type, contract_address),
            )) is not None:
                return string_to_evm_address(value)

        try:
            value = deserialize_evm_address(self.node_inquirer.call_contract(
                contract_address=contract_address,
                abi=contract_abi,
                method_name=contract_method,
            ))
        except (RemoteError, DeserializationError) as e:
            log.error(
                f'Failed to retrieve an evm address from the {contract_method} method on the '
                f'{self.node_inquirer.chain_name} Curve contract {contract_address} due to {e!s}',
            )
            return None

        with GlobalDBHandler().conn.write_ctx() as write_cursor:
            globaldb_set_unique_cache_value(
                write_cursor=write_cursor,
                key_parts=(cache_type, contract_address),
                value=value,
            )
        return value

    def _maybe_get_cached_token(
            self,
            cache_type: Literal[
                CacheType.CURVE_LENDING_VAULT_BORROWED_TOKEN,
                CacheType.CURVE_CRVUSD_COLLATERAL_TOKEN,
            ],
            contract_address: 'ChecksumEvmAddress',
    ) -> 'EvmToken | None':
        """Get token from the cache or the specified vault contract method.
        Returns the token or None on error."""
        contract_method: Literal['collateral_token', 'borrowed_token']
        if cache_type == CacheType.CURVE_CRVUSD_COLLATERAL_TOKEN:
            contract_method = 'collateral_token'
            contract_abi = CURVE_VAULT_ABI
        else:
            contract_method = 'borrowed_token'
            contract_abi = CURVE_VAULT_ABI

        if (token_address := self._maybe_get_cached_address_from_contract(
            cache_type=cache_type,
            contract_address=contract_address,
            contract_abi=contract_abi,
            contract_method=contract_method,
        )) is None:
            return None

        try:
            return self.base.get_or_create_evm_token(
                address=string_to_evm_address(token_address),
            )
        except (NotERC20Conformant, NotERC721Conformant) as e:
            log.error(
                f'Failed to get or create token {token_address} associated with Curve contract '
                f'{contract_address} on {self.node_inquirer.chain_name} due to {e}',
            )
            return None

    @abstractmethod
    def _get_controller_event_tokens_and_amounts(
            self,
            controller_address: 'ChecksumEvmAddress',
            context: DecoderContext,
    ) -> tuple['EvmToken', 'EvmToken', 'FVal', 'FVal'] | None:
        """Get the collateral token, borrowed token, and the corresponding amounts.
        Returns the tokens and amounts in a tuple or None on error."""

    @abstractmethod
    def maybe_decode_leveraged_borrow(
            self,
            context: DecoderContext,
    ) -> EvmDecodingOutput | None:
        """Decode events associated with creating a leveraged Curve position."""

    def _decode_borrow(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode events associated with getting a loan."""
        if (decoding_output := self.maybe_decode_leveraged_borrow(context=context)) is not None:
            return decoding_output

        if (tokens_and_amounts := self._get_controller_event_tokens_and_amounts(
            controller_address=context.tx_log.address,
            context=context,
        )) is None:
            log.error(f'Failed to find tokens and amounts for Curve borrow transaction {context.transaction}')  # noqa: E501
            return DEFAULT_EVM_DECODING_OUTPUT

        collateral_token, borrowed_token, collateral_amount, borrowed_amount = tokens_and_amounts
        out_event, in_event = None, None
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == collateral_token and
                event.amount == collateral_amount
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.notes = f'Deposit {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} as collateral on Curve'  # noqa: E501
                event.counterparty = CPT_CURVE
                out_event = event
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == borrowed_token and
                event.amount == borrowed_amount
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.GENERATE_DEBT
                event.notes = f'Borrow {borrowed_amount} {borrowed_token.symbol} from Curve'
                event.counterparty = CPT_CURVE
                event.extra_data = {'controller_address': context.tx_log.address}
                in_event = event

                if out_event is not None and in_event is not None:
                    maybe_reshuffle_events(
                        ordered_events=[out_event, in_event],
                        events_list=context.decoded_events,
                    )
                    return DEFAULT_EVM_DECODING_OUTPUT

        # In Borrow_more transactions these events will not yet be present in decoded_events
        return EvmDecodingOutput(action_items=[
            ActionItem(
                action='transform',
                from_event_type=HistoryEventType.SPEND,
                from_event_subtype=HistoryEventSubType.NONE,
                asset=collateral_token,
                amount=collateral_amount,
                to_event_type=HistoryEventType.DEPOSIT,
                to_event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
                to_notes=f'Deposit {collateral_amount} {collateral_token.symbol} as collateral on Curve',  # noqa: E501
                to_counterparty=CPT_CURVE,
            ), ActionItem(
                action='transform',
                from_event_type=HistoryEventType.RECEIVE,
                from_event_subtype=HistoryEventSubType.NONE,
                asset=borrowed_token,
                amount=borrowed_amount,
                to_event_type=HistoryEventType.WITHDRAWAL,
                to_event_subtype=HistoryEventSubType.GENERATE_DEBT,
                to_notes=f'Borrow {borrowed_amount} {borrowed_token.symbol} from Curve',
                to_counterparty=CPT_CURVE,
                extra_data={'controller_address': context.tx_log.address},
            ),
        ])

    def _decode_repay(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode events associated with repaying a loan."""
        if (amm_address := self._maybe_get_cached_address_from_contract(
            cache_type=CacheType.CURVE_CRVUSD_AMM,
            contract_address=(controller_address := context.tx_log.address),
            contract_abi=CURVE_CRVUSD_CONTROLLER_ABI,
            contract_method='amm',
        )) is None:
            log.error(f'Failed to find AMM address for Curve crvUSD controller {controller_address} in transaction {context.transaction}')  # noqa: E501
            return DEFAULT_EVM_DECODING_OUTPUT

        if (tokens_and_amounts := self._get_controller_event_tokens_and_amounts(
            controller_address=controller_address,
            context=context,
        )) is None:
            log.error(f'Failed to find tokens and amounts for Curve repay transaction {context.transaction}')  # noqa: E501
            return DEFAULT_EVM_DECODING_OUTPUT

        collateral_token, borrowed_token, collateral_amount, borrowed_amount = tokens_and_amounts
        in_event = None
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset in {collateral_token, borrowed_token} and
                (
                    event.address in {controller_address, amm_address} or
                    (self.leverage_zap is not None and event.address == self.leverage_zap)
                )
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                event.notes = f'Withdraw {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} from Curve after repaying loan'  # noqa: E501
                event.counterparty = CPT_CURVE
                in_event = event

        paired_events_data = ([in_event], False) if in_event is not None else None
        return EvmDecodingOutput(action_items=[
            ActionItem(
                action='transform',
                from_event_type=HistoryEventType.SPEND,
                from_event_subtype=HistoryEventSubType.NONE,
                asset=token,
                amount=amount,
                to_event_subtype=HistoryEventSubType.PAYBACK_DEBT,
                to_notes=f'Repay {amount} {token.symbol} to Curve',
                to_counterparty=CPT_CURVE,
                paired_events_data=paired_events_data,
            ) for token, amount in [
                (collateral_token, collateral_amount),
                (borrowed_token, borrowed_amount),
            ]
        ])

    def _decode_remove_collateral(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode events associated with removing collateral from a loan.
        Note that adding collateral is handled by _decode_borrow."""
        if (collateral_token := self._maybe_get_cached_token(
            cache_type=CacheType.CURVE_CRVUSD_COLLATERAL_TOKEN,
            contract_address=context.tx_log.address,
        )) is None:
            return DEFAULT_EVM_DECODING_OUTPUT

        collateral_amount = token_normalized_value(
            token_amount=int.from_bytes(context.tx_log.data[0:32]),
            token=collateral_token,
        )
        return EvmDecodingOutput(action_items=[ActionItem(
            action='transform',
            from_event_type=HistoryEventType.RECEIVE,
            from_event_subtype=HistoryEventSubType.NONE,
            asset=collateral_token,
            amount=collateral_amount,
            to_event_type=HistoryEventType.WITHDRAWAL,
            to_event_subtype=HistoryEventSubType.REMOVE_ASSET,
            to_notes=f'Withdraw {collateral_amount} {collateral_token.symbol} from Curve loan collateral',  # noqa: E501
            to_counterparty=CPT_CURVE,
        )])

    def _decode_vault_controller_events(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode events from the vault controller contract."""
        if context.tx_log.topics[0] == BORROW_TOPIC:
            return self._decode_borrow(context=context)
        elif context.tx_log.topics[0] == REPAY_TOPIC:
            return self._decode_repay(context=context)
        elif context.tx_log.topics[0] == REMOVE_COLLATERAL_TOPIC:
            return self._decode_remove_collateral(context=context)

        return DEFAULT_EVM_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return dict.fromkeys(self.controllers, (self._decode_vault_controller_events,))

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CURVE_COUNTERPARTY_DETAILS,)
