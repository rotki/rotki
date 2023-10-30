from typing import Any, Union

from hexbytes import HexBytes
from web3.datastructures import AttributeDict

from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.accounting.structures.balance import AssetBalance, Balance, BalanceType
from rotkehlchen.accounting.structures.base import HistoryBaseEntryType, StakingEvent
from rotkehlchen.accounting.structures.evm_event import EvmProduct
from rotkehlchen.accounting.structures.types import (
    EventCategory,
    EventCategoryDetails,
    EventDirection,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.assets.asset import Asset
from rotkehlchen.balances.manual import ManuallyTrackedBalanceWithValue
from rotkehlchen.chain.accounts import BlockchainAccountData, SingleBlockchainAccountData
from rotkehlchen.chain.bitcoin.xpub import XpubData
from rotkehlchen.chain.ethereum.defi.structures import (
    DefiBalance,
    DefiProtocol,
    DefiProtocolBalances,
)
from rotkehlchen.chain.ethereum.interfaces.ammswap.types import (
    LiquidityPool,
    LiquidityPoolAsset,
    LiquidityPoolEventsBalance,
)
from rotkehlchen.chain.ethereum.modules.aave.aave import (
    AaveBalances,
    AaveBorrowingBalance,
    AaveLendingBalance,
)
from rotkehlchen.chain.ethereum.modules.aave.common import AaveStats
from rotkehlchen.chain.ethereum.modules.balancer import (
    BalancerBPTEventPoolToken,
    BalancerEvent,
    BalancerPoolBalance,
    BalancerPoolEventsBalance,
    BalancerPoolTokenBalance,
)
from rotkehlchen.chain.ethereum.modules.compound.compound import CompoundBalance
from rotkehlchen.chain.ethereum.modules.liquity.trove import Trove
from rotkehlchen.chain.ethereum.modules.makerdao.dsr import DSRAccountReport, DSRCurrentBalances
from rotkehlchen.chain.ethereum.modules.makerdao.vaults import (
    MakerdaoVault,
    MakerdaoVaultDetails,
    VaultEvent,
    VaultEventType,
)
from rotkehlchen.chain.ethereum.modules.nft.structures import NFTResult
from rotkehlchen.chain.ethereum.modules.pickle_finance.main import DillBalance
from rotkehlchen.chain.ethereum.modules.yearn.vaults import (
    YearnVaultBalance,
    YearnVaultEvent,
    YearnVaultHistory,
)
from rotkehlchen.chain.evm.accounting.structures import TxAccountingTreatment
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.types import NodeName, WeightedNode
from rotkehlchen.chain.optimism.types import OptimismTransaction
from rotkehlchen.db.settings import DBSettings
from rotkehlchen.db.utils import DBAssetBalance, LocationData, SingleDBAssetBalance
from rotkehlchen.exchanges.data_structures import Trade
from rotkehlchen.exchanges.kraken import KrakenAccountType
from rotkehlchen.fval import FVal
from rotkehlchen.history.types import HistoricalPriceOracle
from rotkehlchen.inquirer import CurrentPriceOracle
from rotkehlchen.types import (
    AddressbookEntry,
    AssetMovementCategory,
    ChainID,
    CostBasisMethod,
    EvmTokenKind,
    EvmTransaction,
    ExchangeLocationID,
    Location,
    LocationDetails,
    SupportedBlockchain,
    TradeType,
)
from rotkehlchen.utils.version_check import VersionCheckResult


def _process_entry(entry: Any) -> Union[str, list[Any], dict[str, Any], Any]:
    if isinstance(entry, FVal):
        return str(entry)
    if isinstance(entry, list):
        return [_process_entry(x) for x in entry]

    if isinstance(entry, (dict, AttributeDict)):
        new_dict = {}
        for k, v in entry.items():
            if isinstance(k, Asset) is True:
                k = k.identifier  # noqa: PLW2901
            elif isinstance(k, (HistoryEventType, HistoryEventSubType, EventCategory, Location, AccountingEventType)) is True:  # noqa: E501
                k = _process_entry(k)  # noqa: PLW2901
            new_dict[k] = _process_entry(v)
        return new_dict
    if isinstance(entry, HexBytes):
        return entry.hex()
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
            AddressbookEntry,
            AssetBalance,
            DefiProtocol,
            MakerdaoVault,
            XpubData,
            StakingEvent,
            NodeName,
            NodeName,
            ChainID,
            SingleBlockchainAccountData,
            SupportedBlockchain,
            HistoryEventType,
            HistoryEventSubType,
            EventDirection,
            LocationDetails,
            EvmProduct,
            DBSettings,
            TxAccountingTreatment,
            EventCategoryDetails,
    )):
        return entry.serialize()
    if isinstance(entry, (
            Trade,
            EvmTransaction,
            OptimismTransaction,
            MakerdaoVault,
            DSRAccountReport,
            Balance,
            AaveLendingBalance,
            AaveBorrowingBalance,
            CompoundBalance,
            YearnVaultEvent,
            YearnVaultBalance,
            LiquidityPool,
            LiquidityPoolAsset,
            LiquidityPoolEventsBalance,
            BalancerBPTEventPoolToken,
            BalancerEvent,
            BalancerPoolEventsBalance,
            BalancerPoolBalance,
            BalancerPoolTokenBalance,
            ManuallyTrackedBalanceWithValue,
            Trove,
            DillBalance,
            NFTResult,
            ExchangeLocationID,
            WeightedNode,
    )):
        return process_result(entry.serialize())
    if isinstance(entry, (
            VersionCheckResult,
            DSRCurrentBalances,
            VaultEvent,
            MakerdaoVaultDetails,
            AaveBalances,
            DefiBalance,
            DefiProtocolBalances,
            YearnVaultHistory,
            BlockchainAccountData,
            CounterpartyDetails,
            AaveStats,
    )):
        return process_result(entry._asdict())
    if isinstance(entry, tuple):
        return list(entry)
    if isinstance(entry, Asset):
        return entry.identifier
    if isinstance(entry, (
            TradeType,
            Location,
            KrakenAccountType,
            Location,
            VaultEventType,
            AssetMovementCategory,
            CurrentPriceOracle,
            HistoricalPriceOracle,
            BalanceType,
            CostBasisMethod,
            EvmTokenKind,
            HistoryBaseEntryType,
            EventCategory,
            AccountingEventType,
    )):
        return str(entry)

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
    assert isinstance(processed_result, (dict, AttributeDict))  # pylint: disable=isinstance-second-argument-not-valid-type
    return processed_result  # type: ignore


def process_result_list(result: list[Any]) -> list[Any]:
    """Just like process_result but for lists"""
    processed_result = _process_entry(result)
    assert isinstance(processed_result, list)  # pylint: disable=isinstance-second-argument-not-valid-type
    return processed_result
