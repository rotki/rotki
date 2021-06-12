import logging
from typing import TYPE_CHECKING, Any, Dict, List, Tuple

from typing_extensions import Literal

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import EthereumToken, UnderlyingToken
from rotkehlchen.assets.utils import get_or_create_ethereum_token
from rotkehlchen.chain.ethereum.trades import AMMSwap, AMMTrade
from rotkehlchen.constants import ZERO
from rotkehlchen.errors import DeserializationError, UnknownAsset
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_ethereum_address,
    deserialize_timestamp,
)
from rotkehlchen.typing import AssetAmount, ChecksumEthAddress, Location, Price, TradeType

from .typing import (
    BalancerBPTEvent,
    BalancerBPTEventType,
    BalancerInvestEvent,
    BalancerInvestEventType,
    BalancerPoolBalance,
    BalancerPoolTokenBalance,
)

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

SUBGRAPH_REMOTE_ERROR_MSG = (
    "Failed to request the Balancer subgraph due to {error_msg}. "
    "All Balancer balances and historical queries are not functioning until this is fixed. "  # noqa: E501
    "Probably will get fixed with time. If not report it to rotki's support channel"  # noqa: E501
)
UNISWAP_REMOTE_ERROR_MSG = (
    "Could not initialize the Uniswap subgraph due to {error_msg}. "
    "All Balancer balances and historical queries won't be able to use a "
    "secondary price oracle for requesting the USD price of the unsupported tokens. "
    "Probably will get fixed with time. If not report it to rotki's support channel"
)


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def deserialize_bpt_event(
        userdb: 'DBHandler',
        raw_event: Dict[str, Any],
        event_type: Literal[BalancerBPTEventType.MINT, BalancerBPTEventType.BURN],
) -> BalancerBPTEvent:
    """May raise DeserializationError"""
    try:
        tx_hash, log_index = deserialize_transaction_id(raw_event['id'])
        raw_user_address = raw_event['user']['id']
        amount = deserialize_asset_amount(raw_event['amount'])
        raw_pool = raw_event['pool']
        raw_pool_address = raw_pool['id']
        raw_pool_tokens = raw_pool['tokens']
        total_weight = deserialize_asset_amount(raw_pool['totalWeight'])
    except KeyError as e:
        raise DeserializationError(f'Missing key: {str(e)}.') from e

    if total_weight == ZERO:
        raise DeserializationError('Pool weight is zero.')

    user_address = deserialize_ethereum_address(raw_user_address)
    pool_address = deserialize_ethereum_address(raw_pool_address)

    underlying_tokens = []
    for raw_token in raw_pool_tokens:
        try:
            raw_token_address = raw_token['address']
            token_symbol = raw_token['symbol']
            token_name = raw_token['name']
            token_decimals = raw_token['decimals']
            token_weight = deserialize_asset_amount(raw_token['denormWeight'])
        except KeyError as e:
            raise DeserializationError(f'Missing key: {str(e)}.') from e

        token_address = deserialize_ethereum_address(raw_token_address)

        token = get_or_create_ethereum_token(
            userdb=userdb,
            symbol=token_symbol,
            ethereum_address=token_address,
            name=token_name,
            decimals=token_decimals,
        )
        underlying_tokens.append(UnderlyingToken(
            address=token.ethereum_address,
            weight=token_weight / total_weight,
        ))

    underlying_tokens.sort(key=lambda x: x.address)
    pool_address_token = get_or_create_ethereum_token(
        userdb=userdb,
        ethereum_address=pool_address,
        symbol='BPT',
        protocol='balancer',
        underlying_tokens=underlying_tokens,
    )
    bpt_event = BalancerBPTEvent(
        tx_hash=tx_hash,
        log_index=log_index,
        address=user_address,
        event_type=event_type,
        pool_address_token=pool_address_token,
        amount=amount,
    )
    return bpt_event


