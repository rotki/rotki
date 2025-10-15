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


def _process_entry(entry: Any) -> str | (list[Any] | (dict[str, Any] | Any)):
    if isinstance(entry, FVal):
        return str(entry)
    if isinstance(entry, list):
        return [_process_entry(x) for x in entry]

    if isinstance(entry, dict | AttributeDict):
        new_dict = {}
        for k, v in entry.items():
            if isinstance(k, Asset) is True:
                k = k.identifier  # noqa: PLW2901
            elif isinstance(k, HistoryEventType | HistoryEventSubType | EventCategory | Location | AccountingEventType) is True:  # noqa: E501
                k = _process_entry(k)  # noqa: PLW2901
            new_dict[k] = _process_entry(v)
        return new_dict
    if isinstance(entry, HexBytes):
        return entry.to_0x_hex()
    if isinstance(entry, LocationData):
        return {
            'time': entry.time,
            'location': str(Location.deserialize_from_db(entry.location)),
            'usd_value': entry.usd_value,
        }
    if isinstance(entry, SingleDBAssetBalance):
        return {
            'time': entry.time,
            'category': str(entry.category),
            'amount': str(entry.amount),
            'usd_value': str(entry.usd_value),
        }
    if isinstance(entry, DBAssetBalance):
        return {
            'time': entry.time,
            'category': str(entry.category),
            'asset': entry.asset.identifier,
            'amount': str(entry.amount),
            'usd_value': str(entry.usd_value),
        }
    if isinstance(entry, (
            AddressbookEntry |
            AddressbookEntryWithSource |
            AssetBalance |
            DefiProtocol |
            MakerdaoVault |
            XpubData |
            NodeName |
            NodeName |
            SingleBlockchainAccountData |
            SupportedBlockchain |
            HistoryEventType |
            HistoryEventSubType |
            EventDirection |
            DBSettings |
            TxAccountingTreatment |
            EventCategoryDetails |
            CalendarEntry |
            ReminderEntry |
            CounterpartyDetails
    )):
        return entry.serialize()
    if isinstance(entry, (
            MakerdaoVault |
            Balance |
            CompoundBalance |
            LiquidityPool |
            LiquidityPoolAsset |
            ManuallyTrackedBalanceWithValue |
            Trove |
            DillBalance |
            NFTResult |
            ExchangeLocationID |
            WeightedNode
    )):
        return process_result(entry.serialize())
    if isinstance(entry, (
            VersionCheckResult |
            DSRCurrentBalances |
            VaultEvent |
            DefiBalance |
            DefiProtocolBalances |
            BlockchainAccountData
    )):
        return process_result(entry._asdict())
    if isinstance(entry, tuple):
        return list(entry)
    if isinstance(entry, Asset):
        return entry.identifier
    if isinstance(entry, (
            Location |
            KrakenAccountType |
            Location |
            VaultEventType |
            CurrentPriceOracle |
            HistoricalPriceOracle |
            BalanceType |
            CostBasisMethod |
            TokenKind |
            HistoryBaseEntryType |
            EventCategory |
            AccountingEventType |
            Version |
            WSMessageType
    )):
        return str(entry)
    if isinstance(entry, ChainID):
        return entry.to_name()

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
