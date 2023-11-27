from collections.abc import Callable, Iterator
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING, Any, Optional

from rotkehlchen.accounting.mixins.event import AccountingEventMixin, AccountingEventType
from rotkehlchen.assets.asset import Asset, CryptoAsset
from rotkehlchen.types import EVMTxHash, Timestamp

if TYPE_CHECKING:
    from rotkehlchen.accounting.pot import AccountingPot

    from .balance import AssetBalance, Balance
    from .types import ActionType


class DefiEventType(Enum):
    DSR_EVENT = 0
    MAKERDAO_VAULT_EVENT = auto()
    AAVE_EVENT = auto()
    YEARN_VAULTS_EVENT = auto()
    COMPOUND_EVENT = auto()
    ETH2_EVENT = auto()
    LIQUITY = auto()

    def __str__(self) -> str:
        if self == DefiEventType.DSR_EVENT:
            return 'MakerDAO DSR event'
        if self == DefiEventType.MAKERDAO_VAULT_EVENT:
            return 'MakerDAO vault event'
        if self == DefiEventType.AAVE_EVENT:
            return 'Aave event'
        if self == DefiEventType.YEARN_VAULTS_EVENT:
            return 'Yearn vault event'
        if self == DefiEventType.COMPOUND_EVENT:
            return 'Compound event'
        if self == DefiEventType.ETH2_EVENT:
            return 'ETH2 event'
        if self == DefiEventType.LIQUITY:
            return 'Liquity event'
        # else
        raise RuntimeError(f'Corrupt value {self} for DefiEventType -- Should never happen')


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DefiEvent(AccountingEventMixin):
    timestamp: Timestamp
    wrapped_event: Any
    event_type: DefiEventType
    got_asset: CryptoAsset | None
    got_balance: Optional['Balance']
    spent_asset: CryptoAsset | None
    spent_balance: Optional['Balance']
    pnl: list['AssetBalance'] | None
    # If this is true then both got and spent asset count in cost basis
    # So it will count as if you got asset at given amount and price of timestamp
    # and spent asset at given amount and price of timestamp
    count_spent_got_cost_basis: bool
    tx_hash: EVMTxHash | None = None

    def __str__(self) -> str:
        """Default string constructor"""
        result = str(self.wrapped_event)
        if self.tx_hash is not None:
            result += f' {self.tx_hash.hex()}'
        return result

    def to_string(self, timestamp_converter: Callable[[Timestamp], str]) -> str:
        """A customizable string constructor"""
        result = str(self)
        result += f' at {timestamp_converter(self.timestamp)}'
        return result

    # -- Methods of AccountingEventMixin

    def get_timestamp(self) -> Timestamp:
        return self.timestamp

    @staticmethod
    def get_accounting_event_type() -> AccountingEventType:
        """DefiEvent should be eventually deleted. Will not be called from accounting"""
        raise AssertionError('Should never be called')

    def get_identifier(self) -> str:
        return self.__str__()

    def get_assets(self) -> list[Asset]:
        assets: set[Asset] = set()
        if self.got_asset is not None:
            assets.add(self.got_asset)
        if self.spent_asset is not None:
            assets.add(self.spent_asset)
        if self.pnl is not None:
            for entry in self.pnl:
                assets.add(entry.asset)

        return list(assets)

    def process(
            self,
            accounting: 'AccountingPot',
            events_iterator: Iterator['AccountingEventMixin'],  # pylint: disable=unused-argument
    ) -> int:
        """DefiEvent should be eventually deleted. Will not be called from accounting"""
        raise AssertionError('Should never be called')

    def should_ignore(self, ignored_ids_mapping: dict['ActionType', set[str]]) -> bool:
        """DefiEvent should be eventually deleted. Will not be called from accounting"""
        raise AssertionError('Should never be called')

    def serialize(self) -> dict[str, Any]:
        """DefiEvent should be eventually deleted. Will not be called from accounting"""
        raise AssertionError('Should never be called')

    @classmethod
    def deserialize(cls, data: dict[str, Any]) -> 'DefiEvent':
        """DefiEvent should be eventually deleted. Will not be called from accounting"""
        raise AssertionError('Should never be called')
