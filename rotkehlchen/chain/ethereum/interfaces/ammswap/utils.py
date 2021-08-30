import logging
from typing import TYPE_CHECKING, NamedTuple, Set, Tuple

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.assets.utils import get_or_create_ethereum_token
from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import ChecksumEthAddress

from .typing import LiquidityPool, LiquidityPoolAsset

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


SUBGRAPH_REMOTE_ERROR_MSG = (
    "Failed to request the {location} subgraph due to {error_msg}. "
    "All {location} balances and historical queries are not functioning until this is fixed. "  # noqa: E501
    "Probably will get fixed with time. If not report it to rotki's support channel"  # noqa: E501
)


class TokenDetails(NamedTuple):
    address: ChecksumEthAddress
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
        known_assets: Set[EthereumToken],
        unknown_assets: Set[EthereumToken],
) -> LiquidityPool:
    pool_token = _decode_token(data[0])
    token0 = _decode_token(data[1][0])
    token1 = _decode_token(data[1][1])

    assets = []
    for token in (token0, token1):
        asset = get_or_create_ethereum_token(
            userdb=userdb,
            symbol=token.symbol,
            ethereum_address=token.address,
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
