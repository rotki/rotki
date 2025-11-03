import logging
from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.utils import token_normalized_value, token_normalized_value_decimals
from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.ethereum.utils import should_update_protocol_cache
from rotkehlchen.chain.evm.constants import (
    DEFAULT_TOKEN_DECIMALS,
    DEPOSIT_TOPIC,
    DEPOSIT_TOPIC_V2,
    STAKING_DEPOSIT,
    WITHDRAW_TOPIC_V2,
    WITHDRAW_TOPIC_V3,
    ZERO_ADDRESS,
)
from rotkehlchen.chain.evm.decoding.curve.constants import CPT_CURVE
from rotkehlchen.chain.evm.decoding.interfaces import ReloadableDecoderMixin
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    FAILED_ENRICHMENT_OUTPUT,
    ActionItem,
    DecoderContext,
    EnricherContext,
    EvmDecodingOutput,
    TransferEnrichmentOutput,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.errors.misc import NotERC20Conformant, NotERC721Conformant
from rotkehlchen.globaldb.cache import globaldb_get_unique_cache_value
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import CacheType, ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

from .common import CurveBorrowRepayCommonDecoder
from .constants import (
    CURVE_LEND_VAULT_SYMBOL,
    CURVE_VAULT_ABI,
)
from .utils import query_curve_lending_vaults

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.fval import FVal
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class CurveLendCommonDecoder(CurveBorrowRepayCommonDecoder, ReloadableDecoderMixin):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',  # pylint: disable=unused-argument
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            leverage_zap: 'ChecksumEvmAddress | None',
    ) -> None:
        """Decoder for Curve lending.

        - leverage_zap is the LlamaLendLeverageZap contract used with leveraged positions.
        - vaults holds the Curve lending vault contract addresses.
        - controllers holds the vault's crvUSD controller contract addresses (one for every vault).
        """
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            leverage_zap=leverage_zap,
        )
        self.vaults: set[ChecksumEvmAddress] = set()
        self.controllers: set[ChecksumEvmAddress] = set()
        self.gauges: set[ChecksumEvmAddress] = set()

    def reload_data(self) -> Mapping['ChecksumEvmAddress', tuple[Any, ...]] | None:
        """Check that cache is up to date and refresh cache from db.
        Returns a fresh addresses to decoders mapping."""
        if should_update_protocol_cache(
                userdb=self.base.database,
                cache_key=CacheType.CURVE_LENDING_VAULTS,
        ) is True:
            query_curve_lending_vaults(
                database=self.node_inquirer.database,
                chain_id=self.node_inquirer.chain_id,
            )
        elif len(self.vaults) != 0:
            return None  # we didn't update the globaldb cache, and we have the data already

        with GlobalDBHandler().conn.read_ctx() as cursor:
            query_body = (
                'FROM evm_tokens LEFT JOIN common_asset_details '
                'ON evm_tokens.identifier = common_asset_details.identifier '
                'WHERE protocol=? AND symbol=? AND chain=?'
            )
            bindings = (CPT_CURVE, CURVE_LEND_VAULT_SYMBOL, self.node_inquirer.chain_id.serialize_for_db())  # noqa: E501

            cursor.execute(f'SELECT COUNT(*) {query_body}', bindings)
            if cursor.fetchone()[0] == len(self.vaults):
                return None  # up to date

            # we are missing new vaults. Populate the cache
            vault_data = cursor.execute(f'SELECT address {query_body}', bindings).fetchall()

            for row in vault_data:
                if (controller_address := self._maybe_get_cached_address_from_contract(
                    cache_type=CacheType.CURVE_LENDING_VAULT_CONTROLLER,
                    contract_address=(vault_address := row[0]),
                    contract_abi=CURVE_VAULT_ABI,
                    contract_method='controller',
                )) is None:
                    log.error(f'Failed to load controller address for Curve lending vault {vault_address}')  # noqa: E501
                    continue

                if (gauge_address := globaldb_get_unique_cache_value(
                    cursor=cursor,
                    key_parts=[CacheType.CURVE_LENDING_VAULT_GAUGE, str(vault_address)],
                )) is not None:
                    self.gauges.add(string_to_evm_address(gauge_address))

                self.vaults.add(vault_address)
                self.controllers.add(controller_address)

        return self.addresses_to_decoders()

    def _get_vault_event_tokens_and_amounts(
            self,
            vault_address: 'ChecksumEvmAddress',
            context: DecoderContext,
    ) -> tuple['EvmToken', 'EvmToken', 'FVal', 'FVal'] | None:
        """Get the vault token, underlying token, and the corresponding amounts.
        Returns the tokens and amounts in a tuple or None on error."""
        try:
            vault_token = self.base.get_or_create_evm_token(address=vault_address)
            if vault_token.underlying_tokens is None or len(vault_token.underlying_tokens) == 0:
                return None

            underlying_token = self.base.get_or_create_evm_token(
                address=vault_token.underlying_tokens[0].address,
            )
        except (NotERC20Conformant, NotERC721Conformant) as e:
            log.error(f'Failed to get tokens for Curve lending vault {vault_address} due to {e!s}')
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
        if (tokens_and_amounts := self._get_vault_event_tokens_and_amounts(
                vault_address=context.tx_log.address,
                context=context,
        )) is None:
            log.error(f'Failed to find tokens and amounts for Curve lending vault deposit transaction {context.transaction}')  # noqa: E501
            return None, None

        vault_token, underlying_token, shares_amount, assets_amount = tokens_and_amounts
        out_event, in_event = None, None
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == underlying_token and
                event.amount == assets_amount
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
                event.notes = f'Deposit {assets_amount} {underlying_token.symbol} in a Curve lending vault'  # noqa: E501
                event.counterparty = CPT_CURVE
                out_event = event
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.address == ZERO_ADDRESS and
                event.asset == vault_token and
                event.amount == shares_amount
            ):
                event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                event.notes = f'Receive {shares_amount} {vault_token.symbol} after deposit in a Curve lending vault'  # noqa: E501
                event.counterparty = CPT_CURVE
                in_event = event

            if out_event is not None and in_event is not None:
                break

        return out_event, in_event

    def _decode_withdraw(
            self,
            context: DecoderContext,
    ) -> tuple['EvmEvent | None', 'EvmEvent | None']:
        """Decode events associated with a withdrawal.
        Returns out_event and in_event in a tuple to be used for reordering."""
        if (tokens_and_amounts := self._get_vault_event_tokens_and_amounts(
                vault_address=context.tx_log.address,
                context=context,
        )) is None:
            log.error(f'Failed to find tokens and amounts for Curve lending vault withdrawal transaction {context.transaction}')  # noqa: E501
            return None, None

        vault_token, underlying_token, shares_amount, assets_amount = tokens_and_amounts
        out_event, in_event = None, None
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.address == ZERO_ADDRESS and
                event.asset == vault_token and
                event.amount == shares_amount
            ):
                event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                event.notes = f'Return {shares_amount} {vault_token.symbol} to a Curve lending vault'  # noqa: E501
                event.counterparty = CPT_CURVE
                out_event = event
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == underlying_token and
                event.amount == assets_amount
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REDEEM_WRAPPED
                event.notes = f'Withdraw {assets_amount} {underlying_token.symbol} from a Curve lending vault'  # noqa: E501
                event.counterparty = CPT_CURVE
                in_event = event

            if out_event is not None and in_event is not None:
                break

        return out_event, in_event

    def _decode_vault_events(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode events from Curve lending vaults."""
        if context.tx_log.topics[0] == DEPOSIT_TOPIC:
            out_event, in_event = self._decode_deposit(context=context)
        elif context.tx_log.topics[0] == WITHDRAW_TOPIC_V3:
            out_event, in_event = self._decode_withdraw(context=context)
        else:
            return DEFAULT_EVM_DECODING_OUTPUT

        if out_event is None or in_event is None:
            log.error(f'Failed to find both out and in events for Curve lending vault transaction {context.transaction}')  # noqa: E501
            return DEFAULT_EVM_DECODING_OUTPUT

        maybe_reshuffle_events(
            ordered_events=[out_event, in_event],
            events_list=context.decoded_events,
        )
        return DEFAULT_EVM_DECODING_OUTPUT

    def _get_vault_for_controller(
            self,
            controller_address: 'ChecksumEvmAddress',
    ) -> 'ChecksumEvmAddress | None':
        """Find the vault address associated with the specified controller address.
        Returns the vault address or None on error."""
        with GlobalDBHandler().conn.read_ctx() as cursor:
            if (key := cursor.execute(
                    'SELECT key FROM unique_cache WHERE value = ?',
                    (controller_address,),
            ).fetchone()) is None:
                log.error(
                    'Failed to find Curve lending vault address for controller '
                    f'{controller_address} on {self.node_inquirer.chain_name}',
                )
                return None

        return string_to_evm_address(key[0][-42:])  # 42 is the length of the EVM address

    def _get_controller_event_tokens_and_amounts(
            self,
            controller_address: 'ChecksumEvmAddress',
            context: DecoderContext,
    ) -> tuple['EvmToken', 'EvmToken', 'FVal', 'FVal'] | None:
        """Get the collateral token, borrowed token, and the corresponding amounts.
        Returns the tokens and amounts in a tuple or None on error."""
        if (vault_address := self._get_vault_for_controller(controller_address)) is None:
            return None

        if (collateral_token := self._maybe_get_cached_token(
            cache_type=CacheType.CURVE_CRVUSD_COLLATERAL_TOKEN,
            contract_address=controller_address,
        )) is None:
            return None

        if (borrowed_token := self._maybe_get_cached_token(
            cache_type=CacheType.CURVE_LENDING_VAULT_BORROWED_TOKEN,
            contract_address=vault_address,
        )) is None:
            log.error(
                'Failed to get borrowed token for Curve lending vault '
                f'{vault_address} on {self.node_inquirer.chain_name}',
            )
            return None

        return (
            collateral_token,
            borrowed_token,
            token_normalized_value(
                token_amount=int.from_bytes(context.tx_log.data[0:32]),
                token=collateral_token,
            ),
            token_normalized_value(
                token_amount=int.from_bytes(context.tx_log.data[32:64]),
                token=borrowed_token,
            ),
        )

    def maybe_decode_leveraged_borrow(self, context: DecoderContext) -> EvmDecodingOutput | None:
        """Decode events associated with creating a leveraged Curve position."""
        if (tokens_and_amounts := self._get_controller_event_tokens_and_amounts(
                controller_address=(controller_address := context.tx_log.address),
                context=context,
        )) is None:
            log.error(f'Failed to find tokens and amounts for Curve borrow transaction {context.transaction}')  # noqa: E501
            return DEFAULT_EVM_DECODING_OUTPUT

        collateral_token, borrowed_token, _, _ = tokens_and_amounts

        # Find tx_log of the deposit into the leverage zap contract and get the amounts.
        # Note that 'borrowed' and 'collateral' here only refer to which token
        # is being used. Both are being deposited for use as collateral in the leveraged position.
        for tx_log in context.all_logs:
            if (
                tx_log.address == self.leverage_zap and
                tx_log.topics[0] == STAKING_DEPOSIT and
                self.base.is_tracked(bytes_to_address(tx_log.topics[1]))
            ):
                collateral_amount = token_normalized_value(
                    token_amount=int.from_bytes(tx_log.data[0:32]),
                    token=collateral_token,
                )
                borrowed_amount = token_normalized_value(
                    token_amount=int.from_bytes(tx_log.data[32:64]),
                    token=borrowed_token,
                )
                break
        else:
            return None  # This is not a leveraged loan.

        # The borrowed token deposit (if present) should already be in decoded_events,
        # but an ActionItem must be used for collateral deposits.
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.address == self.leverage_zap and
                event.asset == borrowed_token and
                event.amount == borrowed_amount
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.notes = f'Deposit {event.amount} {borrowed_token.symbol} into a leveraged Curve position'  # noqa: E501
                event.counterparty = CPT_CURVE
                event.extra_data = {'controller_address': controller_address}
                break

        return EvmDecodingOutput(action_items=[ActionItem(
            action='transform',
            from_event_type=HistoryEventType.SPEND,
            from_event_subtype=HistoryEventSubType.NONE,
            asset=collateral_token,
            amount=collateral_amount,
            to_event_type=HistoryEventType.DEPOSIT,
            to_event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            to_notes=f'Deposit {collateral_amount} {collateral_token.symbol} into a leveraged Curve position',  # noqa: E501
            to_counterparty=CPT_CURVE,
            extra_data={'controller_address': controller_address},
        )])

    def _decode_staking_events(self, context: DecoderContext) -> EvmDecodingOutput:
        """This decodes deposit & withdraw events of the vault's gauge contract."""
        if context.tx_log.topics[0] not in (DEPOSIT_TOPIC_V2, WITHDRAW_TOPIC_V2):
            return DEFAULT_EVM_DECODING_OUTPUT

        amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[:32]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )
        gauge_asset = self.base.get_or_create_evm_asset(context.tx_log.address)
        paired_events_data, from_event_type, from_event_subtype, to_event_type, to_event_subtype, to_notes = None, HistoryEventType.SPEND, HistoryEventSubType.NONE, None, None, ''  # noqa: E501
        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.amount == amount and
                    event.address == context.tx_log.address
            ):
                event.counterparty = CPT_CURVE
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
                event.notes = f'Deposit {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} into {gauge_asset.symbol}'  # noqa: E501

                paired_events_data = ([event], True)
                from_event_type = HistoryEventType.RECEIVE
                from_event_subtype = HistoryEventSubType.NONE
                to_event_type = HistoryEventType.RECEIVE
                to_event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                to_notes = f'Receive {amount} {gauge_asset.symbol} after depositing in curve lending vault gauge'  # noqa: E501
                break

            if (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.amount == amount and
                    event.address == context.tx_log.address
            ):
                event.counterparty = CPT_CURVE
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REDEEM_WRAPPED
                event.notes = f'Withdraw {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} from {gauge_asset.symbol}'  # noqa: E501

                paired_events_data = ([event], False)
                from_event_type = HistoryEventType.SPEND
                from_event_subtype = HistoryEventSubType.NONE
                to_event_type = HistoryEventType.SPEND
                to_event_subtype = HistoryEventSubType.RETURN_WRAPPED
                to_notes = f'Return {amount} {gauge_asset.symbol} after withdrawing from curve lending vault gauge'  # noqa: E501
                break
        else:
            log.error(f'Failed to find deposit/withdraw event for curve lending vault gauge for {context.transaction}')  # noqa: E501
            return DEFAULT_EVM_DECODING_OUTPUT

        return EvmDecodingOutput(action_items=[
            ActionItem(
                action='transform',
                from_event_type=from_event_type,
                from_event_subtype=from_event_subtype,
                asset=gauge_asset,
                amount=amount,
                to_counterparty=CPT_CURVE,
                to_notes=to_notes,
                paired_events_data=paired_events_data,
                to_event_type=to_event_type,
                to_event_subtype=to_event_subtype,
            ),
        ])

    def _maybe_enrich_curve_lending_gauge_rewards(self, context: EnricherContext) -> TransferEnrichmentOutput:  # noqa: E501
        """ This enriches rewards paid to users from the vault's gauge contract.
        It is always a transfer of the reward tokens of the gauge without any other log emitted.

        May raise:
        - UnknownAsset
        - WrongAssetType
        """
        if (
                (source_address := bytes_to_address(context.tx_log.topics[1])) in self.gauges and
                context.event.event_type == HistoryEventType.RECEIVE and
                context.event.event_subtype == HistoryEventSubType.NONE and
                (crypto_asset := context.event.asset.resolve_to_evm_token()).evm_address not in self.vaults  # noqa: E501
        ):
            context.event.event_subtype = HistoryEventSubType.REWARD
            context.event.notes = f'Receive {context.event.amount} {crypto_asset.symbol} rewards from curve lending {self.base.get_or_create_evm_asset(source_address).symbol}'  # noqa: E501
            context.event.counterparty = CPT_CURVE
            return TransferEnrichmentOutput(matched_counterparty=CPT_CURVE)

        return FAILED_ENRICHMENT_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return (
            super().addresses_to_decoders() |
            dict.fromkeys(self.vaults, (self._decode_vault_events,)) |
            dict.fromkeys(self.gauges, (self._decode_staking_events,))
        )

    def enricher_rules(self) -> list[Callable]:
        return [self._maybe_enrich_curve_lending_gauge_rewards]
