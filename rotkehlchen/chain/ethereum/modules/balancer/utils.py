from typing import Any, Dict, List, Tuple

from eth_utils import to_checksum_address

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.utils import get_ethereum_token
from rotkehlchen.chain.ethereum.trades import AMMSwap, AMMTrade
from rotkehlchen.constants import ZERO
from rotkehlchen.errors import DeserializationError
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_price,
    deserialize_timestamp,
)
from rotkehlchen.typing import AssetAmount, ChecksumEthAddress, Location, Price, TradeType

from .typing import BalancerPool, BalancerPoolToken, SwapAddresses, SwapRawAddresses

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


def deserialize_pool_share(
        raw_pool_share: Dict[str, Any],
) -> Tuple[ChecksumEthAddress, BalancerPool]:
    """May raise DeserializationError"""
    try:
        user_address = raw_pool_share['userAddress']['id']
        user_amount = deserialize_asset_amount(raw_pool_share['balance'])
        raw_pool = raw_pool_share['poolId']
        total_amount = deserialize_asset_amount(raw_pool['totalShares'])
        address = raw_pool['id']
        raw_tokens = raw_pool['tokens']
        total_weight = deserialize_asset_amount(raw_pool['totalWeight'])
    except KeyError as e:
        raise DeserializationError(f'Missing key: {str(e)}.') from e

    if total_weight == ZERO:
        raise DeserializationError('Pool weight is zero')

    try:
        user_address = to_checksum_address(user_address)
    except ValueError as e:
        raise DeserializationError(
            f'Invalid ethereum address: {address} in pool userAddress.',
        ) from e

    try:
        address = to_checksum_address(address)
    except ValueError as e:
        raise DeserializationError(
            f'Invalid ethereum address: {address} in pool id.',
        ) from e

    pool_tokens = []
    for raw_token in raw_tokens:
        try:
            token_address = raw_token['address']
            token_symbol = raw_token['symbol']
            token_name = raw_token['name']
            token_decimals = raw_token['decimals']
            token_total_amount = deserialize_asset_amount(raw_token['balance'])
            token_weight = deserialize_asset_amount(raw_token['denormWeight'])
        except KeyError as e:
            raise DeserializationError(f'Missing key: {str(e)}.') from e

        try:
            token_address = to_checksum_address(token_address)
        except ValueError as e:
            raise DeserializationError(
                f'Invalid ethereum address: {token_address} in pool token: {token_symbol}.',  # noqa: E501
            ) from e

        token = get_ethereum_token(
            symbol=token_symbol,
            ethereum_address=token_address,
            name=token_name,
            decimals=token_decimals,
        )
        if token_total_amount == ZERO:
            raise DeserializationError(f'Token {token.identifier} balance is zero')

        token_user_amount = user_amount / total_amount * token_total_amount
        weight = token_weight * 100 / total_weight
        pool_token = BalancerPoolToken(
            token=token,
            total_amount=token_total_amount,
            user_balance=Balance(amount=token_user_amount),
            weight=weight,
        )
        pool_tokens.append(pool_token)

    pool = BalancerPool(
        address=address,
        tokens=pool_tokens,
        total_amount=total_amount,
        user_balance=Balance(amount=user_amount),
    )
    return user_address, pool


def deserialize_transaction_id(raw_tx_id: str) -> Tuple[str, int]:
    try:
        tx_hash, raw_log_index = raw_tx_id.split('-')
        log_index = int(raw_log_index)
    except ValueError as e:
        raise DeserializationError(f'Unexpected transaction id: {raw_tx_id}') from e
    return tx_hash, log_index


