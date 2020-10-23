from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.errors import DeserializationError, UnknownAsset
from rotkehlchen.fval import FVal
from rotkehlchen.typing import Price
from .typing import (
    BalancerTrade,
    BalancerTradeDBTuple,
    UnknownEthereumToken,
)


def balancer_trade_from_db(trade_tuple: BalancerTradeDBTuple) -> BalancerTrade:
    """Turns a tuple read from the DB into an appropriate BalancerTrade

    May raise a DeserializationError if something is wrong with the DB data
    for known assets.

    Trade_tuple index - Schema columns
    ----------------------------------
     0 - tx_hash
     1 - log_index
     2 - address
     3 - timestamp
     4 - usd_fee
     5 - usd_value
     6 - pool_address
     7 - pool_name
     8 - pool_liquidity
     9 - usd_pool_total_swap_fee
    10 - usd_pool_total_swap_volume
    11 - is_asset_in_known
    12 - asset_in_address
    13 - asset_in_symbol
    14 - asset_in_amount
    15 - is_asset_out_known
    16 - asset_out_address
    17 - asset_out_symbol
    18 - asset_out_amount
    """
    is_asset_in_known = trade_tuple[11]
    is_asset_out_known = trade_tuple[15]

    if is_asset_in_known:
        try:
            asset_in = EthereumToken(trade_tuple[13])
        except UnknownAsset as e:
            raise DeserializationError(
                f'Unknown asset {trade_tuple[13]} with address {trade_tuple[12]} '
                f'encountered during deserialization of Balancer trade from DB',
            ) from e
    else:
        asset_in = (
            UnknownEthereumToken(
                identifier=trade_tuple[13],
                ethereum_address=trade_tuple[12],
            )
        )

    if is_asset_out_known:
        try:
            asset_out = EthereumToken(trade_tuple[17])
        except UnknownAsset as e:
            raise DeserializationError(
                f'Unknown asset {trade_tuple[17]} with address {trade_tuple[16]} '
                f'encountered during deserialization of Balancer trade from DB',
            ) from e
    else:
        asset_out = (
            UnknownEthereumToken(
                identifier=trade_tuple[17],
                ethereum_address=trade_tuple[16],
            )
        )

    balancer_trade = BalancerTrade(
        tx_hash=trade_tuple[0],
        log_index=int(trade_tuple[1]),
        address=trade_tuple[2],
        timestamp=trade_tuple[3],
        usd_fee=Price(trade_tuple[4]),
        usd_value=Price(trade_tuple[5]),
        pool_address=trade_tuple[6],
        pool_name=trade_tuple[7],
        pool_liquidity=trade_tuple[8],
        usd_pool_total_swap_fee=Price(trade_tuple[9]),
        usd_pool_total_swap_volume=Price(trade_tuple[10]),
        asset_in=asset_in,
        asset_in_amount=FVal(trade_tuple[14]),
        asset_out=asset_out,
        asset_out_amount=FVal(trade_tuple[18]),
    )

    return balancer_trade
