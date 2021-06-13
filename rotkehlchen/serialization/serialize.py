from typing import Any, Dict, List, Union

from hexbytes import HexBytes
from web3.datastructures import AttributeDict

from rotkehlchen.accounting.ledger_actions import LedgerActionType
from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.balances.manual import ManuallyTrackedBalanceWithValue
from rotkehlchen.chain.bitcoin.xpub import XpubData
from rotkehlchen.chain.ethereum.defi.structures import (
    DefiBalance,
    DefiProtocol,
    DefiProtocolBalances,
)
from rotkehlchen.chain.ethereum.modules.aave.aave import (
    AaveBalances,
    AaveBorrowingBalance,
    AaveHistory,
    AaveLendingBalance,
)
from rotkehlchen.chain.ethereum.modules.adex import ADXStakingHistory
from rotkehlchen.chain.ethereum.modules.balancer import (
    BalancerBPTEventPoolToken,
    BalancerEvent,
    BalancerPoolBalance,
    BalancerPoolEventsBalance,
    BalancerPoolTokenBalance,
)
from rotkehlchen.chain.ethereum.modules.compound import CompoundBalance, CompoundEvent
from rotkehlchen.chain.ethereum.modules.makerdao.dsr import DSRAccountReport, DSRCurrentBalances
from rotkehlchen.chain.ethereum.modules.makerdao.vaults import (
    MakerdaoVault,
    MakerdaoVaultDetails,
    VaultEvent,
    VaultEventType,
)
from rotkehlchen.chain.ethereum.modules.uniswap import (
    UniswapPool,
    UniswapPoolAsset,
    UniswapPoolEventsBalance,
)
from rotkehlchen.chain.ethereum.modules.yearn.vaults import (
    YearnVaultBalance,
    YearnVaultEvent,
    YearnVaultHistory,
)
from rotkehlchen.chain.ethereum.structures import AaveEvent
from rotkehlchen.chain.ethereum.trades import AMMTrade
from rotkehlchen.chain.ethereum.typing import Eth2Deposit
from rotkehlchen.db.settings import DBSettings
from rotkehlchen.db.utils import DBAssetBalance, LocationData, SingleDBAssetBalance
from rotkehlchen.exchanges.data_structures import Trade
from rotkehlchen.exchanges.kraken import KrakenAccountType
from rotkehlchen.fval import FVal
from rotkehlchen.history.typing import HistoricalPriceOracle
from rotkehlchen.inquirer import CurrentPriceOracle
from rotkehlchen.typing import (
    AssetMovementCategory,
    BlockchainAccountData,
    EthereumTransaction,
    Location,
    TradeType,
)
from rotkehlchen.utils.version_check import VersionCheckResult


def _process_entry(entry: Any) -> Union[str, List[Any], Dict[str, Any], Any]:
    if isinstance(entry, FVal):
        return str(entry)
    if isinstance(entry, list):
        new_list = []
        for new_entry in entry:
            new_list.append(_process_entry(new_entry))
        return new_list
    if isinstance(entry, (dict, AttributeDict)):
        new_dict = {}
        for k, v in entry.items():
            if isinstance(k, Asset):
                k = k.identifier
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
            'amount': entry.amount,
            'usd_value': entry.usd_value,
        }
    if isinstance(entry, DBAssetBalance):
        return {
            'time': entry.time,
            'category': str(entry.category),
            'asset': entry.asset.identifier,
            'amount': entry.amount,
            'usd_value': entry.usd_value,
        }
    if isinstance(entry, (
            DefiProtocol,
            MakerdaoVault,
            XpubData,
    )):
        return entry.serialize()
    if isinstance(entry, (
            Trade,
            EthereumTransaction,
            MakerdaoVault,
            DSRAccountReport,
            Balance,
            AaveLendingBalance,
            AaveBorrowingBalance,
            CompoundBalance,
            YearnVaultEvent,
            YearnVaultBalance,
            AaveEvent,
            UniswapPool,
            UniswapPoolAsset,
            AMMTrade,
            UniswapPoolEventsBalance,
            ADXStakingHistory,
            BalancerBPTEventPoolToken,
            BalancerEvent,
            BalancerPoolEventsBalance,
            BalancerPoolBalance,
            BalancerPoolTokenBalance,
    )):
        return process_result(entry.serialize())
    if isinstance(entry, (
            DBSettings,
            CompoundEvent,
            VersionCheckResult,
            DBSettings,
            DSRCurrentBalances,
            ManuallyTrackedBalanceWithValue,
            VaultEvent,
            MakerdaoVaultDetails,
            AaveBalances,
            AaveHistory,
            DefiBalance,
            DefiProtocolBalances,
            YearnVaultHistory,
            BlockchainAccountData,
            Eth2Deposit,
    )):
        return process_result(entry._asdict())
    if isinstance(entry, tuple):
        raise ValueError('Query results should not contain plain tuples')
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
            LedgerActionType,
    )):
        return str(entry)

    # else
    return entry


def process_result(result: Any) -> Dict[Any, Any]:
    """Before sending out a result dictionary via the server we are serializing it.
    Turning:

        - all Decimals to strings so that the serialization to float/big number
          is handled by the client application and we lose nothing in the transfer

        - if a dictionary has an Asset for a key use its identifier as the key value
        - all NamedTuples and Dataclasses must be serialized into dicts
        - all enums and more
    """
    processed_result = _process_entry(result)
    assert isinstance(processed_result, (Dict, AttributeDict))  # pylint: disable=isinstance-second-argument-not-valid-type  # noqa: E501
    return processed_result  # type: ignore


def process_result_list(result: List[Any]) -> List[Any]:
    """Just like process_result but for lists"""
    processed_result = _process_entry(result)
    assert isinstance(processed_result, List)  # pylint: disable=isinstance-second-argument-not-valid-type  # noqa: E501
    return processed_result