def deserialize_invest_event(
        raw_event: Dict[str, Any],
        event_type: Literal[
            BalancerInvestEventType.ADD_LIQUIDITY,
            BalancerInvestEventType.REMOVE_LIQUIDITY,
        ],
) -> BalancerInvestEvent:
    """May raise DeserializationError"""
    try:
        tx_hash, log_index = deserialize_transaction_id(raw_event['id'])
        timestamp = deserialize_timestamp(raw_event['timestamp'])
        raw_user_address = raw_event['userAddress']['id']
        raw_pool_address = raw_event['poolAddress']['id']
        if event_type == BalancerInvestEventType.ADD_LIQUIDITY:
            raw_token_address = raw_event['tokenIn']['address']
            amount = deserialize_asset_amount(raw_event['tokenAmountIn'])
        elif event_type == BalancerInvestEventType.REMOVE_LIQUIDITY:
            raw_token_address = raw_event['tokenOut']['address']
            amount = deserialize_asset_amount(raw_event['tokenAmountOut'])
        else:
            raise AssertionError(f'Unexpected event type: {event_type}.')

    except KeyError as e:
        raise DeserializationError(f'Missing key: {str(e)}.') from e

    user_address = deserialize_ethereum_address(raw_user_address)
    pool_address = deserialize_ethereum_address(raw_pool_address)
    try:
        pool_address_token = EthereumToken(pool_address)
    except UnknownAsset as e:
        raise DeserializationError(
            f'Balancer pool token with address {pool_address} should have been in the DB',
        ) from e
    token_address = deserialize_ethereum_address(raw_token_address)

    invest_event = BalancerInvestEvent(
        tx_hash=tx_hash,
        log_index=log_index,
        address=user_address,
        timestamp=timestamp,
        event_type=event_type,
        pool_address_token=pool_address_token,
        token_address=token_address,
        amount=amount,
    )
    return invest_event


def deserialize_pool_share(
        userdb: 'DBHandler',
        raw_pool_share: Dict[str, Any],
) -> Tuple[ChecksumEthAddress, BalancerPoolBalance]:
    """May raise DeserializationError"""
    try:
        raw_user_address = raw_pool_share['userAddress']['id']
        user_amount = deserialize_asset_amount(raw_pool_share['balance'])
        raw_pool = raw_pool_share['poolId']
        total_amount = deserialize_asset_amount(raw_pool['totalShares'])
        raw_address = raw_pool['id']
        raw_tokens = raw_pool['tokens']
        total_weight = deserialize_asset_amount(raw_pool['totalWeight'])
    except KeyError as e:
        raise DeserializationError(f'Missing key: {str(e)}.') from e

    if total_weight == ZERO:
        raise DeserializationError('Pool weight is zero.')

    user_address = deserialize_ethereum_address(raw_user_address)
    pool_address = deserialize_ethereum_address(raw_address)

    pool_tokens = []
    pool_token_balances = []
    for raw_token in raw_tokens:
        try:
            raw_token_address = raw_token['address']
            token_symbol = raw_token['symbol']
            token_name = raw_token['name']
            token_decimals = raw_token['decimals']
            token_total_amount = deserialize_asset_amount(raw_token['balance'])
            token_weight = deserialize_asset_amount(raw_token['denormWeight'])
        except KeyError as e:
            raise DeserializationError(f'Missing key: {str(e)}.') from e

        token_address = deserialize_ethereum_address(raw_token_address)

        token = get_or_create_ethereum_token(
            userdb=userdb,
            symbol=token_symbol,
            ethereum_address=token_address,
            name=token_name,
            decimals=token_decimals,
        )
        if token_total_amount == ZERO:
            raise DeserializationError(f'Token {token.identifier} balance is zero.')

        weight = token_weight * 100 / total_weight
        token_user_amount = user_amount / total_amount * token_total_amount
        pool_token_balance = BalancerPoolTokenBalance(
            token=token,
            total_amount=token_total_amount,
            user_balance=Balance(amount=token_user_amount),
            weight=weight,
        )
        pool_token_balances.append(pool_token_balance)
        pool_token = UnderlyingToken(address=token.ethereum_address, weight=weight / 100)
        pool_tokens.append(pool_token)

    pool_tokens.sort(key=lambda x: x.address)
    pool_token_balances.sort(key=lambda x: x.token.ethereum_address)
    balancer_pool_token = get_or_create_ethereum_token(
        userdb=userdb,
        symbol='BPT',
        ethereum_address=pool_address,
        protocol='balancer',
        underlying_tokens=pool_tokens,
    )
    pool = BalancerPoolBalance(
        pool_token=balancer_pool_token,
        underlying_tokens_balance=pool_token_balances,
        total_amount=total_amount,
        user_balance=Balance(amount=user_amount),
    )
    return user_address, pool