def deserialize_swap(raw_swap: Dict[str, Any]) -> AMMSwap:
    """May raise DeserializationError"""
    try:
        tx_hash, log_index = deserialize_transaction_id(raw_swap['id'])
        timestamp = deserialize_timestamp(raw_swap['timestamp'])
        raw_tokens = raw_swap['poolAddress']['tokens']
        token0_symbol = raw_swap['tokenInSym']
        token1_symbol = raw_swap['tokenOutSym']
        amount0_in = deserialize_asset_amount(raw_swap['tokenAmountIn'])
        amount1_out = deserialize_asset_amount(raw_swap['tokenAmountOut'])
        raw_token_in = raw_swap['tokenIn']
        raw_token_out = raw_swap['tokenOut']
        raw_addresses = SwapRawAddresses(
            user_address=raw_swap['userAddress']['id'],  # address
            caller=raw_swap['caller'],  # from_address
            pool_address=raw_swap['poolAddress']['id'],  # to_address
            token_in=raw_token_in,  # token0_address
            token_out=raw_token_out,  # token1_address
        )
    except KeyError as e:
        raise DeserializationError(f'Missing key: {str(e)}.') from e

    # Checksum addresses
    try:
        addresses = SwapAddresses(
            user_address=to_checksum_address(raw_addresses.user_address),
            caller=to_checksum_address(raw_addresses.caller),
            pool_address=to_checksum_address(raw_addresses.pool_address),
            token_in=to_checksum_address(raw_addresses.token_in),
            token_out=to_checksum_address(raw_addresses.token_out),
        )
    except ValueError as e:
        error_msg = str(e)
        for field in raw_addresses._fields:
            if getattr(raw_addresses, field) in error_msg:
                break
        raise DeserializationError(
            f'Invalid ethereum address: {getattr(raw_addresses, field)} in swap {field}.',
        ) from e

    # Get token0 and token1
    # When the controller removes all the tokens from a pool, `raw_tokens` will
    # be an empty list. Therefore it won't be possible to get their names and
    # decimals. In case of having to instantiate an UnknownEthereumToken both
    # params will be None.
    if len(raw_tokens):
        try:
            raw_address_tokens = {raw_token['address']: raw_token for raw_token in raw_tokens}
            raw_token0 = raw_address_tokens[raw_token_in]
            raw_token1 = raw_address_tokens[raw_token_out]
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

    token0 = get_ethereum_token(
        symbol=token0_symbol,
        ethereum_address=addresses.token_in,
        name=token0_name,
        decimals=token0_decimals,
    )
    token1 = get_ethereum_token(
        symbol=token1_symbol,
        ethereum_address=addresses.token_out,
        name=token1_name,
        decimals=token1_decimals,
    )
    amm_swap = AMMSwap(
        tx_hash=tx_hash,
        log_index=log_index,
        address=addresses.user_address,
        from_address=addresses.caller,
        to_address=addresses.pool_address,
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

    try:
        token_address = to_checksum_address(token_address)
    except ValueError as e:
        raise DeserializationError(
            f'Invalid ethereum address: {token_address} in token price.',
        ) from e

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

    try:
        token_address = to_checksum_address(token_address)
    except ValueError as e:
        raise DeserializationError(
            f'Invalid ethereum address: {token_address} in token day data.',
        ) from e

    return token_address, usd_price


def calculate_amm_trade_from_amm_swaps(swaps: List[AMMSwap]) -> AMMTrade:
    """AMMTrade is always a buy.

    [USDC -> AMPL]               BASE_QUOTE pair is AMPL_USDC.
    [USDC -> AMPL, AMPL -> WETH] BASE_QUOTE pair is WETH_USDC.
    """
    if len(swaps) == 0:
        raise AssertionError("Swaps can't be an empty list")

    amm_trade = AMMTrade(
        trade_type=TradeType.BUY,
        base_asset=swaps[-1].token1,
        quote_asset=swaps[0].token0,
        amount=swaps[-1].amount1_out,
        rate=Price(swaps[-1].amount1_out / swaps[0].amount0_in),
        swaps=swaps,
        trade_index=0,
    )
    return amm_trade


def get_trades_from_tx_swaps(swaps: List[AMMSwap]) -> List[AMMTrade]:
    """Aggregates N AMMSwaps in an AMMTrade.

    We expect that the swaps likely to be aggregated in a single trade are in
    sequence (the next). This function currently does not have interleaved
    matching capabilities.

    When swaps are done via the Balancer Exchange Proxy (caller address is
    `0x3e66b66fd1d0b02fda6c811da9e0547970db2f21`) the previous swap N amount out
    matches the swap N+1 amount in. However, there may be slightly differences
    between these amounts when the caller is a custom contract. The former case
    will be always be a trade with two swaps. On the latter it will depend on
    the quantities. If they match, a trade with two swaps, otherwise two trades
    (each one with one swap).

    Aggregation criteria:
    - AMMSwap N amount1_out == AMMSwap N+1 amount0_in
    - AMMSwap N token1 == AMMSwap N+1 token0
    """
    trades: List[AMMTrade] = []
    trade_swaps: List[AMMSwap] = []
    last_idx = len(swaps) - 1
    for idx, swap in enumerate(swaps):
        trade_swaps.append(swap)
        if idx == last_idx:
            trade = calculate_amm_trade_from_amm_swaps(trade_swaps)
            trades.append(trade)
            break

        next_swap = swaps[idx + 1]
        if (
            swap.amount1_out != next_swap.amount0_in or
            swap.token1.ethereum_address != next_swap.token0.ethereum_address
        ):
            trade = calculate_amm_trade_from_amm_swaps(trade_swaps)
            trades.append(trade)
            trade_swaps = []

    return trades
