from typing import Dict, NamedTuple

from rotkehlchen.fval import FVal
from rotkehlchen.utils.misc import from_gwei


class ValidatorBalance(NamedTuple):
    epoch: int
    balance: int  # in gwei
    effective_balance: int  # in wei


def _serialize_gwei_with_price(value: int, eth_usd_price: FVal) -> Dict[str, str]:
    normalized_value = from_gwei(value)
    return {
        'amount': str(normalized_value),
        'usd_value': str(normalized_value * eth_usd_price),
    }


class ValidatorPerformance(NamedTuple):
    balance: int  # in gwei
    performance_1d: int  # in gwei
    performance_1w: int  # in gwei
    performance_1m: int  # in gwei
    performance_1y: int  # in gwei

    def serialize(self, eth_usd_price: FVal) -> Dict[str, Dict[str, str]]:
        return {
            'balance': _serialize_gwei_with_price(self.balance, eth_usd_price),
            'performance_1d': _serialize_gwei_with_price(self.performance_1d, eth_usd_price),
            'performance_1w': _serialize_gwei_with_price(self.performance_1w, eth_usd_price),
            'performance_1m': _serialize_gwei_with_price(self.performance_1m, eth_usd_price),
            'performance_1y': _serialize_gwei_with_price(self.performance_1y, eth_usd_price),
        }


DEPOSITING_VALIDATOR_PERFORMANCE = ValidatorPerformance(
    balance=32000000000,
    performance_1d=0,
    performance_1w=0,
    performance_1m=0,
    performance_1y=0,
)


class ValidatorID(NamedTuple):
    # not using index due to : https://github.com/python/mypy/issues/9043
    validator_index: int
    public_key: str
