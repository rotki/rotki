import logging
from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.utils import should_update_protocol_cache, token_normalized_value
from rotkehlchen.chain.evm.constants import DEPOSIT_TOPIC, WITHDRAW_TOPIC_V3, ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import REWARD_CLAIMED
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface, ReloadableDecoderMixin
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.errors.misc import NotERC20Conformant, NotERC721Conformant
from rotkehlchen.globaldb.cache import globaldb_get_general_cache_values
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import CacheType, ChecksumEvmAddress, EvmTransaction
from rotkehlchen.utils.misc import bytes_to_address

from .constants import CPT_MORPHO
from .utils import query_morpho_reward_distributors, query_morpho_vaults

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset, EvmToken
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.fval import FVal
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class MorphoCommonDecoder(DecoderInterface, ReloadableDecoderMixin):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            bundlers: set['ChecksumEvmAddress'],
            adapters: set['ChecksumEvmAddress'],
            weth: 'Asset',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.vaults: set[ChecksumEvmAddress] = set()
        self.bundlers = bundlers
        self.adapters = adapters
        self.rewards_distributors: list[ChecksumEvmAddress] = []
        self.weth = weth

    def reload_data(self) -> Mapping['ChecksumEvmAddress', tuple[Any, ...]] | None:
        """Check that cache is up to date and refresh cache from db.
        Returns a fresh addresses to decoders mapping.
        """
        updated = False
        if should_update_protocol_cache(self.base.database, CacheType.MORPHO_VAULTS) is True:
            query_morpho_vaults(
                database=self.evm_inquirer.database,
                chain_id=self.evm_inquirer.chain_id,
            )
            updated = True
        if should_update_protocol_cache(
                userdb=self.base.database,
                cache_key=CacheType.MORPHO_REWARD_DISTRIBUTORS,
                args=(str(self.evm_inquirer.chain_id),),
        ) is True:
            query_morpho_reward_distributors()
            updated = True
        if updated is False and len(self.vaults) != 0 and len(self.rewards_distributors) != 0:
            return None  # we didn't update the globaldb cache, and we have the data already

        with GlobalDBHandler().conn.read_ctx() as cursor:
            query_body = 'FROM evm_tokens WHERE protocol=? AND chain=?'
            bindings = (CPT_MORPHO, self.evm_inquirer.chain_id.serialize_for_db())

            cursor.execute(f'SELECT COUNT(*) {query_body}', bindings)
            if cursor.fetchone()[0] != len(self.vaults):
                # we are missing new vaults. Populate the cache
                cursor.execute(f'SELECT protocol, address {query_body}', bindings)
                self.vaults = {string_to_evm_address(row[1]) for row in cursor}

            self.rewards_distributors = [
                string_to_evm_address(address) for address in globaldb_get_general_cache_values(
                    cursor=cursor,
                    key_parts=(
                        CacheType.MORPHO_REWARD_DISTRIBUTORS,
                        str(self.evm_inquirer.chain_id),
                    ),
                )
            ]

        return self.addresses_to_decoders()

    def _get_vault_event_tokens_and_amounts(
            self,
            context: DecoderContext,
    ) -> tuple['EvmToken', 'EvmToken', 'FVal', 'FVal'] | None:
        """Get the vault token, underlying token, and the corresponding amounts.
        Returns the tokens and amounts in a tuple or None on error."""
        try:
            vault_token = self.base.get_or_create_evm_token(address=context.tx_log.address)
            if len(vault_token.underlying_tokens) == 0:
                return None

            underlying_token = self.base.get_or_create_evm_token(
                address=vault_token.underlying_tokens[0].address,
            )
        except (NotERC20Conformant, NotERC721Conformant) as e:
            log.error(f'Failed to get tokens for Morpho vault {context.tx_log.address} due to {e!s}')  # noqa: E501
            return None

        assets_amount = token_normalized_value(
            token_amount=int.from_bytes(context.tx_log.data[0:32]),
            token=underlying_token,
        )
        shares_amount = token_normalized_value(
            token_amount=int.from_bytes(context.tx_log.data[32:64]),
            token=vault_token,
        )

        return vault_token, underlying_token, shares_amount, assets_amount

    def _decode_deposit(
            self,
            context: DecoderContext,
    ) -> tuple[list['EvmEvent'], 'EvmEvent | None']:
        """Decode events associated with a deposit.
        Returns out_events and in_event in a tuple to be used for reordering."""
        if (tokens_and_amounts := self._get_vault_event_tokens_and_amounts(context)) is None:
            log.error(f'Failed to find tokens and amounts for Morpho vault deposit transaction {context.transaction}')  # noqa: E501
            return [], None

        vault_token, underlying_token, shares_amount, assets_amount = tokens_and_amounts
        spend_events, spent_amount, receive_event, is_weth_vault = [], ZERO, None, False
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                (
                    event.asset == underlying_token or
                    (is_weth_vault := (event.asset == A_ETH and underlying_token == self.weth))  # WETH vaults can have an ETH send event  # noqa: E501
                ) and
                (
                    event.amount == assets_amount or
                    (is_weth_vault and event.address in self.bundlers)
                ) and
                self.base.is_tracked(bytes_to_address(context.tx_log.topics[2]))  # owner address should be tracked  # noqa: E501
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
                event.notes = f'Deposit {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} in a Morpho vault'  # noqa: E501
                event.counterparty = CPT_MORPHO
                event.extra_data = {'vault': vault_token.evm_address}  # Used when querying balances  # noqa: E501
                spend_events.append(event)
                spent_amount += event.amount
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.address == ZERO_ADDRESS and
                event.asset == vault_token and
                event.amount == shares_amount
            ):
                event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                event.notes = f'Receive {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} after deposit in a Morpho vault'  # noqa: E501
                event.counterparty = CPT_MORPHO
                receive_event = event

            if (is_weth_vault is False and len(spend_events) == 1) and receive_event is not None:
                return spend_events, receive_event

        if (
            receive_event is not None and
            (len(spend_events) == 0 or (is_weth_vault and spent_amount != assets_amount))
        ):  # Create a deposit event for funds moved from another vault if the spend events don't cover the deposited amount.  # noqa: E501
            deposit_event = self.base.make_event_from_transaction(
                transaction=context.transaction,
                tx_log=context.tx_log,
                event_type=HistoryEventType.DEPOSIT,
                event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
                asset=underlying_token,
                amount=(amount := assets_amount - spent_amount),
                location_label=receive_event.location_label,
                notes=f'Deposit {amount} {underlying_token.symbol} in a Morpho vault',
                counterparty=CPT_MORPHO,
                address=vault_token.evm_address,
                extra_data={'vault': vault_token.evm_address},  # Used when querying balances  # noqa: E501
            )
            context.decoded_events.append(deposit_event)
            spend_events.append(deposit_event)

        return spend_events, receive_event

    def _decode_withdraw(
            self,
            context: DecoderContext,
    ) -> tuple['EvmEvent | None', 'EvmEvent | None']:
        """Decode events associated with a withdrawal.
        Returns out_event and in_event in a tuple to be used for reordering."""
        if (tokens_and_amounts := self._get_vault_event_tokens_and_amounts(context)) is None:
            log.error(f'Failed to find tokens and amounts for Morpho vault withdrawal transaction {context.transaction}')  # noqa: E501
            return None, None

        vault_token, underlying_token, shares_amount, assets_amount = tokens_and_amounts
        spend_event, receive_event = None, None
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.address == ZERO_ADDRESS and
                event.asset == vault_token and
                event.amount == shares_amount
            ):
                event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                event.notes = f'Return {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} to a Morpho vault'  # noqa: E501
                event.counterparty = CPT_MORPHO
                spend_event = event
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                (
                    event.asset == underlying_token or
                    (event.asset == A_ETH and underlying_token == self.weth)  # WETH vaults can have an ETH receive event  # noqa: E501
                ) and
                event.amount == assets_amount
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REDEEM_WRAPPED
                event.notes = f'Withdraw {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} from a Morpho vault'  # noqa: E501
                event.counterparty = CPT_MORPHO
                receive_event = event

            if spend_event is not None and receive_event is not None:
                return spend_event, receive_event

        if spend_event is not None and receive_event is None:
            receive_event = self.base.make_event_from_transaction(
                transaction=context.transaction,
                tx_log=context.tx_log,
                event_type=HistoryEventType.WITHDRAWAL,
                event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
                asset=underlying_token,
                amount=assets_amount,
                location_label=spend_event.location_label,
                notes=f'Withdraw {assets_amount} {underlying_token.symbol} from a Morpho vault',
                counterparty=CPT_MORPHO,
                address=vault_token.evm_address,
            )
            context.decoded_events.append(receive_event)

        return spend_event, receive_event

    def _decode_vault_events(self, context: DecoderContext) -> DecodingOutput:
        """Decode events from Morpho vaults."""
        if context.tx_log.topics[0] == DEPOSIT_TOPIC:
            out_events, in_event = self._decode_deposit(context=context)
        elif context.tx_log.topics[0] == WITHDRAW_TOPIC_V3:
            out_event, in_event = self._decode_withdraw(context=context)
            out_events = [out_event] if out_event is not None else []
        else:
            return DEFAULT_DECODING_OUTPUT

        if len(out_events) == 0 or in_event is None:
            log.error(f'Failed to find both out and in events for Morpho vault transaction {context.transaction}')  # noqa: E501
            return DEFAULT_DECODING_OUTPUT

        maybe_reshuffle_events(
            ordered_events=out_events + [in_event],
            events_list=context.decoded_events,
        )
        return DEFAULT_DECODING_OUTPUT

    def _decode_reward_claim(self, context: DecoderContext) -> DecodingOutput:
        """Decode Morpho vault reward claim event."""
        if context.tx_log.topics[0] != REWARD_CLAIMED:
            return DEFAULT_DECODING_OUTPUT

        claimed_asset = self.base.get_or_create_evm_asset(
            address=bytes_to_address(context.tx_log.topics[2]),
        )
        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.address == context.tx_log.address and
                    event.asset == claimed_asset
            ):
                event.event_subtype = HistoryEventSubType.REWARD
                event.counterparty = CPT_MORPHO
                event.notes = f'Claim {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} from Morpho'  # noqa: E501
                break
        else:
            log.error(f'Failed to find Morpho reward claim event in {context.transaction}')

        return DEFAULT_DECODING_OUTPUT

    def _remove_unneeded_bundler_events(
            self,
            transaction: 'EvmTransaction',
            decoded_events: list['EvmEvent'],
            all_logs: list['EvmTxReceiptLog'],  # pylint: disable=unused-argument
    ) -> list['EvmEvent']:
        """Remove any transfers to/from the bundler since their amounts are included in
        the deposit/withdrawal vault events."""
        return [
            event for event in decoded_events if not (
                event.event_type in {HistoryEventType.SPEND, HistoryEventType.RECEIVE} and
                event.event_subtype == HistoryEventSubType.NONE and
                (
                    (event.address in self.bundlers and event.address == transaction.to_address) or
                    event.address in self.adapters
                )
            )
        ]

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return dict.fromkeys(self.rewards_distributors, (self._decode_reward_claim,)) | dict.fromkeys(self.vaults, (self._decode_vault_events,))  # noqa: E501

    def addresses_to_counterparties(self) -> dict['ChecksumEvmAddress', str]:
        return dict.fromkeys(self.bundlers, CPT_MORPHO)

    def post_decoding_rules(self) -> dict[str, list[tuple[int, Callable]]]:
        return {
            CPT_MORPHO: [(0, self._remove_unneeded_bundler_events)],
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(identifier=CPT_MORPHO, label='Morpho', image='morpho.svg'),)
