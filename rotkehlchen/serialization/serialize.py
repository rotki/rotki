from typing import Any, Dict, List, Union

from hexbytes import HexBytes
from web3.datastructures import AttributeDict

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.balances.manual import ManuallyTrackedBalanceWithValue
from rotkehlchen.chain.bitcoin.xpub import XpubData
from rotkehlchen.chain.ethereum.aave import (
    AaveBalances,
    AaveBorrowingBalance,
    AaveHistory,
    AaveLendingBalance,
)
from rotkehlchen.chain.ethereum.balancer import (
    BalancerPool,
    BalancerPoolAsset,
    BalancerTrade,
    UnknownEthereumToken,
)
from rotkehlchen.chain.ethereum.compound import CompoundBalance, CompoundEvent
from rotkehlchen.chain.ethereum.makerdao.dsr import DSRAccountReport, DSRCurrentBalances
from rotkehlchen.chain.ethereum.makerdao.vaults import (
    MakerDAOVault,
    MakerDAOVaultDetails,
    VaultEvent,
    VaultEventType,
)
from rotkehlchen.chain.ethereum.structures import AaveEvent
from rotkehlchen.chain.ethereum.yearn.vaults import (
    YearnVaultBalance,
    YearnVaultEvent,
    YearnVaultHistory,
)
from rotkehlchen.chain.ethereum.zerion import DefiBalance, DefiProtocol, DefiProtocolBalances
from rotkehlchen.db.settings import DBSettings
from rotkehlchen.db.utils import AssetBalance, LocationData, SingleAssetBalance
from rotkehlchen.exchanges.data_structures import Trade
from rotkehlchen.exchanges.kraken import KrakenAccountType
from rotkehlchen.fval import FVal
from rotkehlchen.serialization.deserialize import deserialize_location_from_db
from rotkehlchen.typing import (
    AssetMovementCategory,
    BlockchainAccountData,
    EthereumTransaction,
    EthTokenInfo,
    Location,
    TradeType,
)
from rotkehlchen.utils.version_check import VersionCheckResult


def _process_entry(entry: Any) -> Union[str, List[Any], Dict[str, Any], Any]:
    if isinstance(entry, FVal):
        return str(entry)
    elif isinstance(entry, list):
        new_list = []
        for new_entry in entry:
            new_list.append(_process_entry(new_entry))
        return new_list
    elif isinstance(entry, (dict, AttributeDict)):
        new_dict = {}
        for k, v in entry.items():
            if isinstance(k, Asset):
                k = k.identifier
            new_dict[k] = _process_entry(v)
        return new_dict
    elif isinstance(entry, HexBytes):
        return entry.hex()
    elif isinstance(entry, LocationData):
        return {
            'time': entry.time,
            'location': str(deserialize_location_from_db(entry.location)),
            'usd_value': entry.usd_value,
        }
    elif isinstance(entry, SingleAssetBalance):
        return {'time': entry.time, 'amount': entry.amount, 'usd_value': entry.usd_value}
    elif isinstance(entry, AssetBalance):
        return {
            'time': entry.time,
            'asset': entry.asset.identifier,
            'amount': entry.amount,
            'usd_value': entry.usd_value,
        }
    elif isinstance(entry, (DefiProtocol, MakerDAOVault, XpubData)):
        return entry.serialize()
    elif isinstance(entry, (
            Trade,
            EthereumTransaction,
            MakerDAOVault,
            DSRAccountReport,
            Balance,
            AaveLendingBalance,
            AaveBorrowingBalance,
            CompoundBalance,
            YearnVaultEvent,
            YearnVaultBalance,
            AaveEvent,
            UnknownEthereumToken,
            BalancerPool,
            BalancerPoolAsset,
    )):
        return process_result(entry.serialize())
    elif isinstance(entry, (
            DBSettings,
            EthTokenInfo,
            CompoundEvent,
            VersionCheckResult,
            DBSettings,
            DSRCurrentBalances,
            ManuallyTrackedBalanceWithValue,
            VaultEvent,
            MakerDAOVaultDetails,
            AaveBalances,
            AaveHistory,
            DefiBalance,
            DefiProtocolBalances,
            YearnVaultHistory,
            BlockchainAccountData,
            BalancerTrade,
    )):
        return process_result(entry._asdict())
    elif isinstance(entry, tuple):
        raise ValueError('Query results should not contain plain tuples')
    elif isinstance(entry, Asset):
        return entry.identifier
    elif isinstance(entry, (
            TradeType,
            Location,
            KrakenAccountType,
            Location,
            VaultEventType,
            AssetMovementCategory,
    )):
        return str(entry)
    else:
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
    assert isinstance(processed_result, (Dict, AttributeDict))
    return processed_result  # type: ignore


def process_result_list(result: List[Any]) -> List[Any]:
    """Just like process_result but for lists"""
    processed_result = _process_entry(result)
    assert isinstance(processed_result, List)
    return processed_result
