from dataclasses import dataclass, field
from typing import (
    Any,
    DefaultDict,
    Dict,
    List,
    NamedTuple,
    Set,
    Tuple,
    Union,
)

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.constants import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.typing import (
    ChecksumEthAddress,
    Price,
    Timestamp,
)


@dataclass(init=True, repr=True, eq=False, unsafe_hash=False, frozen=True)
class UnknownEthereumToken:
    """Alternative minimal class to EthereumToken for unknown assets"""
    identifier: str
    ethereum_address: ChecksumEthAddress
    name: str = None
    decimals: int = None
    symbol: str = field(init=False)

    def __post_init__(self) -> None:
        """Asset post initialization as the frozen property is desirable
        """
        object.__setattr__(self, 'symbol', self.identifier)

    def __hash__(self) -> int:
        return hash((self.identifier, self.ethereum_address))

    def __eq__(self, other: Any) -> bool:
        if other is None:
            return False
        if not isinstance(other, UnknownEthereumToken):
            raise TypeError(f'Invalid type: {type(other)}')

        return (
            self.identifier == other.identifier and
            self.ethereum_address == other.ethereum_address
        )

    def serialize(self) -> Dict:
        return {
            'decimals': self.decimals,
            'ethereum_address': self.ethereum_address,
            'identifier': self.identifier,
            'name': self.name,
            'symbol': self.symbol,
        }


# Below set of classes where to store PoolShare, Pool and PoolToken data
# BalancerPoolAsset stores PoolToken data, and adds custom ones
@dataclass(init=True, repr=True)
class BalancerPoolAsset:
    balance: FVal  # PoolToken.balance
    denorm_weight: FVal  # PoolToken.denormWeight
    user_balance: Balance  # Estimated token balance and USD price
    asset: Union[EthereumToken, UnknownEthereumToken]
    asset_usd: Price = Price(ZERO)  # price in USD per token

    def serialize(self) -> Dict:
        return {
            'balance': self.balance,
            'denorm_weight': self.denorm_weight,
            'user_balance': self.user_balance.serialize(),
            'asset': self.asset.serialize(),
            'asset_usd': self.asset_usd,
        }


# BalancerPool stores PoolShare and Pool data
# TODO: currently `asset` field can't be populated with <Asset> or
# <EthereumToken> because BPT is not a unique symbol for Balancer.
# Explore something similar to `converters.py`
@dataclass(init=True, repr=True)
class BalancerPool:
    asset: UnknownEthereumToken  # Pool.id, Pool.symbol
    assets: List[BalancerPoolAsset]  # Pool.tokens
    assets_count: FVal  # Pool.tokensCount
    balance: FVal  # Pool.totalShares
    weight: FVal  # Pool.totalWeight
    user_balance: Balance  # Pool.totalShares and estimated total USD price

    def serialize(self) -> Dict:
        return {
            'asset': self.asset.serialize(),
            'assets': [asset.serialize() for asset in self.assets],
            'assets_count': self.assets_count,
            'balance': self.balance,
            'weight': self.weight,
            'user_balance': self.user_balance.serialize(),
        }


class BalancerBalances(NamedTuple):
    addresses_balancer_pools: Dict[ChecksumEthAddress, List[BalancerPool]]
    known_assets: Set[EthereumToken]
    unknown_assets: Set[UnknownEthereumToken]


# Get history

# Get history type aliases
BalancerTradeDBTuple = (
    Tuple[
        str,  # tx_hash
        int,  # log_index
        ChecksumEthAddress,  # address
        Timestamp,  # timestamp
        str,  # usd_fee
        str,  # usd_value
        ChecksumEthAddress,  # pool_address
        str,  # pool_name
        str,  # pool_liquidity
        str,  # usd_pool_total_swap_fee
        str,  # usd_pool_total_swap_volume
        int,  # is_asset_in_known
        ChecksumEthAddress,  # asset_in_address
        str,  # asset_in_symbol
        str,  # asset_in_amount
        int,  # is_asset_out_known
        ChecksumEthAddress,  # asset_out_address
        str,  # asset_out_symbol
        str,  # asset_out_amount
    ]
)