def deserialize_transaction_id(raw_tx_id: str) -> Tuple[str, int]:
    try:
        tx_hash, raw_log_index = raw_tx_id.split('-')
        log_index = int(raw_log_index)
    except ValueError as e:
        raise DeserializationError(f'Unexpected transaction id: {raw_tx_id}.') from e
    return tx_hash, log_index


def deserialize_swap(userdb: 'DBHandler', raw_swap: Dict[str, Any]) -> AMMSwap:
    """May raise DeserializationError"""
    try:
        tx_hash, log_index = deserialize_transaction_id(raw_swap['id'])
        timestamp = deserialize_timestamp(raw_swap['timestamp'])
        raw_tokens = raw_swap['poolAddress']['tokens']
        token0_symbol = raw_swap['tokenInSym']
        token1_symbol = raw_swap['tokenOutSym']
        amount0_in = deserialize_asset_amount(raw_swap['tokenAmountIn'])
        amount1_out = deserialize_asset_amount(raw_swap['tokenAmountOut'])
        raw_user_address = raw_swap['userAddress']['id']  # address
        raw_caller_address = raw_swap['caller']  # from_address
        raw_pool_address = raw_swap['poolAddress']['id']  # to_address
        raw_token_in_address = raw_swap['tokenIn']  # token0_address
        raw_token_out_address = raw_swap['tokenOut']  # token1_address
    except KeyError as e:
        raise DeserializationError(f'Missing key: {str(e)}.') from e

    if amount0_in == ZERO:
        # Prevent a division by zero error when creating the trade
        raise DeserializationError('TokenAmountIn balance is zero.')

    # Checksum addresses
    user_address = deserialize_ethereum_address(raw_user_address)
    caller_address = deserialize_ethereum_address(raw_caller_address)
    pool_address = deserialize_ethereum_address(raw_pool_address)
    token_in_address = deserialize_ethereum_address(raw_token_in_address)
    token_out_address = deserialize_ethereum_address(raw_token_out_address)

    # Get token0 and token1
    # When the controller removes all the tokens from a pool, `raw_tokens` will
    # be an empty list. Therefore it won't be possible to get their names and
    # decimals.
    if len(raw_tokens) != 0:
        try:
            raw_address_tokens = {raw_token['address']: raw_token for raw_token in raw_tokens}
            raw_token0 = raw_address_tokens[raw_token_in_address]
            raw_token1 = raw_address_tokens[raw_token_out_address]
            token0_name = raw_token0['name']
            token0_decimals = raw_token0['decimals']
            token1_name = raw_token1['name']
            token1_decimals = raw_token1['decimals']
        except KeyError as e:
            raise DeserializationError(f'Missing key: {str(e)}.') from e
    else:
        token0_name = None
        token0_decimals = None
        token1_name = None
        token1_decimals = None

    token0 = get_or_create_ethereum_token(
        userdb=userdb,
        symbol=token0_symbol,
        ethereum_address=token_in_address,
        name=token0_name,
        decimals=token0_decimals,
    )
    token1 = get_or_create_ethereum_token(
        userdb=userdb,
        symbol=token1_symbol,
        ethereum_address=token_out_address,
        name=token1_name,
        decimals=token1_decimals,
    )
    amm_swap = AMMSwap(
        tx_hash=tx_hash,
        log_index=log_index,
        address=user_address,
        from_address=caller_address,
        to_address=pool_address,
        timestamp=timestamp,
        location=Location.BALANCER,
        token0=token0,
        token1=token1,
        amount0_in=amount0_in,
        amount1_in=AssetAmount(ZERO),
        amount0_out=AssetAmount(ZERO),
        amount1_out=amount1_out,
    )
    return amm_swap


def deserialize_token_price(
        raw_token_price: Dict[str, Any],
) -> Tuple[ChecksumEthAddress, Price]:
    """May raise DeserializationError"""
    try:
        token_address = raw_token_price['id']
        usd_price = deserialize_price(raw_token_price['price'])
    except KeyError as e:
        raise DeserializationError(f'Missing key: {str(e)}.') from e

    token_address = deserialize_ethereum_address(token_address)

    return token_address, usd_price


