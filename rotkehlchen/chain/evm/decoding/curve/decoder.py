import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Literal

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.constants import ETH_SPECIAL_ADDRESS, ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.aave.constants import CPT_AAVE_V1, CPT_AAVE_V2, CPT_AAVE_V3
from rotkehlchen.chain.evm.decoding.curve.constants import (
    ADD_LIQUIDITY_EVENTS,
    CPT_CURVE,
    EXCHANGE_MULTIPLE,
    GAUGE_DEPOSIT,
    GAUGE_VOTE,
    GAUGE_WITHDRAW,
    REMOVE_LIQUIDITY_EVENTS,
    REMOVE_LIQUIDITY_IMBALANCE,
    TOKEN_EXCHANGE,
    TOKEN_EXCHANGE_UNDERLYING,
)
from rotkehlchen.chain.evm.decoding.curve.curve_cache import (
    query_curve_data,
    read_curve_pools_and_gauges,
    save_curve_data_to_cache,
)
from rotkehlchen.chain.evm.decoding.interfaces import (
    DecoderInterface,
    ReloadablePoolsAndGaugesDecoderMixin,
)
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    FAILED_ENRICHMENT_OUTPUT,
    DecoderContext,
    DecodingOutput,
    EnricherContext,
    TransferEnrichmentOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.history.events.structures.evm_event import EvmProduct
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import CacheType, ChainID, ChecksumEvmAddress, EvmTokenKind, EvmTransaction
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.user_messages import MessagesAggregator


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class CurveCommonDecoder(DecoderInterface, ReloadablePoolsAndGaugesDecoderMixin):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',  # pylint: disable=unused-argument
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            native_currency: 'Asset',
            aave_pools: set['ChecksumEvmAddress'],
            curve_deposit_contracts: set['ChecksumEvmAddress'],
            curve_swap_router: 'ChecksumEvmAddress',
            gauge_controller: 'ChecksumEvmAddress',
    ) -> None:
        self.native_currency = native_currency
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        ReloadablePoolsAndGaugesDecoderMixin.__init__(
            self,
            evm_inquirer=evm_inquirer,
            cache_type_to_check_for_freshness=CacheType.CURVE_LP_TOKENS,
            query_data_method=query_curve_data,
            save_data_to_cache_method=save_curve_data_to_cache,
            read_data_from_cache_method=read_curve_pools_and_gauges,
            chain_id=evm_inquirer.chain_id,
        )
        self.aave_pools = aave_pools
        self.curve_deposit_contracts = curve_deposit_contracts
        self.curve_swap_router = curve_swap_router
        self.gauge_controller = gauge_controller

    def _read_curve_asset(
            self: 'CurveCommonDecoder',
            asset_address: ChecksumEvmAddress | None,
            chain_id: ChainID,
    ) -> Asset | None:
        """
        A thin wrapper that turns asset address into an asset object.

        Object returned here is a pure Asset (not a resolved CryptoAsset) since it is meant only for
        comparison with other assets. And to compare with other assets there is no need to resolve.
        """  # noqa: E501
        if asset_address is None:
            return None

        if asset_address == ETH_SPECIAL_ADDRESS:
            return self.native_currency

        return Asset(evm_address_to_identifier(
            address=asset_address,
            chain_id=chain_id,
            token_type=EvmTokenKind.ERC20,
        ))

    @property
    def pools(self) -> dict[ChecksumEvmAddress, list[ChecksumEvmAddress]]:
        assert isinstance(self.cache_data[0], dict), 'CurveDecoder cache_data[0] is not a dict'
        return self.cache_data[0]

    def _decode_curve_remove_events(
            self,
            transaction: EvmTransaction,
            tx_log: EvmTxReceiptLog,
            decoded_events: list['EvmEvent'],
            user_or_contract_address: ChecksumEvmAddress,
    ) -> DecodingOutput:
        """Decode information related to withdrawing assets from curve pools"""
        withdrawal_events: list[EvmEvent] = []
        return_event: EvmEvent | None = None
        for event in decoded_events:
            try:
                crypto_asset = event.asset.resolve_to_crypto_asset()
            except (UnknownAsset, WrongAssetType):
                self.notify_user(event=event, counterparty=CPT_CURVE)
                continue

            if (  # Withdraw eth
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == self.native_currency and
                event.location_label == user_or_contract_address
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                event.counterparty = CPT_CURVE
                event.notes = f'Remove {event.balance.amount} {crypto_asset.symbol} from the curve pool'  # noqa: E501
                withdrawal_events.append(event)
            elif (  # Withdraw send wrapped
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype in {HistoryEventSubType.NONE, HistoryEventSubType.RETURN_WRAPPED} and  # noqa: E501
                event.location_label == transaction.from_address and
                (
                    user_or_contract_address == event.location_label or
                    user_or_contract_address in self.curve_deposit_contracts or
                    tx_log.topics[0] in REMOVE_LIQUIDITY_IMBALANCE
                )
            ):
                event.event_type = HistoryEventType.SPEND
                event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                event.counterparty = CPT_CURVE
                event.notes = f'Return {event.balance.amount} {crypto_asset.symbol}'
                return_event = event
            elif (  # Withdraw receive asset
                tx_log.address in self.pools and
                transaction.from_address == user_or_contract_address
            ):
                notes = f'Remove {event.balance.amount} {crypto_asset.symbol} from {tx_log.address} curve pool'  # noqa: E501
                if (  # Raw event
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.location_label == user_or_contract_address
                ):
                    event.event_type = HistoryEventType.WITHDRAWAL
                    event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                    event.counterparty = CPT_CURVE
                    event.notes = notes
                    withdrawal_events.append(event)
                elif (  # Is already decoded by aave
                    tx_log.address in self.aave_pools and
                    event.event_type == HistoryEventType.WITHDRAWAL and
                    event.event_subtype == HistoryEventSubType.REMOVE_ASSET and
                    event.location_label == tx_log.address and
                    event.counterparty in (CPT_AAVE_V1, CPT_AAVE_V2, CPT_AAVE_V3)
                ):
                    event.location_label = user_or_contract_address
                    event.notes = notes
                    event.counterparty = CPT_CURVE
                    withdrawal_events.append(event)
            # Two conditions below handle withdrawals from metapools via zap contracts. In this
            # case there are 2 RemoveLiquidity events emitted. One for withdrawing from the
            # metapool and one for withdrawing from the underlying pool. This means that this
            # decoding method is executed twice. Between 2 RemoveLiquidity events an extra transfer
            # can occur, and we have to handle it together with the events that were decoded in the
            # first run (i.e. those that already have proper event type and counterparty set) in
            # order to have extra_data properly populated for accounting. Same happens for deposits
            # in another method below.
            elif (
                event.event_type == HistoryEventType.WITHDRAWAL and
                event.event_subtype == HistoryEventSubType.REMOVE_ASSET and
                event.counterparty == CPT_CURVE
            ):
                withdrawal_events.append(event)
            elif (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.RETURN_WRAPPED and
                event.counterparty == CPT_CURVE
            ):
                return_event = event

        # Make sure that the order is the following:
        # 1. Return pool token event
        # 2. Withdrawal 1
        # 3. Withdrawal 2
        # etc.
        if return_event is None or len(withdrawal_events) == 0:
            # for deposit zap contracts, this is handled during post decoding
            if user_or_contract_address in self.curve_deposit_contracts and return_event is not None:  # noqa: E501
                return DecodingOutput(matched_counterparty=CPT_CURVE)

            log.error(
                f'Expected to see a return pool token event and '
                f'withdrawal events for a curve pool, but have not found them. '
                f'Tx_hash: {transaction.tx_hash.hex()} '
                f'User address: {user_or_contract_address}',
            )
            return DEFAULT_DECODING_OUTPUT

        self._sort_events(
            action_type='removal',
            return_or_receive_event=return_event,
            withdrawal_or_deposit_events=withdrawal_events,
            all_events=decoded_events,
        )
        return DEFAULT_DECODING_OUTPUT

    def _decode_curve_deposit_events(
            self,
            transaction: EvmTransaction,
            tx_log: EvmTxReceiptLog,
            decoded_events: list['EvmEvent'],
            user_or_contract_address: ChecksumEvmAddress,
    ) -> DecodingOutput:
        """Decode information related to depositing assets in curve pools"""
        deposit_events: list[EvmEvent] = []
        receive_event: EvmEvent | None = None
        for event in decoded_events:
            try:
                crypto_asset = event.asset.resolve_to_crypto_asset()
            except (UnknownAsset, WrongAssetType):
                self.notify_user(event=event, counterparty=CPT_CURVE)
                continue

            if (  # Deposit ETH
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == self.native_currency and
                event.location_label == user_or_contract_address
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.counterparty = CPT_CURVE
                event.notes = f'Deposit {event.balance.amount} {crypto_asset.symbol} in curve pool'
                deposit_events.append(event)
            elif (  # Deposit receive pool token
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == user_or_contract_address and
                tx_log.address in self.pools
            ):
                event.event_type = HistoryEventType.RECEIVE
                event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                event.counterparty = CPT_CURVE
                event.notes = f'Receive {event.balance.amount} {crypto_asset.symbol} after depositing in curve pool {tx_log.address}'  # noqa: E501
                receive_event = event
            elif (  # deposit give asset
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                (
                    event.location_label == user_or_contract_address or
                    user_or_contract_address in self.curve_deposit_contracts
                ) and
                tx_log.address in self.pools
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.counterparty = CPT_CURVE
                event.notes = f'Deposit {event.balance.amount} {crypto_asset.symbol} in curve pool {tx_log.address}'  # noqa: E501
                deposit_events.append(event)
            elif (
                event.event_type == HistoryEventType.DEPOSIT and
                event.event_subtype == HistoryEventSubType.DEPOSIT_ASSET and
                event.counterparty == CPT_CURVE
            ):
                deposit_events.append(event)
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.RECEIVE_WRAPPED and
                event.counterparty == CPT_CURVE
            ):
                receive_event = event

        # Make sure that the order is the following:
        # 1. Receive pool token event
        # 2. Deposit 1
        # 3. Deposit 2
        # etc.
        if receive_event is None or len(deposit_events) == 0:
            # for deposit zap contracts, this is handled during post decoding
            if user_or_contract_address in self.curve_deposit_contracts and len(deposit_events) > 0:  # noqa: E501
                return DecodingOutput(matched_counterparty=CPT_CURVE)

            log.warning(  # can happen as part of complicated swaps
                f'Expected to see a receive pool token event and deposit '
                f'events for a curve pool, but have not found them. '
                f'Tx_hash: {transaction.tx_hash.hex()} '
                f'User address: {user_or_contract_address}',
            )
            return DEFAULT_DECODING_OUTPUT

        self._sort_events(
            action_type='addition',
            return_or_receive_event=receive_event,
            withdrawal_or_deposit_events=deposit_events,
            all_events=decoded_events,
        )
        return DEFAULT_DECODING_OUTPUT

    def _decode_curve_trades(self, context: DecoderContext) -> DecodingOutput:
        """Decode curve trades made via single pools or curve swap router
        First determine:
        - `spender_address`
        - `receiver_address`
        - `sold_token_address`
        - `bought_token_address`
        - `raw_sold_amount`
        - `raw_bought_amount`

        Then create assets if `sold_token_address` and `bought_token_address` were found.
        Then match and label events.
        Then reshuffle events to make sure that spend and receive are consecutive.

        Note that `sold_token_address` and `bought_token_address` are not always found (e.g.
        when pool for some reason is not present in our cache). If tokens that were swapped are
        detected then we use them when iterating over `decoded_events` list and matching transfers.
        If they are not detected then conditions when matching transfer events are a bit broader.
        """

        # These are nullable because in case a curve pool is not stored in our cache or if it
        # is a swap in a metapool (TOKEN_EXCHANGE_UNDERLYING) we will skip token check.
        sold_token_address: ChecksumEvmAddress | None = None
        bought_token_address: ChecksumEvmAddress | None = None

        swapping_contract: ChecksumEvmAddress
        if context.tx_log.topics[0] in (TOKEN_EXCHANGE, TOKEN_EXCHANGE_UNDERLYING):
            pool_address = context.tx_log.address
            swapping_contract = pool_address
            # When a single pool is used, spender and receiver is always the same
            spender_address = receiver_address = hex_or_bytes_to_address(context.tx_log.topics[1])
            sold_token_id = hex_or_bytes_to_int(context.tx_log.data[:32])
            raw_sold_amount = hex_or_bytes_to_int(context.tx_log.data[32:64])
            bought_token_id = hex_or_bytes_to_int(context.tx_log.data[64:96])
            raw_bought_amount = hex_or_bytes_to_int(context.tx_log.data[96:128])
            if (
                context.tx_log.topics[0] == TOKEN_EXCHANGE and
                pool_address in self.pools and
                len(self.pools[pool_address]) > max(sold_token_id, bought_token_id)  # Make sure that tokens of the pool are cached  # noqa: E501
            ):
                sold_token_address = self.pools[pool_address][sold_token_id]
                bought_token_address = self.pools[pool_address][bought_token_id]
        else:  # EXCHANGE_MULTIPLE
            swapping_contract = self.curve_swap_router
            spender_address = hex_or_bytes_to_address(context.tx_log.topics[1])
            receiver_address = hex_or_bytes_to_address(context.tx_log.topics[2])
            raw_sold_amount = hex_or_bytes_to_int(context.tx_log.data[-64:-32])
            raw_bought_amount = hex_or_bytes_to_int(context.tx_log.data[-32:])
            # Curve swap router logs route (a list of addresses) that was used. Route consists of
            # 9 elements. Consider X a number of pools that was used. Then the structure can be
            # described in the following way:
            # At 0 index: Address of the sold token (token that goes in the router)
            # From 1 to X indices: Addresses of pools that were used
            # At X + 1 index: Address of the bought token (token that comes from the router)
            # From X + 2 to 8 indices: Unused elements (zero addresses)
            # Here we read only addresses of token in and token out.
            sold_token_address = hex_or_bytes_to_address(context.tx_log.data[:32])
            for i in range(1, 9):  # Starting from 1 because at 0 is `sold_token_address`
                address = hex_or_bytes_to_address(context.tx_log.data[32 * i:32 * (i + 1)])
                if address == ZERO_ADDRESS:
                    break
                bought_token_address = address

        sold_asset = self._read_curve_asset(sold_token_address, self.evm_inquirer.chain_id)
        bought_asset = self._read_curve_asset(bought_token_address, self.evm_inquirer.chain_id)
        spend_event: EvmEvent | None = None
        receive_event: EvmEvent | None = None
        for event in context.decoded_events:
            if event.address != swapping_contract:
                continue

            crypto_asset = event.asset.resolve_to_crypto_asset()
            if (
                event.location_label == spender_address and
                event.event_type == HistoryEventType.SPEND and
                event.balance.amount == asset_normalized_value(amount=raw_sold_amount, asset=crypto_asset) and  # noqa: E501
                (sold_asset is None or event.asset == sold_asset)
            ):
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.SPEND
                event.notes = f'Swap {event.balance.amount} {crypto_asset.symbol} in curve'
                event.counterparty = CPT_CURVE
                spend_event = event
            elif (
                event.location_label == receiver_address and
                event.event_type == HistoryEventType.RECEIVE and
                event.balance.amount == asset_normalized_value(amount=raw_bought_amount, asset=crypto_asset) and  # noqa: E501
                (bought_asset is None or event.asset == bought_asset)
            ):
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.RECEIVE
                event.notes = f'Receive {event.balance.amount} {crypto_asset.symbol} as the result of a swap in curve'  # noqa: E501
                event.counterparty = CPT_CURVE
                receive_event = event

        if spend_event is not None and receive_event is not None:
            # Just to make sure that spend and receive events are consecutive
            maybe_reshuffle_events(ordered_events=[spend_event, receive_event], events_list=context.decoded_events)  # noqa: E501
        else:
            log.debug(
                f'Did not find spend and receive events for a curve swap. '
                f'{context.transaction.tx_hash.hex()}. Probably some aggregator was used and '
                f'decoding needs to happen in the aggregator-specific decoder.',
            )

        return DEFAULT_DECODING_OUTPUT

    def _decode_pool_events(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] in REMOVE_LIQUIDITY_EVENTS:
            # it can either be the user or a deposit zap contract
            user_or_contract_address = hex_or_bytes_to_address(context.tx_log.topics[1])
            return self._decode_curve_remove_events(
                tx_log=context.tx_log,
                transaction=context.transaction,
                decoded_events=context.decoded_events,
                user_or_contract_address=user_or_contract_address,
            )
        if context.tx_log.topics[0] in ADD_LIQUIDITY_EVENTS:
            # it can either be the user or a deposit zap contract
            user_or_contract_address = hex_or_bytes_to_address(context.tx_log.topics[1])
            return self._decode_curve_deposit_events(
                transaction=context.transaction,
                tx_log=context.tx_log,
                decoded_events=context.decoded_events,
                user_or_contract_address=user_or_contract_address,
            )

        if context.tx_log.topics[0] in (
            TOKEN_EXCHANGE,
            TOKEN_EXCHANGE_UNDERLYING,
            EXCHANGE_MULTIPLE,
        ):
            return self._decode_curve_trades(context=context)

        return DEFAULT_DECODING_OUTPUT

    def _decode_curve_gauge_votes(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] != GAUGE_VOTE:
            return DEFAULT_DECODING_OUTPUT

        user_address = hex_or_bytes_to_address(context.tx_log.data[32:64])
        if not self.base.is_tracked(user_address):
            return DEFAULT_DECODING_OUTPUT

        user_note = ''
        if user_address != context.transaction.from_address:
            user_note = f' from {user_address}'
        gauge_address = hex_or_bytes_to_address(context.tx_log.data[64:96])
        vote_weight = hex_or_bytes_to_int(context.tx_log.data[96:128])
        if vote_weight == 0:
            verb = 'Reset vote'
            weight_note = ''
        else:
            verb = 'Vote'
            weight_note = f' with {vote_weight / 100}% voting power'
        event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.GOVERNANCE,
            asset=self.native_currency,
            balance=Balance(),
            location_label=context.transaction.from_address,
            notes=f'{verb}{user_note} for {gauge_address} curve gauge{weight_note}',
            address=gauge_address,
            counterparty=CPT_CURVE,
            product=EvmProduct.GAUGE,
        )
        return DecodingOutput(event=event, refresh_balances=False)

    def _decode_gauge_events(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] not in (GAUGE_DEPOSIT, GAUGE_WITHDRAW):
            return DEFAULT_DECODING_OUTPUT

        provider = hex_or_bytes_to_address(context.tx_log.topics[1])
        gauge_address = context.tx_log.address
        raw_amount = hex_or_bytes_to_int(context.tx_log.data)
        found_event_modifying_balances = False
        for event in context.decoded_events:
            crypto_asset = event.asset.resolve_to_crypto_asset()
            if (
                event.location_label == provider and
                event.address == gauge_address and
                event.balance.amount == asset_normalized_value(amount=raw_amount, asset=crypto_asset)  # noqa: E501
            ):
                event.counterparty = CPT_CURVE
                event.product = EvmProduct.GAUGE
                found_event_modifying_balances = True
                if context.tx_log.topics[0] == GAUGE_DEPOSIT:
                    event.event_type = HistoryEventType.DEPOSIT
                    event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                    event.notes = f'Deposit {event.balance.amount} {crypto_asset.symbol} into {gauge_address} curve gauge'  # noqa: E501
                else:  # Withdraw
                    event.event_type = HistoryEventType.WITHDRAWAL
                    event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                    event.notes = f'Withdraw {event.balance.amount} {crypto_asset.symbol} from {gauge_address} curve gauge'  # noqa: E501

        return DecodingOutput(refresh_balances=found_event_modifying_balances)

    def _handle_post_decoding(
            self,
            transaction: EvmTransaction,
            decoded_events: list['EvmEvent'],
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
    ) -> list['EvmEvent']:
        """This method handles post decoding for curve events made through the deposit contracts.

        This is required because certain events are not available when `AddLiquidity` or `RemoveLiquidity` occurs.
        An example of such is when liquidity is removed, the transfer event of the token removed comes after the
        `RemoveLiquidity` event.
        """  # noqa: E501
        for tx_log in all_logs:
            if (
                tx_log.topics[0] in ADD_LIQUIDITY_EVENTS and
                hex_or_bytes_to_address(tx_log.topics[1]) in self.curve_deposit_contracts
            ):
                self._handle_zap_contracts_liquidity_addition(
                    transaction=transaction,
                    decoded_events=decoded_events,
                )
                break  # We only need to handle zap contracts once
            if (
                tx_log.topics[0] in REMOVE_LIQUIDITY_EVENTS and
                hex_or_bytes_to_address(tx_log.topics[1]) in self.curve_deposit_contracts
            ):
                self._handle_zap_contracts_liquidity_removal(
                    pool_address=tx_log.address,
                    transaction=transaction,
                    decoded_events=decoded_events,
                )
                break  # We only need to handle zap contracts once

        return decoded_events  # noop. just return the decoded events.

    def _handle_zap_contracts_liquidity_addition(
            self,
            transaction: EvmTransaction,
            decoded_events: list['EvmEvent'],
    ) -> None:
        """
        This method completes the decoding of liquidity addition made through
        Curve zap contracts such as e.g. Curve Deposit USDN, etc.
        """
        receive_event_idx, deposit_events = None, []
        for idx, event in enumerate(decoded_events):
            if (
                event.event_type == HistoryEventType.DEPOSIT and
                event.event_subtype == HistoryEventSubType.DEPOSIT_ASSET and
                event.counterparty == CPT_CURVE
            ):
                deposit_events.append(event)

            # search for the event of the wrapped token received after deposit
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == transaction.from_address and
                (
                    event.address in self.curve_deposit_contracts or
                    event.address == ZERO_ADDRESS or
                    event.address in self.pools
                )
            ):
                receive_event_idx = idx
                crypto_asset = event.asset.resolve_to_crypto_asset()
                event.event_type = HistoryEventType.RECEIVE
                event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                event.counterparty = CPT_CURVE
                event.notes = f'Receive {event.balance.amount} {crypto_asset.symbol} after depositing in a curve pool'  # noqa: E501

        if receive_event_idx is not None and len(deposit_events) > 0:
            self._sort_events(
                action_type='addition',
                return_or_receive_event=decoded_events[receive_event_idx],
                withdrawal_or_deposit_events=deposit_events,
                all_events=decoded_events,
            )
            return

        log.warning(  # can happen as part of a complicated swap
            f'Expected to see a receive pool token event and deposit events for a curve pool, '
            f'but have not found them. Tx_hash: {transaction.tx_hash.hex()}',
        )

    def _handle_zap_contracts_liquidity_removal(
            self,
            pool_address: ChecksumEvmAddress,
            transaction: EvmTransaction,
            decoded_events: list['EvmEvent'],
    ) -> None:
        """
        This method completes the decoding of liquidity removal made through
        Curve zap contracts such as e.g. Curve Deposit USDN, etc.
        """
        return_event_idx, withdrawal_events = None, []
        for idx, event in enumerate(decoded_events):
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.RETURN_WRAPPED and
                event.counterparty == CPT_CURVE and
                event.extra_data is None
            ):
                return_event_idx = idx

            elif (  # find receive events from the deposit contract.
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == transaction.from_address and
                (
                    event.address in self.curve_deposit_contracts or
                    event.address in self.pools
                )
            ):
                crypto_asset = event.asset.resolve_to_crypto_asset()
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                event.counterparty = CPT_CURVE
                event.notes = f'Remove {event.balance.amount} {crypto_asset.symbol} from {pool_address} curve pool'  # noqa: E501
                withdrawal_events.append(event)

        if return_event_idx is not None and len(withdrawal_events) > 0:
            self._sort_events(
                action_type='removal',
                return_or_receive_event=decoded_events[return_event_idx],
                withdrawal_or_deposit_events=withdrawal_events,
                all_events=decoded_events,
            )
            return

        log.warning(  # can happen if it's part of a complicated swap
            f'Expected to see a return pool token event and withdrawal events '
            f'for a curve pool, but have not found them. '
            f'Tx_hash: {transaction.tx_hash.hex()}',
        )

    def _maybe_enrich_curve_transfers(self, context: EnricherContext) -> TransferEnrichmentOutput:
        """
        May raise:
        - UnknownAsset
        - WrongAssetType
        """
        source_address = hex_or_bytes_to_address(context.tx_log.topics[1])
        if (
            context.event.event_type == HistoryEventType.RECEIVE and
            context.event.event_subtype == HistoryEventSubType.NONE and
            source_address in self.gauges
        ):
            crypto_asset = context.event.asset.resolve_to_crypto_asset()
            context.event.event_subtype = HistoryEventSubType.REWARD
            context.event.notes = f'Receive {context.event.balance.amount} {crypto_asset.symbol} rewards from {source_address} curve gauge'  # noqa: E501
            context.event.counterparty = CPT_CURVE
            return TransferEnrichmentOutput(matched_counterparty=CPT_CURVE)
        return FAILED_ENRICHMENT_OUTPUT

    @staticmethod
    def _sort_events(
            action_type: Literal['addition', 'removal'],
            return_or_receive_event: 'EvmEvent',
            withdrawal_or_deposit_events: list['EvmEvent'],
            all_events: list['EvmEvent'],
    ) -> list['EvmEvent']:
        """
        This method sorts the events in the expected order and adds
        extra info to the in/out event depending on the action_type.
        """
        if action_type == 'addition':
            return_or_receive_event.extra_data = {
                'deposit_events_num': len(withdrawal_or_deposit_events),
            }
        else:  # can only be removal
            return_or_receive_event.extra_data = {
                'withdrawal_events_num': len(withdrawal_or_deposit_events),
            }
        maybe_reshuffle_events(
            ordered_events=[return_or_receive_event] + withdrawal_or_deposit_events,
            events_list=all_events,
        )
        return all_events

    # -- DecoderInterface methods

    @staticmethod
    def possible_products() -> dict[str, list[EvmProduct]]:
        return {CPT_CURVE: [EvmProduct.GAUGE]}

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        mapping: dict[ChecksumEvmAddress, tuple[Any, ...]] = dict.fromkeys(self.pools, (self._decode_pool_events,))  # noqa: E501
        mapping.update(dict.fromkeys(self.gauges, (self._decode_gauge_events,)))
        mapping[self.curve_swap_router] = (self._decode_pool_events,)
        mapping[self.gauge_controller] = (self._decode_curve_gauge_votes,)
        return mapping

    def post_decoding_rules(self) -> dict[str, list[tuple[int, Callable]]]:
        return {CPT_CURVE: [(0, self._handle_post_decoding)]}

    def enricher_rules(self) -> list[Callable]:
        return [self._maybe_enrich_curve_transfers]

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(identifier=CPT_CURVE, label='Curve.fi', image='curve.png'),)
