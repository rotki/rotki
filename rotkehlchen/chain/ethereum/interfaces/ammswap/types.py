import logging
from dataclasses import dataclass
from typing import Any

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, Price

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


# Get balances
@dataclass(init=True, repr=True)
class LiquidityPoolAsset:
    token: EvmToken
    total_amount: FVal | None
    user_balance: Balance

    def serialize(self) -> dict[str, Any]:
        return {
            'asset': self.token.serialize(),
            'total_amount': self.total_amount,
            'user_balance': self.user_balance.serialize(),
        }


@dataclass(init=True, repr=True)
class LiquidityPool:
    address: ChecksumEvmAddress
    assets: list[LiquidityPoolAsset]
    total_supply: FVal | None
    user_balance: Balance

    def serialize(self) -> dict[str, Any]:
        return {
            'address': self.address,
            'assets': [asset.serialize() for asset in self.assets],
            'total_supply': self.total_supply,
            'user_balance': self.user_balance.serialize(),
        }


AddressToLPBalances = dict[ChecksumEvmAddress, list[LiquidityPool]]
AssetToPrice = dict[ChecksumEvmAddress, Price]
