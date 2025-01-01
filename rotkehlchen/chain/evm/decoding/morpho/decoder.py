import logging
from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.chain.ethereum.utils import should_update_protocol_cache, token_normalized_value
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface, ReloadableDecoderMixin
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.errors.misc import NotERC20Conformant, NotERC721Conformant
from rotkehlchen.globaldb.cache import globaldb_get_general_cache_values
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import MORPHO_VAULT_PROTOCOL, CacheType, ChecksumEvmAddress, EvmTransaction
from rotkehlchen.utils.misc import bytes_to_address

from .constants import CPT_MORPHO
from .utils import query_morpho_reward_distributors, query_morpho_vaults

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset, EvmToken
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.fval import FVal
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

DEPOSIT_TOPIC: Final = b'\xdc\xbc\x1c\x05$\x0f1\xff:\xd0g\xef\x1e\xe3\\\xe4\x99wbu.:\tR\x84uED\xf4\xc7\t\xd7'  # noqa: E501
WITHDRAW_TOPIC: Final = b'\xfb\xdey} \x1ch\x1b\x91\x05e)\x11\x9e\x0b\x02@|{\xb9jJ,u\xc0\x1f\xc9fr2\xc8\xdb'  # noqa: E501
CLAIM_TOPIC: Final = b'\xf7\xa4\x00w\xffz\x04\xc7\xe6\x1fo&\xfb\x13wBY\xdd\xf1\xb6\xbc\xe9\xec\xf2j\x82v\xcd\xd3\x99&\x83'  # noqa: E501


class MorphoCommonDecoder(DecoderInterface, ReloadableDecoderMixin):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            bundlers: set['ChecksumEvmAddress'],
            weth: 'Asset',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.vaults: set[ChecksumEvmAddress] = set()
        self.bundlers = bundlers
        self.rewards_distributors: list[ChecksumEvmAddress] = []
        self.weth = weth

    def reload_data(self) -> Mapping['ChecksumEvmAddress', tuple[Any, ...]] | None:
        """Check that cache is up to date and refresh cache from db.
        Returns a fresh addresses to decoders mapping.
        """
        updated = False
        if should_update_protocol_cache(CacheType.MORPHO_VAULTS) is True:
            query_morpho_vaults(database=self.evm_inquirer.database)
            updated = True
        if should_update_protocol_cache(CacheType.MORPHO_REWARD_DISTRIBUTORS) is True:
            query_morpho_reward_distributors()
            updated = True
        if updated is False and len(self.vaults) != 0 and len(self.rewards_distributors) != 0:
            return None  # we didn't update the globaldb cache, and we have the data already

        with GlobalDBHandler().conn.read_ctx() as cursor:
            query_body = 'FROM evm_tokens WHERE protocol=? AND chain=?'
            bindings = (MORPHO_VAULT_PROTOCOL, self.evm_inquirer.chain_id.serialize_for_db())

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
    ) -> tuple['EvmEvent | None', 'EvmEvent | None']:
        """Decode events associated with a deposit.
        Returns out_event and in_event in a tuple to be used for reordering."""
        if (tokens_and_amounts := self._get_vault_event_tokens_and_amounts(context)) is None:
            log.error(f'Failed to find tokens and amounts for Morpho vault deposit transaction {context.transaction}')  # noqa: E501
            return None, None

        vault_token, underlying_token, shares_amount, assets_amount = tokens_and_amounts
        spend_event, receive_event = None, None
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                (
                    event.asset == underlying_token or
                    (event.asset == A_ETH and underlying_token == self.weth)  # WETH vaults can have an ETH send event  # noqa: E501
                ) and
                event.balance.amount == assets_amount
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.notes = f'Deposit {event.balance.amount} {event.asset.resolve_to_asset_with_symbol().symbol} in a Morpho vault'  # noqa: E501
                event.counterparty = CPT_MORPHO
                event.extra_data = {'vault': vault_token.evm_address}  # Used when querying balances  # noqa: E501
                spend_event = event
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.address == ZERO_ADDRESS and
                event.asset == vault_token and
                event.balance.amount == shares_amount
            ):
                event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                event.notes = f'Receive {event.balance.amount} {event.asset.resolve_to_asset_with_symbol().symbol} after deposit in a Morpho vault'  # noqa: E501
                event.counterparty = CPT_MORPHO
                receive_event = event

            if spend_event is not None and receive_event is not None:
                return spend_event, receive_event

        if receive_event is not None and spend_event is None:
            spend_event = self.base.make_event_from_transaction(
                transaction=context.transaction,
                tx_log=context.tx_log,
                event_type=HistoryEventType.DEPOSIT,
                event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
                asset=underlying_token,
                balance=Balance(amount=assets_amount),
                location_label=receive_event.location_label,
                notes=f'Deposit {assets_amount} {underlying_token.symbol} in a Morpho vault',
                counterparty=CPT_MORPHO,
                address=vault_token.evm_address,
            )
            context.decoded_events.append(spend_event)

        return spend_event, receive_event

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
                event.balance.amount == shares_amount
            ):
                event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                event.notes = f'Return {event.balance.amount} {event.asset.resolve_to_asset_with_symbol().symbol} to a Morpho vault'  # noqa: E501
                event.counterparty = CPT_MORPHO
                spend_event = event
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                (
                    event.asset == underlying_token or
                    (event.asset == A_ETH and underlying_token == self.weth)  # WETH vaults can have an ETH receive event  # noqa: E501
                ) and
                event.balance.amount == assets_amount
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                event.notes = f'Withdraw {event.balance.amount} {event.asset.resolve_to_asset_with_symbol().symbol} from a Morpho vault'  # noqa: E501
                event.counterparty = CPT_MORPHO
                receive_event = event

            if spend_event is not None and receive_event is not None:
                return spend_event, receive_event

        if spend_event is not None and receive_event is None:
            receive_event = self.base.make_event_from_transaction(
                transaction=context.transaction,
                tx_log=context.tx_log,
                event_type=HistoryEventType.WITHDRAWAL,
                event_subtype=HistoryEventSubType.REMOVE_ASSET,
                asset=underlying_token,
                balance=Balance(amount=assets_amount),
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
            out_event, in_event = self._decode_deposit(context=context)
        elif context.tx_log.topics[0] == WITHDRAW_TOPIC:
            out_event, in_event = self._decode_withdraw(context=context)
        else:
            return DEFAULT_DECODING_OUTPUT

        if out_event is None or in_event is None:
            log.error(f'Failed to find both out and in events for Morpho vault transaction {context.transaction}')  # noqa: E501
            return DEFAULT_DECODING_OUTPUT

        maybe_reshuffle_events(
            ordered_events=[out_event, in_event],
            events_list=context.decoded_events,
        )
        return DEFAULT_DECODING_OUTPUT

    def _decode_reward_claim(self, context: DecoderContext) -> DecodingOutput:
        """Decode Morpho vault reward claim event."""
        if context.tx_log.topics[0] != CLAIM_TOPIC:
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
                event.notes = f'Claim {event.balance.amount} {event.asset.resolve_to_asset_with_symbol().symbol} from Morpho'  # noqa: E501
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
                event.address in self.bundlers and
                event.address == transaction.to_address
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
