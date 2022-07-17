from dataclasses import dataclass
from typing import Any, Dict, List, NamedTuple, Set, Tuple

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.interfaces.ammswap.types import LiquidityPool
from rotkehlchen.fval import FVal
from rotkehlchen.types import ChecksumEvmAddress


@dataclass(init=True, repr=True)
class NFTLiquidityPool(LiquidityPool):
    nft_id: str
    price_range: Tuple[FVal, FVal]

    def serialize(self) -> Dict[str, Any]:
        result = super().serialize()
        result.update({
            'price_range': list(self.price_range),
            'nft_id': self.nft_id,
        })
        return result


AddressToUniswapV3LPBalances = Dict[ChecksumEvmAddress, List[NFTLiquidityPool]]


class UniswapV3ProtocolBalance(NamedTuple):
    """Container structure for uniswap V3 LP balances

    Known assets are all assets we have an oracle for.
    Unknown assets are those we would have to try to query through uniswap directly.
    """
    address_balances: AddressToUniswapV3LPBalances
    known_assets: Set[EvmToken]
    unknown_assets: Set[EvmToken]
