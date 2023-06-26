import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, NamedTuple, Optional

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.constants.misc import ZERO, ZERO_PRICE
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, Price

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


# Get balances
@dataclass(init=True, repr=True)
class LiquidityPoolAsset:
    token: EvmToken
    total_amount: Optional[FVal]
    user_balance: Balance
    usd_price: Price = ZERO_PRICE

    def serialize(self) -> dict[str, Any]:
        return {
            'asset': self.token.serialize(),
            'total_amount': self.total_amount,
            'user_balance': self.user_balance.serialize(),
            'usd_price': self.usd_price,
        }


@dataclass(init=True, repr=True)
class LiquidityPool:
    address: ChecksumEvmAddress
    assets: list[LiquidityPoolAsset]
    total_supply: Optional[FVal]
    user_balance: Balance

    def serialize(self) -> dict[str, Any]:
        return {
            'address': self.address,
            'assets': [asset.serialize() for asset in self.assets],
            'total_supply': self.total_supply,
            'user_balance': self.user_balance.serialize(),
        }


AddressToLPBalances = dict[ChecksumEvmAddress, list[LiquidityPool]]
DDAddressToLPBalances = defaultdict[ChecksumEvmAddress, list[LiquidityPool]]
AssetToPrice = dict[ChecksumEvmAddress, Price]


class ProtocolBalance(NamedTuple):
    """Container structure for uniswap LP balances

    Known assets are all assets we have an oracle for
    Unknown assets are those we would have to try to query through uniswap directly
    """
    address_balances: AddressToLPBalances


class LiquidityPoolEventsBalance(NamedTuple):
    pool_address: ChecksumEvmAddress
    token0: EvmToken
    token1: EvmToken
    profit_loss0: FVal
    profit_loss1: FVal
    usd_profit_loss: FVal

    def serialize(self) -> dict[str, Any]:
        return {
            'pool_address': self.pool_address,
            'token0': self.token0.serialize(),
            'token1': self.token1.serialize(),
            'profit_loss0': str(self.profit_loss0),
            'profit_loss1': str(self.profit_loss1),
            'usd_profit_loss': str(self.usd_profit_loss),
        }


@dataclass(init=True, repr=True)
class AggregatedAmount:
    profit_loss0: FVal = ZERO
    profit_loss1: FVal = ZERO
    usd_profit_loss: FVal = ZERO


AddressEventsBalances = dict[ChecksumEvmAddress, list[LiquidityPoolEventsBalance]]
