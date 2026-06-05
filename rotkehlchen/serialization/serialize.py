from collections import defaultdict
from collections.abc import Callable
from typing import Any

from hexbytes import HexBytes
from packaging.version import Version
from web3.datastructures import AttributeDict

from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.accounting.structures.balance import AssetBalance, Balance, BalanceType
from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.balances.manual import ManuallyTrackedBalanceWithValue
from rotkehlchen.chain.accounts import BlockchainAccountData, SingleBlockchainAccountData
from rotkehlchen.chain.bitcoin.xpub import XpubData
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.defi.structures import (
    DefiBalance,
    DefiProtocol,
    DefiProtocolBalances,
)
from rotkehlchen.chain.ethereum.interfaces.ammswap.types import (
    LiquidityPool,
    LiquidityPoolAsset,
)
from rotkehlchen.chain.ethereum.modules.compound.utils import CompoundBalance
from rotkehlchen.chain.ethereum.modules.liquity.trove import Trove
from rotkehlchen.chain.ethereum.modules.makerdao.dsr import DSRCurrentBalances
from rotkehlchen.chain.ethereum.modules.makerdao.vaults import (
    MakerdaoVault,
    VaultEvent,
    VaultEventType,
)
from rotkehlchen.chain.ethereum.modules.nft.structures import NFTResult
from rotkehlchen.chain.ethereum.modules.pickle_finance.main import DillBalance
from rotkehlchen.chain.evm.accounting.structures import TxAccountingTreatment
from rotkehlchen.chain.evm.types import NodeName, WeightedNode
from rotkehlchen.db.calendar import CalendarEntry, ReminderEntry
from rotkehlchen.db.settings import DBSettings
from rotkehlchen.db.utils import DBAssetBalance, LocationData, SingleDBAssetBalance
from rotkehlchen.exchanges.kraken import KrakenAccountType
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryBaseEntryType
from rotkehlchen.history.events.structures.types import (
    EventCategory,
    EventCategoryDetails,
    EventDirection,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.history.types import HistoricalPriceOracle
from rotkehlchen.inquirer import CurrentPriceOracle
from rotkehlchen.types import (
    AddressbookEntry,
    AddressbookEntryWithSource,
    ChainID,
    CostBasisMethod,
    ExchangeLocationID,
    Location,
    SupportedBlockchain,
    TokenKind,
)
from rotkehlchen.utils.version_check import VersionCheckResult


class PreSerializedList(list):  # noqa: FURB189  # we want a genuine list subclass (not UserList) so json.dumps serializes it natively and isinstance(x, list) holds; it adds no methods, just acts as a marker type
    """A list whose elements are already plain JSON primitives (produced by the
    objects' own ``serialize()``). ``process_result`` returns it untouched instead
    of recursively re-walking and rebuilding it, which for large payloads (e.g. a
    full page of history events) avoids a redundant deep copy of the whole list.

    It subclasses ``list`` so that even on a code path that does not pass through
    ``process_result`` ``json.dumps`` still serializes it correctly as a normal
    array rather than raising.
    """


def _process_dict(entry: dict) -> dict:
    new_dict = {}
    for k, v in entry.items():
        if isinstance(k, Asset) is True:
            k = k.identifier  # noqa: PLW2901
        elif isinstance(k, HistoryEventType | HistoryEventSubType | EventCategory | Location | AccountingEventType) is True:  # noqa: E501
            k = _process_entry(k)  # noqa: PLW2901
        new_dict[k] = _process_entry(v)
    return new_dict


# Map types to their handler functions
HANDLERS: dict[type, Callable[[Any], Any]] = {
    HexBytes: lambda x: x.to_0x_hex(),
    ChainID: lambda x: x.to_name(),
    LocationData: lambda entry: {
        'time': entry.time,
        'location': str(Location.deserialize_from_db(entry.location)),
        'usd_value': entry.usd_value,
    },
    SingleDBAssetBalance: lambda entry: {
        'time': entry.time,
        'category': str(entry.category),
        'amount': str(entry.amount),
        'usd_value': str(entry.usd_value),
    },
    DBAssetBalance: lambda entry: {
        'time': entry.time,
        'category': str(entry.category),
        'asset': entry.asset.identifier,
        'amount': str(entry.amount),
        'usd_value': str(entry.usd_value),
    },
}
HANDLERS.update(dict.fromkeys((list, tuple), lambda x: [_process_entry(z) for z in x]))
HANDLERS.update(dict.fromkeys((
    FVal,
    Location,
    KrakenAccountType,
    VaultEventType,
    CurrentPriceOracle,
    HistoricalPriceOracle,
    BalanceType,
    CostBasisMethod,
    TokenKind,
    HistoryBaseEntryType,
    EventCategory,
    AccountingEventType,
    Version,
    WSMessageType,
), str))
HANDLERS.update(dict.fromkeys((
    AddressbookEntry,
    AddressbookEntryWithSource,
    AssetBalance,
    DefiProtocol,
    MakerdaoVault,
    XpubData,
    NodeName,
    SingleBlockchainAccountData,
    SupportedBlockchain,
    HistoryEventType,
    HistoryEventSubType,
    EventDirection,
    DBSettings,
    TxAccountingTreatment,
    EventCategoryDetails,
    CalendarEntry,
    ReminderEntry,
    CounterpartyDetails,
), lambda x: x.serialize()))
HANDLERS.update(dict.fromkeys((dict, defaultdict, AttributeDict), _process_dict))
HANDLERS.update(dict.fromkeys((
    MakerdaoVault,
    Balance,
    CompoundBalance,
    LiquidityPool,
    LiquidityPoolAsset,
    ManuallyTrackedBalanceWithValue,
    Trove,
    DillBalance,
    NFTResult,
    ExchangeLocationID,
    WeightedNode,
), lambda x: _process_dict(x.serialize())))
HANDLERS.update(dict.fromkeys((
    VersionCheckResult,
    DSRCurrentBalances,
    VaultEvent,
    DefiBalance,
    DefiProtocolBalances,
    BlockchainAccountData,
), lambda x: _process_dict(x._asdict())))
# already JSON-ready: return as-is and skip the (expensive) recursive re-walk
HANDLERS[PreSerializedList] = lambda x: x


def _process_entry(entry: Any) -> str | (list[Any] | (dict[str, Any] | Any)):
    """Process an entry for the api. First checks for a handler for the entry's type, then uses
    isinstance for things with a common base class. Otherwise, returns the entry itself.
    """
    if (handler := HANDLERS.get(type(entry))) is not None:
        return handler(entry)
    if isinstance(entry, Asset):
        return entry.identifier

    # else
    return entry


def process_result(result: Any) -> dict[Any, Any]:
    """Before sending out a result dictionary via the server we are serializing it.
    Turning:

        - all Decimals to strings so that the serialization to float/big number
          is handled by the client application and we lose nothing in the transfer
        - if a dictionary has an Asset for a key use its identifier as the key value
        - all NamedTuples and Dataclasses must be serialized into dicts
        - all enums and more
    """
    processed_result = _process_entry(result)
    assert isinstance(processed_result, dict | AttributeDict)  # pylint: disable=isinstance-second-argument-not-valid-type
    return processed_result  # type: ignore


def process_result_list(result: list[Any]) -> list[Any]:
    """Just like process_result but for lists"""
    processed_result = _process_entry(result)
    assert isinstance(processed_result, list)  # pylint: disable=isinstance-second-argument-not-valid-type
    return processed_result
