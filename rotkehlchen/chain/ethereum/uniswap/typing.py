import logging
from dataclasses import dataclass
from typing import Any, DefaultDict, Dict, List, NamedTuple, Optional, Set, Union

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.assets.unknown_asset import UnknownEthereumToken
from rotkehlchen.chain.ethereum.trades import AMMTrade
from rotkehlchen.constants import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.typing import ChecksumEthAddress, Price

log = logging.getLogger(__name__)

SWAP_FEE = FVal('0.003')  # 0.3% fee for swapping tokens
UNISWAP_TRADES_PREFIX = 'uniswap_trades'

# Get balances


@dataclass(init=True, repr=True)
class LiquidityPoolAsset:
    asset: Union[EthereumToken, UnknownEthereumToken]
    total_amount: Optional[FVal]
    user_balance: Balance
    usd_price: Price = Price(ZERO)

    def serialize(self) -> Dict[str, Any]:
        serialized_asset: Union[str, Dict[str, Any]]

        if isinstance(self.asset, EthereumToken):
            serialized_asset = self.asset.serialize()
        elif isinstance(self.asset, UnknownEthereumToken):
            unknown_asset_keys = ('ethereum_address', 'name', 'symbol')
            serialized_asset = self.asset.serialize_as_dict(keys=unknown_asset_keys)
        else:
            raise AssertionError(
                f'Got type {type(self.asset)} for a LiquidityPool Asset. '
                f'This should never happen.',
            )

        return {
            'asset': serialized_asset,
            'total_amount': self.total_amount,
            'user_balance': self.user_balance.serialize(),
            'usd_price': self.usd_price,
        }


@dataclass(init=True, repr=True)
class LiquidityPool:
    address: ChecksumEthAddress
    assets: List[LiquidityPoolAsset]
    total_supply: Optional[FVal]
    user_balance: Balance

    def serialize(self) -> Dict[str, Any]:
        return {
            'address': self.address,
            'assets': [asset.serialize() for asset in self.assets],
            'total_supply': self.total_supply,
            'user_balance': self.user_balance.serialize(),
        }


AddressBalances = Dict[ChecksumEthAddress, List[LiquidityPool]]
DDAddressBalances = DefaultDict[ChecksumEthAddress, List[LiquidityPool]]
AssetPrice = Dict[ChecksumEthAddress, Price]


class ProtocolBalance(NamedTuple):
    address_balances: AddressBalances
    known_assets: Set[EthereumToken]
    unknown_assets: Set[UnknownEthereumToken]


# Get History

AddressTrades = Dict[ChecksumEthAddress, List[AMMTrade]]