def deserialize_token_day_data(
        raw_token_day_data: Dict[str, Any],
) -> Tuple[ChecksumEthAddress, Price]:
    """May raise DeserializationError"""
    try:
        token_address = raw_token_day_data['token']['id']
        usd_price = deserialize_price(raw_token_day_data['priceUSD'])
    except KeyError as e:
        raise DeserializationError(f'Missing key: {str(e)}.') from e

    token_address = deserialize_ethereum_address(token_address)

    return token_address, usd_price


def calculate_trade_from_swaps(
        swaps: List[AMMSwap],
        trade_index: int = 0,
) -> AMMTrade:
    """Given a list of 1 or more AMMSwap (swap) return an AMMTrade (trade).
    The trade is calculated using the first swap token (QUOTE) and last swap
    token (BASE). Be aware that any token data in between will be ignored for
    calculating the trade.

    Examples:
    [USDC -> AMPL]                              BASE_QUOTE pair is AMPL_USDC.
    [USDC -> AMPL, AMPL -> WETH]                BASE_QUOTE pair is WETH_USDC.
    [USDC -> AMPL, AMPL -> WETH, WETH -> USDC]  BASE_QUOTE pair is USDC_USDC.

    May raise DeserializationError
    """
    assert len(swaps) != 0, "Swaps can't be an empty list here"

    if swaps[0].amount0_in == ZERO:
        # Prevent a division by zero error when creating the trade.
        # Swaps with `tokenIn` amount (<AMMSwap>.amount0_in) equals to zero are
        # not expected nor supported. The function `deserialize_swap` will raise
        # a DeserializationError, preventing to store them in the DB. In case
        # of having a zero amount it means the db data was corrupted.
        log.error(
            'Failed to deserialize swap from db. First swap amount0_in is zero',
            swaps=swaps,
        )
        raise DeserializationError('First swap amount0_in is zero.')

    amm_trade = AMMTrade(
        trade_type=TradeType.BUY,  # AMMTrade is always a buy
        base_asset=swaps[-1].token1,
        quote_asset=swaps[0].token0,
        amount=swaps[-1].amount1_out,
        rate=Price(swaps[0].amount0_in / swaps[-1].amount1_out),
        swaps=swaps,
        trade_index=trade_index,
    )
    return amm_trade


def get_trades_from_tx_swaps(swaps: List[AMMSwap]) -> List[AMMTrade]:
    """Given a list of AMMSwap (swap) return a list of AMMTrade (trade). Each
    trade is made from 1 or more swaps (N swaps aggregated).

    Swaps aggregation criteria (all must be true):
    - Sequence: the swaps are in sequence ([swap N, swap N+1]).
    - Token: swap N token is swap N+1 token.
    - Amount: swap N "amount out" is equal to swap N+1 "amount in".

    When swaps are done via the Balancer Exchange Proxy (caller address is
    0x3e66b66fd1d0b02fda6c811da9e0547970db2f21) the swap N "amount out" equals
    to the swap N+1 "amount in". However, there may be a slight difference
    (e.g. 1e-5) when the caller is a custom contract. In this case the swaps
    won't be aggregated under the same trade.

    May raise DeserializationError
    """
    trades: List[AMMTrade] = []
    trade_swaps: List[AMMSwap] = []
    last_idx = len(swaps) - 1
    trade_index = 0
    for idx, swap in enumerate(swaps):
        trade_swaps.append(swap)
        if idx == last_idx:
            trade = calculate_trade_from_swaps(swaps=trade_swaps, trade_index=trade_index)
            trades.append(trade)
            break

        # Create the trade when the current swap can't be aggregated with the next one
        next_swap = swaps[idx + 1]
        is_not_aggregable = (
            swap.amount1_out != next_swap.amount0_in or
            swap.token1.ethereum_address != next_swap.token0.ethereum_address
        )
        if is_not_aggregable:
            trade = calculate_trade_from_swaps(swaps=trade_swaps, trade_index=trade_index)
            trades.append(trade)
            trade_index = trade_index + 1 if swap.tx_hash == next_swap.tx_hash else 0
            trade_swaps = []

    return trades
