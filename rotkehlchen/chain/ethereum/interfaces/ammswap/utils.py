import logging
from typing import TYPE_CHECKING, NamedTuple, Union

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.ethereum.interfaces.ammswap.types import (
    AddressToLPBalances,
    AssetToPrice,
    LiquidityPool,
    LiquidityPoolAsset,
)
from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID, ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.modules.uniswap.v3.types import AddressToUniswapV3LPBalances
    from rotkehlchen.db.dbhandler import DBHandler


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


SUBGRAPH_REMOTE_ERROR_MSG = (
    'Failed to request the {location} subgraph due to {error_msg}. '
    'All {location} balances and historical queries are not functioning until this is fixed. '
    "Probably will get fixed with time. If not report it to rotki's support channel"
)


class TokenDetails(NamedTuple):
    address: ChecksumEvmAddress
    name: str
    symbol: str
    decimals: int
    amount: FVal


def _decode_token(entry: tuple) -> TokenDetails:
    decimals = entry[0][3]
    return TokenDetails(
        address=entry[0][0],
        name=entry[0][1],
        symbol=entry[0][2],
        decimals=decimals,
        amount=token_normalized_value_decimals(entry[1], decimals),
    )


def decode_result(userdb: 'DBHandler', data: tuple) -> LiquidityPool:
    """
    Process information obtained from the zerion adapter for uniswap/sushiswap
    pools making sure that involved tokens exist in the globaldb
    """
    pool_token = _decode_token(data[0])
    token0 = _decode_token(data[1][0])
    token1 = _decode_token(data[1][1])

    assets = []
    for token in (token0, token1):
        asset = get_or_create_evm_token(
            userdb=userdb,
            symbol=token.symbol,
            evm_address=token.address,
            chain_id=ChainID.ETHEREUM,
            name=token.name,
            decimals=token.decimals,
        )
        assets.append(LiquidityPoolAsset(
            token=asset,
            total_amount=None,
            user_balance=Balance(amount=token.amount),
        ))

    pool = LiquidityPool(
        address=pool_token.address,
        assets=assets,
        total_supply=None,
        user_balance=Balance(amount=pool_token.amount),
    )
    return pool


def update_asset_price_in_lp_balances(
        address_balances: Union[AddressToLPBalances, 'AddressToUniswapV3LPBalances'],
        known_asset_price: AssetToPrice,
        unknown_asset_price: AssetToPrice,
) -> None:
    """Utility function to update the pools underlying assets prices in USD
    (prices obtained via Inquirer) used by all AMM platforms.
    """
    for lps in address_balances.values():
        for lp in lps:
            # Try to get price from either known or unknown asset price.
            # Otherwise keep existing price (zero)
            total_user_balance = ZERO
            for asset in lp.assets:
                asset_ethereum_address = asset.token.evm_address
                asset_usd_price = known_asset_price.get(
                    asset_ethereum_address,
                    unknown_asset_price.get(asset_ethereum_address, ZERO_PRICE),
                )
                # Update <LiquidityPoolAsset> if asset USD price exists
                if asset_usd_price != ZERO_PRICE:
                    asset.usd_price = asset_usd_price
                    asset.user_balance.usd_value = FVal(
                        asset.user_balance.amount * asset_usd_price,
                    )

                total_user_balance += asset.user_balance.usd_value

            # Update <LiquidityPool> total balance in USD
            lp.user_balance.usd_value = total_user_balance
