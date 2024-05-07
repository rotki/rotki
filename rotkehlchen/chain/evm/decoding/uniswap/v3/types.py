from dataclasses import dataclass
from typing import Any, NamedTuple

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.interfaces.ammswap.types import LiquidityPool
from rotkehlchen.fval import FVal
from rotkehlchen.types import ChecksumEvmAddress


@dataclass(init=True, repr=True)
class NFTLiquidityPool(LiquidityPool):
    nft_id: str
    price_range: tuple[FVal, FVal]

    def serialize(self) -> dict[str, Any]:
        result = super().serialize()
        result.update({
            'price_range': list(self.price_range),
            'nft_id': self.nft_id,
        })
        return result


AddressToUniswapV3LPBalances = dict[ChecksumEvmAddress, list[NFTLiquidityPool]]


class UniswapV3ProtocolBalance(NamedTuple):
    """Container structure for uniswap V3 LP balances

    Known assets are all assets we have an oracle for.
    Unknown assets are those we would have to try to query through uniswap directly.
    """
    address_balances: AddressToUniswapV3LPBalances
    known_tokens: set[EvmToken]
    unknown_tokens: set[EvmToken]
