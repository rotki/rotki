from typing import TYPE_CHECKING, NamedTuple

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.ethereum.interfaces.ammswap.types import (
    LiquidityPool,
    LiquidityPoolAsset,
)
from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.fval import FVal
from rotkehlchen.types import ChainID, ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


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

    return LiquidityPool(
        address=pool_token.address,
        assets=assets,
        total_supply=None,
        user_balance=Balance(amount=pool_token.amount),
    )
