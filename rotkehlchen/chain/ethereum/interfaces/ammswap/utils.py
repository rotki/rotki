import logging
from typing import TYPE_CHECKING, NamedTuple, Set, Tuple, Union

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.ethereum.interfaces.ammswap.types import (
    AddressToLPBalances,
    AssetToPrice,
    LiquidityPool,
    LiquidityPoolAsset,
)
from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.constants.resolver import ChainID
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, Price

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.modules.uniswap.v3.types import AddressToUniswapV3LPBalances
    from rotkehlchen.db.dbhandler import DBHandler


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


SUBGRAPH_REMOTE_ERROR_MSG = (
    "Failed to request the {location} subgraph due to {error_msg}. "
    "All {location} balances and historical queries are not functioning until this is fixed. "  # noqa: E501
    "Probably will get fixed with time. If not report it to rotki's support channel"  # noqa: E501
)


class TokenDetails(NamedTuple):
    address: ChecksumEvmAddress
    name: str
    symbol: str
    decimals: int
    amount: FVal


def _decode_token(entry: Tuple) -> TokenDetails:
    decimals = entry[0][3]
    return TokenDetails(
        address=entry[0][0],
        name=entry[0][1],
        symbol=entry[0][2],
        decimals=decimals,
        amount=token_normalized_value_decimals(entry[1], decimals),
    )


def _decode_result(
        userdb: 'DBHandler',
        data: Tuple,
        known_assets: Set[EvmToken],
        unknown_assets: Set[EvmToken],
) -> LiquidityPool:
    pool_token = _decode_token(data[0])
    token0 = _decode_token(data[1][0])
    token1 = _decode_token(data[1][1])

    assets = []
    for token in (token0, token1):
        asset = get_or_create_evm_token(
            userdb=userdb,
            symbol=token.symbol,
            evm_address=token.address,
            chain=ChainID.ETHEREUM,
            name=token.name,
            decimals=token.decimals,
        )
        # Classify the asset either as price known or unknown
        if asset.has_oracle():
            known_assets.add(asset)
        else:
            unknown_assets.add(asset)
        assets.append(LiquidityPoolAsset(
            asset=asset,
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
    (prices obtained via Inquirer and the subgraph) used by all AMM platforms.
    """
    for lps in address_balances.values():
        for lp in lps:
            # Try to get price from either known or unknown asset price.
            # Otherwise keep existing price (zero)
            total_user_balance = ZERO
            for asset in lp.assets:
                asset_ethereum_address = asset.asset.evm_address
                asset_usd_price = known_asset_price.get(
                    asset_ethereum_address,
                    unknown_asset_price.get(asset_ethereum_address, Price(ZERO)),
                )
                # Update <LiquidityPoolAsset> if asset USD price exists
                if asset_usd_price != Price(ZERO):
                    asset.usd_price = asset_usd_price
                    asset.user_balance.usd_value = FVal(
                        asset.user_balance.amount * asset_usd_price,
                    )

                total_user_balance += asset.user_balance.usd_value

            # Update <LiquidityPool> total balance in USD
            lp.user_balance.usd_value = total_user_balance
