from typing import (
    Any,
    DefaultDict,
    Dict,
    List,
    NamedTuple, NewType,
    Optional,
    Set,
)

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.typing import ChecksumEthAddress


# Below set of classes where to store PoolShare, Pool and PoolToken data
# BalancerPoolAsset stores PoolToken data, and adds custom ones
class BalancerPoolAsset(NamedTuple):
    address: ChecksumEthAddress  # PoolToken.id, token contract address
    balance: FVal  # PoolToken.balance
    denorm_weight: FVal  # PoolToken.denormWeight
    name: str  # PoolToken.name
    symbol: str  # PoolToken.symbol
    # Custom fields
    user_balance: FVal  # Estimated token balance
    user_balance_usd: Optional[FVal] = ZERO  # Estimated token balance in USD
    asset: Optional[Asset] = None
    asset_usd: Optional[FVal] = ZERO  # price in USD per token


# BalancerPool stores PoolShare and Pool data
# ! TODO VN PR: currently `asset` field can't be populated with <Asset> because
# ! there are as many BPT contracts as pools in Balancer
class BalancerPool(NamedTuple):
    address: ChecksumEthAddress  # Pool.id, pool contract address
    assets: List[BalancerPoolAsset]  # Pool.tokens
    assets_count: FVal  # Pool.tokensCount
    symbol: str  # Pool.symbol
    balance: FVal  # Pool.totalShares
    weight: FVal  # Pool.totalWeight
    # Custom fields
    user_balance: FVal  # PoolShare.balance
    asset: Optional[Asset] = None


class KnownAsset(NamedTuple):
    address: ChecksumEthAddress
    asset: Asset

    def __hash__(self) -> int:
        return hash((self.address, hash(self.asset)))

    def __eq__(self, other: Any) -> bool:
        if other is None:
            return False
        if not isinstance(other, KnownAsset):
            raise TypeError(f'Invalid type: {type(other)}')

        return self.address == other.address and self.asset == other.asset


class BalancerBalances(NamedTuple):
    addresses_balancer_pools: Dict[ChecksumEthAddress, List[BalancerPool]]
    known_assets: Set[KnownAsset]
    unknown_assets: Set[ChecksumEthAddress]


# Types aliases
AddressesBalancerPools = Dict[ChecksumEthAddress, List[BalancerPool]]
DDAddressesBalancerPools = DefaultDict[ChecksumEthAddress, List[BalancerPool]]
AssetsPrices = Dict[ChecksumEthAddress, FVal]
BalancerPools = List[BalancerPool]
BalancerPoolAssets = List[BalancerPoolAsset]
