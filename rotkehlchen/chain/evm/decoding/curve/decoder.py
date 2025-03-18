import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.utils import TokenEncounterInfo
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.constants import ETH_SPECIAL_ADDRESS, ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.aave.constants import CPT_AAVE_V1, CPT_AAVE_V2, CPT_AAVE_V3
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.curve.constants import (
    ADD_LIQUIDITY_EVENTS,
    ADD_LIQUIDITY_IN_DEPOSIT_AND_STAKE,
    CPT_CURVE,
    CURVE_COUNTERPARTY_DETAILS,
    EXCHANGE_MULTIPLE,
    EXCHANGE_NG,
    GAUGE_DEPOSIT,
    GAUGE_WITHDRAW,
    REMOVE_LIQUIDITY_EVENTS,
    REMOVE_LIQUIDITY_IMBALANCE,
    TOKEN_EXCHANGE,
    TOKEN_EXCHANGE_NG,
    TOKEN_EXCHANGE_UNDERLYING,
)
from rotkehlchen.chain.evm.decoding.curve.curve_cache import (
    get_lp_and_gauge_token_addresses,
    query_curve_data,
    read_curve_pools_and_gauges,
)
from rotkehlchen.chain.evm.decoding.interfaces import (
    DecoderInterface,
    ReloadablePoolsAndGaugesDecoderMixin,
)
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    FAILED_ENRICHMENT_OUTPUT,
    ActionItem,
    DecoderContext,
    DecodingOutput,
    EnricherContext,
    TransferEnrichmentOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.errors.misc import NotERC20Conformant, NotERC721Conformant
