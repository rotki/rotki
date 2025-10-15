import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.utils import (
    asset_normalized_value,
    token_normalized_value,
    token_normalized_value_decimals,
)
from rotkehlchen.chain.evm.constants import REWARD_PAID_TOPIC
from rotkehlchen.chain.evm.decoding.extrafi.cache import (
    get_existing_reward_pools,
    query_extrafi_data,
)
from rotkehlchen.chain.evm.decoding.extrafi.constants import (
    CLAIM,
    CLOSE_POSITION_PARTIALLY,
    CPT_EXTRAFI,
    DEPOSITED,
    EXACT_REPAY,
    EXTRAFI_DISTRIBUTOR,
    EXTRAFI_FARMING_CONTRACT,
    EXTRAFI_POOL_CONTRACT,
    EXTRAFI_STAKING_CONTRACT,
    INVEST_TO_VAULT_POSITION,
    REDEEM,
    USER_CHECKPOINT,
    VOTE_ESCROW,
)
from rotkehlchen.chain.evm.decoding.extrafi.utils import maybe_query_farm_data
from rotkehlchen.chain.evm.decoding.interfaces import (
    EvmDecoderInterface,
    ReloadableCacheDecoderMixin,
)
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.history.events.structures.types import (
    EventDirection,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_timestamp
from rotkehlchen.types import CacheType, TokenKind
from rotkehlchen.utils.misc import bytes_to_address, timestamp_to_date

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.types import ChecksumEvmAddress
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class ExtrafiCommonDecoder(EvmDecoderInterface, ReloadableCacheDecoderMixin):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            extra_token_identifier: str,
    ) -> None:
        ReloadableCacheDecoderMixin.__init__(
            self,
            evm_inquirer=evm_inquirer,
            cache_type_to_check_for_freshness=CacheType.EXTRAFI_NEXT_RESERVE_ID,
            query_data_method=query_extrafi_data,
            read_data_from_cache_method=get_existing_reward_pools,
            chain_id=evm_inquirer.chain_id,
        )
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.extra_token_id = extra_token_identifier

    def _decode_deposit_event(self, context: DecoderContext) -> EvmDecodingOutput:
        on_behalf_of = bytes_to_address(context.tx_log.topics[2])
        user = bytes_to_address(context.tx_log.data[0:32])
        token_amount = int.from_bytes(context.tx_log.data[32:64])

        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == user
            ):
                if asset_normalized_value(
                    amount=token_amount,
                    asset=(asset := event.asset.resolve_to_crypto_asset()),
                ) != event.amount:
                    continue

                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.counterparty = CPT_EXTRAFI
                event.extra_data = {'reserve_index': int.from_bytes(context.tx_log.topics[1])}  # index of the extrafi position. Used to query for balances later  # noqa: E501
                event.notes = f'Deposit {event.amount} {asset.symbol} into Extrafi lend'
                if on_behalf_of != user:
                    event.notes += f' on behalf of {on_behalf_of}'

                break
        else:
            log.error(f'Failed to find deposit event for extrafi in {context.transaction}')

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_withdrawal_event(self, context: DecoderContext) -> EvmDecodingOutput:
        on_behalf_of = bytes_to_address(context.tx_log.topics[3])
        user = bytes_to_address(context.tx_log.topics[2])
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == user
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                event.counterparty = CPT_EXTRAFI
                event.notes = f'Withdraw {event.amount} {event.asset.symbol_or_name()} from Extrafi lend'  # noqa: E501
                if on_behalf_of != user:
                    event.notes += f' on behalf of {on_behalf_of}'

                break
        else:
            log.error(f'Failed to find withdrawal event for extrafi in {context.transaction}')

        return DEFAULT_EVM_DECODING_OUTPUT

    def _farm_name(self, vault_id: int) -> str:
        _, token0, token1 = maybe_query_farm_data(
            vault_id=vault_id,
            evm_inquirer=self.node_inquirer,
        )
        return f'{token0.symbol_or_name()}-{token1.symbol_or_name()} farm'

    def _handle_pool_events(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] == DEPOSITED:
            return self._decode_deposit_event(context)
        if context.tx_log.topics[0] == REDEEM:
            return self._decode_withdrawal_event(context)

        return DEFAULT_EVM_DECODING_OUTPUT

    def _handle_claim(self, context: DecoderContext) -> EvmDecodingOutput:
        """Handle claim events for the EXTRA token from the distributor"""
        if context.tx_log.topics[0] != CLAIM:
            return DEFAULT_EVM_DECODING_OUTPUT

        recipient = bytes_to_address(context.tx_log.topics[1])
        raw_amount = int.from_bytes(context.tx_log.data[32:64])
        amount = token_normalized_value_decimals(raw_amount, 18)  # extrafi has 18 decimals

        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.amount == amount and
                event.asset == self.extra_token_id and
                event.location_label == recipient
            ):
                event.event_subtype = HistoryEventSubType.REWARD
                event.counterparty = CPT_EXTRAFI
                event.notes = f'Claim {amount} EXTRA from Extrafi'
                break
        else:
            log.error(f'Could not match claim event of EXTRA in {context.transaction}')

        return DEFAULT_EVM_DECODING_OUTPUT

    def _handle_pool_rewards(self, context: DecoderContext) -> EvmDecodingOutput:
        """Handle rewards claimed for depositing in extrafi pools"""
        if context.tx_log.topics[0] != REWARD_PAID_TOPIC:
            return DEFAULT_EVM_DECODING_OUTPUT

        user = bytes_to_address(context.tx_log.topics[1])
        token_identifier = evm_address_to_identifier(
            address=bytes_to_address(context.tx_log.topics[2]),
            chain_id=self.node_inquirer.chain_id,
            token_type=TokenKind.ERC20,
        )
        amount = int.from_bytes(context.tx_log.data[0:32])
        for event in context.decoded_events:
            if (
                event.location_label == user and
                event.asset == token_identifier and
                event.amount == token_normalized_value(token_amount=amount, token=(token := EvmToken(token_identifier))) and  # noqa: E501
                event.maybe_get_direction() == EventDirection.IN
            ):
                event.event_type = HistoryEventType.RECEIVE
                event.event_subtype = HistoryEventSubType.REWARD
                event.counterparty = CPT_EXTRAFI
                event.notes = f'Claim {event.amount} {token.symbol_or_name()} from Extrafi'
                break
        else:
            log.error(f'Could not find extrafi reward transfer at {context.transaction}')

        return DEFAULT_EVM_DECODING_OUTPUT

    def _vote_escrow_contract(self, context: DecoderContext) -> EvmDecodingOutput:
        """Handle lock of extra tokens in the protocol"""
        if context.tx_log.topics[0] != USER_CHECKPOINT:
            return DEFAULT_EVM_DECODING_OUTPUT

        amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[0:32]),
            token_decimals=18,
        )

        for event in context.decoded_events:
            if (
                event.asset == self.extra_token_id and
                event.amount == amount and
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == bytes_to_address(context.tx_log.topics[2])
            ):
                locktime = deserialize_timestamp(int.from_bytes(context.tx_log.topics[3]))
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.counterparty = CPT_EXTRAFI
                event.notes = f'Lock {amount} EXTRA until {timestamp_to_date(locktime, formatstr="%d/%m/%Y %H:%M:%S")}'  # noqa: E501
                break
        else:
            log.error(f'Failed to find lock of EXTRA in {context.transaction}')

        return DEFAULT_EVM_DECODING_OUTPUT

    def _partially_close_farm_position(self, context: DecoderContext) -> EvmDecodingOutput:
        """Close a position in a farm partially"""
        manager = bytes_to_address(context.tx_log.topics[3])
        amount_0_received = int.from_bytes(context.tx_log.data[32:64])
        amount_1_received = int.from_bytes(context.tx_log.data[64:96])
        vault_id = int.from_bytes(context.tx_log.topics[1])

        for event in context.decoded_events:
            if event.location_label != manager:
                continue

            if (
                event.maybe_get_direction() == EventDirection.IN and
                (
                    asset_normalized_value(amount_0_received, event.asset) == event.amount or  # type: ignore
                    asset_normalized_value(amount_1_received, event.asset) == event.amount  # type: ignore
                )
            ):
                event.counterparty = CPT_EXTRAFI
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                event.notes = f'Withdraw {event.amount} {event.asset.symbol_or_name()} from Extrafi {self._farm_name(vault_id)}'  # noqa: E501
                break
        else:
            log.error(f'Could not find withdrawal event for extrafi at {context.transaction}')

        return DEFAULT_EVM_DECODING_OUTPUT

    def _invest_into_farm_position(self, context: DecoderContext) -> EvmDecodingOutput:
        """Handle the creation of farm positions and changing the collateral/borrowed amount"""
        manager = bytes_to_address(context.tx_log.topics[3])
        amount_0_invested = int.from_bytes(context.tx_log.data[0:32])
        amount_1_invested = int.from_bytes(context.tx_log.data[32:64])
        amount_0_borrowed = int.from_bytes(context.tx_log.data[64:96])
        amount_1_borrowed = int.from_bytes(context.tx_log.data[96:128])
        vault_id = int.from_bytes(context.tx_log.topics[1])

        if amount_0_borrowed != 0 or amount_1_borrowed != 0:
            _, token0, token1 = maybe_query_farm_data(
                vault_id=vault_id,
                evm_inquirer=self.node_inquirer,
            )
            if amount_0_borrowed != 0:
                borrow_token, amount = token0, asset_normalized_value(amount_0_borrowed, token0)
            else:
                borrow_token, amount = token1, asset_normalized_value(amount_1_borrowed, token1)

            borrow_event = self.base.make_event_next_index(
                tx_hash=context.transaction.tx_hash,
                timestamp=context.transaction.timestamp,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.GENERATE_DEBT,
                asset=borrow_token,
                amount=amount,
                location_label=manager,
                notes=f'Borrow {amount} {borrow_token.symbol_or_name()} in Extrafi {self._farm_name(vault_id)}',  # noqa: E501
                address=context.tx_log.address,
                counterparty=CPT_EXTRAFI,
            )
            deposit_event = self.base.make_event_next_index(
                tx_hash=context.transaction.tx_hash,
                timestamp=context.transaction.timestamp,
                event_type=HistoryEventType.DEPOSIT,
                event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
                asset=borrow_token,
                amount=amount,
                location_label=manager,
                notes=f'Deposit {amount} {borrow_token.symbol_or_name()} in Extrafi {self._farm_name(vault_id)}',  # noqa: E501
                address=context.tx_log.address,
                counterparty=CPT_EXTRAFI,
            )
            # the user did used leverage by borrowing from the lending pool at extrafi and
            # depositing the borrowed amount in the pool to earn rewards and swap fees.
            context.decoded_events.extend([borrow_event, deposit_event])
            maybe_reshuffle_events(
                ordered_events=[borrow_event, deposit_event],
                events_list=context.decoded_events,
            )

        for event in context.decoded_events:
            if (
                event.maybe_get_direction() == EventDirection.OUT and
                event.location_label == manager and
                (
                    event.amount == asset_normalized_value(amount_0_invested, event.asset) or  # type: ignore
                    event.amount == asset_normalized_value(amount_1_invested, event.asset)  # type: ignore
                )
            ):
                event.counterparty = CPT_EXTRAFI
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.extra_data = {
                    'vault_id': vault_id,
                    'vault_position': int.from_bytes(context.tx_log.topics[2]),
                }
                event.notes = f'Deposit {event.amount} {event.asset.symbol_or_name()} in Extrafi {self._farm_name(vault_id)}'  # noqa: E501
                if amount_0_invested == 0 or amount_1_invested == 0:
                    # It means we have decoded the only existing event and we can exit the logic
                    break
        else:
            log.error(f'Could not find the invest event for extrafi in {context.transaction}')

        return DEFAULT_EVM_DECODING_OUTPUT

    def _handle_farm_repayment(self, context: DecoderContext) -> EvmDecodingOutput:
        amount_0_repaid = int.from_bytes(context.tx_log.data[32:64])
        amount_1_repaid = int.from_bytes(context.tx_log.data[64:96])
        vault_id = int.from_bytes(context.tx_log.topics[1])
        refund_event: EvmEvent | None = None

        # the refund event appears before the send event in the case of an ETH transfer
        # or after the send event in the case of tokens
        for event in context.decoded_events[1:]:
            if event.maybe_get_direction() == EventDirection.IN:
                refund_event = event
                break

        for event in context.decoded_events[1:]:
            if event.maybe_get_direction() != EventDirection.OUT or event.counterparty == CPT_GAS:
                continue

            comparing_amount = event.amount
            if (
                refund_event is not None and
                event.asset == refund_event.asset and
                event.address == refund_event.address
            ):
                # When there is a refund in the transaction we need to check that the amount
                # matches taking into account that we sent a little bit more
                comparing_amount -= refund_event.amount

            if not (
                comparing_amount == asset_normalized_value(
                    amount=amount_0_repaid,
                    asset=event.asset.resolve_to_crypto_asset(),
                ) or
                comparing_amount == asset_normalized_value(
                    amount=amount_1_repaid,
                    asset=event.asset.resolve_to_crypto_asset(),
                )
            ):
                continue

            event.counterparty = CPT_EXTRAFI
            event.event_type = HistoryEventType.SPEND
            event.event_subtype = HistoryEventSubType.PAYBACK_DEBT
            event.notes = f'Repay {event.amount} {event.asset.symbol_or_name()} in Extrafi {self._farm_name(vault_id)}'  # noqa: E501

            if refund_event is not None:
                refund_event.counterparty = CPT_EXTRAFI
                refund_event.event_type = HistoryEventType.WITHDRAWAL
                refund_event.event_subtype = HistoryEventSubType.REFUND
                refund_event.notes = f'Receive {refund_event.amount} {refund_event.asset.symbol_or_name()} as refund from Extrafi'  # noqa: E501

                maybe_reshuffle_events(
                    ordered_events=[event, refund_event],
                    events_list=context.decoded_events,
                )

            break
        else:
            log.error(f'Could not find repayment event for extrafi in {context.transaction}')

        return DEFAULT_EVM_DECODING_OUTPUT

    def _handle_farm_events(self, context: DecoderContext) -> EvmDecodingOutput:
        """Handle creating and closing farm positions"""
        if context.tx_log.topics[0] == CLOSE_POSITION_PARTIALLY:
            return self._partially_close_farm_position(context)
        if context.tx_log.topics[0] == INVEST_TO_VAULT_POSITION:
            return self._invest_into_farm_position(context)
        if context.tx_log.topics[0] == EXACT_REPAY:
            return self._handle_farm_repayment(context)
        return DEFAULT_EVM_DECODING_OUTPUT

    def decode_lending_claim_reward(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] != REWARD_PAID_TOPIC:
            return DEFAULT_EVM_DECODING_OUTPUT

        token_address = bytes_to_address(context.tx_log.topics[2])
        token = get_or_create_evm_token(
            userdb=self.node_inquirer.database,
            evm_address=token_address,
            evm_inquirer=self.node_inquirer,
            chain_id=self.node_inquirer.chain_id,
        )
        claimed = int.from_bytes(context.tx_log.data[0:32])

        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.asset == token and
                token_normalized_value(token_amount=claimed, token=token) == event.amount
            ):
                event.event_subtype = HistoryEventSubType.REWARD
                event.counterparty = CPT_EXTRAFI
                event.notes = f'Claim {event.amount} {token.symbol_or_name()} from Extrafi lending'
                break

        return DEFAULT_EVM_DECODING_OUTPUT

    def _cache_mapping_methods(self) -> tuple[Callable[[DecoderContext], EvmDecodingOutput]]:
        return (self.decode_lending_claim_reward,)

    def addresses_to_decoders(self) -> dict['ChecksumEvmAddress', tuple[Any, ...]]:
        return {  # same addresses are used in base and optimism
            EXTRAFI_POOL_CONTRACT: (self._handle_pool_events,),
            EXTRAFI_DISTRIBUTOR: (self._handle_claim,),
            EXTRAFI_STAKING_CONTRACT: (self._handle_pool_rewards,),
            VOTE_ESCROW: (self._vote_escrow_contract,),
            EXTRAFI_FARMING_CONTRACT: (self._handle_farm_events,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_EXTRAFI,
            label='Extrafi',
            image='extrafi.svg',
        ),)
