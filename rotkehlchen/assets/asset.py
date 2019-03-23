from typing import Any, Optional

from dataclasses import dataclass, field

from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.binance import WORLD_TO_BINANCE
from rotkehlchen.bittrex import WORLD_TO_BITTREX
from rotkehlchen.errors import UnknownAsset
from rotkehlchen.externalapis.cryptocompare import WORLD_TO_CRYPTOCOMPARE
from rotkehlchen.kraken import WORLD_TO_KRAKEN
from rotkehlchen.typing import AssetType, Timestamp


@dataclass(init=True, repr=True, eq=False, order=False, unsafe_hash=False, frozen=True)
class Asset():
    symbol: str
    name: str = field(init=False)
    active: bool = field(init=False)
    asset_type: AssetType = field(init=False)
    started: Timestamp = field(init=False)
    ended: Optional[Timestamp] = field(init=False)
    forked: Optional[str] = field(init=False)
    swapped_for: Optional[str] = field(init=False)

    def __post_init__(self):
        if not AssetResolver().is_symbol_canonical(self.symbol):
            raise UnknownAsset(self.symbol)
        data = AssetResolver().get_asset_data(self.symbol)

        # Ugly hack to set attributes of a frozen data class as post init
        # https://docs.python.org/3/library/dataclasses.html#frozen-instances
        object.__setattr__(self, 'name', data.name)
        object.__setattr__(self, 'active', data.active)
        object.__setattr__(self, 'asset_type', data.asset_type)
        object.__setattr__(self, 'started', data.started)
        object.__setattr__(self, 'ended', data.ended)
        object.__setattr__(self, 'forked', data.forked)
        object.__setattr__(self, 'swapped_for', data.swapped_for)

    def canonical(self) -> str:
        return self.symbol

    def __str__(self) -> str:
        return self.name

    def to_kraken(self) -> str:
        return WORLD_TO_KRAKEN[self.symbol]

    def to_bittrex(self) -> str:
        return WORLD_TO_BITTREX.get(self.symbol, self.symbol)

    def to_binance(self) -> str:
        return WORLD_TO_BINANCE.get(self.symbol, self.symbol)

    def to_cryptocompare(self) -> str:
        return WORLD_TO_CRYPTOCOMPARE.get(self.symbol, self.symbol)

    def __hash__(self):
        return hash(self.symbol)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Asset):
            return self.symbol == other.symbol
        elif isinstance(other, str):
            return self.symbol == other
        else:
            raise ValueError(f'Invalid comparison of asset with {type(other)}')

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)