from rotkehlchen.history.events.structures.evm_event import EvmProduct
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import CacheType, ChecksumEvmAddress, EvmTokenKind, EvmTransaction
from rotkehlchen.utils.misc import bytes_to_address

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
            curve_swap_routers: set['ChecksumEvmAddress'],
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
            read_data_from_cache_method=read_curve_pools_and_gauges,
            chain_id=evm_inquirer.chain_id,
        )
        self.aave_pools = aave_pools
        self.curve_deposit_contracts = curve_deposit_contracts
        self.curve_swap_routers = curve_swap_routers

    def _read_curve_asset(
            self: 'CurveCommonDecoder',
            asset_address: ChecksumEvmAddress | None,
            encounter: 'TokenEncounterInfo | None' = None,
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

        try:
            return self.base.get_or_create_evm_token(
                address=asset_address,
                encounter=encounter,
            )
        except (NotERC20Conformant, NotERC721Conformant) as e:
            log.error(f'Failed to read curve asset with address {asset_address} due to {e!s}')
            return None

    @property
    def pools(self) -> dict[ChecksumEvmAddress, list[ChecksumEvmAddress]]:
        assert isinstance(self.cache_data[0], dict), 'CurveDecoder cache_data[0] is not a dict'
        return self.cache_data[0]

    def _decode_curve_remove_events(
            self,
            transaction: EvmTransaction,
            tx_log: EvmTxReceiptLog,
            all_logs: list[EvmTxReceiptLog],
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
                event.event_subtype = HistoryEventSubType.REDEEM_WRAPPED
                event.counterparty = CPT_CURVE
                event.notes = f'Remove {event.amount} {crypto_asset.symbol} from the curve pool'
                withdrawal_events.append(event)
            elif (  # Withdraw send wrapped
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype in {HistoryEventSubType.NONE, HistoryEventSubType.RETURN_WRAPPED} and  # noqa: E501
                event.location_label == transaction.from_address and
                (
                    user_or_contract_address == event.location_label or
                    user_or_contract_address in self.curve_deposit_contracts or
                    tx_log.topics[0] in REMOVE_LIQUIDITY_IMBALANCE or
                    user_or_contract_address == bytes_to_address(tx_log.topics[1])
                )
            ):
                event.event_type = HistoryEventType.SPEND
                event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                event.counterparty = CPT_CURVE
                event.notes = f'Return {event.amount} {crypto_asset.symbol}'
                return_event = event
            elif (  # Withdraw receive asset
                tx_log.address in self.pools and
                event.location_label is not None and (
                    transaction.from_address == user_or_contract_address or
                    self.base.is_tracked(string_to_evm_address(event.location_label))
                )
            ):
                notes = f'Remove {event.amount} {crypto_asset.symbol} from {tx_log.address} curve pool'  # noqa: E501
                if (  # Raw event
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE
                ):
                    event.event_type = HistoryEventType.WITHDRAWAL
                    event.event_subtype = HistoryEventSubType.REDEEM_WRAPPED
                    event.counterparty = CPT_CURVE
                    event.notes = notes
                    withdrawal_events.append(event)
                elif (  # Is already decoded by aave
                    tx_log.address in self.aave_pools and
                    event.event_type == HistoryEventType.WITHDRAWAL and
                    event.event_subtype == HistoryEventSubType.REDEEM_WRAPPED and
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
                event.event_subtype == HistoryEventSubType.REDEEM_WRAPPED and
                event.counterparty == CPT_CURVE
            ):
                withdrawal_events.append(event)
            elif (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.RETURN_WRAPPED and
                event.counterparty == CPT_CURVE
            ):
                return_event = event

        if return_event is not None:  # find withdrawn assets through the logs
            withdrawn_assets = [event.asset for event in withdrawal_events] + [
                withdrawn_asset
                for _log in all_logs[all_logs.index(tx_log) + 1:] if (
                    (_log.topics[0] == ERC20_OR_ERC721_TRANSFER) and
                    (bytes_to_address(_log.topics[1]) == return_event.address) and
                    self.base.is_tracked(bytes_to_address(_log.topics[2])) and
                    (withdrawn_asset := self._read_curve_asset(
                        asset_address=_log.address,
                        encounter=TokenEncounterInfo(tx_hash=transaction.tx_hash),
                    )) is not None
                )
            ]

            # Make sure that the order is the following:
            # 1. Return pool token event
            # 2. Withdrawal 1
            # 3. Withdrawal 2
            # etc.
            if len(withdrawn_assets) > 0:
                # for deposit zap contracts, this is handled using an action item
                if (
                    user_or_contract_address in self.curve_deposit_contracts or
                    self.base.is_tracked(user_or_contract_address) is False
                ):
                    action_items = [ActionItem(
                        action='transform',
                        from_event_type=HistoryEventType.RECEIVE,
                        from_event_subtype=HistoryEventSubType.NONE,
                        asset=withdrawal_asset,
                        to_event_type=HistoryEventType.WITHDRAWAL,
                        to_event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
                        to_notes=f'Remove {{amount}} {{symbol}} from {tx_log.address} curve pool',  # amount and symbol set at actionitem process  # noqa: E501
                        to_counterparty=CPT_CURVE,
                    ) for withdrawal_asset in withdrawn_assets]
                    action_items[0].paired_events_data = ((return_event,), True)
                    return DecodingOutput(action_items=action_items)

                maybe_reshuffle_events(
                    ordered_events=[return_event] + withdrawal_events,
                    events_list=decoded_events,
                )

        else:
            log.error(
                f'Expected to see a return pool token event and '
                f'withdrawal events for a curve pool, but have not found them. '
                f'Tx_hash: {transaction.tx_hash.hex()} '
                f'User address: {user_or_contract_address}',
            )

        return DEFAULT_DECODING_OUTPUT

    def _decode_curve_deposit_events(
            self,
            transaction: EvmTransaction,
            tx_log: EvmTxReceiptLog,
            all_logs: list[EvmTxReceiptLog],
            decoded_events: list['EvmEvent'],
            user_or_contract_address: ChecksumEvmAddress,
    ) -> DecodingOutput:
        """Decode information related to depositing assets in curve pools"""
        deposit_events: list[EvmEvent] = []
        receive_event: EvmEvent | None = None
        received_asset: Asset | None = None
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
                event.event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
                event.counterparty = CPT_CURVE
                event.notes = f'Deposit {event.amount} {crypto_asset.symbol} in curve pool'
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
                event.notes = f'Receive {event.amount} {crypto_asset.symbol} after depositing in curve pool {tx_log.address}'  # noqa: E501
                receive_event = event
            elif (  # deposit give asset
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE
            ):
                if (
                    (
                        event.location_label == user_or_contract_address or
                        user_or_contract_address in self.curve_deposit_contracts
                    ) and
                    tx_log.address in self.pools
                ):
                    event.event_type = HistoryEventType.DEPOSIT
                    event.event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
                    event.counterparty = CPT_CURVE
                    event.notes = f'Deposit {event.amount} {crypto_asset.symbol} in curve pool {tx_log.address}'  # noqa: E501
                    deposit_events.append(event)
                else:
                    # when depositing in a gauge with deposit and stake
                    # we need to check if there is a transfer targeting the same contract address
                    # (should not be the user address) and if so save the address of the pool
                    # example: https://gnosisscan.io/tx/0xcbeaaee59405d5f7fd456dc510f1b841cc1329cd9624255ce64c894ac6643bd7  # noqa: E501
                    for _log in all_logs:
                        if (
                            _log.topics[0] == ERC20_OR_ERC721_TRANSFER and
                            bytes_to_address(_log.topics[1]) == ZERO_ADDRESS and
                            bytes_to_address(_log.topics[2]) == user_or_contract_address and
                            _log.log_index < tx_log.log_index
                        ):
                            event.extra_data = {'address_pool_tokens_received': _log.address}
                            break
            elif (
                event.event_type == HistoryEventType.DEPOSIT and
                event.event_subtype == HistoryEventSubType.DEPOSIT_FOR_WRAPPED and
                event.counterparty == CPT_CURVE
            ):
                deposit_events.append(event)
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.RECEIVE_WRAPPED and
                event.counterparty == CPT_CURVE
            ):
                receive_event = event
                received_asset = event.asset

        if received_asset is None:  # find lp_tokens through the logs
            lp_and_gauge_token_addresses = None
            for _log in all_logs:
                # first search for the pool address, because it may come after the receive event
                if _log.topics[0] in ADD_LIQUIDITY_EVENTS:
                    lp_and_gauge_token_addresses = get_lp_and_gauge_token_addresses(
                        pool_address=_log.address,
                        chain_id=self.evm_inquirer.chain_id,
                    )

            if lp_and_gauge_token_addresses is not None:
                deposit_addresses = {event.address for event in deposit_events} | {ZERO_ADDRESS}
                for _log in all_logs[all_logs.index(tx_log) + 1:]:
                    if (  # find the first log after deposit, where user receives the token from a deposit address  # noqa: E501
                        (_log.topics[0] == ERC20_OR_ERC721_TRANSFER) and
                        (bytes_to_address(_log.topics[1]) in deposit_addresses) and
                        self.base.is_tracked(bytes_to_address(_log.topics[2])) and
                        _log.address in lp_and_gauge_token_addresses and
                        (received_asset := self._read_curve_asset(
                            asset_address=_log.address,
                            encounter=TokenEncounterInfo(tx_hash=transaction.tx_hash),
                        )) is not None
                    ):
                        break

        # Make sure that the order is the following:
        # 1. Receive pool token event
        # 2. Deposit 1
        # 3. Deposit 2
        # etc.
        if (
            user_or_contract_address in self.curve_deposit_contracts and
            len(deposit_events) > 0 and
            received_asset is not None
        ):  # for deposit zap contracts, this is handled using an action item
            return DecodingOutput(
                action_items=[ActionItem(
                    action='transform',
                    from_event_type=HistoryEventType.RECEIVE,
                    from_event_subtype=HistoryEventSubType.NONE,
                    asset=received_asset,
                    to_event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
                    to_notes='Receive {amount} {symbol} after depositing in a curve pool',  # amount and symbol set at actionitem process  # noqa: E501
                    to_counterparty=CPT_CURVE,
                    paired_events_data=(deposit_events, True),
                )],
            )

        if receive_event is not None and len(deposit_events) > 0:
            maybe_reshuffle_events(
                ordered_events=deposit_events + [receive_event],
                events_list=decoded_events,
            )
        else:
            log.warning(  # can happen as part of complicated swaps
                f'Expected to see a receive pool token event and deposit '
                f'events for a curve pool, but have not found them. '
                f'Tx_hash: {transaction.tx_hash.hex()} '
                f'User address: {user_or_contract_address}',
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

        First iterate all logs to check if any pool is used separately before the router. If there
        is one then get the spender side of details from it. Then check if the current tx_log is
        from router, extract the rest of the details from it.

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
        # Spender/receiver and raw bought amount should be found below or else we error
        spender_address, receiver_address, raw_bought_amount = None, None, None

        swapping_contracts: set[ChecksumEvmAddress] = set()
        # we check if before using the router any pool is used separately, by checking all the logs
        for tx_log in context.all_logs[:context.all_logs.index(context.tx_log) + 1]:
            if tx_log.topics[0] in (TOKEN_EXCHANGE, TOKEN_EXCHANGE_UNDERLYING, TOKEN_EXCHANGE_NG):
                # if a pool is used then we extract the sold token address and amount here.
                pool_address = tx_log.address
                swapping_contracts = {pool_address}
                # When a single pool is used, spender and receiver is always the same
                spender_address = receiver_address = bytes_to_address(tx_log.topics[1])
                sold_token_id = int.from_bytes(tx_log.data[:32])
                raw_sold_amount = int.from_bytes(tx_log.data[32:64])
                bought_token_id = int.from_bytes(tx_log.data[64:96])
                raw_bought_amount = int.from_bytes(tx_log.data[96:128])
                if (
                    tx_log.topics[0] in {TOKEN_EXCHANGE, TOKEN_EXCHANGE_NG} and
                    pool_address in self.pools and
                    len(self.pools[pool_address]) > max(sold_token_id, bought_token_id)  # Make sure that tokens of the pool are cached  # noqa: E501
                ):
                    sold_token_address = self.pools[pool_address][sold_token_id]
                    bought_token_address = self.pools[pool_address][bought_token_id]
                break  # As soon as we find the info, we break out of the loop.

        else:  # only the router is used
            raw_sold_amount = None

        # if any curve router is used
        if context.tx_log.topics[0] in (EXCHANGE_MULTIPLE, EXCHANGE_NG):
            swapping_contracts = self.curve_swap_routers
            spender_address = bytes_to_address(context.tx_log.topics[1])
            receiver_address = bytes_to_address(context.tx_log.topics[2])
            if raw_sold_amount is None:  # if it's not already set in token exchange event
                raw_sold_amount = int.from_bytes(context.tx_log.data[-64:-32])

            raw_bought_amount = int.from_bytes(context.tx_log.data[-32:])
            # 11 if the router is new generation https://docs.curve.fi/router/CurveRouterNG/#route-and-swap-parameters  # noqa: E501
            route_length = 11 if context.tx_log.topics[0] == EXCHANGE_NG else 9

            # Curve swap router logs route (a list of addresses) that was used. Route consists of
            # 9 elements. Consider X a number of pools that was used. Then the structure can be
            # described in the following way:
            # At 0 index: Address of the sold token (token that goes in the router)
            # From 1 to X indices: Addresses of pools that were used
            # At X + 1 index: Address of the bought token (token that comes from the router)
            # From X + (2 to route_length-1) indices: Unused elements (zero addresses)
            # Here we read only addresses of token in and token out.
            if sold_token_address is None:
                sold_token_address = bytes_to_address(context.tx_log.data[:32])
            for i in range(1, route_length):  # Starting from 1 because at 0 is `sold_token_address`  # noqa: E501
                address = bytes_to_address(context.tx_log.data[32 * i:32 * (i + 1)])
                if address == ZERO_ADDRESS:
                    break
                bought_token_address = address

        if spender_address is None or receiver_address is None or raw_bought_amount is None:
            log.error(
                f'Did not find spend or receive addresses or raw bought amount for a curve swap. '
                f'{context.transaction.tx_hash.hex()}.',
            )
            return DEFAULT_DECODING_OUTPUT

        sold_asset = self._read_curve_asset(
            asset_address=sold_token_address,
            encounter=(encounter := TokenEncounterInfo(tx_hash=context.transaction.tx_hash)),
        )
        bought_asset = self._read_curve_asset(
            asset_address=bought_token_address,
            encounter=encounter,
        )
        spend_event: EvmEvent | None = None
        receive_event: EvmEvent | None = None
        for event in context.decoded_events:
            if event.address not in swapping_contracts:
                continue

            crypto_asset = event.asset.resolve_to_crypto_asset()
            if (
                event.location_label == spender_address and
                event.event_type == HistoryEventType.SPEND and
                raw_sold_amount is not None and
                event.amount == asset_normalized_value(amount=raw_sold_amount, asset=crypto_asset) and  # noqa: E501
                (sold_asset is None or event.asset in (self.native_currency, sold_asset))
            ):
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.SPEND
                event.notes = f'Swap {event.amount} {crypto_asset.symbol} in curve'
                event.counterparty = CPT_CURVE
                spend_event = event
                event.extra_data = None
            elif (
                event.location_label == receiver_address and
                event.event_type == HistoryEventType.RECEIVE and
                event.amount == asset_normalized_value(amount=raw_bought_amount, asset=crypto_asset) and  # noqa: E501
                (bought_asset is None or event.asset in (self.native_currency, bought_asset))
            ):
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.RECEIVE
                event.notes = f'Receive {event.amount} {crypto_asset.symbol} as the result of a swap in curve'  # noqa: E501
                event.counterparty = CPT_CURVE
                receive_event = event
                event.extra_data = None

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

    def _decode_deposit_and_stake(self, context: DecoderContext) -> DecodingOutput:
        """
        Enrich the transfer for deposit and stake to save the amount of gauge tokens
        received. We need to match against transfers manually because they are not
        made from the user address but an intermediate contract
        """
        if (pool_addresses := self.pools.get(context.tx_log.address)) is None:
            log.error(
                f'Curve pool for {self.evm_inquirer.chain_name} {context.tx_log.address} '
                f'not present in cache at {context.transaction.tx_hash.hex()}. Skipping',
            )
            return DEFAULT_DECODING_OUTPUT

        provider = bytes_to_address(context.tx_log.topics[1])
        deposited_amounts = [
            deposited_amount
            for deposit_amount in [context.tx_log.data[i:i + 32] for i in range(len(pool_addresses))]  # noqa: E501
            if (deposited_amount := int.from_bytes(deposit_amount)) != 0
        ]
        pool_assets = [
            Asset(evm_address_to_identifier(
                address=address,
                chain_id=self.evm_inquirer.chain_id,
                token_type=EvmTokenKind.ERC20,
            )) if address != ETH_SPECIAL_ADDRESS else A_ETH for address in pool_addresses
        ]

        gauge_tokens = None
        for event in context.decoded_events:
            if event.asset not in pool_assets:
                continue

            # The context.tx_log is a deposit event from curve. We deposit an underlying token
            # of the pool (for example EURE) and we get an amount of the pool token. The problem
            # is that the event log doesn't contain the amount of the LP received and it is needed
            # later when decoding the gauge events since the amounts that we compare with are
            # different. The next for loop iterates over the logs to find the transfer that follows
            # the current log entry and extract from there the amount of LP tokens obtained after
            # the deposit.
            for tx_log in context.all_logs:
                if (
                    tx_log.log_index > context.tx_log.log_index and
                    tx_log.topics[0] == ERC20_OR_ERC721_TRANSFER and
                    bytes_to_address(tx_log.topics[1]) == provider
                ):
                    gauge_tokens = int.from_bytes(tx_log.data[0:32])
                    break
            else:
                log.error(f'Could not find transfer of gauge tokens in {context.transaction}. Skipping...')  # noqa: E501
                continue

            # add the amount of gauge_tokens obtained, to the event's extra_data
            for deposit_amount in deposited_amounts:
                if event.amount == asset_normalized_value(
                    amount=deposit_amount,
                    asset=event.asset.resolve_to_crypto_asset(),
                ):
                    event.event_type = HistoryEventType.DEPOSIT
                    event.event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
                    event.counterparty = CPT_CURVE
                    event.extra_data = {'gauge_tokens': gauge_tokens}
                    break
            else:
                log.error(f'Could not find event depositing any of {deposited_amounts} in {context.transaction}. Continuing')  # noqa: E501

        return DEFAULT_DECODING_OUTPUT

    def _decode_pool_events(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] in REMOVE_LIQUIDITY_EVENTS:
            # it can either be the user or a deposit zap contract
            user_or_contract_address = bytes_to_address(context.tx_log.topics[1])
            return self._decode_curve_remove_events(
                tx_log=context.tx_log,
                all_logs=context.all_logs,
                transaction=context.transaction,
                decoded_events=context.decoded_events,
                user_or_contract_address=user_or_contract_address,
            )
        if context.tx_log.topics[0] in ADD_LIQUIDITY_EVENTS:
            # it can either be the user or a deposit zap contract
            user_or_contract_address = bytes_to_address(context.tx_log.topics[1])
            return self._decode_curve_deposit_events(
                transaction=context.transaction,
                tx_log=context.tx_log,
                all_logs=context.all_logs,
                decoded_events=context.decoded_events,
                user_or_contract_address=user_or_contract_address,
            )
        if context.tx_log.topics[0] == ADD_LIQUIDITY_IN_DEPOSIT_AND_STAKE:
            return self._decode_deposit_and_stake(context=context)

        if context.tx_log.topics[0] in (
            TOKEN_EXCHANGE,
            TOKEN_EXCHANGE_UNDERLYING,
            TOKEN_EXCHANGE_NG,
            EXCHANGE_MULTIPLE,
            EXCHANGE_NG,
        ):
            return self._decode_curve_trades(context=context)

        return DEFAULT_DECODING_OUTPUT

    def _decode_gauge_events(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] not in (GAUGE_DEPOSIT, GAUGE_WITHDRAW):
            return DEFAULT_DECODING_OUTPUT

        provider = bytes_to_address(context.tx_log.topics[1])
        gauge_address = context.tx_log.address
        raw_amount = int.from_bytes(context.tx_log.data)
        found_event_modifying_balances = False
        gauge_events = []
        # get pool tokens for this gauge
        lp_and_gauge_token_addresses = get_lp_and_gauge_token_addresses(
            pool_address=context.tx_log.address,
            chain_id=self.evm_inquirer.chain_id,
        )
        pool_tokens = []
        for address in lp_and_gauge_token_addresses:
            pool_tokens += self.pools.get(address, [])

        # if gauge token is None, that means the gauge is an old one, without any token
        if (gauge_token := self._read_curve_asset(
            asset_address=gauge_address,
            encounter=TokenEncounterInfo(tx_hash=context.transaction.tx_hash),
        )) is not None:
            try:
                gauge_token = gauge_token.resolve_to_evm_token()
            except (WrongAssetType, UnknownAsset):
                gauge_token = None

        for event in context.decoded_events:
            if (  # first check against common conditions for gauge deposits
                event.location_label == provider and
                (event.address == gauge_address or event.address in self.curve_deposit_contracts) and  # noqa: E501
                event.asset.is_evm_token() and
                (
                    (  # case of staking using deposit_and_stake
                        event.extra_data is not None and
                        (
                            (
                                (gauge_amount := event.extra_data.get('gauge_tokens')) is not None and  # user sends tokens of the pool # noqa: E501
                                gauge_amount == raw_amount
                            ) or (
                                (pool_token_address := event.extra_data.get('address_pool_tokens_received')) is not None and  # case of underlying pools like 3crv in eure-3crv. The user sends USDC but the gauge received 3crv # noqa: E501
                                pool_token_address in pool_tokens
                            )
                        )
                    ) or
                    event.amount == asset_normalized_value(  # direct deposit in the gauge
                        amount=raw_amount,
                        asset=(evm_asset := event.asset.resolve_to_evm_token()),
                    )
                )
            ):
                evm_asset = event.asset.resolve_to_evm_token()
                event.counterparty = CPT_CURVE
                event.product = EvmProduct.GAUGE
                found_event_modifying_balances = True
                gauge_events.append(event)
                if context.tx_log.topics[0] == GAUGE_DEPOSIT:
                    event.event_type = HistoryEventType.DEPOSIT
                    event.event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED if gauge_token is not None else HistoryEventSubType.DEPOSIT_ASSET  # noqa: E501
                    event.notes = f'Deposit {event.amount} {evm_asset.symbol} into {gauge_address} curve gauge'  # noqa: E501
                    from_event_type = HistoryEventType.RECEIVE
                    pair_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                    event.extra_data = None
                    pair_note = 'Receive {{amount}} {symbol} after depositing in {address} curve gauge'  # noqa: E501
                else:  # Withdraw
                    event.event_type = HistoryEventType.WITHDRAWAL
                    event.event_subtype = HistoryEventSubType.REDEEM_WRAPPED if gauge_token is not None else HistoryEventSubType.REMOVE_ASSET  # noqa: E501
                    event.notes = f'Withdraw {event.amount} {evm_asset.symbol} from {gauge_address} curve gauge'  # noqa: E501
                    from_event_type = HistoryEventType.SPEND
                    pair_subtype = HistoryEventSubType.RETURN_WRAPPED
                    event.extra_data = None
                    pair_note = 'Return {{amount}} {symbol} after withdrawing from {address} curve gauge'  # noqa: E501

        # `pair_note` is formatted twice, first below with `symbol` and `address`. `amount` is left
        # due to double {}. Then later in the action item `amount` is replaced by its value.
        action_items = [] if gauge_token is None or len(gauge_events) == 0 else [ActionItem(
            action='transform',
            from_event_type=from_event_type,  # pyright: ignore  # the above if check makes sure this exists
            from_event_subtype=HistoryEventSubType.NONE,
            asset=gauge_token,
            to_event_subtype=pair_subtype,  # pyright: ignore  # the above if check makes sure this exists
            to_notes=pair_note.format(  # pyright: ignore  # the above if check makes sure pair_node exists
                symbol=gauge_token.symbol,
                address=gauge_address,
            ),  # amount set at action item process
            to_counterparty=CPT_CURVE,
            paired_events_data=(gauge_events, from_event_type == HistoryEventType.RECEIVE),  # pyright: ignore  # the above if check makes sure from_event_type exists
        )]

        return DecodingOutput(
            refresh_balances=found_event_modifying_balances,
            matched_counterparty=CPT_CURVE,
            action_items=action_items,
        )

    def _maybe_enrich_curve_transfers(self, context: EnricherContext) -> TransferEnrichmentOutput:
        """
        May raise:
        - UnknownAsset
        - WrongAssetType
        """
        source_address = bytes_to_address(context.tx_log.topics[1])
        if (
            context.event.event_type == HistoryEventType.RECEIVE and
            context.event.event_subtype == HistoryEventSubType.NONE and
            source_address in self.gauges
        ):
            crypto_asset = context.event.asset.resolve_to_crypto_asset()
            context.event.event_subtype = HistoryEventSubType.REWARD
            context.event.notes = f'Receive {context.event.amount} {crypto_asset.symbol} rewards from {source_address} curve gauge'  # noqa: E501
            context.event.counterparty = CPT_CURVE
            return TransferEnrichmentOutput(matched_counterparty=CPT_CURVE)
        return FAILED_ENRICHMENT_OUTPUT

    # -- DecoderInterface methods

    @staticmethod
    def possible_products() -> dict[str, list[EvmProduct]]:
        return {CPT_CURVE: [EvmProduct.GAUGE]}

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return dict.fromkeys(self.curve_swap_routers, (self._decode_pool_events,))

    def enricher_rules(self) -> list[Callable]:
        return [self._maybe_enrich_curve_transfers]

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CURVE_COUNTERPARTY_DETAILS,)
