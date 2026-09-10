import logging
from typing import TYPE_CHECKING, Any, Final, Literal

from rotkehlchen.assets.utils import (
    asset_normalized_value,
    get_or_create_evm_token,
    token_normalized_value_decimals,
)
from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.constants import (
    BURN_TOPIC,
    DEFAULT_TOKEN_DECIMALS,
    MINT_TOPIC,
    WITHDRAW_TOPIC_V2,
    ZERO_ADDRESS,
)
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.decoding.interfaces import (
    EvmDecoderInterface,
    ReloadablePoolsAndGaugesDecoderMixin,
)
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.decoding.uniswap.utils import (
    decode_uniswap_v3_like_position_create_or_exit,
)
from rotkehlchen.chain.evm.decoding.uniswap.v2.constants import (
    UNISWAP_V2_SWAP_SIGNATURE as SWAP_V1,
)
from rotkehlchen.chain.evm.decoding.uniswap.v3.constants import (
    COLLECT_LIQUIDITY_SIGNATURE,
    INCREASE_LIQUIDITY_SIGNATURE,
    SWAP_SIGNATURE as SWAP_CL,
)
from rotkehlchen.chain.evm.decoding.uniswap.v3.utils import (
    decode_uniswap_v3_like_deposit_or_withdrawal,
)
from rotkehlchen.chain.evm.decoding.velodrome.constants import (
    CL_GAUGE_DEPOSIT,
    CL_GAUGE_WITHDRAW,
    CL_POOL_BURN,
    CL_POOL_COLLECT,
    CL_POOL_COLLECT_FEES,
    CL_POOL_FLASH,
    CL_POOL_MINT,
    CLAIM_REWARDS_V2,
    DROME_ROTKI_ABI,
    GAUGE_DEPOSIT_V2,
    REMOVE_LIQUIDITY_EVENT_V2,
    SWAP_V2,
    VOTER_CLAIM_REWARDS,
    VOTER_VOTED,
    VOTING_ESCROW_CREATE_LOCK,
    VOTING_ESCROW_METADATA_UPDATE,
    VOTING_ESCROW_WITHDRAW,
)
from rotkehlchen.chain.evm.decoding.velodrome.velodrome_cache import (
    query_velodrome_like_data,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.errors.misc import NotERC20Conformant, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.globaldb.cache import globaldb_get_general_cache_values
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address, deserialize_timestamp
from rotkehlchen.types import CacheType, ChecksumEvmAddress, GeneralCacheType, TokenKind
from rotkehlchen.utils.misc import bytes_to_address, timestamp_to_date

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.chain.optimism.manager import OptimismInquirer
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.types import EvmTransaction
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# Log signatures emitted by concentrated liquidity (Slipstream) pools
CL_POOL_TOPICS: Final = frozenset({
    SWAP_CL,
    CL_POOL_MINT,
    CL_POOL_BURN,
    CL_POOL_COLLECT,
    CL_POOL_FLASH,
    CL_POOL_COLLECT_FEES,
})


class VelodromeLikeDecoder(EvmDecoderInterface, ReloadablePoolsAndGaugesDecoderMixin):
    """A decoder class for velodrome-like related events."""

    def __init__(
            self,
            evm_inquirer: OptimismInquirer | BaseInquirer,
            base_tools: BaseEvmDecoderTools,
            msg_aggregator: MessagesAggregator,
            counterparty: Literal['velodrome', 'aerodrome'],
            voting_escrow_address: ChecksumEvmAddress,
            voter_address: ChecksumEvmAddress,
            routers: set[ChecksumEvmAddress],
            slipstream_nfpm: ChecksumEvmAddress,
            drome_rotki_address: ChecksumEvmAddress,
            token_symbol: Literal['AERO', 'VELO'],
            gauge_bribes_cache_type: GeneralCacheType,
            gauge_fees_cache_type: GeneralCacheType,
            pool_cache_type: CacheType,
            read_fn: Callable[[], tuple[set[ChecksumEvmAddress], set[ChecksumEvmAddress]]],
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        ReloadablePoolsAndGaugesDecoderMixin.__init__(
            self,
            evm_inquirer=evm_inquirer,
            cache_type_to_check_for_freshness=pool_cache_type,
            query_data_method=query_velodrome_like_data,
            read_data_from_cache_method=read_fn,
        )
        self.counterparty = counterparty
        self.routers = routers
        self.slipstream_nfpm = slipstream_nfpm
        self.cl_pool_tokens: dict[ChecksumEvmAddress, tuple[ChecksumEvmAddress, ChecksumEvmAddress]] = {}  # noqa: E501
        self.protocol_addresses = routers.copy()  # protocol_addresses are updated with pools in post_cache_update_callback  # noqa: E501
        self.voting_escrow_address = voting_escrow_address
        self.gauge_bribes_cache_type = gauge_bribes_cache_type
        self.gauge_fees_cache_type = gauge_fees_cache_type
        self.voter_address = voter_address
        self.drome_rotki_address = drome_rotki_address
        self.token_symbol = token_symbol

    @property
    def pools(self) -> set[ChecksumEvmAddress]:
        if (pools := self.cached_container(0)) is None:
            return set()  # no pools known until the cache is loaded

        assert isinstance(pools, set), f'{self.counterparty} Decoder cache_data[0] is not a set'
        return pools

    def post_cache_update_callback(self) -> None:
        self.protocol_addresses.update(self.pools)

    def _decode_add_liquidity_events(
            self,
            tx_log: EvmTxReceiptLog,
            decoded_events: list[EvmEvent],
    ) -> EvmDecodingOutput:
        """
        Decodes events that add liquidity to a (velo/aero)drome v1 or v2 pool.

        With addLiquidityETH the native asset goes to the router, which wraps it and forwards
        the wrapped token to the pool, refunding any unused native asset. So the native spend
        to the router is the pool deposit, minus any refund received from the router.

        It can raise
        - UnknownAsset if the asset identifier is not known
        - WrongAssetType if the asset is not of the correct type
        """
        out_events, in_events = [], []
        native_deposit, native_refund = None, None
        for event in decoded_events:
            crypto_asset = event.asset.resolve_to_crypto_asset()
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.address in self.pools
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
                event.counterparty = self.counterparty
                event.notes = f'Deposit {event.amount} {crypto_asset.symbol} in {self.counterparty} pool {event.address}'  # noqa: E501
                out_events.append(event)
            elif (
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == self.node_inquirer.native_token and
                event.address in self.routers
            ):
                if event.event_type == HistoryEventType.SPEND and native_deposit is None:
                    native_deposit = event
                elif event.event_type == HistoryEventType.RECEIVE and native_refund is None:
                    native_refund = event
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.address == ZERO_ADDRESS
            ):
                event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                event.counterparty = self.counterparty
                event.notes = f'Receive {event.amount} {crypto_asset.symbol} after depositing in {self.counterparty} pool {tx_log.address}'  # noqa: E501
                in_events.append(event)
                GlobalDBHandler.set_tokens_protocol_if_missing(
                    tokens=[event.asset.resolve_to_evm_token()],
                    new_protocol=self.counterparty,
                )

        if native_deposit is not None:
            if native_refund is not None:
                native_deposit.amount -= native_refund.amount
                decoded_events.remove(native_refund)

            native_deposit.event_type = HistoryEventType.DEPOSIT
            native_deposit.event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
            native_deposit.counterparty = self.counterparty
            native_deposit.address = tx_log.address
            native_deposit.notes = f'Deposit {native_deposit.amount} {self.node_inquirer.native_token.symbol} in {self.counterparty} pool {tx_log.address}'  # noqa: E501
            out_events.append(native_deposit)

        maybe_reshuffle_events(
            ordered_events=[*out_events, *in_events],
            events_list=decoded_events,
        )
        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_remove_liquidity_events(
            self,
            tx_log: EvmTxReceiptLog,
            decoded_events: list[EvmEvent],
    ) -> EvmDecodingOutput:
        """Decodes events that remove liquidity from a (velo/aero)drome v1 or v2 pool.

        With removeLiquidityETH the pool sends the wrapped token to the router, which unwraps
        it and sends the native asset to the user, so the native receive from the router is
        part of the withdrawal.
        """
        out_events, in_events = [], []
        for event in decoded_events:
            crypto_asset = event.asset.resolve_to_crypto_asset()
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.address in self.pools
            ):
                event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                event.counterparty = self.counterparty
                event.notes = f'Return {event.amount} {crypto_asset.symbol}'
                out_events.append(event)
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                (
                    event.address in self.pools or
                    (event.address in self.routers and event.asset == self.node_inquirer.native_token)  # noqa: E501
                )
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REDEEM_WRAPPED
                event.counterparty = self.counterparty
                event.address = tx_log.address
                event.notes = f'Remove {event.amount} {crypto_asset.symbol} from {self.counterparty} pool {tx_log.address}'  # noqa: E501
                in_events.append(event)

        maybe_reshuffle_events(
            ordered_events=[*out_events, *in_events],
            events_list=decoded_events,
        )
        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_swap(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decodes events that swap eth or tokens in a (velo/aero)drome v1 or v2 pool"""
        spend_event, receive_event = None, None
        for event in context.decoded_events:
            if (
                    ((event.event_type == HistoryEventType.SPEND and event.event_subtype == HistoryEventSubType.NONE) or  # noqa: E501
                    (event.event_type == HistoryEventType.TRADE and event.event_subtype == HistoryEventSubType.SPEND))  # noqa: E501
                    and event.address in self.protocol_addresses
            ):
                spend_event = event
            elif ((
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE
            ) or (
                event.event_type == HistoryEventType.TRADE and
                event.event_subtype == HistoryEventSubType.RECEIVE
            )) and event.address in self.protocol_addresses:
                receive_event = event

        if spend_event is None or receive_event is None:
            log.error(
                f'A swap in {self.counterparty} pool must have both a spend and a receive event '
                'but one or both of them are missing for transaction hash: '
                f'{context.transaction.tx_hash!s}. '
                f'Spend event: {spend_event}, receive event: {receive_event}.',
            )
            return DEFAULT_EVM_DECODING_OUTPUT

        for event, subtype in ((spend_event, HistoryEventSubType.SPEND), (receive_event, HistoryEventSubType.RECEIVE)):  # noqa: E501
            crypto_asset = event.asset.resolve_to_crypto_asset()
            event.event_type = HistoryEventType.TRADE
            event.event_subtype = subtype
            event.counterparty = self.counterparty
            if subtype == HistoryEventSubType.SPEND:
                event.notes = f'Swap {event.amount} {crypto_asset.symbol} in {self.counterparty}'
            else:
                event.notes = f'Receive {event.amount} {crypto_asset.symbol} as the result of a swap in {self.counterparty}'  # noqa: E501

        maybe_reshuffle_events(
            ordered_events=[spend_event, receive_event],
            events_list=context.decoded_events,
        )
        return EvmDecodingOutput(process_swaps=True)

    def _ensure_pool_tokens_exist(self, pool_address: ChecksumEvmAddress) -> None:
        """Ensure the pool token and its token0 and token1 exist in the DB.
        Queries pool info from our custom DROME_ROTKI_CONTRACT.

        Note: As of 2026/01 the LpSugar source code on Github appears to have a byAddress method
        that we should use instead of this custom contract, but the current deployment is missing
        this method. It would be advisable to switch to using that instead of the custom contract
        if it becomes available in a future deployment of the LpSugar contract. For the latest
        deployment addresses see https://github.com/velodrome-finance/sugar/tree/main/deployments
        """
        if pool_address in self.cl_pool_tokens or (
            (pool_token := self.base.get_evm_token(address=pool_address)) is not None and
            pool_token.protocol == self.counterparty
        ):
            return  # CL pool already seen or pool token already exists

        try:
            pool_info = EvmContract(
                address=self.drome_rotki_address,
                abi=DROME_ROTKI_ABI,
            ).call(
                node_inquirer=self.node_inquirer,
                method_name='get_pool_info',
                arguments=[pool_address],
            )
        except RemoteError as e:
            log.error(
                f'Failed to get info for {self.counterparty} '
                f'pool {pool_address} due to {e!s}',
            )
            return

        symbol, decimals, token0, token1, tick_spacing = pool_info
        try:
            token0, token1 = (
                self.base.get_or_create_evm_token(address=addr)
                for addr in (deserialize_evm_address(token0), deserialize_evm_address(token1))
            )
        except (DeserializationError, NotERC20Conformant) as e:
            log.error(
                f'Failed to create token0 and token1 for {self.counterparty} '
                f'pool {pool_address} due to {e!s}',
            )
            return

        if tick_spacing > 0:  # CL pool. Positions are NFTs so there is no ERC20 pool token
            self.cl_pool_tokens[pool_address] = (token0.evm_address, token1.evm_address)
            return

        fallback_symbol = f'{token0.symbol}/{token1.symbol}' if symbol == '' else symbol
        get_or_create_evm_token(  # this will not raise NotERC20Conformant because we give fallback info  # noqa: E501
            userdb=self.base.database,
            evm_address=pool_address,
            chain_id=self.node_inquirer.chain_id,
            evm_inquirer=self.node_inquirer,
            protocol=self.counterparty,  # mark with protocol which triggers the inquirer to use find_lp_price_from_uniswaplike_pool to query the price  # noqa: E501
            fallback_decimals=decimals or DEFAULT_TOKEN_DECIMALS,
            fallback_name=f'{fallback_symbol} Pool',
            fallback_symbol=fallback_symbol,
        )

    def _decode_pool_events(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decodes transactions that interact with a (velo/aero)drome v1, v2 or
        concentrated liquidity (Slipstream) pool.

        Slipstream pools emit the Uniswap V3 log signatures. Their liquidity changes are
        decoded from the position manager logs instead, so only their swaps are handled here.
        They are also not ERC20 tokens, so the pool token creation is skipped for them.
        """
        if context.tx_log.topics[0] in CL_POOL_TOPICS:
            if context.tx_log.topics[0] == SWAP_CL:
                return self._decode_swap(context=context)
            return DEFAULT_EVM_DECODING_OUTPUT

        self._ensure_pool_tokens_exist(context.tx_log.address)
        if context.tx_log.topics[0] in (REMOVE_LIQUIDITY_EVENT_V2, BURN_TOPIC):
            return self._decode_remove_liquidity_events(
                tx_log=context.tx_log,
                decoded_events=context.decoded_events,
            )
        if context.tx_log.topics[0] == MINT_TOPIC:
            return self._decode_add_liquidity_events(
                tx_log=context.tx_log,
                decoded_events=context.decoded_events,
            )
        if context.tx_log.topics[0] in (SWAP_V2, SWAP_V1):
            return self._decode_swap(context=context)

        return DEFAULT_EVM_DECODING_OUTPUT

    def _get_cl_pool_tokens(
            self,
            pool_address: ChecksumEvmAddress,
    ) -> tuple[ChecksumEvmAddress, ChecksumEvmAddress] | None:
        """Get the token0 and token1 of a concentrated liquidity pool, caching the result.

        Queries the pool directly. The drome rotki helper contract is not used since its
        get_pool_info needs more gas than indexer eth_call proxies allow, so it only works
        through an RPC node. Returns None if the pool could not be queried.
        """
        if (tokens := self.cl_pool_tokens.get(pool_address)) is not None:
            return tokens

        pool_contract = EvmContract(
            address=pool_address,
            abi=self.node_inquirer.contracts.abi('UNISWAP_V3_POOL'),
        )
        try:
            result = self.node_inquirer.multicall(calls=[
                (pool_address, pool_contract.encode(method_name='token0')),
                (pool_address, pool_contract.encode(method_name='token1')),
            ])
            tokens = (
                deserialize_evm_address(pool_contract.decode(result[0], 'token0')[0]),
                deserialize_evm_address(pool_contract.decode(result[1], 'token1')[0]),
            )
        except (RemoteError, DeserializationError) as e:
            log.error(
                'Failed to query the tokens of a concentrated liquidity pool',
                counterparty=self.counterparty,
                pool=pool_address,
                error=str(e),
            )
            return None

        self.cl_pool_tokens[pool_address] = tokens
        return tokens

    def _decode_slipstream_position_events(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decodes liquidity additions and removals of Slipstream (concentrated liquidity)
        positions via the NonfungiblePositionManager, which works like Uniswap V3's.

        The pool of the position is taken from the pool Mint/Collect log that precedes the
        position manager log and carries the same amounts. This avoids querying positions()
        on the position manager, which reverts once a position has been burned.
        """
        if context.tx_log.topics[0] == INCREASE_LIQUIDITY_SIGNATURE:
            is_deposit, pool_topic = True, CL_POOL_MINT
        elif context.tx_log.topics[0] == COLLECT_LIQUIDITY_SIGNATURE:
            is_deposit, pool_topic = False, CL_POOL_COLLECT
        else:
            return DEFAULT_EVM_DECODING_OUTPUT

        amount0_raw = int.from_bytes(context.tx_log.data[32:64])
        amount1_raw = int.from_bytes(context.tx_log.data[64:96])
        if amount0_raw == 0 and amount1_raw == 0:
            return DEFAULT_EVM_DECODING_OUTPUT  # nothing moved, e.g. a collect on gauge withdrawal

        for tx_log in reversed(context.all_logs):
            if (
                tx_log.log_index < context.tx_log.log_index and
                tx_log.topics[0] == pool_topic and
                int.from_bytes(tx_log.data[-64:-32]) == amount0_raw and
                int.from_bytes(tx_log.data[-32:]) == amount1_raw
            ):
                pool_address = tx_log.address
                break
        else:
            log.error(
                'Could not find the pool log of a Slipstream position',
                counterparty=self.counterparty,
                position_id=int.from_bytes(context.tx_log.topics[1]),
                tx_hash=context.transaction.tx_hash,
            )
            return DEFAULT_EVM_DECODING_OUTPUT

        if (tokens := self._get_cl_pool_tokens(pool_address)) is None:
            return DEFAULT_EVM_DECODING_OUTPUT

        return decode_uniswap_v3_like_deposit_or_withdrawal(
            context=context,
            is_deposit=is_deposit,
            counterparty=self.counterparty,
            token0_raw_address=tokens[0],
            token1_raw_address=tokens[1],
            amount0_raw=amount0_raw,
            amount1_raw=amount1_raw,
            position_id=int.from_bytes(context.tx_log.topics[1]),
            evm_inquirer=self.node_inquirer,
            display_name=self.slipstream_display_name,
        )

    def _slipstream_position_post_decoding(
            self,
            transaction: EvmTransaction,  # pylint: disable=unused-argument
            decoded_events: list[EvmEvent],
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
    ) -> list[EvmEvent]:
        return decode_uniswap_v3_like_position_create_or_exit(
            decoded_events=decoded_events,
            evm_inquirer=self.node_inquirer,
            nft_manager=self.slipstream_nfpm,
            counterparty=self.counterparty,
            token_symbol=f'{self.token_symbol}-CL-POS',
            token_name=f'{self.slipstream_display_name} Positions',
            display_name=self.slipstream_display_name,
        )

    @property
    def slipstream_display_name(self) -> str:
        return f'{self.counterparty.capitalize()} Slipstream'

    def _decode_gauge_events(self, context: DecoderContext) -> EvmDecodingOutput:
        """
        Decodes transactions that interact with a (velo/aero)drome v2 or concentrated
        liquidity (Slipstream) gauge. Velodrome v1 had no gauges.
        """
        if context.tx_log.topics[0] in (CL_GAUGE_DEPOSIT, CL_GAUGE_WITHDRAW):
            return self._decode_cl_gauge_events(context=context)

        if context.tx_log.topics[0] not in (GAUGE_DEPOSIT_V2, WITHDRAW_TOPIC_V2, CLAIM_REWARDS_V2):
            return DEFAULT_EVM_DECODING_OUTPUT

        user_or_contract_address = bytes_to_address(context.tx_log.topics[1])
        gauge_address = context.tx_log.address
        raw_amount = int.from_bytes(context.tx_log.data)
        found_event_modifying_balances = False
        for event in context.decoded_events:
            crypto_asset = event.asset.resolve_to_crypto_asset()
            if (
                event.location_label == user_or_contract_address and
                event.address == gauge_address and
                event.amount == asset_normalized_value(amount=raw_amount, asset=crypto_asset)
            ):
                event.counterparty = self.counterparty
                found_event_modifying_balances = True
                if context.tx_log.topics[0] == GAUGE_DEPOSIT_V2:
                    event.event_type = HistoryEventType.DEPOSIT
                    event.event_subtype = HistoryEventSubType.DEPOSIT_TO_PROTOCOL
                    event.notes = f'Deposit {event.amount} {crypto_asset.symbol} into {gauge_address} {self.counterparty} gauge'  # noqa: E501
                    GlobalDBHandler.set_tokens_protocol_if_missing(
                        tokens=[event.asset.resolve_to_evm_token()],
                        new_protocol=self.counterparty,
                    )
                elif context.tx_log.topics[0] == WITHDRAW_TOPIC_V2:
                    event.event_type = HistoryEventType.WITHDRAWAL
                    event.event_subtype = HistoryEventSubType.WITHDRAW_FROM_PROTOCOL
                    event.notes = f'Withdraw {event.amount} {crypto_asset.symbol} from {gauge_address} {self.counterparty} gauge'  # noqa: E501
                else:  # CLAIM_REWARDS
                    event.event_type = HistoryEventType.RECEIVE
                    event.event_subtype = HistoryEventSubType.REWARD
                    event.notes = f'Receive {event.amount} {crypto_asset.symbol} rewards from {gauge_address} {self.counterparty} gauge'  # noqa: E501

        return EvmDecodingOutput(refresh_balances=found_event_modifying_balances)

    def _decode_cl_gauge_events(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decodes staking and unstaking of a Slipstream position NFT in a CL gauge.
        Reward claims share the v2 gauge ClaimRewards signature and are handled with them."""
        user_address = bytes_to_address(context.tx_log.topics[1])
        position_id = int.from_bytes(context.tx_log.topics[2])
        gauge_address = context.tx_log.address
        position_token = get_or_create_evm_token(
            userdb=self.base.database,
            evm_address=self.slipstream_nfpm,
            chain_id=self.node_inquirer.chain_id,
            token_kind=TokenKind.ERC721,
            collectible_id=str(position_id),
            protocol=self.counterparty,
        )
        for event in context.decoded_events:
            if (
                event.location_label == user_address and
                event.address == gauge_address and
                event.asset == position_token and
                event.event_subtype == HistoryEventSubType.NONE
            ):
                event.counterparty = self.counterparty
                if context.tx_log.topics[0] == CL_GAUGE_DEPOSIT and event.event_type == HistoryEventType.SPEND:  # noqa: E501
                    event.event_type = HistoryEventType.DEPOSIT
                    event.event_subtype = HistoryEventSubType.DEPOSIT_TO_PROTOCOL
                    event.notes = f'Deposit {self.slipstream_display_name} LP {position_id} into {gauge_address} {self.counterparty} gauge'  # noqa: E501
                elif context.tx_log.topics[0] == CL_GAUGE_WITHDRAW and event.event_type == HistoryEventType.RECEIVE:  # noqa: E501
                    event.event_type = HistoryEventType.WITHDRAWAL
                    event.event_subtype = HistoryEventSubType.WITHDRAW_FROM_PROTOCOL
                    event.notes = f'Withdraw {self.slipstream_display_name} LP {position_id} from {gauge_address} {self.counterparty} gauge'  # noqa: E501
                else:
                    continue

                return EvmDecodingOutput(refresh_balances=True)

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_voting_escrow_events(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] == VOTING_ESCROW_WITHDRAW:
            return self._decode_withdraw_event(context)
        elif context.tx_log.topics[0] == VOTING_ESCROW_CREATE_LOCK:
            return self._decode_create_lock_event(context)
        elif context.tx_log.topics[0] == VOTING_ESCROW_METADATA_UPDATE:
            return self._decode_metadata_update_event(context)

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_withdraw_event(self, context: DecoderContext) -> EvmDecodingOutput:
        amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[:32]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )
        token_id = int.from_bytes(context.tx_log.topics[2])
        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.location_label == bytes_to_address(context.tx_log.topics[1]) and
                    event.address == ZERO_ADDRESS and
                    event.amount == ONE
            ):
                event.event_type = HistoryEventType.BURN
                event.event_subtype = HistoryEventSubType.NFT
                event.counterparty = self.counterparty
                event.notes = f'Burn veNFT-{token_id} to unlock {amount} {self.token_symbol} from vote escrow'  # noqa: E501

            elif (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.amount == amount and
                    event.address == self.voting_escrow_address
            ):
                event.counterparty = self.counterparty
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.WITHDRAW_FROM_PROTOCOL
                event.notes = f'Receive {amount} {self.token_symbol} from vote escrow after burning veNFT-{token_id}'  # noqa: E501

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_create_lock_event(self, context: DecoderContext) -> EvmDecodingOutput:
        in_event, out_event = None, None
        token_id = int.from_bytes(context.tx_log.topics[2])
        amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[:32]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )
        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.address == ZERO_ADDRESS and
                    event.amount == ONE
            ):
                event.event_type = HistoryEventType.MINT
                event.event_subtype = HistoryEventSubType.NFT
                event.notes = f'Receive veNFT-{token_id} for locking {amount} {self.token_symbol} in vote escrow'  # noqa: E501
                event.counterparty = self.counterparty
                in_event = event

            elif (
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.address == self.voting_escrow_address and
                    event.amount == amount
            ):
                event.notes = f'Lock {amount} {self.token_symbol} in vote escrow until {timestamp_to_date((lock_time := deserialize_timestamp(int.from_bytes(context.tx_log.data[32:64]))), formatstr="%d/%m/%Y")}'  # noqa: E501
                event.event_subtype = HistoryEventSubType.DEPOSIT_TO_PROTOCOL
                event.extra_data = {
                    'token_id': token_id,
                    'lock_time': lock_time,
                }
                event.event_type = HistoryEventType.DEPOSIT
                event.counterparty = self.counterparty
                out_event = event

        maybe_reshuffle_events(
            ordered_events=[out_event, in_event],
            events_list=context.decoded_events,
        )

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_metadata_update_event(self, context: DecoderContext) -> EvmDecodingOutput:
        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.DEPOSIT and
                    event.event_subtype == HistoryEventSubType.DEPOSIT_TO_PROTOCOL and
                    event.counterparty == self.counterparty
            ):  # increase amount locked
                token_id = event.extra_data['token_id']  # type: ignore[index]  # it is always available
                event.notes = f'Increase locked amount in veNFT-{token_id} by {event.amount} {self.token_symbol}'  # noqa: E501
                # The lock time on amount increases is zero, so remove it from the extra data.
                # But keep the token_id for balance detection if the original deposit was from a
                # different address or wasn't decoded for some reason.
                event.extra_data.pop('lock_time', None)  # type: ignore[union-attr]  # extra_data is not None
                return DEFAULT_EVM_DECODING_OUTPUT

        for tx_log in context.all_logs:  # Handle increase unlock time case
            if tx_log.topics[0] != VOTING_ESCROW_CREATE_LOCK:
                continue

            # depositType=3 (i.e. increase unlock time)
            if int.from_bytes(tx_log.topics[3]) != 3:
                continue

            return EvmDecodingOutput(events=[self.base.make_event_from_transaction(
                transaction=context.transaction,
                tx_log=context.tx_log,
                event_type=HistoryEventType.INFORMATIONAL,
                event_subtype=HistoryEventSubType.NONE,
                extra_data={
                    'token_id': (token_id := int.from_bytes(tx_log.topics[2])),
                    'lock_time': (new_unlock_time := deserialize_timestamp(int.from_bytes(tx_log.data[32:64]))),  # noqa: E501
                },
                amount=ZERO,
                counterparty=self.counterparty,
                address=self.voting_escrow_address,
                location_label=bytes_to_address(tx_log.topics[1]),
                notes=f'Increase unlock time to {timestamp_to_date(new_unlock_time, "%d/%m/%Y")} for {self.token_symbol} veNFT-{token_id}',  # noqa: E501
                asset=get_or_create_evm_token(
                    userdb=self.base.database,
                    evm_address=self.voting_escrow_address,
                    chain_id=self.node_inquirer.chain_id,
                    token_kind=TokenKind.ERC721,
                    collectible_id=str(token_id),
                ),
            )])

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_claim_rewards_events(
            self,
            suffix: str,
            context: DecoderContext,
    ) -> EvmDecodingOutput:
        if context.tx_log.topics[0] != VOTER_CLAIM_REWARDS:
            return DEFAULT_EVM_DECODING_OUTPUT

        for event in context.decoded_events:
            if (
                event.asset != (reward_token := self.base.get_or_create_evm_asset(bytes_to_address(context.tx_log.topics[2]))) and  # noqa: E501
                event.amount != asset_normalized_value(
                    amount=int.from_bytes(context.tx_log.data[:32]),
                    asset=reward_token,
                )
            ):
                continue

            event.counterparty = self.counterparty
            event.event_type = HistoryEventType.RECEIVE
            event.event_subtype = HistoryEventSubType.REWARD
            event.notes = f'Claim {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} from {self.counterparty} as a {suffix}'  # noqa: E501
            return DEFAULT_EVM_DECODING_OUTPUT

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_vote_events(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] != VOTER_VOTED:
            return DEFAULT_EVM_DECODING_OUTPUT

        weight = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[:32]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )
        return EvmDecodingOutput(events=[self.base.make_event_from_transaction(
            tx_log=context.tx_log,
            transaction=context.transaction,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=get_or_create_evm_token(
                userdb=self.base.database,
                evm_address=self.voting_escrow_address,
                chain_id=self.node_inquirer.chain_id,
                token_kind=TokenKind.ERC721,
                collectible_id=str(int.from_bytes(context.tx_log.topics[3])),
            ),
            amount=ZERO,
            counterparty=self.counterparty,
            address=self.voter_address,
            location_label=bytes_to_address(context.tx_log.topics[1]),
            notes=f'Cast {weight} votes for pool {bytes_to_address(context.tx_log.topics[2])}',
        )])

    def reload_data(self) -> Mapping[ChecksumEvmAddress, tuple[Any, ...]] | None:
        parent_mappings = super().reload_data()
        decoder_mappings = self.addresses_to_decoders()
        if parent_mappings is None:
            return decoder_mappings

        return dict(parent_mappings) | decoder_mappings

    def post_decoding_rules(self) -> dict[str, list[tuple[int, Callable]]]:
        return {self.counterparty: [(0, self._slipstream_position_post_decoding)]}

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        decoders = {
            self.voting_escrow_address: (self._decode_voting_escrow_events,),
            self.voter_address: (self._decode_vote_events,),
            self.slipstream_nfpm: (self._decode_slipstream_position_events,),
        }
        with GlobalDBHandler().conn.read_ctx() as cursor:
            for addy in globaldb_get_general_cache_values(
                cursor=cursor,
                key_parts=[self.gauge_fees_cache_type],
            ):
                decoders[string_to_evm_address(addy)] = (lambda context: self._decode_claim_rewards_events(context=context, suffix='fee'),)  # noqa: E501

            for addy in globaldb_get_general_cache_values(
                cursor=cursor,
                key_parts=[self.gauge_bribes_cache_type],
            ):
                decoders[string_to_evm_address(addy)] = (lambda context: self._decode_claim_rewards_events(context=context, suffix='bribe'),)  # noqa: E501

            return decoders