# BalancerTrade stores swap, userAddress and poolAddress data
# TODO: If storing the USD value of both `asset_in` and `asset_out` is
# required,this should be a dataclass with `asset_in_balance` and
# `asset_out_balance` of type Balance, instead of `asset_in_amount` and
# `asset_out_amount`. Pending to know how to fetch historical usd prices
# without compromising performance... there could be lots of trades.
class BalancerTrade(NamedTuple):
    """An trade in the Balancer protocol"""
    tx_hash: str  # from Swap.tx
    log_index: int  # from Swap.tx
    address: ChecksumEthAddress  # Custom, but equals to Swap.userAddress.id
    timestamp: Timestamp  # Swap.timestamp
    usd_fee: Price  # Swap.feeValue
    usd_value: Price  # Swap.value
    pool_address: ChecksumEthAddress  # Swap.poolAddress.id
    pool_name: Union[str, None]  # Swap.poolAddress.name
    pool_liquidity: FVal  # Swap.poolLiquidity
    usd_pool_total_swap_fee: Price  # Swap.poolTotalSwapFee
    usd_pool_total_swap_volume: Price  # Swap.poolTotalSwapVolume
    asset_in: Union[EthereumToken, UnknownEthereumToken]  # Swap.tokenIn, Swap.tokenInSym
    asset_in_amount: FVal  # Swap.tokenAmountIn
    asset_out: Union[EthereumToken, UnknownEthereumToken]  # Swap.tokenOut, Swap.tokenOutSym
    asset_out_amount: FVal  # Swap.tokenAmountOut

    def to_db_tuple(self, address: ChecksumEthAddress) -> BalancerTradeDBTuple:
        is_asset_in_known = 1 if isinstance(self.asset_in, EthereumToken) else 0
        asset_in_address = self.asset_in.ethereum_address
        asset_in_symbol = self.asset_in.identifier
        is_asset_out_known = 1 if isinstance(self.asset_in, EthereumToken) else 0
        asset_out_address = self.asset_out.ethereum_address
        asset_out_symbol = self.asset_out.identifier

        return (
            self.tx_hash,
            self.log_index,
            address,
            self.timestamp,
            str(self.usd_fee),
            str(self.usd_value),
            self.pool_address,
            self.pool_name,
            str(self.pool_liquidity),
            str(self.usd_pool_total_swap_fee),
            str(self.usd_pool_total_swap_volume),
            is_asset_in_known,
            asset_in_address,
            asset_in_symbol,
            str(self.asset_in_amount),
            is_asset_out_known,
            asset_out_address,
            asset_out_symbol,
            str(self.asset_out_amount),
        )

    def __hash__(self) -> int:
        return hash((self.tx_hash, self.log_index))

    def __eq__(self, other: Any) -> bool:
        if other is None:
            return False
        if not isinstance(other, BalancerTrade):
            raise TypeError(f'Invalid type: {type(other)}')

        return (
            self.tx_hash == other.tx_hash and
            self.log_index == other.log_index
        )


# Get balances type aliases

#  Get balances
AddressesBalancerPools = Dict[ChecksumEthAddress, List[BalancerPool]]
DDAddressesBalancerPools = DefaultDict[ChecksumEthAddress, List[BalancerPool]]
AssetsPrices = Dict[ChecksumEthAddress, FVal]
BalancerPools = List[BalancerPool]
BalancerPoolAssets = List[BalancerPoolAsset]

# Get trades
AddressesBalancerTrades = Dict[ChecksumEthAddress, List[BalancerTrade]]
DDAddressesBalancerTrades = Dict[ChecksumEthAddress, List[BalancerTrade]]
